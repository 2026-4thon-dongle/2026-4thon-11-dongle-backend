"""피드 조회 규칙 (FEED-01, 02, 04). 문서 레포 spec/feed.md를 따른다."""

from django.db.models import Exists, OuterRef, Q, QuerySet

from apps.diaries.models import Diary
from apps.letters.models import Conversation
from apps.regions.models import Region
from apps.users.models import User

OWN_DIARY = "own_diary"
LETTERS_OFF = "letters_off"
RECIPIENT_PAUSED = "recipient_paused"
ALREADY_SENT = "already_sent"


def region_scope(region: Region) -> Q:
    """본가 지역에 속하는 일기 지역. 시·도(광역시·세종)면 그 안 전체, 시·군이면 그 시·군."""
    if region.parent_id is None:
        return Q(region=region) | Q(region__parent=region)
    return Q(region=region)


def hometown_scope(regions: list[Region]) -> Q:
    scope = Q(pk__in=[])
    for region in regions:
        scope |= region_scope(region)
    return scope


def _with_sent_flag(diaries: QuerySet[Diary], viewer: User) -> QuerySet[Diary]:
    return diaries.annotate(
        already_sent=Exists(Conversation.objects.filter(diary=OuterRef("pk"), guest=viewer))
    )


def _feed_base(viewer: User) -> QuerySet[Diary]:
    """viewer가 볼 수 있는 일기(내 일기 포함), 최신순. 내 일기는 can_reply가 false다."""
    diaries = (
        Diary.objects.visible_to(viewer)
        .select_related("author", "region__parent")
        .order_by("-created_at", "-id")
    )
    return _with_sent_flag(diaries, viewer)


def hometown_feed(viewer: User, region: Region | None = None) -> QuerySet[Diary]:
    regions = [region] if region is not None else list(viewer.hometowns.select_related("parent"))
    return _feed_base(viewer).filter(hometown_scope(regions))


def others_feed(viewer: User, sido: Region | None = None) -> QuerySet[Diary]:
    """본가 지역에 속하지 않고, 내 거주 구에서 쓰지 않은 일기(가정).

    내 일기는 거주 구에서 썼어도 넣는다(게시판에 내 글도 보이게, QA 요청).
    """
    hometowns = list(viewer.hometowns.select_related("parent"))
    feed = _feed_base(viewer).exclude(hometown_scope(hometowns))
    if viewer.residence_id is not None:
        feed = feed.exclude(Q(region_id=viewer.residence_id) & ~Q(author=viewer))
    if sido is not None:
        feed = feed.filter(region_scope(sido))
    return feed


def feed_diary(viewer: User, diary_id: int) -> Diary | None:
    """피드 일기 상세. 내 일기도 볼 수 있다."""
    diaries = Diary.objects.visible_to(viewer).filter(id=diary_id)
    return (
        _with_sent_flag(diaries, viewer)
        .select_related("author__residence__parent", "region__parent")
        .first()
    )


def reply_block_reason(diary: Diary, viewer: User) -> str | None:
    """첫 편지를 보낼 수 없는 이유. 보낼 수 있으면 None. diary는 already_sent 주석이 있어야 한다."""
    if diary.author_id == viewer.pk:
        return OWN_DIARY
    if not diary.accepts_letters:
        return LETTERS_OFF
    if diary.author.letter_paused:
        return RECIPIENT_PAUSED
    if getattr(diary, "already_sent", False):
        return ALREADY_SENT
    return None
