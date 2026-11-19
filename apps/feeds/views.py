from datetime import datetime, time
from typing import Any, cast

from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.diaries.models import Diary
from apps.letters.mailbox import preview
from apps.letters.models import Draft
from apps.letters.services import route_between
from apps.regions.models import Region
from apps.regions.serializers import RegionWithSidoSerializer
from apps.users.models import User
from config.exceptions import ApiError
from config.params import parse_id
from config.schema import error_response

from .models import FeedSeen
from .queries import feed_diary, hometown_feed, others_feed
from .serializers import FeedDiaryDetailSerializer, FeedDiarySerializer, FeedSummarySerializer


def _viewer(request: Request) -> User:
    return cast(User, request.user)


def _region_param(request: Request, name: str) -> Region | None:
    value = request.query_params.get(name)
    if value is None:
        return None
    region_id = parse_id(value)
    region = Region.objects.filter(id=region_id).first() if region_id is not None else None
    if region is None:
        raise ApiError("VALIDATION_ERROR", f"{name} 값을 확인해 주세요.")
    return region


@extend_schema(tags=["피드"])
class HometownFeedView(generics.ListAPIView[Diary]):
    serializer_class = FeedDiarySerializer

    @extend_schema(
        summary="고향 ↔ 타지 피드",
        description=(
            "작성 지역이 내 본가 지역에 속하는 일기를 최신순으로 준다 (3-1, FEED-01). 본가가 "
            "시·군이면 그 시·군, 광역시·세종이면 그 시·도 안에서 쓴 일기다. 남의 나만 보기, "
            "차단·신고·숨김 일기는 빠진다. 내 일기도 나오며 `can_reply`는 false다."
        ),
        parameters=[
            OpenApiParameter("region", int, required=False, description="본가 지역 id (칩 필터)"),
        ],
        responses={
            200: FeedDiarySerializer(many=True),
            400: error_response("`VALIDATION_ERROR`: region이 내 본가 지역이 아님"),
        },
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)

    def get_queryset(self) -> Any:
        viewer = _viewer(self.request)
        region = _region_param(self.request, "region")
        if region is not None and not viewer.hometowns.filter(id=region.id).exists():
            raise ApiError("VALIDATION_ERROR", "region은 내 본가 지역이어야 합니다.")
        return hometown_feed(viewer, region)


def _today_start() -> datetime:
    return timezone.make_aware(datetime.combine(timezone.localdate(), time.min))


@extend_schema(tags=["피드"])
class HometownSummaryView(APIView):
    @extend_schema(
        summary="고향 피드 요약",
        description=(
            "홈 배너 「새 일기 N편이 도착했어요」와 본가 칩 목록을 준다 (3-1). `new_count`는 "
            "마지막으로 피드를 확인한 시각 이후의 고향 일기 수다(내 일기 제외). "
            "처음이면 오늘 0시 이후."
        ),
        responses={200: FeedSummarySerializer},
    )
    def get(self, request: Request) -> Response:
        viewer = _viewer(request)
        seen = FeedSeen.objects.filter(user=viewer).first()
        since = seen.seen_at if seen else _today_start()
        hometowns = viewer.hometowns.select_related("parent").order_by("id")
        return Response(
            {
                "hometowns": RegionWithSidoSerializer(hometowns, many=True).data,
                "new_count": hometown_feed(viewer)
                .exclude(author=viewer)
                .filter(created_at__gt=since)
                .count(),
                "last_seen_at": seen.seen_at if seen else None,
            }
        )


@extend_schema(tags=["피드"])
class HometownSeenView(APIView):
    @extend_schema(
        summary="고향 피드 확인 기록",
        description="고향 ↔ 타지 피드를 확인했다고 기록한다. 이후 new_count는 이 시각부터 센다.",
        request=None,
        responses={204: OpenApiResponse(description="기록 완료")},
    )
    def post(self, request: Request) -> Response:
        FeedSeen.objects.update_or_create(
            user=_viewer(request), defaults={"seen_at": timezone.now()}
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["피드"])
class OthersFeedView(generics.ListAPIView[Diary]):
    serializer_class = FeedDiarySerializer

    @extend_schema(
        summary="전체 타지 피드",
        description=(
            "내 본가 지역에 속하지 않고 내 거주 구에서 쓰지 않은 일기를 최신순으로 준다 "
            "(3-2, FEED-02). 내 일기는 거주 구에서 썼어도 나오며 `can_reply`는 false다."
        ),
        parameters=[
            OpenApiParameter("sido", int, required=False, description="시·도 id (칩 필터)")
        ],
        responses={
            200: FeedDiarySerializer(many=True),
            400: error_response("`VALIDATION_ERROR`: sido가 시·도가 아님"),
        },
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)

    def get_queryset(self) -> Any:
        sido = _region_param(self.request, "sido")
        if sido is not None and sido.parent_id is not None:
            raise ApiError("VALIDATION_ERROR", "sido는 시·도여야 합니다.")
        return others_feed(_viewer(self.request), sido)


@extend_schema(tags=["피드"])
class FeedDiaryDetailView(APIView):
    @extend_schema(
        summary="피드 일기 상세",
        description=(
            "피드에서 고른 일기 상세 (3-5, FEED-04). 예상 배송 시간과 이 일기에 임시저장한 편지를 "
            "함께 준다. 내 일기도 볼 수 있다. 편지 받기 OFF·내 일기·쉬기 중·이미 보냄이면 "
            "`can_reply=false`와 이유를 준다."
        ),
        responses={
            200: FeedDiaryDetailSerializer,
            404: error_response("`NOT_FOUND`: 없거나 볼 수 없는 일기 (차단·숨김·공개 범위)"),
        },
    )
    def get(self, request: Request, pk: int) -> Response:
        viewer = _viewer(request)
        diary = feed_diary(viewer, pk)
        if diary is None:
            raise ApiError("NOT_FOUND", "일기를 찾을 수 없습니다.", status.HTTP_404_NOT_FOUND)
        delivery = None
        if diary.author_id != viewer.pk:
            try:
                route = route_between(viewer, diary.author, fallback=diary.region)
            except ApiError:
                route = None
            if route is not None:
                delivery = {
                    "from_region": RegionWithSidoSerializer(route.from_region).data,
                    "to_region": RegionWithSidoSerializer(route.to_region).data,
                    "band": route.band,
                    "duration_minutes": route.duration_minutes,
                    "arrives_at": route.arrives_at(timezone.now()),
                }
        draft = Draft.objects.filter(owner=viewer, diary=diary).first()
        my_draft = (
            {"id": draft.id, "body_preview": preview(draft.body), "saved_at": draft.saved_at}
            if draft is not None
            else None
        )
        context = {"request": request, "delivery": delivery, "my_draft": my_draft}
        return Response(FeedDiaryDetailSerializer(diary, context=context).data)
