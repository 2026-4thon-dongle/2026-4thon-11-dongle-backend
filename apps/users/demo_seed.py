"""시연용 계정과 데이터 (관리 명령 seed_demo).

시연 계정은 메일 도메인 DEMO_DOMAIN으로만 구분한다. 시연 계정이 아닌 사용자의 데이터는
만들지도, 지우지도, 고치지도 않는다. 시연 계정과 다른 사용자 사이에 대화가 있으면
그 대화와 대화가 달린 일기는 남겨 둔다.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.diaries.models import Diary
from apps.games.models import GameRun
from apps.letters.delivery import DURATION_MINUTES
from apps.letters.models import Conversation, Draft, Letter
from apps.letters.notifications import notify_departed
from apps.letters.services import send_letter
from apps.moderations.models import Block, Report
from apps.notifications.models import Notification
from apps.regions.models import Region
from apps.stamps.models import RewardSeen, Stamp, UserStamp
from apps.stamps.services import grant_stamps

from .models import TermsAgreement, User

DEMO_DOMAIN = "dongle-demo.ac.kr"


class DemoSeedError(Exception):
    pass


@dataclass(frozen=True)
class DemoUser:
    key: str
    nickname: str
    hometown: tuple[str, str | None]
    residence: tuple[str, str]
    diaries: tuple[str, str]

    @property
    def email(self) -> str:
        return f"{self.key}@{DEMO_DOMAIN}"


USERS = (
    DemoUser(
        "demo1",
        "부산갈매기",
        ("부산", None),
        ("서울", "성북구"),
        (
            "성북천 따라 걷다가 붕어빵 트럭을 만났다. 부산 어묵 생각이 나서 하나 더 샀다.",
            "학교 앞 오르막길에 은행잎이 다 떨어졌다. 바다 없는 가을은 아직 어색하다.",
        ),
    ),
    DemoUser(
        "demo2",
        "서울토박이",
        ("서울", None),
        ("부산", "해운대구"),
        (
            "해운대 아침 바다는 생각보다 조용하다. 산책하는 강아지가 제일 많다.",
            "돼지국밥집 아주머니가 이제 내 얼굴을 알아보신다. 부추를 더 주셨다.",
        ),
    ),
    DemoUser(
        "demo3",
        "제주귤밭",
        ("제주", None),
        ("대전", "유성구"),
        (
            "유성온천 족욕장에 처음 가 봤다. 발만 담갔는데 온몸이 따뜻했다.",
            "성심당 줄이 길어서 포기하고 편의점 빵을 샀다. 다음엔 꼭 일찍 간다.",
        ),
    ),
    DemoUser(
        "demo4",
        "대구사과",
        ("대구", None),
        ("광주", "북구"),
        (
            "전남대 후문 골목에 고양이가 다섯 마리 산다. 오늘은 세 마리만 봤다.",
            "광주 사람들은 떡갈비를 정말 좋아한다. 나도 좋아하게 됐다.",
        ),
    ),
    DemoUser(
        "demo5",
        "강릉커피",
        ("강원", None),
        ("서울", "마포구"),
        (
            "망원 한강공원에서 해 지는 걸 봤다. 경포대 노을이랑은 색이 다르다.",
            "연남동 카페가 너무 많아서 고르다가 집에 왔다. 커피는 집에서 내렸다.",
        ),
    ),
)

DECORATION_STAMPS = ["tulip", "tangerine", "little-whale"]


@dataclass
class SeedResult:
    users: int = 0
    diaries: int = 0
    letters: int = 0
    kept_conversations: int = 0
    removed_users: int = 0
    kept_users: list[str] = field(default_factory=list)


def demo_users() -> QuerySet[User]:
    return User.objects.filter(email__iendswith=f"@{DEMO_DOMAIN}")


def _region(sido: str, name: str | None) -> Region:
    sido_region = Region.objects.get(short_name=sido, parent__isnull=True)
    if name is None:
        return sido_region
    return Region.objects.get(parent=sido_region, name=name)


def _mixed_conversations(ids: list[int]) -> QuerySet[Conversation]:
    """시연 계정과 시연 계정이 아닌 사용자 사이의 대화."""
    return Conversation.objects.filter(
        (Q(host_id__in=ids) & ~Q(guest_id__in=ids)) | (Q(guest_id__in=ids) & ~Q(host_id__in=ids))
    )


def _clear(ids: list[int], result: SeedResult) -> None:
    """시연 계정끼리의 데이터와 시연 계정이 남긴 기록(게임, 차단, 신고)을 지운다.

    다른 사용자가 시연 계정을 차단·신고한 기록은 그 사용자의 데이터라 남긴다.
    """
    mixed = _mixed_conversations(ids)
    result.kept_conversations = mixed.count()
    # 다른 사용자의 대화나 임시저장이 달린 일기는 지우면 그 사용자의 데이터가 함께 바뀌므로 남긴다
    kept_diary_ids = Diary.objects.filter(
        Q(id__in=mixed.exclude(diary__isnull=True).values("diary_id"))
        | Q(id__in=Draft.objects.exclude(owner_id__in=ids).values("diary_id"))
    ).values("id")
    Conversation.objects.filter(host_id__in=ids, guest_id__in=ids).delete()
    Diary.objects.filter(author_id__in=ids).exclude(id__in=kept_diary_ids).delete()
    Draft.objects.filter(owner_id__in=ids).delete()
    Notification.objects.filter(user_id__in=ids).delete()
    UserStamp.objects.filter(user_id__in=ids).delete()
    RewardSeen.objects.filter(user_id__in=ids).delete()
    GameRun.objects.filter(user_id__in=ids).delete()
    Block.objects.filter(blocker_id__in=ids).delete()
    Report.objects.filter(reporter_id__in=ids).delete()


def _check_nicknames() -> None:
    nicknames = [u.nickname for u in USERS]
    taken = (
        User.objects.filter(nickname__in=nicknames)
        .exclude(email__iendswith=f"@{DEMO_DOMAIN}")
        .values_list("nickname", flat=True)
    )
    if taken:
        raise DemoSeedError(
            f"시연 닉네임을 다른 사용자가 쓰고 있습니다: {', '.join(taken)}. "
            "아무것도 바꾸지 않았습니다."
        )


def _ensure_user(spec: DemoUser) -> User:
    user = User.objects.filter(email=spec.email).first()
    if user is None:
        user = User.objects.create_user(spec.email, spec.nickname)
    user.nickname = spec.nickname
    user.residence = _region(*spec.residence)
    # 설정 화면(7-1-1, 7-11)도 처음 상태로 되돌린다. 값은 User 모델의 기본값과 같다.
    user.letter_paused = False
    user.push_enabled = True
    user.daily_digest_enabled = False
    user.weekly_prompt_enabled = True
    user.letter_arrival_push_enabled = True
    user.letter_departure_push_enabled = True
    user.save()
    user.hometowns.set([_region(*spec.hometown)])
    TermsAgreement.objects.get_or_create(user=user, defaults={"version": settings.TERMS_VERSION})
    return user


def _write_diary(user: User, body: str, at: datetime) -> Diary:
    assert user.residence is not None
    diary = Diary.objects.create(author=user, region=user.residence, body=body)
    Diary.objects.filter(pk=diary.pk).update(created_at=at, updated_at=at)
    diary.refresh_from_db()
    return diary


def _send(
    sender: User,
    *,
    body: str,
    diary: Diary | None = None,
    reply_to: Letter | None = None,
    stationery: str = "basic",
    stickers: list[dict[str, float | str]] | None = None,
) -> Letter:
    return send_letter(
        sender,
        diary=diary,
        reply_to=reply_to,
        body=body,
        stationery=stationery,
        font="nanum-pen",
        signature=None,
        stickers=stickers or [],
        stamp=Stamp.objects.get(code="first-step"),
    ).letter


def _deliver(letter: Letter, sent_at: datetime, *, read: bool) -> None:
    """보낸 시각을 과거로 옮겨 도착한 편지로 만든다. 읽은 편지는 도착 알림을 만들지 않는다."""
    arrives_at = sent_at + timedelta(minutes=letter.duration_minutes)
    Letter.objects.filter(pk=letter.pk).update(
        sent_at=sent_at,
        arrives_at=arrives_at,
        read_at=arrives_at + timedelta(minutes=30) if read else None,
        arrival_notified_at=arrives_at if read else None,
    )
    letter.refresh_from_db()


def _in_transit(letter: Letter, now: datetime, *, arrive_in: int | None = None) -> None:
    """데모 모드와 관계없이 실제 구간 시간으로 배송 중에 둔다.

    arrive_in(분)을 주면 그만큼 뒤에 도착하고, 주지 않으면 구간 시간의 4분의 1이 지난 상태로 둔다.
    """
    minutes = DURATION_MINUTES[letter.band]
    if arrive_in is None:
        sent_at = now - timedelta(minutes=minutes // 4)
    else:
        minutes = max(minutes, arrive_in)
        sent_at = now + timedelta(minutes=arrive_in - minutes)
    Letter.objects.filter(pk=letter.pk).update(
        sent_at=sent_at, arrives_at=sent_at + timedelta(minutes=minutes), duration_minutes=minutes
    )
    letter.refresh_from_db()


def _create(users: dict[str, User], arrive_in: int, result: SeedResult) -> None:
    now = timezone.now()
    diaries: dict[str, list[Diary]] = {}
    for index, spec in enumerate(USERS):
        user = users[spec.key]
        diaries[spec.key] = [
            _write_diary(user, spec.diaries[0], now - timedelta(days=3, hours=index)),
            _write_diary(user, spec.diaries[1], now - timedelta(days=1, hours=index)),
        ]
        grant_stamps(user, ["first-step", "first-diary"])
    d1, d2, d3, d4, d5 = (users[k] for k in ("demo1", "demo2", "demo3", "demo4", "demo5"))

    # 시연3 ↔ 시연1: 첫 편지와 답장이 오간 뒤 시연3의 두 번째 편지가 배송 중
    first = _send(
        d3,
        diary=diaries["demo1"][0],
        body="저도 붕어빵 좋아해요! 대전은 튀김소보로가 유명한데 혹시 드셔 보셨어요?",
    )
    _deliver(first, now - timedelta(days=2, hours=20), read=True)
    reply = _send(
        d1,
        reply_to=first,
        body="아직 못 먹어 봤어요. 대전 가면 꼭 먹어 볼게요. 제주 귤은 요즘 제철이죠?",
    )
    _deliver(reply, now - timedelta(days=1, hours=6), read=True)
    second = _send(
        d3, reply_to=reply, body="네! 본가에서 귤 한 박스 왔어요. 주소만 알면 보내 드리고 싶네요."
    )
    _in_transit(second, now)

    # 시연2 → 시연1: 도착했지만 아직 안 읽음 (새 편지)
    unread = _send(
        d2,
        diary=diaries["demo1"][1],
        body=(
            "부산에서 서울 일기를 보니 반가워요. 저는 반대로 서울에서 부산으로 왔어요. "
            "바다 대신 뭐가 제일 좋으세요?"
        ),
    )
    _deliver(unread, now - timedelta(hours=14), read=False)

    # 시연1 꾸미기 우표: 우표가 5개를 넘어 스티커·「밤하늘」 보상이 열린다
    grant_stamps(d1, DECORATION_STAMPS)

    # 시연1 → 시연4: 배송 중 (배송 경로 화면용). 열린 편지지·스티커를 쓴다
    outgoing = _send(
        d1,
        diary=diaries["demo4"][0],
        body="고양이 다섯 마리 골목 저도 가 보고 싶어요. 이름도 지어 주셨어요?",
        stationery="night-sky",
        stickers=[{"code": "cat-wink", "x": 0.78, "y": 0.84, "rotation": -8, "scale": 0.18}],
    )
    _in_transit(outgoing, now)

    # 시연5 → 시연2: 도착해서 읽음
    read = _send(
        d5,
        diary=diaries["demo2"][0],
        body="해운대 아침 바다 부러워요. 서울 한강도 아침엔 꽤 조용해요.",
    )
    _deliver(read, now - timedelta(days=1, hours=2), read=True)

    # 시연1 ↔ 시연5: 왕복 3번이 끝난 펜팔 친구 (5-14·5-15).
    # 마지막은 시연5의 편지라 시연1이 답장할 차례다
    penpal_bodies = (
        (
            d1,
            "망원 노을 사진처럼 보여요. 저는 성북천 노을을 자주 봐요. 경포대 노을은 어떤 색이에요?",
        ),
        (d5, "경포대는 바다 위로 분홍빛이 길게 번져요. 성북천은 처음 들어 봐요. 어떤 곳이에요?"),
        (d1, "작은 개천인데 밤에 산책하기 좋아요. 커피 좋아하시면 근처 로스터리도 알려 드릴게요."),
        (d5, "커피라면 언제나 좋아요! 강릉 안목해변 커피거리도 꼭 한번 가 보세요."),
        (d1, "다음 방학에 꼭 가 볼게요. 부산 오시면 제가 어묵 투어 해 드릴게요."),
        (d5, "약속이에요. 이번 주말엔 연남동에서 핸드드립 클래스를 들어요. 다녀와서 또 쓸게요."),
    )
    previous: Letter | None = None
    for step, (sender, body) in enumerate(penpal_bodies):
        if previous is None:
            previous = _send(sender, diary=diaries["demo5"][0], body=body)
        else:
            previous = _send(sender, reply_to=previous, body=body)
        _deliver(previous, now - timedelta(hours=70 - step * 11), read=True)

    # 시연4 → 시연1: 읽고 넘긴 첫 편지. 보관함(넘긴 편지)에 보인다
    passed = _send(
        d4,
        diary=diaries["demo1"][1],
        body="광주도 은행잎이 다 떨어졌어요. 바다가 그리우면 목포 바다라도 보러 가세요.",
    )
    _deliver(passed, now - timedelta(hours=20), read=True)
    Conversation.objects.filter(pk=passed.conversation_id).update(
        passed_at=now - timedelta(hours=12)
    )

    # 시연1이 시연3 일기(성심당)에 쓰다 만 첫 편지. 임시저장(7-3)과 이어 쓰기(4-9)에 보인다
    Draft.objects.create(
        owner=d1,
        diary=diaries["demo3"][1],
        body="성심당 줄 저도 포기한 적 있어요! 평일 아침 일찍 가면",
        stationery="basic",
        font="nanum-pen",
    )

    # 시연4 → 시연1: 시연 중 arrive_in분 뒤 도착 (도착 알림을 보여 준다)
    soon = _send(
        d4,
        diary=diaries["demo1"][0],
        body="광주에도 붕어빵 트럭이 있어요. 팥보다 슈크림이 먼저 팔려요.",
    )
    _in_transit(soon, now, arrive_in=arrive_in)

    # 출발 알림은 보낼 때의 소요 시간으로 만들어졌다. 배송 중인 편지만 바뀐 시간으로 다시 만든다.
    ids = [u.pk for u in users.values()]
    Notification.objects.filter(user_id__in=ids, type=Notification.Type.LETTER_DEPARTED).delete()
    for letter in (second, outgoing, soon):
        notify_departed(letter)

    result.diaries = sum(len(v) for v in diaries.values())
    result.letters = Letter.objects.filter(sender__in=users.values()).count()


def seed(*, arrive_in: int = 3) -> SeedResult:
    """시연 데이터를 지우고 다시 만든다. 몇 번 실행해도 결과가 같다."""
    result = SeedResult()
    with transaction.atomic():
        _check_nicknames()
        existing = list(demo_users().values_list("id", flat=True))
        _clear(existing, result)
        users = {spec.key: _ensure_user(spec) for spec in USERS}
        result.users = len(users)
        _create(users, arrive_in, result)
    return result


def remove() -> SeedResult:
    """시연 데이터와 계정을 지운다. 다른 사용자와 대화가 있는 시연 계정은 남긴다."""
    result = SeedResult()
    with transaction.atomic():
        ids = list(demo_users().values_list("id", flat=True))
        _clear(ids, result)
        mixed = _mixed_conversations(ids)
        linked = set(mixed.values_list("host_id", flat=True)) | set(
            mixed.values_list("guest_id", flat=True)
        )
        removable = demo_users().exclude(id__in=linked)
        result.kept_users = list(demo_users().filter(id__in=linked).values_list("email", flat=True))
        result.removed_users, _ = removable.count(), removable.delete()
    return result
