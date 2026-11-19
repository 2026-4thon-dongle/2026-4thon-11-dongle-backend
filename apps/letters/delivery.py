"""두 지역 사이 배송 구간과 소요 시간 (LETTER-07).

구간은 시·도 단위로 판정한다. 거리는 시·도 대표 좌표 사이 직선거리다(가정).
"""

import math

from apps.regions.models import Region

from .demo_mode import is_demo_mode

SAME_SIDO = "same_sido"
ADJACENT = "adjacent"
NEAR = "near"
FAR = "far"

DURATION_MINUTES = {SAME_SIDO: 60, ADJACENT: 180, NEAR: 360, FAR: 720}
DEMO_DURATION_MINUTES = 1
NEAR_LIMIT_KM = 300

# 시·도 약칭 → 대표 좌표(위도, 경도). 광역시는 시청, 도는 대략 가운데.
SIDO_CENTERS: dict[str, tuple[float, float]] = {
    "서울": (37.5665, 126.9780),
    "부산": (35.1796, 129.0756),
    "대구": (35.8714, 128.6014),
    "인천": (37.4563, 126.7052),
    "광주": (35.1595, 126.8526),
    "대전": (36.3504, 127.3845),
    "울산": (35.5384, 129.3114),
    "세종": (36.4800, 127.2890),
    "경기": (37.4138, 127.5183),
    "강원": (37.8228, 128.1555),
    "충북": (36.8000, 127.7000),
    "충남": (36.5184, 126.8000),
    "전북": (35.7175, 127.1530),
    "전남": (34.8679, 126.9910),
    "경북": (36.4919, 128.8889),
    "경남": (35.4606, 128.2132),
    "제주": (33.4996, 126.5312),
}

# 육지로 맞닿은 시·도
_BORDERS = {
    "서울": ["경기", "인천"],
    "인천": ["경기"],
    "경기": ["강원", "충북", "충남"],
    "강원": ["충북", "경북"],
    "충북": ["경북", "전북", "충남", "대전", "세종"],
    "충남": ["세종", "대전", "전북"],
    "대전": ["세종"],
    "전북": ["경북", "경남", "전남"],
    "광주": ["전남"],
    "전남": ["경남"],
    "경북": ["대구", "울산", "경남"],
    "대구": ["경남"],
    "울산": ["경남", "부산"],
    "부산": ["경남"],
}
ADJACENT_PAIRS = {frozenset((a, b)) for a, others in _BORDERS.items() for b in others}

# 바다 건너라 거리와 관계없이 가장 긴 구간으로 보는 시·도
ISLANDS = {"제주"}


def sido_of(region: Region) -> Region:
    return region.parent if region.parent is not None else region


def sido_name(region: Region) -> str:
    return sido_of(region).short_name


def distance_km(a: str, b: str) -> float:
    (lat1, lng1), (lat2, lng2) = SIDO_CENTERS[a], SIDO_CENTERS[b]
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def band_between(origin: Region, destination: Region) -> str:
    a, b = sido_name(origin), sido_name(destination)
    if a == b:
        return SAME_SIDO
    if a in ISLANDS or b in ISLANDS:
        return FAR
    if frozenset((a, b)) in ADJACENT_PAIRS:
        return ADJACENT
    return NEAR if distance_km(a, b) < NEAR_LIMIT_KM else FAR


def duration_minutes(band: str) -> int:
    if is_demo_mode():
        return DEMO_DURATION_MINUTES
    return DURATION_MINUTES[band]
