"""게임 코스 만들기. 같은 시드면 항상 같은 코스가 나온다.

코스는 시간 순서의 물건 목록이다. `t`초에 `lane`번 레인(0~2)에서 고향이 앞을 지나간다.

- 한 줄(같은 t)에 물웅덩이는 최대 하나라서 항상 피할 수 있는 레인이 있다.
- 한 줄에 조각은 최대 하나라서, 모든 조각을 줍는 길이 항상 있다(무지개 편지 우표 조건).
  조각 두 개짜리 줄은 같은 레인에 조금 뒤(TRAIL_GAP초)로 이어 놓는다.
"""

import random
from typing import Any

from .rules import LANES, RUN_SECONDS

PIECE = "piece"
PUDDLE = "puddle"

START_AT = 2.0
END_BEFORE = 2.0
GAP_MIN = 0.9
GAP_MAX = 1.4
TRAIL_GAP = 0.35
MIN_PIECES = 12


def _item(kind: str, lane: int, t: float) -> dict[str, Any]:
    return {"kind": kind, "lane": lane, "t": round(t, 2)}


def build_course(seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    items: list[dict[str, Any]] = []
    # 조각이 없는 줄(물웅덩이만 있는 줄): 조각이 모자라면 채운다.
    bare_rows: list[tuple[float, int]] = []
    t = START_AT
    while t <= RUN_SECONDS - END_BEFORE:
        lanes = list(range(LANES))
        rng.shuffle(lanes)
        roll = rng.random()
        if roll < 0.30:
            items += [_item(PUDDLE, lanes[0], t), _item(PIECE, lanes[1], t)]
        elif roll < 0.45:
            items.append(_item(PUDDLE, lanes[0], t))
            bare_rows.append((t, lanes[1]))
        elif roll < 0.85:
            items.append(_item(PIECE, lanes[0], t))
        else:
            items += [_item(PIECE, lanes[0], t), _item(PIECE, lanes[0], t + TRAIL_GAP)]
        t += rng.uniform(GAP_MIN, GAP_MAX)
    pieces = count_kind(items, PIECE)
    for row_t, free_lane in bare_rows:
        if pieces >= MIN_PIECES:
            break
        items.append(_item(PIECE, free_lane, row_t))
        pieces += 1
    items.sort(key=lambda item: (item["t"], item["lane"]))
    return items


def count_kind(course: list[dict[str, Any]], kind: str) -> int:
    return sum(1 for item in course if item["kind"] == kind)
