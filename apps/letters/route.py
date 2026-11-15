"""실시간 배송 지도(4-12)용 경로 (LETTER-10).

경유지는 출발·도착 시·도 대표 좌표를 잇는 직선 위의 점마다 가장 가까운 시·도를
지나는 순서대로 고른다(가정). 시·군 좌표가 없어서 경유지는 시·도 단위다.
"""

import math
from dataclasses import dataclass

from django.db.models import Q

from apps.diaries.models import Diary
from apps.regions.models import Region
from apps.users.models import User

from .delivery import SIDO_CENTERS, sido_name
from .mailbox import preview
from .models import Letter

MAP_THEMES = ["city", "sea", "mountain", "field", "river"]
SAMPLES = 40


def map_theme(letter: Letter) -> str:
    """편지마다 고정된 지도 테마."""
    return MAP_THEMES[letter.id % len(MAP_THEMES)]


def _nearest_sido(lat: float, lng: float) -> str:
    # 경도 1도는 위도 1도보다 짧다(한반도 위도에서 약 0.8배).
    scale = math.cos(math.radians(lat))
    return min(
        SIDO_CENTERS,
        key=lambda s: (SIDO_CENTERS[s][0] - lat) ** 2 + ((SIDO_CENTERS[s][1] - lng) * scale) ** 2,
    )


def path_sidos(origin: str, destination: str) -> list[tuple[str, float]]:
    """출발·도착 사이에 지나는 시·도와 그 지점의 진행률(0~1). 출발·도착 시·도는 뺀다."""
    if origin == destination:
        return []
    (lat1, lng1), (lat2, lng2) = SIDO_CENTERS[origin], SIDO_CENTERS[destination]
    seen = {origin, destination}
    result: list[tuple[str, float]] = []
    for i in range(1, SAMPLES):
        t = i / SAMPLES
        sido = _nearest_sido(lat1 + (lat2 - lat1) * t, lng1 + (lng2 - lng1) * t)
        if sido not in seen:
            seen.add(sido)
            result.append((sido, round(t, 2)))
    return result


@dataclass
class Waypoint:
    region: Region
    progress: float
    story: Diary | None


def _latest_story(viewer: User, sido: Region) -> Diary | None:
    return (
        Diary.objects.visible_to(viewer)
        .exclude(author=viewer)
        .filter(Q(region=sido) | Q(region__parent=sido))
        .order_by("-created_at", "-id")
        .first()
    )


def waypoints(letter: Letter, viewer: User) -> list[Waypoint]:
    stops = path_sidos(sido_name(letter.from_region), sido_name(letter.to_region))
    sidos = {
        r.short_name: r
        for r in Region.objects.filter(
            parent__isnull=True, short_name__in=[name for name, _ in stops]
        )
    }
    return [
        Waypoint(sidos[name], progress, _latest_story(viewer, sidos[name]))
        for name, progress in stops
        if name in sidos
    ]


def story_payload(diary: Diary | None) -> dict[str, object] | None:
    if diary is None:
        return None
    return {"diary_id": diary.id, "body_preview": preview(diary.body)}
