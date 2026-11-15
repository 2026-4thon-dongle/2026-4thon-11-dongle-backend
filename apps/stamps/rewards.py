"""꾸미기 아이템(편지지·글씨체·스티커)과 수집 보상 카탈로그.

DB에 두지 않는다. 보상이 열렸는지는 보유 우표 수로 계산한다 (STAMP-05, 문서 레포 api/stamps.md).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    type: str
    code: str
    name: str


@dataclass(frozen=True)
class Reward:
    code: str
    threshold: int
    name: str
    description: str
    items: tuple[Item, ...]


STATIONERIES = (
    Item("stationery", "basic", "기본"),
    Item("stationery", "lined", "줄노트"),
    Item("stationery", "grid", "체크"),
    Item("stationery", "cat-border", "고향이 테두리"),
    Item("stationery", "night-sky", "밤하늘"),
    Item("stationery", "gold-postcard", "금박 엽서"),
)

FONTS = (
    Item("font", "nanum-pen", "나눔손글씨 펜"),
    Item("font", "nanum-brush", "나눔손글씨 붓"),
    Item("font", "mini", "미니 손글씨"),
    Item("font", "delicious", "맛있는체"),
    Item("font", "meaningful", "의미있는 한글"),
    Item("font", "sparkle-star", "반짝반짝 별"),
    Item("font", "nineteen", "열아홉의 반짝임"),
    Item("font", "mom-love", "엄마사랑"),
    Item("font", "mom-letter", "엄마의 손편지"),
)

# Figma 4-5 고르기 줄의 5종 (2026-11-11 수정 기준)
STICKERS = (
    Item("sticker", "cat-wink", "고향이 윙크"),
    Item("sticker", "cat-sparkle", "고향이 반짝"),
    Item("sticker", "cat-shy", "고향이 부끄"),
    Item("sticker", "cat-basic", "고향이 기본"),
    Item("sticker", "cat-smile", "고향이 웃음"),
)

STAMP_COLLECTOR = "stamp-collector"

REWARDS = (
    Reward(
        "stickers-cat",
        3,
        "고향이 표정 스티커",
        "편지 서명 단계에서 스티커를 붙일 수 있어요",
        STICKERS,
    ),
    Reward(
        "stationery-night-sky",
        5,
        "편지지 「밤하늘」",
        "달과 별이 뜬 남색 편지지",
        (STATIONERIES[4],),
    ),
    Reward(
        "collector-and-font",
        10,
        "「우표 수집가」 우표 + 글씨체",
        "전설 우표와 글씨체 「엄마의 손편지」",
        (Item("stamp", STAMP_COLLECTOR, "우표 수집가"), FONTS[8]),
    ),
    Reward(
        "stationery-gold-postcard",
        15,
        "한정 편지지 「금박 엽서」",
        "금박 테두리 엽서 · 기간 한정",
        (STATIONERIES[5],),
    ),
)

REWARDS_BY_CODE = {reward.code: reward for reward in REWARDS}


def reward_for_item(type_: str, code: str) -> Reward | None:
    """이 아이템을 여는 보상. 처음부터 열린 아이템이면 None."""
    for reward in REWARDS:
        if any(item.type == type_ and item.code == code for item in reward.items):
            return reward
    return None
