import random
from typing import Any, cast

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.stamps.serializers import StampSerializer
from apps.stamps.services import FIRST_DIARY, grant_stamp
from apps.users.models import User
from config.exceptions import ApiError

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


class DiaryCreateView(APIView):
    parser_classes = UPLOAD_PARSERS

    @extend_schema(request=DiaryWriteSerializer, responses={201: DiaryCreateResultSerializer})
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


class MyDiaryListView(generics.ListAPIView[Diary]):
    serializer_class = DiarySerializer

    def get_queryset(self) -> QuerySet[Diary]:
        return Diary.objects.filter(author_id=self.request.user.pk).select_related(
            "author", "region", "region__parent"
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

    @extend_schema(request=DiaryWriteSerializer, responses={200: DiarySerializer})
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


class DiaryPromptView(APIView):
    """오늘의 글감. exclude를 주면 '다른 글감'으로 그 글감을 뺀 하나를 고른다."""

    @extend_schema(
        parameters=[OpenApiParameter("exclude", int, required=False)],
        responses={200: DiaryPromptSerializer},
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
