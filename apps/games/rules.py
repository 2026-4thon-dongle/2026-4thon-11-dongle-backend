"""직접 배달 게임 규칙. 수치를 바꿀 때는 이 파일만 고친다 (문서 레포 spec/game.md).

시간 값은 모두 초 단위다. 데모 모드(LETTER_DEMO_MODE)에서는 편지가 1분 만에 도착하므로
분 단위 값을 초 단위로 바꿔 쓴다(10분 → 10초).
"""

from dataclasses import dataclass

from django.conf import settings

from apps.letters.delivery import FAR

RUN_SECONDS = 30
LANES = 3
# 결과는 시작 뒤 이 시간이 지나야 받는다(한 판 30초, 네트워크 여유 5초).
MIN_RUN_SECONDS = 25
# 시작 뒤 이 시간이 지나면 판이 무효가 된다.
RUN_TTL_SECONDS = 180

PLAYS_PER_LETTER = 3
DAILY_LIMIT = 10
MAX_REDUCE_RATIO = 0.5


@dataclass(frozen=True)
class StarRule:
    stars: int
    min_piece_ratio: float
    max_hits: int | None


# 위에서부터 먼저 맞는 규칙을 쓴다.
STAR_RULES = (
    StarRule(3, 0.85, 1),
    StarRule(2, 0.65, 2),
    StarRule(1, 0.40, None),
)


def time_unit() -> int:
    """규칙의 「분」이 실제로 몇 초인지. 데모 모드면 1초."""
    return 1 if settings.LETTER_DEMO_MODE else 60


def reduce_seconds_for(stars: int) -> int:
    """별 하나에 10분(데모 10초)."""
    return stars * 10 * time_unit()


def min_remaining_seconds() -> int:
    """시작하려면 도착까지 이만큼 남아야 한다. 10분(데모 10초)."""
    return 10 * time_unit()


def floor_seconds() -> int:
    """줄인 뒤에도 도착까지 이만큼은 남긴다. 1분(데모 1초)."""
    return 1 * time_unit()


def max_reduce_seconds(duration_minutes: int) -> int:
    """한 편지에서 줄일 수 있는 총시간(보낸 사람·받는 사람 합산)."""
    return int(duration_minutes * 60 * MAX_REDUCE_RATIO)


def stars_for(pieces: int, piece_total: int, hits: int) -> int:
    ratio = pieces / piece_total if piece_total else 0
    for rule in STAR_RULES:
        if ratio >= rule.min_piece_ratio and (rule.max_hits is None or hits <= rule.max_hits):
            return rule.stars
    return 0


@dataclass(frozen=True)
class StampGoal:
    code: str
    condition: str
    target: int
    # 진행 값을 고르는 키. progress 딕셔너리의 키와 같다.
    measure: str


# 기존 꾸미기 우표 8종만 쓴다(새 우표를 만들지 않는다).
STAMP_GOALS = (
    StampGoal("star-candy", "배달에 처음 성공하기 (별 1개 이상)", 1, "successes"),
    StampGoal("strawberry-cat", "처음으로 별 3개 받기", 1, "three_stars"),
    StampGoal("cloud-bread", "배달 성공 5번", 5, "successes"),
    StampGoal("tulip", "별 3개 3번", 3, "three_stars"),
    StampGoal("little-whale", "12시간 거리 편지를 별 3개로 배달하기", 1, "far_three_stars"),
    StampGoal(
        "rainbow-letter", "한 판에서 우표 조각을 모두 줍고 한 번도 안 부딪히기", 1, "perfects"
    ),
    StampGoal("tangerine", "배달 성공 10번", 10, "successes"),
    StampGoal("bungeoppang", "배달 성공 15번", 15, "successes"),
)

FAR_BAND = FAR
