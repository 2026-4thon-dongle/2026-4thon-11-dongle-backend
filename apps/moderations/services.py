"""안전 관련 공용 함수. 편지 담당도 발송·수신 검사에 그대로 쓴다."""

import re

from django.db.models import Q

from apps.users.models import User

from .models import Block

CONTACT_PATTERNS: dict[str, re.Pattern[str]] = {
    "phone": re.compile(
        r"(?<!\d)(?:\+?82[-.\s]?1[016789]|01[016789])[-.\s]?\d{3,4}[-.\s]?\d{4}(?!\d)"
    ),
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+"),
    "kakao": re.compile(
        r"open\.kakao\.com/\S+|(?:카카오톡|카톡|kakao(?:talk)?)\s*(?:아이디|id)?\s*[:：]?\s*[A-Za-z0-9._-]{3,}",
        re.IGNORECASE,
    ),
    "instagram": re.compile(
        r"instagram\.com/\S+|(?:인스타그램|인스타|instagram|insta)\s*(?:아이디|id)?\s*[:：]?\s*@?[A-Za-z0-9._]{3,}",
        re.IGNORECASE,
    ),
}


def detect_contact_patterns(text: str) -> list[str]:
    """본문에서 찾은 연락처 종류를 돌려준다. 막지 않고 경고만 한다 (SAFE-04)."""
    return [kind for kind, pattern in CONTACT_PATTERNS.items() if pattern.search(text)]


def blocked_user_ids(user: User) -> set[int]:
    """내가 차단했거나 나를 차단한 사용자 id."""
    pairs = Block.objects.filter(Q(blocker=user) | Q(blocked=user)).values_list(
        "blocker_id", "blocked_id"
    )
    return {other for pair in pairs for other in pair if other != user.pk}
