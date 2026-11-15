"""편지 알림 (SET-02). 이동 대상은 문서 레포 api/notifications.md의 표를 따른다."""

from datetime import datetime

from django.db import transaction
from django.utils import timezone

from apps.moderations.services import blocked_user_ids
from apps.notifications.models import Notification
from apps.notifications.services import notify
from apps.users.models import User

from .models import Letter


def _duration_text(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes}분"
    return f"{minutes // 60}시간"


def notify_departed(letter: Letter) -> None:
    """나에게 오는 편지가 출발했다. 이동: 5-5 배송 중 (target=편지 id)."""
    notify(
        letter.recipient,
        Notification.Type.LETTER_DEPARTED,
        f"{letter.sender_nickname}님의 편지가 출발했어요",
        body=f"도착까지 약 {_duration_text(letter.duration_minutes)} 걸려요",
        target_id=letter.id,
    )


def _notify_arrived(letter: Letter) -> None:
    recipient = letter.recipient
    if letter.sender_id in blocked_user_ids(recipient):
        return
    notify(
        recipient,
        Notification.Type.LETTER_ARRIVED,
        f"{letter.sender_nickname}님의 편지가 도착했어요",
        target_id=letter.id,
    )
    # 첫 편지에 대한 답장이 도착하면 그 대화의 첫 왕복이 끝난다.
    if letter.reply_to is not None and letter.reply_to.is_first:
        notify(
            recipient,
            Notification.Type.ROUND_TRIP,
            f"첫 왕복 완료! {letter.sender_nickname}님과 우표를 주고받았어요",
            target_id=letter.conversation_id,
        )


def notify_arrived_letters(user: User | None = None, now: datetime | None = None) -> int:
    """도착했지만 알림을 아직 만들지 않은 편지의 알림을 만든다. 만든 편지 수를 돌려준다.

    명령이 1분마다 부르고, 스케줄러가 없을 때를 위해 알림 조회 때도 부른다.
    """
    now = now or timezone.now()
    letters = Letter.objects.filter(arrival_notified_at=None, arrives_at__lte=now)
    if user is not None:
        letters = letters.filter(recipient=user)
    count = 0
    for letter in letters.select_related("recipient", "reply_to").order_by("arrives_at", "id"):
        with transaction.atomic():
            # 다른 실행이 먼저 처리했으면 건너뛴다.
            claimed = Letter.objects.filter(id=letter.id, arrival_notified_at=None).update(
                arrival_notified_at=now
            )
            if claimed:
                _notify_arrived(letter)
                count += 1
    return count
