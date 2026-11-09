from typing import cast

from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.diaries.models import Diary
from apps.users.models import User
from config.exceptions import ApiError

from .models import Block, Report
from .serializers import (
    BlockCreateSerializer,
    BlockSerializer,
    ContactCheckResultSerializer,
    ContactCheckSerializer,
    ReportCreateSerializer,
    ReportResultSerializer,
)
from .services import detect_contact_patterns

HIDE_THRESHOLD = 3


def _resolve_report_target(reporter: User, target_type: str, target_id: int) -> User:
    """신고 대상의 작성자를 찾는다. reporter가 볼 수 없는 대상은 없는 것으로 다룬다."""
    target_user: User | None = None
    if target_type == Report.TargetType.DIARY:
        diary = Diary.objects.visible_to(reporter).filter(id=target_id).first()
        target_user = diary.author if diary else None
    elif target_type == Report.TargetType.USER:
        target_user = User.objects.filter(id=target_id).first()
    else:
        raise ApiError("UNSUPPORTED_REPORT_TARGET", "편지 신고는 편지 기능 연결 후 지원합니다.")

    if target_user is None:
        raise ApiError(
            "TARGET_NOT_FOUND", "신고 대상을 찾을 수 없습니다.", status.HTTP_404_NOT_FOUND
        )
    if target_user.pk == reporter.pk:
        raise ApiError("CANNOT_REPORT_SELF", "내 글이나 내 계정은 신고할 수 없습니다.")
    return target_user


class ReportCreateView(APIView):
    @extend_schema(request=ReportCreateSerializer, responses={201: ReportResultSerializer})
    def post(self, request: Request) -> Response:
        reporter = cast(User, request.user)
        serializer = ReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        target_user = _resolve_report_target(reporter, data["target_type"], data["target_id"])

        try:
            with transaction.atomic():
                report = Report.objects.create(
                    reporter=reporter,
                    target_user=target_user,
                    target_type=data["target_type"],
                    target_id=data["target_id"],
                    reason=data["reason"],
                    detail=data["detail"],
                )
                if data["target_type"] == Report.TargetType.DIARY:
                    count = Report.objects.filter(
                        target_type=Report.TargetType.DIARY, target_id=data["target_id"]
                    ).count()
                    if count >= HIDE_THRESHOLD:
                        Diary.objects.filter(id=data["target_id"]).update(is_hidden=True)
                if data["block_user"]:
                    Block.objects.get_or_create(blocker=reporter, blocked=target_user)
        except IntegrityError as exc:
            raise ApiError(
                "ALREADY_REPORTED", "이미 신고한 대상입니다.", status.HTTP_409_CONFLICT
            ) from exc
        return Response(
            {"id": report.id, "blocked": data["block_user"]}, status=status.HTTP_201_CREATED
        )


class BlockListCreateView(generics.ListAPIView[Block]):
    serializer_class = BlockSerializer

    def get_queryset(self) -> QuerySet[Block]:
        return Block.objects.filter(blocker_id=self.request.user.pk).select_related("blocked")

    @extend_schema(request=BlockCreateSerializer, responses={201: BlockSerializer})
    def post(self, request: Request) -> Response:
        serializer = BlockCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target = serializer.validated_data["user_id"]
        if target.pk == request.user.pk:
            raise ApiError("CANNOT_BLOCK_SELF", "자기 자신은 차단할 수 없습니다.")
        block, _ = Block.objects.get_or_create(blocker_id=request.user.pk, blocked=target)
        return Response(BlockSerializer(block).data, status=status.HTTP_201_CREATED)


class BlockDeleteView(APIView):
    @extend_schema(responses={204: None})
    def delete(self, request: Request, user_id: int) -> Response:
        get_object_or_404(Block, blocker_id=request.user.pk, blocked_id=user_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ContactCheckView(APIView):
    @extend_schema(request=ContactCheckSerializer, responses={200: ContactCheckResultSerializer})
    def post(self, request: Request) -> Response:
        serializer = ContactCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        types = detect_contact_patterns(serializer.validated_data["text"])
        return Response({"has_contact": bool(types), "types": types})
