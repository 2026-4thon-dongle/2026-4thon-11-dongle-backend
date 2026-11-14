from typing import Any, cast

from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.regions.serializers import RegionWithSidoSerializer
from apps.stamps.models import Stamp, UserStamp
from apps.stamps.rewards import FONTS, STATIONERIES, STICKERS, Item, reward_for_item
from apps.stamps.serializers import StampSerializer
from apps.stamps.services import (
    is_item_unlocked,
    owned_count,
    reward_unlocked_at,
    seen_reward_codes,
)
from apps.stamps.views import reward_payload
from apps.users.models import User
from config.exceptions import ApiError
from config.schema import error_response

from .serializers import (
    EstimateSerializer,
    LetterSentSerializer,
    LetterWriteSerializer,
    MaterialsSerializer,
)
from .services import (
    find_diary_for_letter,
    find_received_letter,
    route_between,
    send_letter,
)

UPLOAD_PARSERS = [MultiPartParser, FormParser, JSONParser]


def _material(item: Item, count: int) -> dict[str, Any]:
    reward = reward_for_item(item.type, item.code)
    unlocked = is_item_unlocked(item.type, item.code, count)
    return {
        "code": item.code,
        "name": item.name,
        "unlocked": unlocked,
        "unlock_condition": None if unlocked or reward is None else f"우표 {reward.threshold}개",
    }


def _stationery(item: Item, count: int, seen: set[str]) -> dict[str, Any]:
    """보상으로 열렸는데 해금 모달을 아직 확인하지 않은 편지지는 NEW로 표시한다 (4-1)."""
    material = _material(item, count)
    reward = reward_for_item(item.type, item.code)
    material["is_new"] = material["unlocked"] and reward is not None and reward.code not in seen
    return material


@extend_schema(tags=["편지"])
class MaterialsView(APIView):
    @extend_schema(
        summary="편지 쓰기 재료",
        description=(
            "편지 쓰기 단계에서 고를 수 있는 편지지·글씨체·스티커·보유 우표를 한 번에 준다 "
            "(4-1, 4-3, 4-5, 4-6). 잠긴 항목은 해금 조건을 함께 준다. 해금은 보유 우표 수로 정한다."
        ),
        responses={200: MaterialsSerializer},
    )
    def get(self, request: Request) -> Response:
        user = cast(User, request.user)
        count = owned_count(user)
        seen = seen_reward_codes(user)
        stamps = [
            grant.stamp
            for grant in UserStamp.objects.filter(user=user)
            .select_related("stamp")
            .order_by("granted_at", "id")
        ]
        return Response(
            {
                "stationeries": [_stationery(item, count, seen) for item in STATIONERIES],
                "fonts": [_material(item, count) for item in FONTS],
                "stickers": [_material(item, count) for item in STICKERS],
                "stamps": [
                    {"code": s.code, "number": s.number, "name": s.name, "kind": s.kind}
                    for s in stamps
                ],
            }
        )


@extend_schema(tags=["편지"])
class EstimateView(APIView):
    @extend_schema(
        summary="배송 시간 미리 보기",
        description=(
            "지금 보내면 걸리는 시간을 준다 (4-6 「도착까지 약 6시간」, LETTER-07). "
            "`diary_id`와 `reply_to` 중 하나만 보낸다.\n\n"
            "구간: same_sido 60분 / adjacent 180분 / near(300km 미만) 360분 / "
            "far(300km 이상·제주) 720분. 데모 모드면 1분."
        ),
        parameters=[
            OpenApiParameter("diary_id", int, required=False, description="첫 편지를 보낼 일기"),
            OpenApiParameter("reply_to", int, required=False, description="답장할 받은 편지"),
        ],
        responses={
            200: EstimateSerializer,
            400: error_response(
                "`VALIDATION_ERROR`: 둘 다 없거나 둘 다 있음 / "
                "`RESIDENCE_REQUIRED`: 거주 지역 미설정"
            ),
            404: error_response("`NOT_FOUND`: 볼 수 없는 일기·편지"),
        },
    )
    def get(self, request: Request) -> Response:
        user = cast(User, request.user)
        diary_id = request.query_params.get("diary_id")
        reply_to = request.query_params.get("reply_to")
        if (diary_id is None) == (reply_to is None) or not (diary_id or reply_to or "").isdigit():
            raise ApiError("VALIDATION_ERROR", "diary_id와 reply_to 중 하나만 보내 주세요.")
        if diary_id is not None:
            diary = find_diary_for_letter(user, int(diary_id))
            route = route_between(user, diary.author, fallback=diary.region)
        else:
            letter = find_received_letter(user, int(reply_to or 0))
            route = route_between(user, letter.sender)
        return Response(
            {
                "from_region": RegionWithSidoSerializer(route.from_region).data,
                "to_region": RegionWithSidoSerializer(route.to_region).data,
                "band": route.band,
                "duration_minutes": route.duration_minutes,
                "arrives_at": route.arrives_at(timezone.now()),
            }
        )


SEND_ERRORS = {
    400: error_response(
        "`VALIDATION_ERROR`: 입력값 오류(둘 다 없음, 본문 길이, 서명 형식 등) / "
        "`ITEM_LOCKED`: 보유하지 않은 편지지·글씨체·스티커·우표 / "
        "`RESIDENCE_REQUIRED`: 거주 지역 미설정"
    ),
    403: error_response(
        "`OWN_DIARY`: 내 일기 / `LETTERS_OFF`: 편지 받기 OFF / "
        "`RECIPIENT_PAUSED`: 받는 사람이 편지 잠시 쉬기 중 / `BLOCKED`: 차단 관계"
    ),
    404: error_response("`NOT_FOUND`: 볼 수 없는 일기·편지"),
    409: error_response(
        "`ALREADY_SENT`: 이 일기에 이미 첫 편지를 보냄 / `ALREADY_REPLIED`: 이미 답장함 / "
        "`NOT_ARRIVED`: 아직 도착하지 않은 편지 / `CONVERSATION_CLOSED`: 마무리·넘긴 대화"
    ),
}


def _check_items(user: User, data: dict[str, Any]) -> Stamp:
    count = owned_count(user)
    items = [("stationery", data["stationery"]), ("font", data["font"])]
    items += [("sticker", sticker["code"]) for sticker in data["stickers"]]
    if not all(is_item_unlocked(type_, code, count) for type_, code in items):
        raise ApiError("ITEM_LOCKED", "아직 열리지 않은 편지지·글씨체·스티커예요.")
    stamp = Stamp.objects.filter(code=data["stamp"]).first()
    if stamp is None or not UserStamp.objects.filter(user=user, stamp=stamp).exists():
        raise ApiError("ITEM_LOCKED", "가지고 있지 않은 우표예요.")
    return stamp


@extend_schema(tags=["편지"])
class LetterSendView(APIView):
    parser_classes = UPLOAD_PARSERS

    @extend_schema(
        summary="편지 보내기",
        description=(
            "편지를 보낸다. `diary_id`를 보내면 그 일기에 대한 첫 편지, `reply_to`를 보내면 "
            "받은 편지에 대한 답장이다. 보낸 뒤에는 취소·수정할 수 없다 "
            "(LETTER-06, 07, 09, MAIL-07).\n\n"
            "- 서명 이미지가 있으면 `multipart/form-data`, 없으면 JSON도 된다. multipart에서 "
            "`stickers`는 JSON 문자열로 보낸다.\n"
            "- 출발은 내 거주지, 도착은 받는 사람 거주지다. 도착 시각(`arrives_at`)이 지나야 "
            "받는 사람 우체통에 보인다.\n"
            "- 우표는 붙여도 우표첩에서 없어지지 않는다.\n"
            "- 새로 받은 우표는 `granted_stamps`, 새로 열린 수집 보상은 "
            "`unlocked_rewards`에 담긴다."
        ),
        request=LetterWriteSerializer,
        responses={201: LetterSentSerializer, **SEND_ERRORS},
    )
    def post(self, request: Request) -> Response:
        user = cast(User, request.user)
        serializer = LetterWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        diary = find_diary_for_letter(user, data["diary_id"]) if "diary_id" in data else None
        reply_to = find_received_letter(user, data["reply_to"]) if "reply_to" in data else None
        stamp = _check_items(user, data)

        result = send_letter(
            user,
            diary=diary,
            reply_to=reply_to,
            body=data["body"],
            stationery=data["stationery"],
            font=data["font"],
            signature=data.get("signature"),
            stickers=data["stickers"],
            stamp=stamp,
        )
        letter = result.letter
        unlocked = reward_unlocked_at(user)
        seen = seen_reward_codes(user)
        payload = {
            "id": letter.id,
            "conversation_id": letter.conversation_id,
            "is_first": letter.is_first,
            "recipient": {"id": letter.recipient_id, "nickname": letter.recipient_nickname},
            "from_region": RegionWithSidoSerializer(letter.from_region).data,
            "to_region": RegionWithSidoSerializer(letter.to_region).data,
            "band": letter.band,
            "duration_minutes": letter.duration_minutes,
            "sent_at": letter.sent_at,
            "arrives_at": letter.arrives_at,
            "stamp": {"code": stamp.code, "number": stamp.number, "name": stamp.name},
            "granted_stamps": StampSerializer(result.granted_stamps, many=True).data,
            "unlocked_rewards": [
                reward_payload(reward, unlocked, seen) for reward in result.unlocked_rewards
            ],
        }
        return Response(payload, status=status.HTTP_201_CREATED)
