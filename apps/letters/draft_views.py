from typing import Any, cast

from django.db.models import QuerySet
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.models import User
from config.exceptions import ApiError
from config.schema import error_response

from .draft_serializers import DraftListItemSerializer, DraftSerializer, DraftWriteSerializer
from .models import Draft
from .services import find_diary_for_letter, find_received_letter

NOT_FOUND = error_response("`NOT_FOUND`: 없거나 내 임시저장이 아님")


def _drafts(user: User) -> QuerySet[Draft]:
    return Draft.objects.filter(owner=user).select_related("diary__author", "reply_to")


def _get_draft(user: User, pk: int) -> Draft:
    draft = _drafts(user).filter(id=pk).first()
    if draft is None:
        raise ApiError("NOT_FOUND", "임시저장을 찾을 수 없습니다.", status.HTTP_404_NOT_FOUND)
    return draft


@extend_schema(tags=["편지"])
class DraftListCreateView(generics.ListAPIView[Draft]):
    serializer_class = DraftListItemSerializer

    @extend_schema(
        summary="임시저장 목록",
        description="내 임시저장 편지를 최근 저장한 순서로 준다 (7-3, LETTER-11).",
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet[Draft]:
        return _drafts(cast(User, self.request.user))

    @extend_schema(
        summary="임시저장",
        description=(
            "쓰던 편지를 임시저장한다 (4-8, LETTER-11). 대상(일기 또는 받은 편지)마다 1통만 두고, "
            "같은 대상에 다시 저장하면 덮어쓴다(200). 서명·스티커·우표는 저장하지 않는다."
        ),
        request=DraftWriteSerializer,
        responses={
            201: DraftSerializer,
            200: DraftSerializer,
            400: error_response("`VALIDATION_ERROR`: 대상이 없거나 둘 다 있음, 내 일기"),
            404: error_response("`NOT_FOUND`: 볼 수 없는 일기, 내가 받은 편지가 아님"),
        },
    )
    def post(self, request: Request) -> Response:
        user = cast(User, request.user)
        serializer = DraftWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        diary = find_diary_for_letter(user, data["diary_id"]) if "diary_id" in data else None
        reply_to = find_received_letter(user, data["reply_to"]) if "reply_to" in data else None
        if diary is not None and diary.author_id == user.pk:
            raise ApiError("VALIDATION_ERROR", "내 일기에는 편지를 쓸 수 없습니다.")
        if reply_to is not None and not reply_to.has_arrived():
            # 아직 열 수 없는 편지에는 답장을 쓸 수 없다.
            raise ApiError("NOT_FOUND", "편지를 찾을 수 없습니다.", status.HTTP_404_NOT_FOUND)

        draft, created = Draft.objects.update_or_create(
            owner=user,
            diary=diary,
            reply_to=reply_to,
            defaults={"body": data["body"], "stationery": data["stationery"], "font": data["font"]},
        )
        draft = _get_draft(user, draft.id)
        code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(DraftSerializer(draft).data, status=code)


@extend_schema(tags=["편지"])
class DraftDetailView(APIView):
    @extend_schema(
        summary="임시저장 상세",
        description="이어 쓰기(4-9, 7-3)를 위해 임시저장 하나를 전부 준다 (LETTER-11).",
        responses={200: DraftSerializer, 404: NOT_FOUND},
    )
    def get(self, request: Request, pk: int) -> Response:
        return Response(DraftSerializer(_get_draft(cast(User, request.user), pk)).data)

    @extend_schema(
        summary="임시저장 삭제",
        description="임시저장을 지운다 (7-3 휴지통, 4-8 「저장 안 함」, 4-9 「새로 쓰기」).",
        responses={204: OpenApiResponse(description="삭제 완료"), 404: NOT_FOUND},
    )
    def delete(self, request: Request, pk: int) -> Response:
        _get_draft(cast(User, request.user), pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
