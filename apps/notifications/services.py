from apps.users.models import User

from .models import Notification


def notify(
    user: User, type_: str, title: str, body: str = "", target_id: int | None = None
) -> Notification:
    """알림 센터에 알림을 남긴다. 편지 담당은 도착·왕복 완료 시점에 호출한다."""
    return Notification.objects.create(
        user=user, type=type_, title=title, body=body, target_id=target_id
    )
