"""우체통 조회 규칙 (MAIL-01~09). 문서 레포 api/mailbox.md의 대화 상태 정의를 따른다."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from django.db.models import Prefetch, Q, QuerySet

from apps.moderations.services import blocked_user_ids
from apps.users.models import User

from .models import CLOSE_AFTER, Conversation, Letter
from .services import PENPAL_ROUND_TRIPS

MY_TURN = "my_turn"
WAITING = "waiting"
IN_TRANSIT = "in_transit"
CLOSED = "closed"
STATUS_ORDER = {MY_TURN: 0, IN_TRANSIT: 1, WAITING: 2, CLOSED: 3}
PREVIEW_LENGTH = 40


def preview(text: str) -> str:
    return text if len(text) <= PREVIEW_LENGTH else text[:PREVIEW_LENGTH] + "…"


@dataclass
class ConversationView:
    """viewer가 보는 대화 한 줄."""

    conversation: Conversation
    letters: list[Letter]
    status: str
    closed_at: datetime | None

    @property
    def latest(self) -> Letter:
        return self.letters[-1]

    @property
    def round_trips(self) -> int:
        return len(self.letters) // 2


def conversation_status(
    conversation: Conversation, letters: list[Letter], viewer_id: int, now: datetime
) -> tuple[str, datetime | None]:
    """대화 상태와 마무리 시각. 넘김은 넘긴 사람(host)에게만 반영한다(상대에게 알리지 않음)."""
    latest = letters[-1]
    if viewer_id == conversation.host_id and conversation.passed_at is not None:
        return CLOSED, conversation.passed_at
    if not latest.has_arrived(now):
        return IN_TRANSIT, None
    if now - latest.arrives_at >= CLOSE_AFTER:
        return CLOSED, latest.arrives_at + CLOSE_AFTER
    if latest.recipient_id == viewer_id:
        return MY_TURN, None
    return WAITING, None


def _my_conversations(viewer: User) -> QuerySet[Conversation]:
    blocked = blocked_user_ids(viewer)
    return (
        Conversation.objects.filter(Q(host=viewer) | Q(guest=viewer))
        .exclude(host_id__in=blocked)
        .exclude(guest_id__in=blocked)
        .select_related("host__residence__parent", "guest__residence__parent", "diary__author")
        .prefetch_related(
            Prefetch(
                "letters",
                queryset=Letter.objects.select_related("stamp").order_by("sent_at", "id"),
            )
        )
    )


def conversation_views(viewer: User, now: datetime) -> list[ConversationView]:
    views = []
    for conversation in _my_conversations(viewer):
        letters = list(conversation.letters.all())
        if not letters:
            continue
        status, closed_at = conversation_status(conversation, letters, viewer.pk, now)
        views.append(ConversationView(conversation, letters, status, closed_at))
    return views


def in_conversation_tab(view: ConversationView, viewer_id: int) -> bool:
    """guest는 보낸 순간부터, host는 답장한 뒤부터 대화 중 탭에 나온다. 넘긴 대화는 빠진다."""
    conversation = view.conversation
    if viewer_id == conversation.guest_id:
        return True
    return conversation.passed_at is None and len(view.letters) >= 2


def conversation_tab(
    viewer: User, now: datetime, views: list[ConversationView] | None = None
) -> list[ConversationView]:
    """대화 중 탭. 이미 만든 conversation_views를 넘기면 다시 조회하지 않는다."""
    if views is None:
        views = conversation_views(viewer, now)
    views = [v for v in views if in_conversation_tab(v, viewer.pk)]
    views.sort(key=lambda v: v.latest.sent_at, reverse=True)
    views.sort(key=lambda v: STATUS_ORDER[v.status])
    return views


def round_trips_by_partner(views: list[ConversationView], viewer_id: int) -> dict[int, int]:
    """상대 id → 그 상대와의 왕복 수 합계. services.pair_round_trips와 같은 값을 쿼리 없이 센다."""
    trips: dict[int, int] = defaultdict(int)
    for view in views:
        trips[view.conversation.partner_of(viewer_id)] += view.round_trips
    return trips


def get_conversation_view(
    viewer: User, conversation_id: int, now: datetime
) -> ConversationView | None:
    conversation = _my_conversations(viewer).filter(id=conversation_id).first()
    if conversation is None:
        return None
    letters = list(conversation.letters.all())
    status, closed_at = conversation_status(conversation, letters, viewer.pk, now)
    return ConversationView(conversation, letters, status, closed_at)


def new_letters(viewer: User, now: datetime) -> QuerySet[Letter]:
    """새 편지 탭: 나에게 도착한 첫 편지 중 답장·넘기기 안 한 것."""
    return (
        Letter.objects.filter(
            recipient=viewer,
            is_first=True,
            arrives_at__lte=now,
            reply__isnull=True,
            conversation__passed_at__isnull=True,
        )
        .exclude(sender_id__in=blocked_user_ids(viewer))
        .select_related(
            "sender__residence__parent", "from_region__parent", "stamp", "conversation__diary"
        )
    )


def in_transit_letters(viewer: User, now: datetime) -> QuerySet[Letter]:
    blocked = blocked_user_ids(viewer)
    return (
        Letter.objects.filter(Q(sender=viewer) | Q(recipient=viewer), arrives_at__gt=now)
        .exclude(sender_id__in=blocked)
        .exclude(recipient_id__in=blocked)
        .select_related(
            "sender__residence__parent",
            "recipient__residence__parent",
            "from_region__parent",
            "to_region__parent",
            "stamp",
        )
        .order_by("arrives_at", "id")
    )


@dataclass
class ArchiveItem:
    kind: str
    view: ConversationView
    archived_at: datetime


def archive_items(viewer: User, now: datetime) -> list[ArchiveItem]:
    items = []
    for view in conversation_views(viewer, now):
        conversation = view.conversation
        if viewer.pk == conversation.host_id and conversation.passed_at is not None:
            items.append(ArchiveItem("passed_letter", view, conversation.passed_at))
        elif view.status == CLOSED and view.closed_at is not None:
            if in_conversation_tab(view, viewer.pk):
                items.append(ArchiveItem("closed_conversation", view, view.closed_at))
    items.sort(key=lambda item: item.archived_at, reverse=True)
    return items


@dataclass
class Penpal:
    partner: User
    conversation: Conversation
    letter_count: int
    last_letter_at: datetime


def penpals(viewer: User, now: datetime) -> list[Penpal]:
    """같은 상대와 왕복 3회 이상(가정). 대화가 여러 개면 합친다."""
    by_partner: dict[int, list[ConversationView]] = defaultdict(list)
    for view in conversation_views(viewer, now):
        by_partner[view.conversation.partner_of(viewer.pk)].append(view)

    result = []
    for views in by_partner.values():
        if sum(v.round_trips for v in views) < PENPAL_ROUND_TRIPS:
            continue
        recent = max(views, key=lambda v: v.latest.sent_at)
        conversation = recent.conversation
        partner = conversation.guest if viewer.pk == conversation.host_id else conversation.host
        result.append(
            Penpal(
                partner=partner,
                conversation=conversation,
                letter_count=sum(len(v.letters) for v in views),
                last_letter_at=recent.latest.sent_at,
            )
        )
    result.sort(key=lambda p: p.last_letter_at, reverse=True)
    return result


def can_reply(letter: Letter, viewer: User, now: datetime) -> bool:
    if letter.recipient_id != viewer.pk or not letter.has_arrived(now):
        return False
    if Letter.objects.filter(reply_to=letter).exists():
        return False
    letters = list(letter.conversation.letters.order_by("sent_at", "id"))
    if letters[-1].pk != letter.pk:
        return False
    status, _ = conversation_status(letter.conversation, letters, viewer.pk, now)
    return status != CLOSED


def can_pass(letter: Letter, viewer: User, now: datetime) -> bool:
    return (
        letter.recipient_id == viewer.pk
        and letter.is_first
        and letter.has_arrived(now)
        and letter.conversation.passed_at is None
        and not Letter.objects.filter(reply_to=letter).exists()
    )
