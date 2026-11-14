from typing import Any, cast

from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.moderations.services import blocked_user_ids
from apps.regions.serializers import RegionWithSidoSerializer
from apps.stamps.serializers import UserBriefSerializer
from apps.users.models import User
from config.exceptions import ApiError
from config.schema import error_response

from .models import Letter
from .route import map_theme, story_payload, waypoints


class StorySerializer(serializers.Serializer[Any]):
    diary_id = serializers.IntegerField()
    body_preview = serializers.CharField()


class WaypointSerializer(serializers.Serializer[Any]):
    region = RegionWithSidoSerializer(help_text="지나는 시·도")
    progress = serializers.FloatField(help_text="이 지점을 지나는 진행률 (0~1)")
    story = StorySerializer(allow_null=True, help_text="그 지역 최근 일기 한 줄. 없으면 null")


class LetterRouteSerializer(serializers.Serializer[Any]):
    direction = serializers.CharField(help_text="sent: 내가 보냄 / incoming: 나에게 옴")
    partner = UserBriefSerializer(help_text="상대")
    from_region = RegionWithSidoSerializer()
    to_region = RegionWithSidoSerializer()
    sent_at = serializers.DateTimeField()
    arrives_at = serializers.DateTimeField()
    map_theme = serializers.CharField(
        help_text="city / sea / mountain / field / river. 편지마다 고정"
    )
    waypoints = WaypointSerializer(many=True, help_text="지나는 지역 순서대로")


@extend_schema(tags=["편지"])
class LetterRouteView(APIView):
    @extend_schema(
        summary="배송 경로",
        description=(
            "실시간 배송 지도(4-12)용 경로를 준다 (LETTER-10). 현재 위치와 남은 시간은 "
            "`sent_at`, `arrives_at`으로 프론트가 계산한다. 보낸 사람과 받는 사람 모두 조회할 수 "
            "있고, 편지 내용은 주지 않는다. 경유지는 시·도 단위다."
        ),
        responses={
            200: LetterRouteSerializer,
            404: error_response("`NOT_FOUND`: 내가 보내거나 받은 편지가 아님"),
        },
    )
    def get(self, request: Request, pk: int) -> Response:
        viewer = cast(User, request.user)
        blocked = blocked_user_ids(viewer)
        letter = (
            Letter.objects.filter(Q(sender=viewer) | Q(recipient=viewer), id=pk)
            .exclude(sender_id__in=blocked)
            .exclude(recipient_id__in=blocked)
            .select_related("from_region__parent", "to_region__parent")
            .first()
        )
        if letter is None:
            raise ApiError("NOT_FOUND", "편지를 찾을 수 없습니다.", status.HTTP_404_NOT_FOUND)

        sent = letter.sender_id == viewer.pk
        partner = (
            {"id": letter.recipient_id, "nickname": letter.recipient_nickname}
            if sent
            else {"id": letter.sender_id, "nickname": letter.sender_nickname}
        )
        payload = {
            "direction": "sent" if sent else "incoming",
            "partner": partner,
            "from_region": RegionWithSidoSerializer(letter.from_region).data,
            "to_region": RegionWithSidoSerializer(letter.to_region).data,
            "sent_at": letter.sent_at,
            "arrives_at": letter.arrives_at,
            "map_theme": map_theme(letter),
            "waypoints": [
                {
                    "region": RegionWithSidoSerializer(w.region).data,
                    "progress": w.progress,
                    "story": story_payload(w.story),
                }
                for w in waypoints(letter, viewer)
            ],
        }
        return Response(payload)
