from typing import cast

from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.diaries.models import Diary
from apps.users.models import User
from config.exceptions import ApiError
from config.schema import error_response

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


@extend_schema(tags=["신고·차단"])
class ReportCreateView(APIView):
    @extend_schema(
        summary="신고하기",
        description=(
            "일기나 사용자를 신고한다. 편지 신고(`target_type=letter`)는 편지 기능이 붙은 뒤 "
            "지원한다.\n\n"
            "- 신고한 일기, 신고한 사용자의 일기는 그 뒤로 내 피드에 보이지 않는다.\n"
            f"- 한 일기가 신고 {HIDE_THRESHOLD}건을 넘으면 모두에게서 숨겨진다.\n"
            "- `reason=etc`이면 `detail`에 사유를 꼭 적어야 한다.\n"
            "- `block_user=true`이면 신고와 함께 대상 사용자를 차단한다."
        ),
        request=ReportCreateSerializer,
        responses={
            201: ReportResultSerializer,
            400: error_response(
                "`CANNOT_REPORT_SELF`: 내 글·내 계정 신고 / "
                "`UNSUPPORTED_REPORT_TARGET`: 아직 지원하지 않는 편지 신고 / "
                "`VALIDATION_ERROR`: 기타 사유 미입력 등"
            ),
            404: error_response("`TARGET_NOT_FOUND`: 없거나 내가 볼 수 없는 신고 대상"),
            409: error_response("`ALREADY_REPORTED`: 이미 신고한 대상"),
        },
    )
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


@extend_schema(tags=["신고·차단"])
@extend_schema_view(
    get=extend_schema(
        summary="차단 목록",
        description="내가 차단한 사용자를 최근 차단한 순서로 돌려준다.",
    )
)
class BlockListCreateView(generics.ListAPIView[Block]):
    serializer_class = BlockSerializer

    def get_queryset(self) -> QuerySet[Block]:
        return Block.objects.filter(blocker_id=self.request.user.pk).select_related("blocked")

    @extend_schema(
        summary="사용자 차단",
        description=(
            "사용자를 차단한다. 차단하면 서로의 일기가 피드에 보이지 않는다. "
            "이미 차단한 사용자여도 에러 없이 기존 차단 정보를 돌려준다."
        ),
        request=BlockCreateSerializer,
        responses={
            201: BlockSerializer,
            400: error_response(
                "`CANNOT_BLOCK_SELF`: 자기 자신 차단 / `VALIDATION_ERROR`: 없는 사용자"
            ),
        },
    )
    def post(self, request: Request) -> Response:
        serializer = BlockCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target = serializer.validated_data["user_id"]
        if target.pk == request.user.pk:
            raise ApiError("CANNOT_BLOCK_SELF", "자기 자신은 차단할 수 없습니다.")
        block, _ = Block.objects.get_or_create(blocker_id=request.user.pk, blocked=target)
        return Response(BlockSerializer(block).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["신고·차단"])
class BlockDeleteView(APIView):
    @extend_schema(
        summary="차단 해제",
        description="경로의 `user_id`는 차단한 사용자의 id다.",
        responses={
            204: OpenApiResponse(description="차단 해제 완료"),
            404: error_response("`NOT_FOUND`: 차단하지 않은 사용자"),
        },
    )
    def delete(self, request: Request, user_id: int) -> Response:
        get_object_or_404(Block, blocker_id=request.user.pk, blocked_id=user_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["신고·차단"])
class ContactCheckView(APIView):
    @extend_schema(
        summary="연락처 노출 검사",
        description=(
            "일기·편지를 보내기 전에 본문에 전화번호, 이메일, 카카오톡·인스타그램 아이디가 "
            "있는지 검사한다. 막지 않고 경고만 띄우는 용도라서 결과와 상관없이 200을 돌려준다."
        ),
        request=ContactCheckSerializer,
        responses={200: ContactCheckResultSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = ContactCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        types = detect_contact_patterns(serializer.validated_data["text"])
        return Response({"has_contact": bool(types), "types": types})
