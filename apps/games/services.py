"""직접 배달 게임 서비스. 규칙 수치는 rules.py에 있다."""

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from django.db import transaction
from django.db.models import Count, F, Max, Q, Sum
from django.utils import timezone
from rest_framework import status

from apps.letters.models import Letter
from apps.moderations.services import blocked_user_ids
from apps.stamps.models import Stamp, UserStamp
from apps.stamps.rewards import Reward
from apps.stamps.services import grant_stamps, owned_count, rewards_unlocked_between
from apps.users.models import User
from config.exceptions import ApiError

from . import rules
from .course import PIECE, PUDDLE, build_course, count_kind
from .models import GameRun

REASON_MESSAGES = {
    "LETTER_ARRIVED": "이미 도착한 편지예요.",
    "ARRIVING_SOON": "곧 도착하는 편지라 배달할 수 없어요.",
    "PLAY_LIMIT": f"한 편지는 {rules.PLAYS_PER_LETTER}번까지 배달할 수 있어요.",
    "REDUCE_LIMIT": "이 편지는 더 빨리 보낼 수 없어요.",
}


def find_letter(user: User, letter_id: int) -> Letter:
    """내가 보냈거나 받는 편지. 차단 관계면 없는 것으로 본다."""
    blocked = blocked_user_ids(user)
    letter = (
        Letter.objects.filter(Q(sender=user) | Q(recipient=user), id=letter_id)
        .exclude(sender_id__in=blocked)
        .exclude(recipient_id__in=blocked)
        .select_related("from_region__parent", "to_region__parent")
        .first()
    )
    if letter is None:
        raise ApiError("NOT_FOUND", "편지를 찾을 수 없습니다.", status.HTTP_404_NOT_FOUND)
    return letter


def reduced_total(letter: Letter) -> int:
    """이 편지에서 지금까지 줄인 시간(보낸 사람·받는 사람 합산)."""
    total = GameRun.objects.filter(letter=letter).aggregate(total=Sum("reduced_seconds"))
    return int(total["total"] or 0)


def remaining_seconds(letter: Letter, now: datetime) -> int:
    return max(0, int((letter.arrives_at - now).total_seconds()))


@dataclass
class LetterGameState:
    playable: bool
    reason: str | None
    remaining_seconds: int
    plays_used: int
    plays_left: int
    reduced_seconds: int
    max_reduce_seconds: int
    reducible_seconds: int


def letter_state(
    user: User,
    letter: Letter,
    now: datetime,
    used: int | None = None,
    reduced: int | None = None,
) -> LetterGameState:
    """used(내 판수)·reduced(두 사람이 줄인 합계)를 미리 셌으면 넘겨 다시 조회하지 않는다."""
    remaining = remaining_seconds(letter, now)
    if used is None:
        used = GameRun.objects.filter(user=user, letter=letter).count()
    if reduced is None:
        reduced = reduced_total(letter)
    cap = rules.max_reduce_seconds(letter.duration_minutes)
    reducible = max(0, min(cap - reduced, remaining - rules.floor_seconds()))
    reason = None
    if remaining <= 0:
        reason = "LETTER_ARRIVED"
    elif remaining < rules.min_remaining_seconds():
        reason = "ARRIVING_SOON"
    elif used >= rules.PLAYS_PER_LETTER:
        reason = "PLAY_LIMIT"
    elif cap - reduced <= 0:
        reason = "REDUCE_LIMIT"
    return LetterGameState(
        playable=reason is None,
        reason=reason,
        remaining_seconds=remaining,
        plays_used=used,
        plays_left=max(0, rules.PLAYS_PER_LETTER - used),
        reduced_seconds=reduced,
        max_reduce_seconds=cap,
        reducible_seconds=reducible if reason is None else 0,
    )


def letter_states(user: User, letters: list[Letter], now: datetime) -> dict[int, LetterGameState]:
    """여러 편지의 게임 상태. 편지마다 조회하지 않고 판수·단축 합계를 두 번에 센다."""
    ids = [letter.id for letter in letters]
    used = dict(
        GameRun.objects.filter(user=user, letter_id__in=ids)
        .values("letter_id")
        .annotate(n=Count("id"))
        .values_list("letter_id", "n")
    )
    reduced = dict(
        GameRun.objects.filter(letter_id__in=ids)
        .values("letter_id")
        .annotate(total=Sum("reduced_seconds"))
        .values_list("letter_id", "total")
    )
    return {
        letter.id: letter_state(
            user,
            letter,
            now,
            used=used.get(letter.id, 0),
            reduced=int(reduced.get(letter.id) or 0),
        )
        for letter in letters
    }


def today_played(user: User, now: datetime) -> int:
    start = timezone.localtime(now).replace(hour=0, minute=0, second=0, microsecond=0)
    return GameRun.objects.filter(user=user, started_at__gte=start).count()


def start_run(user: User, letter_id: int | None, now: datetime | None = None) -> GameRun:
    now = now or timezone.now()
    if today_played(user, now) >= rules.DAILY_LIMIT:
        raise ApiError(
            "DAILY_LIMIT",
            f"오늘은 {rules.DAILY_LIMIT}번까지 배달할 수 있어요. 내일 다시 해 주세요.",
            status.HTTP_429_TOO_MANY_REQUESTS,
        )
    letter = None
    if letter_id is not None:
        letter = find_letter(user, letter_id)
        state = letter_state(user, letter, now)
        if state.reason is not None:
            raise ApiError(state.reason, REASON_MESSAGES[state.reason], status.HTTP_409_CONFLICT)
    seed = random.SystemRandom().randrange(1, 2**31 - 1)
    course = build_course(seed)
    with transaction.atomic():
        # 끝내지 않은 이전 판은 무효로 한다(동시에 여러 판을 열어 두지 못하게).
        GameRun.objects.filter(user=user, status=GameRun.Status.PLAYING).update(
            status=GameRun.Status.ABANDONED
        )
        return GameRun.objects.create(
            user=user,
            letter=letter,
            band=letter.band if letter is not None else "",
            seed=seed,
            course=course,
            piece_total=count_kind(course, PIECE),
            puddle_total=count_kind(course, PUDDLE),
            started_at=now,
            expires_at=now + timedelta(seconds=rules.RUN_TTL_SECONDS),
        )


def progress(user: User) -> dict[str, int]:
    """우표 조건에 쓰는 내 기록. 끝낸 판만 센다."""
    finished = GameRun.objects.filter(user=user, status=GameRun.Status.FINISHED)
    stats = finished.aggregate(
        plays=Count("id"),
        successes=Count("id", filter=Q(stars__gte=1)),
        three_stars=Count("id", filter=Q(stars=3)),
        far_three_stars=Count("id", filter=Q(stars=3, band=rules.FAR_BAND)),
        perfects=Count("id", filter=Q(hits=0, pieces=F("piece_total"), piece_total__gt=0)),
        best_stars=Max("stars"),
    )
    return {key: int(value or 0) for key, value in stats.items()}


def goals(user: User) -> list[dict[str, Any]]:
    stats = progress(user)
    codes = [goal.code for goal in rules.STAMP_GOALS]
    stamps = {stamp.code: stamp for stamp in Stamp.objects.filter(code__in=codes)}
    owned = set(
        UserStamp.objects.filter(user=user, stamp__code__in=codes).values_list(
            "stamp__code", flat=True
        )
    )
    return [
        {
            "stamp": stamps[goal.code],
            "condition": goal.condition,
            "target": goal.target,
            "progress": min(stats[goal.measure], goal.target),
            "owned": goal.code in owned,
        }
        for goal in rules.STAMP_GOALS
        if goal.code in stamps
    ]


def _earned_codes(user: User) -> list[str]:
    stats = progress(user)
    return [goal.code for goal in rules.STAMP_GOALS if stats[goal.measure] >= goal.target]


@dataclass
class FinishResult:
    run: GameRun
    letter: Letter | None
    granted_stamps: list[Stamp] = field(default_factory=list)
    unlocked_rewards: list[Reward] = field(default_factory=list)


def finish_run(
    user: User, run_id: int, pieces: int, hits: int, now: datetime | None = None
) -> FinishResult:
    now = now or timezone.now()
    result: FinishResult | None = None
    with transaction.atomic():
        run = GameRun.objects.select_for_update().filter(id=run_id, user=user).first()
        if run is None:
            raise ApiError("NOT_FOUND", "게임을 찾을 수 없습니다.", status.HTTP_404_NOT_FOUND)
        if run.status == GameRun.Status.FINISHED:
            raise ApiError("RUN_FINISHED", "이미 끝난 게임이에요.", status.HTTP_409_CONFLICT)
        if run.status != GameRun.Status.PLAYING:
            raise ApiError("RUN_EXPIRED", "끝난 게임이에요. 다시 시작해 주세요.", 409)
        if now > run.expires_at:
            # 무효 처리는 남기고 에러는 트랜잭션 밖에서 낸다(안에서 내면 되돌려진다).
            run.status = GameRun.Status.EXPIRED
            run.save(update_fields=["status"])
        else:
            if (now - run.started_at).total_seconds() < rules.MIN_RUN_SECONDS:
                raise ApiError("RUN_TOO_FAST", "게임이 아직 끝나지 않았어요.")
            if pieces > run.piece_total or hits > run.puddle_total:
                raise ApiError("VALIDATION_ERROR", "게임 결과가 코스와 맞지 않아요.")
            result = _finish(user, run, pieces, hits, now)
    if result is None:
        raise ApiError("RUN_EXPIRED", "시간이 지나 끝난 게임이에요. 다시 시작해 주세요.", 409)
    return result


def _finish(user: User, run: GameRun, pieces: int, hits: int, now: datetime) -> FinishResult:
    stars = rules.stars_for(pieces, run.piece_total, hits)
    letter = None
    reduced = 0
    if run.letter_id is not None:
        letter = Letter.objects.select_for_update().get(id=run.letter_id)
        if stars > 0:
            cap_left = rules.max_reduce_seconds(letter.duration_minutes) - reduced_total(letter)
            room = remaining_seconds(letter, now) - rules.floor_seconds()
            reduced = max(0, min(rules.reduce_seconds_for(stars), cap_left, room))
            if reduced:
                letter.arrives_at -= timedelta(seconds=reduced)
                letter.save(update_fields=["arrives_at"])
    run.pieces, run.hits, run.stars, run.reduced_seconds = pieces, hits, stars, reduced
    run.status, run.finished_at = GameRun.Status.FINISHED, now
    run.save()

    before = owned_count(user)
    granted = grant_stamps(user, _earned_codes(user))
    after = owned_count(user)
    if granted:
        run.granted_stamps = [stamp.code for stamp in granted]
        run.save(update_fields=["granted_stamps"])
    return FinishResult(run, letter, granted, rewards_unlocked_between(before, after))
