"""편지 발송 규칙 (LETTER-06, 07, 09, MAIL-07). 문서 레포 api/letters.md의 에러 코드를 따른다."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from django.core.files.uploadedfile import UploadedFile
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status

from apps.diaries.models import Diary
from apps.moderations.services import blocked_user_ids
from apps.regions.models import Region
from apps.stamps.models import Stamp, UserStamp
from apps.stamps.rewards import Reward
from apps.stamps.services import (
    DAWN_LETTER,
    FIRST_LETTER,
    FIRST_ROUNDTRIP,
    HANDWRITING_MASTER,
    LONG_DELIVERY,
    PENPAL_FRIEND,
    STEADY_LETTER,
    grant_stamps,
    owned_count,
    rewards_unlocked_between,
)
from apps.users.models import User
from config.exceptions import ApiError

from .delivery import FAR, band_between, duration_minutes
from .models import CLOSE_AFTER, Conversation, Letter

PENPAL_ROUND_TRIPS = 3
HANDWRITING_MASTER_COUNT = 10
STEADY_WEEKS = 4


@dataclass
class Route:
    from_region: Region
    to_region: Region
    band: str
    duration_minutes: int

    def arrives_at(self, sent_at: datetime) -> datetime:
        return sent_at + timedelta(minutes=self.duration_minutes)


@dataclass
class SendResult:
    letter: Letter
    granted_stamps: list[Stamp] = field(default_factory=list)
    unlocked_rewards: list[Reward] = field(default_factory=list)


def _error(code: str, message: str, status_code: int) -> ApiError:
    return ApiError(code, message, status_code)


def route_between(sender: User, recipient: User, fallback: Region | None = None) -> Route:
    """보낸 사람 거주지 → 받는 사람 거주지. 받는 사람 거주지가 없으면 fallback(일기 지역)."""
    if sender.residence is None:
        raise ApiError("RESIDENCE_REQUIRED", "거주 지역을 먼저 설정해 주세요.")
    destination = recipient.residence or fallback
    if destination is None:
        raise ApiError("RESIDENCE_REQUIRED", "받는 사람의 지역을 알 수 없습니다.")
    band = band_between(sender.residence, destination)
    return Route(sender.residence, destination, band, duration_minutes(band))


def find_diary_for_letter(sender: User, diary_id: int) -> Diary:
    diary = (
        Diary.objects.visible_to(sender)
        .filter(id=diary_id)
        .select_related("author__residence__parent", "region__parent")
        .first()
    )
    if diary is None:
        raise _error("NOT_FOUND", "일기를 찾을 수 없습니다.", status.HTTP_404_NOT_FOUND)
    return diary


def find_received_letter(user: User, letter_id: int) -> Letter:
    letter = (
        Letter.objects.filter(id=letter_id, recipient=user)
        .select_related("conversation", "sender__residence__parent")
        .first()
    )
    if letter is None:
        raise _error("NOT_FOUND", "편지를 찾을 수 없습니다.", status.HTTP_404_NOT_FOUND)
    return letter


def is_closed(conversation: Conversation, latest: Letter, now: datetime) -> bool:
    """넘겼거나, 마지막 편지가 도착하고 7일 동안 답장이 없으면 마무리된 대화다."""
    if conversation.passed_at is not None:
        return True
    return latest.has_arrived(now) and now - latest.arrives_at >= CLOSE_AFTER


def check_first_letter(sender: User, diary: Diary) -> None:
    author = diary.author
    if author.pk == sender.pk:
        raise _error("OWN_DIARY", "내 일기에는 편지를 보낼 수 없습니다.", status.HTTP_403_FORBIDDEN)
    if not diary.accepts_letters:
        raise _error("LETTERS_OFF", "편지를 받지 않는 일기입니다.", status.HTTP_403_FORBIDDEN)
    if author.pk in blocked_user_ids(sender):
        raise _error("BLOCKED", "편지를 보낼 수 없는 사용자입니다.", status.HTTP_403_FORBIDDEN)
    if author.letter_paused:
        raise _error(
            "RECIPIENT_PAUSED", "지금은 편지를 잠시 쉬고 있어요.", status.HTTP_403_FORBIDDEN
        )
    if Conversation.objects.filter(diary=diary, guest=sender).exists():
        raise _error("ALREADY_SENT", "이 일기에는 이미 편지를 보냈어요.", status.HTTP_409_CONFLICT)


def check_reply(sender: User, letter: Letter, now: datetime) -> None:
    if not letter.has_arrived(now):
        raise _error("NOT_ARRIVED", "아직 도착하지 않은 편지입니다.", status.HTTP_409_CONFLICT)
    if Letter.objects.filter(reply_to=letter).exists():
        raise _error("ALREADY_REPLIED", "이미 답장한 편지입니다.", status.HTTP_409_CONFLICT)
    latest = letter.conversation.letters.order_by("-sent_at", "-id").first()
    if latest is None or latest.pk != letter.pk or is_closed(letter.conversation, letter, now):
        raise _error(
            "CONVERSATION_CLOSED", "마무리된 대화에는 답장할 수 없습니다.", status.HTTP_409_CONFLICT
        )
    if letter.sender_id in blocked_user_ids(sender):
        raise _error("BLOCKED", "편지를 보낼 수 없는 사용자입니다.", status.HTTP_403_FORBIDDEN)


def pair_round_trips(a_id: int, b_id: int) -> int:
    """두 사람이 주고받은 왕복 수. 대화마다 편지 수 // 2를 더한다."""
    conversations = Conversation.objects.filter(
        Q(host_id=a_id, guest_id=b_id) | Q(host_id=b_id, guest_id=a_id)
    )
    return sum(c.letters.count() // 2 for c in conversations)


def _sent_every_week(sender: User, now: datetime) -> bool:
    local = timezone.localtime(now)
    week_start = (local - timedelta(days=local.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    for weeks_ago in range(STEADY_WEEKS):
        start = week_start - timedelta(weeks=weeks_ago)
        end = start + timedelta(weeks=1)
        if not Letter.objects.filter(sender=sender, sent_at__gte=start, sent_at__lt=end).exists():
            return False
    return True


def _stamps_for_sender(sender: User, letter: Letter, now: datetime) -> list[str]:
    codes = [FIRST_LETTER]
    if timezone.localtime(now).hour < 5:
        codes.append(DAWN_LETTER)
    if letter.band == FAR:
        codes.append(LONG_DELIVERY)
    if (
        letter.signature
        and Letter.objects.filter(sender=sender)
        .exclude(signature="")
        .exclude(signature=None)
        .count()
        >= HANDWRITING_MASTER_COUNT
    ):
        codes.append(HANDWRITING_MASTER)
    if _sent_every_week(sender, now):
        codes.append(STEADY_LETTER)
    return codes


def send_letter(
    sender: User,
    *,
    diary: Diary | None,
    reply_to: Letter | None,
    body: str,
    stationery: str,
    font: str,
    signature: UploadedFile | None,
    stickers: list[dict[str, Any]],
    stamp: Stamp,
) -> SendResult:
    """편지를 만들고 우표를 준다. diary와 reply_to 중 하나만 받는다."""
    now = timezone.now()
    if reply_to is not None:
        check_reply(sender, reply_to, now)
        recipient = reply_to.sender
        conversation = reply_to.conversation
        route = route_between(sender, recipient)
    else:
        assert diary is not None
        check_first_letter(sender, diary)
        recipient = diary.author
        route = route_between(sender, recipient, fallback=diary.region)
        conversation = None

    before = owned_count(sender)
    try:
        with transaction.atomic():
            if conversation is None:
                conversation = Conversation.objects.create(
                    diary=diary, host=recipient, guest=sender
                )
            letter = Letter.objects.create(
                conversation=conversation,
                sender=sender,
                recipient=recipient,
                sender_nickname=sender.nickname,
                recipient_nickname=recipient.nickname,
                reply_to=reply_to,
                is_first=reply_to is None,
                from_region=route.from_region,
                to_region=route.to_region,
                band=route.band,
                duration_minutes=route.duration_minutes,
                body=body,
                stationery=stationery,
                font=font,
                signature=signature,
                stickers=stickers,
                stamp=stamp,
                sent_at=now,
                arrives_at=route.arrives_at(now),
            )
            granted = grant_stamps(sender, _stamps_for_sender(sender, letter, now))
            if reply_to is not None:
                granted += _grant_pair_stamps(sender, recipient)
    except IntegrityError as exc:
        # 같은 일기에 동시에 두 번 보내거나 같은 편지에 동시에 답장한 경우
        code = "ALREADY_REPLIED" if reply_to is not None else "ALREADY_SENT"
        raise _error(code, "이미 보낸 편지입니다.", status.HTTP_409_CONFLICT) from exc

    after = owned_count(sender)
    return SendResult(letter, granted, rewards_unlocked_between(before, after))


def _grant_pair_stamps(sender: User, recipient: User) -> list[Stamp]:
    """답장으로 왕복이 완성되면 두 사람 모두에게 첫 왕복·펜팔 친구 우표를 준다(가정)."""
    codes = [FIRST_ROUNDTRIP]
    if pair_round_trips(sender.pk, recipient.pk) >= PENPAL_ROUND_TRIPS:
        codes.append(PENPAL_FRIEND)
    grant_stamps(recipient, codes, granted_with=sender)
    return grant_stamps(sender, codes, granted_with=recipient)


def owns_stamp(user: User, stamp: Stamp) -> bool:
    return UserStamp.objects.filter(user=user, stamp=stamp).exists()
