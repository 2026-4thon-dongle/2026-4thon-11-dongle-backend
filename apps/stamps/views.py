from datetime import datetime
from typing import Any, cast

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.models import User
from config.exceptions import ApiError
from config.schema import error_response

from .models import RewardSeen, Stamp, UserStamp
from .rewards import REWARDS, REWARDS_BY_CODE, Reward
from .serializers import (
    RewardListSerializer,
    StampBookSerializer,
    StampDetailSerializer,
    StampSerializer,
)
from .services import next_reward, owned_count, reward_unlocked_at, seen_reward_codes


def _next_reward_payload(count: int) -> dict[str, Any] | None:
    reward = next_reward(count)
    if reward is None:
        return None
    return {
        "code": reward.code,
        "name": reward.name,
        "threshold": reward.threshold,
        "remaining": reward.threshold - count,
    }


def _stamp_payload(stamp: Stamp, granted_at: datetime | None) -> dict[str, Any]:
    return {
        **StampSerializer(stamp).data,
        "owned": granted_at is not None,
        "granted_at": granted_at,
    }


def reward_payload(
    reward: Reward, unlocked_at: dict[str, datetime], seen: set[str]
) -> dict[str, Any]:
    return {
        "code": reward.code,
        "threshold": reward.threshold,
        "name": reward.name,
        "description": reward.description,
        "items": [{"type": item.type, "code": item.code} for item in reward.items],
        "unlocked": reward.code in unlocked_at,
        "unlocked_at": unlocked_at.get(reward.code),
        "seen": reward.code in seen,
    }


@extend_schema(tags=["우표"])
class StampBookView(APIView):
    @extend_schema(
        summary="우표첩",
        operation_id="stamps_book",
        description=(
            "전체 우표와 보유 여부, 다음 수집 보상까지의 진행률을 준다 (7-4, 7-5, 7-6).\n\n"
            "- `owned_count`는 업적 + 꾸미기 보유 수이고 수집 보상 기준이다.\n"
            "- `kind`로 업적·꾸미기 탭을 나눠 받을 수 있다."
        ),
        parameters=[
            OpenApiParameter(
                "kind", str, required=False, enum=["achievement", "decoration"], description="종류"
            )
        ],
        responses={
            200: StampBookSerializer,
            400: error_response("`VALIDATION_ERROR`: kind 값이 잘못됨"),
        },
    )
    def get(self, request: Request) -> Response:
        user = cast(User, request.user)
        kind = request.query_params.get("kind")
        stamps = Stamp.objects.all()
        if kind is not None:
            if kind not in Stamp.Kind.values:
                raise ApiError("VALIDATION_ERROR", "kind 값을 확인해 주세요.")
            stamps = stamps.filter(kind=kind)

        granted = dict(UserStamp.objects.filter(user=user).values_list("stamp_id", "granted_at"))
        count = len(granted)
        unlocked = reward_unlocked_at(user)
        return Response(
            {
                "owned_count": count,
                "total_count": Stamp.objects.count(),
                "next_reward": _next_reward_payload(count),
                "received_rewards": [
                    {"code": reward.code, "name": reward.name}
                    for reward in REWARDS
                    if reward.code in unlocked
                ],
                "stamps": [_stamp_payload(stamp, granted.get(stamp.id)) for stamp in stamps],
            }
        )


@extend_schema(tags=["우표"])
class RewardListView(APIView):
    @extend_schema(
        summary="수집 보상",
        description=(
            "수집 보상 4단계와 해금 여부를 준다 (7-8). 보상은 보유 우표 수가 기준에 닿으면 "
            "자동으로 열린다. `unlocked=true, seen=false`면 아직 해금 모달(5-13)을 확인하지 않았다."
        ),
        responses={200: RewardListSerializer},
    )
    def get(self, request: Request) -> Response:
        user = cast(User, request.user)
        unlocked = reward_unlocked_at(user)
        seen = seen_reward_codes(user)
        return Response(
            {
                "owned_count": owned_count(user),
                "rewards": [reward_payload(reward, unlocked, seen) for reward in REWARDS],
            }
        )


@extend_schema(tags=["우표"])
class RewardSeenView(APIView):
    @extend_schema(
        summary="해금 모달 확인",
        description="수집 보상 해금 모달(5-13)을 확인했다고 기록한다. 이미 기록했어도 204다.",
        request=None,
        responses={
            204: OpenApiResponse(description="기록 완료"),
            404: error_response("`NOT_FOUND`: 없는 보상이거나 아직 열리지 않음"),
        },
    )
    def post(self, request: Request, code: str) -> Response:
        user = cast(User, request.user)
        if code not in REWARDS_BY_CODE or code not in reward_unlocked_at(user):
            raise ApiError("NOT_FOUND", "열린 보상이 아닙니다.", status.HTTP_404_NOT_FOUND)
        RewardSeen.objects.get_or_create(user=user, code=code)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["우표"])
class StampDetailView(APIView):
    @extend_schema(
        summary="우표 상세",
        operation_id="stamps_detail",
        description=(
            "우표 하나의 이름·번호·등급·획득 조건을 준다 (7-7). 보유한 우표면 받은 시각과 "
            "획득 계기가 된 상대(`granted_with`)를 함께 준다."
        ),
        responses={
            200: StampDetailSerializer,
            404: error_response("`NOT_FOUND`: 없는 우표 코드"),
        },
    )
    def get(self, request: Request, code: str) -> Response:
        user = cast(User, request.user)
        stamp = Stamp.objects.filter(code=code).first()
        if stamp is None:
            raise ApiError("NOT_FOUND", "없는 우표입니다.", status.HTTP_404_NOT_FOUND)
        grant = (
            UserStamp.objects.filter(user=user, stamp=stamp).select_related("granted_with").first()
        )
        partner = grant.granted_with if grant else None
        count = owned_count(user)
        return Response(
            {
                **_stamp_payload(stamp, grant.granted_at if grant else None),
                "granted_with": {"id": partner.pk, "nickname": partner.nickname}
                if partner
                else None,
                "owned_count": count,
                "next_reward": _next_reward_payload(count),
            }
        )
