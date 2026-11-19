"""데모 모드(편지가 거리와 관계없이 1분 만에 도착) 켜짐 여부."""

from django.conf import settings

from .models import DemoModeSetting


def is_demo_mode() -> bool:
    """화면에서 바꾼 값이 있으면 그 값을, 없으면 환경변수 LETTER_DEMO_MODE를 쓴다."""
    row = DemoModeSetting.objects.first()
    return bool(settings.LETTER_DEMO_MODE) if row is None else row.enabled


def set_demo_mode(enabled: bool) -> None:
    DemoModeSetting.objects.update_or_create(pk=1, defaults={"enabled": enabled})
