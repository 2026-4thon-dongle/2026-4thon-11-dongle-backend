from datetime import datetime
from typing import Any, cast

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.letters.mailbox import in_transit_letters
from apps.letters.models import Letter
from apps.stamps.serializers import StampSerializer
from apps.stamps.services import reward_unlocked_at, seen_reward_codes
from apps.stamps.views import reward_payload
from apps.users.models import User
from config.schema import error_response

from . import rules
from .serializers import (
    GameHomeSerializer,
    GameLetterSerializer,
    RunFinishSerializer,
    RunResultSerializer,
    RunSerializer,
    RunStartSerializer,
)
from .services import (
    LetterGameState,
    find_letter,
    finish_run,
    goals,
    letter_state,
    letter_states,
    progress,
    reduced_total,
    remaining_seconds,
    start_run,
    today_played,
)

DESCRIPTION_RULES = (
    "- 한 판은 30초, 레인 3개. 우표 조각을 줍고 물웅덩이를 피한다.\n"
    "- 별 3개: 조각 85% 이상·부딪힘 1회 이하 / 별 2개: 65% 이상·2회 이하 / 별 1개: 40% 이상.\n"
    "- 별 하나에 도착 시간 10분 단축(데모 모드는 10초). 한 편지에서 줄일 수 있는 총시간은 "
    "배송 시간의 50%(두 사람 합산). 한 사람이 한 편지로 3판, 하루 10판까지.\n"
    "- 보상은 기존 꾸미기 우표 8종이다(`goals`). 시간 값은 모두 초 단위."
)


def _viewer(request: Request) -> User:
    return cast(User, request.user)


def _letter_payload(
    letter: Letter, viewer: User, now: datetime, state: LetterGameState | None = None
) -> dict[str, Any]:
    sent = letter.sender_id == viewer.pk
    return {
        "id": letter.id,
        "direction": "sent" if sent else "incoming",
        "partner": {
            "id": letter.recipient_id if sent else letter.sender_id,
            "nickname": letter.recipient_nickname if sent else letter.sender_nickname,
        },
        "from_region": letter.from_region,
        "to_region": letter.to_region,
        "band": letter.band,
        "duration_minutes": letter.duration_minutes,
        "sent_at": letter.sent_at,
        "arrives_at": letter.arrives_at,
        "game": vars(state if state is not None else letter_state(viewer, letter, now)),
    }


def _rules_payload() -> dict[str, Any]:
    return {
        "run_seconds": rules.RUN_SECONDS,
        "lanes": rules.LANES,
        "plays_per_letter": rules.PLAYS_PER_LETTER,
        "daily_limit": rules.DAILY_LIMIT,
        "max_reduce_ratio": rules.MAX_REDUCE_RATIO,
        "min_remaining_seconds": rules.min_remaining_seconds(),
        "stars": [
            {
                "stars": rule.stars,
                "min_piece_ratio": rule.min_piece_ratio,
                "max_hits": rule.max_hits,
                "reduce_seconds": rules.reduce_seconds_for(rule.stars),
            }
            for rule in rules.STAR_RULES
        ],
    }


def _today(viewer: User, now: datetime) -> dict[str, int]:
    played = today_played(viewer, now)
    return {
        "played": played,
        "limit": rules.DAILY_LIMIT,
        "remaining": max(0, rules.DAILY_LIMIT - played),
    }


@extend_schema(tags=["배달 게임"])
class GameHomeView(APIView):
    @extend_schema(
        summary="게임 홈",
        description=(
            "직접 배달 게임(9-1)의 규칙, 오늘 남은 판수, 내 기록, 꾸미기 우표 목표, 게임할 수 "
            "있는 배송 중 편지 목록을 준다.\n\n" + DESCRIPTION_RULES
        ),
        responses={200: GameHomeSerializer},
    )
    def get(self, request: Request) -> Response:
        viewer, now = _viewer(request), timezone.now()
        letters = list(in_transit_letters(viewer, now))
        states = letter_states(viewer, letters, now)
        payload = {
            "rules": _rules_payload(),
            "today": _today(viewer, now),
            "progress": progress(viewer),
            "goals": goals(viewer),
            "letters": [
                _letter_payload(letter, viewer, now, states[letter.id]) for letter in letters
            ],
        }
        return Response(GameHomeSerializer(payload).data)


@extend_schema(tags=["배달 게임"])
class GameLetterView(APIView):
    @extend_schema(
        summary="편지의 게임 상태",
        description="배송 화면(4-11, 4-12, 5-5)에서 「직접 배달하기」를 보여 줄지 정할 때 쓴다.",
        responses={
            200: GameLetterSerializer,
            404: error_response("`NOT_FOUND`: 내가 보내거나 받는 편지가 아님, 차단 관계"),
        },
    )
    def get(self, request: Request, pk: int) -> Response:
        viewer, now = _viewer(request), timezone.now()
        letter = find_letter(viewer, pk)
        return Response(GameLetterSerializer(_letter_payload(letter, viewer, now)).data)


@extend_schema(tags=["배달 게임"])
class RunStartView(APIView):
    @extend_schema(
        summary="게임 시작",
        description=(
            "한 판을 시작하고 코스를 준다. `letter_id`가 없으면 연습이다(도착 시간을 줄이지 "
            "않고, 「먼 길」을 뺀 우표 조건에는 포함). 끝내지 않은 이전 판은 무효가 된다. "
            "결과는 시작 25초 뒤부터 3분 안에 보낸다.\n\n"
            "- 코스의 `t`초에 `lane` 레인의 물건이 고향이 앞을 지나간다. 한 줄에 물웅덩이와 "
            "조각은 각각 하나 이하라서 모든 조각을 줍고 모든 물웅덩이를 피하는 길이 있다."
        ),
        request=RunStartSerializer,
        responses={
            201: RunSerializer,
            404: error_response("`NOT_FOUND`: 내 편지가 아님, 차단 관계"),
            409: error_response(
                "`LETTER_ARRIVED`: 이미 도착 / `ARRIVING_SOON`: 10분(데모 10초) 안에 도착 / "
                "`PLAY_LIMIT`: 이 편지로 3판을 함 / `REDUCE_LIMIT`: 줄일 수 있는 시간을 다 씀"
            ),
            429: error_response("`DAILY_LIMIT`: 오늘 10판을 함"),
        },
    )
    def post(self, request: Request) -> Response:
        viewer, now = _viewer(request), timezone.now()
        serializer = RunStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        run = start_run(viewer, serializer.validated_data.get("letter_id"), now)
        reducible = 0
        if run.letter is not None:
            reducible = letter_state(viewer, run.letter, now).reducible_seconds
        payload = {
            "id": run.id,
            "letter_id": run.letter_id,
            "practice": run.letter_id is None,
            "seed": run.seed,
            "run_seconds": rules.RUN_SECONDS,
            "lanes": rules.LANES,
            "course": run.course,
            "piece_total": run.piece_total,
            "puddle_total": run.puddle_total,
            "started_at": run.started_at,
            "expires_at": run.expires_at,
            "reducible_seconds": reducible,
            "today_remaining": _today(viewer, now)["remaining"],
        }
        return Response(RunSerializer(payload).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["배달 게임"])
class RunFinishView(APIView):
    @extend_schema(
        summary="게임 결과 보내기",
        description=(
            "주운 조각 수와 부딪힌 수를 보내면 서버가 별을 매기고(9-2), 편지 도착 시간을 "
            "줄이고, 조건을 채운 꾸미기 우표를 준다. 우표 수가 늘어 열린 수집 보상은 "
            "`unlocked_rewards`에 담긴다(편지 보내기와 같은 형식)."
        ),
        request=RunFinishSerializer,
        responses={
            200: RunResultSerializer,
            400: error_response(
                "`RUN_TOO_FAST`: 시작 25초 전 / `VALIDATION_ERROR`: 음수, 코스보다 많은 조각·부딪힘"
            ),
            404: error_response("`NOT_FOUND`: 내 판이 아님"),
            409: error_response(
                "`RUN_FINISHED`: 이미 끝냄 / `RUN_EXPIRED`: 3분이 지났거나 새 판을 시작함"
            ),
        },
    )
    def post(self, request: Request, pk: int) -> Response:
        viewer, now = _viewer(request), timezone.now()
        serializer = RunFinishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = finish_run(
            viewer, pk, serializer.validated_data["pieces"], serializer.validated_data["hits"], now
        )
        run, letter = result.run, result.letter
        unlocked, seen = reward_unlocked_at(viewer), seen_reward_codes(viewer)
        payload = {
            "id": run.id,
            "stars": run.stars,
            "success": bool(run.stars),
            "perfect": run.hits == 0 and run.pieces == run.piece_total,
            "pieces": run.pieces,
            "hits": run.hits,
            "piece_total": run.piece_total,
            "puddle_total": run.puddle_total,
            "reduced_seconds": run.reduced_seconds,
            "letter": None
            if letter is None
            else {
                "id": letter.id,
                "arrives_at": letter.arrives_at,
                "remaining_seconds": remaining_seconds(letter, now),
                "reduced_total_seconds": reduced_total(letter),
            },
            "granted_stamps": StampSerializer(result.granted_stamps, many=True).data,
            "unlocked_rewards": [
                reward_payload(reward, unlocked, seen) for reward in result.unlocked_rewards
            ],
            "progress": progress(viewer),
        }
        return Response(RunResultSerializer(payload).data)
