import random
from typing import Any, cast

from django.db import transaction
from django.db.models import Count, Q, QuerySet
from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.stamps.serializers import StampSerializer
from apps.stamps.services import FIRST_DIARY, grant_stamp
from apps.users.models import User
from config.exceptions import ApiError
from config.schema import error_response

from .models import Diary, DiaryPrompt
from .serializers import (
    DiaryCreateResultSerializer,
    DiaryPromptSerializer,
    DiarySerializer,
    DiaryWriteSerializer,
)

UPLOAD_PARSERS = [MultiPartParser, FormParser, JSONParser]


def _delete_image_on_commit(diary: Diary) -> None:
    """DB 변경이 확정된 뒤에만 파일을 지운다."""
    if diary.image:
        storage, name = diary.image.storage, str(diary.image.name)
        transaction.on_commit(lambda: storage.delete(name))


IMAGE_RULES = "사진은 JPEG·PNG·WEBP, 5MB 이하 1장만 올릴 수 있다."


@extend_schema(tags=["일기"])
class DiaryCreateView(APIView):
    parser_classes = UPLOAD_PARSERS

    @extend_schema(
        summary="고향 일기 작성",
        description=(
            "지금 사는 동네의 하루를 일기로 쓴다. 사진을 올릴 때는 `multipart/form-data`, "
            "글만 쓸 때는 JSON으로 보내도 된다.\n\n"
            "- 일기 지역은 요청 값이 아니라 작성 시점의 내 거주 지역으로 정해진다.\n"
            f"- {IMAGE_RULES}\n"
            "- `accepts_letters`를 빼면 편지 받기가 켜진다(기본 true).\n"
            "- 첫 일기라면 '첫 일기' 우표가 지급되어 `granted_stamps`에 담긴다."
        ),
        request=DiaryWriteSerializer,
        responses={
            201: DiaryCreateResultSerializer,
            400: error_response(
                "`RESIDENCE_REQUIRED`: 거주 지역을 아직 설정하지 않음 / "
                "`VALIDATION_ERROR`: 본문 500자 초과, 사진 형식·크기 위반 등"
            ),
        },
    )
    def post(self, request: Request) -> Response:
        user = cast(User, request.user)
        if user.residence is None:
            raise ApiError("RESIDENCE_REQUIRED", "거주 지역을 먼저 설정해 주세요.")
        serializer = DiaryWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        data.pop("remove_image", None)

        with transaction.atomic():
            diary = Diary.objects.create(author=user, region=user.residence, **data)
            stamp = grant_stamp(user, FIRST_DIARY)

        payload: dict[str, Any] = dict(DiarySerializer(diary, context={"request": request}).data)
        payload["granted_stamps"] = StampSerializer([stamp] if stamp else [], many=True).data
        return Response(payload, status=status.HTTP_201_CREATED)


@extend_schema(tags=["일기"])
@extend_schema_view(
    get=extend_schema(
        summary="내 일기 목록",
        description="내가 쓴 일기를 최신순으로 돌려준다. 숨김·나만 보기 일기도 포함한다.",
    )
)
class MyDiaryListView(generics.ListAPIView[Diary]):
    serializer_class = DiarySerializer

    def get_queryset(self) -> QuerySet[Diary]:
        # 일기마다 받은 편지 수를 따로 세지 않도록 목록 쿼리에서 함께 센다 (DIARY-07)
        arrived_first = Q(
            conversations__letters__is_first=True,
            conversations__letters__arrives_at__lte=timezone.now(),
        )
        return (
            Diary.objects.filter(author_id=self.request.user.pk)
            .select_related("author", "region", "region__parent")
            .annotate(
                received_letters_annotated=Count(
                    "conversations__letters", filter=arrived_first, distinct=True
                )
            )
        )


NOT_MY_DIARY = error_response("`NOT_FOUND`: 없는 일기이거나 내 일기가 아님")


@extend_schema(tags=["일기"])
@extend_schema_view(
    get=extend_schema(
        summary="내 일기 상세",
        responses={200: DiarySerializer, 404: NOT_MY_DIARY},
    ),
    delete=extend_schema(
        summary="내 일기 삭제",
        description="일기와 첨부 사진을 함께 지운다.",
        responses={204: OpenApiResponse(description="삭제 완료"), 404: NOT_MY_DIARY},
    ),
)
class MyDiaryDetailView(generics.RetrieveUpdateDestroyAPIView[Diary]):
    """본인 일기 조회·수정·삭제. 다른 사람의 일기 상세는 FEED-04에서 이 경로에 붙인다."""

    parser_classes = UPLOAD_PARSERS
    serializer_class = DiarySerializer
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self) -> QuerySet[Diary]:
        return Diary.objects.filter(author_id=self.request.user.pk).select_related(
            "author", "region", "region__parent"
        )

    @extend_schema(
        summary="내 일기 수정",
        description=(
            "보낸 항목만 바꾼다(부분 수정). 일기 지역은 바뀌지 않는다.\n\n"
            "- 사진 교체: 새 `image`를 보낸다. 이전 사진은 지워진다.\n"
            "- 사진 삭제: `remove_image=true`를 보낸다. `image`와 함께 보낼 수 없다.\n"
            f"- {IMAGE_RULES}"
        ),
        request=DiaryWriteSerializer,
        responses={
            200: DiarySerializer,
            400: error_response("`VALIDATION_ERROR`: 본문 500자 초과, 사진 규칙 위반 등"),
            404: NOT_MY_DIARY,
        },
    )
    def patch(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        diary = self.get_object()
        serializer = DiaryWriteSerializer(diary, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        remove_image = data.pop("remove_image", False)

        with transaction.atomic():
            if remove_image or "image" in data:
                _delete_image_on_commit(diary)
            if remove_image:
                diary.image = None
            for field, value in data.items():
                setattr(diary, field, value)
            diary.save()
        return Response(DiarySerializer(diary, context={"request": request}).data)

    def perform_destroy(self, instance: Diary) -> None:
        with transaction.atomic():
            _delete_image_on_commit(instance)
            instance.delete()


@extend_schema(tags=["일기"])
class DiaryPromptView(APIView):
    """오늘의 글감. exclude를 주면 '다른 글감'으로 그 글감을 뺀 하나를 고른다."""

    @extend_schema(
        summary="오늘의 글감",
        description=(
            "일기 작성 화면에 보여 줄 글감 하나를 돌려준다. `exclude` 없이 부르면 날짜마다 "
            "정해진 글감이 나와 하루 동안 같다. '다른 글감' 버튼은 지금 글감 id를 `exclude`로 "
            "넘기면 그것을 뺀 글감 중 하나를 무작위로 고른다."
        ),
        parameters=[
            OpenApiParameter(
                "exclude", int, required=False, description="제외할 글감 id (지금 보고 있는 글감)"
            )
        ],
        responses={
            200: DiaryPromptSerializer,
            404: error_response("`PROMPT_NOT_FOUND`: 활성화된 글감이 하나도 없음"),
        },
    )
    def get(self, request: Request) -> Response:
        prompts = list(DiaryPrompt.objects.filter(is_active=True))
        if not prompts:
            raise ApiError("PROMPT_NOT_FOUND", "글감이 없습니다.", status.HTTP_404_NOT_FOUND)

        exclude = request.query_params.get("exclude")
        if exclude is None:
            prompt = prompts[timezone.localdate().toordinal() % len(prompts)]
        else:
            others = [p for p in prompts if str(p.id) != exclude]
            prompt = random.choice(others or prompts)
        return Response(DiaryPromptSerializer(prompt).data)
