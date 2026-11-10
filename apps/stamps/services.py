from typing import Any

from .models import Stamp, UserStamp

FIRST_STEP = "first-step"
FIRST_DIARY = "first-diary"


def grant_stamp(user: Any, code: str) -> Stamp | None:
    """우표를 지급한다. 이미 받은 우표면 None을 돌려줘 획득 모달이 다시 뜨지 않게 한다."""
    stamp = Stamp.objects.get(code=code)
    _, created = UserStamp.objects.get_or_create(user=user, stamp=stamp)
    return stamp if created else None
