from datetime import datetime
from typing import Any

from .models import RewardSeen, Stamp, UserStamp
from .rewards import REWARDS, STAMP_COLLECTOR, Reward, reward_for_item

FIRST_STEP = "first-step"
FIRST_DIARY = "first-diary"
FIRST_LETTER = "first-letter"
FIRST_ROUNDTRIP = "first-roundtrip"
PENPAL_FRIEND = "penpal-friend"
DAWN_LETTER = "dawn-letter"
LONG_DELIVERY = "long-delivery"
HANDWRITING_MASTER = "handwriting-master"
STEADY_LETTER = "steady-letter"

COLLECTOR_THRESHOLD = 10


def grant_stamps(user: Any, codes: list[str], granted_with: Any = None) -> list[Stamp]:
    """우표를 지급하고 새로 받은 것만 돌려준다. 10개가 되면 「우표 수집가」를 함께 준다."""
    granted: list[Stamp] = []
    for code in codes:
        stamp = Stamp.objects.get(code=code)
        _, created = UserStamp.objects.get_or_create(
            user=user, stamp=stamp, defaults={"granted_with": granted_with}
        )
        if created:
            granted.append(stamp)
    if granted and owned_count(user) >= COLLECTOR_THRESHOLD:
        collector = Stamp.objects.get(code=STAMP_COLLECTOR)
        _, created = UserStamp.objects.get_or_create(user=user, stamp=collector)
        if created:
            granted.append(collector)
    return granted


def grant_stamp(user: Any, code: str) -> Stamp | None:
    """우표 하나를 지급한다. 이미 받은 우표면 None을 돌려줘 획득 모달이 다시 뜨지 않게 한다."""
    granted = grant_stamps(user, [code])
    return next((stamp for stamp in granted if stamp.code == code), None)


def owned_count(user: Any) -> int:
    return UserStamp.objects.filter(user=user).count()


def reward_unlocked_at(user: Any) -> dict[str, datetime]:
    """열린 보상 코드 → 열린 시각(그 개수째 우표를 받은 시각)."""
    times = list(
        UserStamp.objects.filter(user=user)
        .order_by("granted_at", "id")
        .values_list("granted_at", flat=True)
    )
    return {
        reward.code: times[reward.threshold - 1]
        for reward in REWARDS
        if len(times) >= reward.threshold
    }


def rewards_unlocked_between(before: int, after: int) -> list[Reward]:
    """우표 수가 before → after로 늘면서 새로 열린 보상."""
    return [reward for reward in REWARDS if before < reward.threshold <= after]


def next_reward(count: int) -> Reward | None:
    return next((reward for reward in REWARDS if count < reward.threshold), None)


def seen_reward_codes(user: Any) -> set[str]:
    return set(RewardSeen.objects.filter(user=user).values_list("code", flat=True))


def is_item_unlocked(type_: str, code: str, count: int) -> bool:
    """편지지·글씨체·스티커를 쓸 수 있는지. count는 보유 우표 수."""
    reward = reward_for_item(type_, code)
    return reward is None or count >= reward.threshold
