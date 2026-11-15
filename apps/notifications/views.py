from typing import cast

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.letters.notifications import notify_arrived_letters
from apps.users.models import User
from config.schema import error_response

from .models import Notification, PushToken
from .serializers import NotificationSerializer, PushTokenSerializer, UnreadCountSerializer


@extend_schema(tags=["알림"])
@extend_schema_view(
    get=extend_schema(
        summary="알림 목록",
        description="내 알림을 최신순으로 돌려준다. 읽지 않은 알림은 `read_at`이 null이다.",
    )
)
class NotificationListView(generics.ListAPIView[Notification]):
    serializer_class = NotificationSerializer

    def get_queryset(self) -> QuerySet[Notification]:
        user = cast(User, self.request.user)
        notify_arrived_letters(user)
        return Notification.objects.filter(user=user)


@extend_schema(tags=["알림"])
class UnreadCountView(APIView):
    @extend_schema(
        summary="읽지 않은 알림 수",
        description="알림 아이콘 배지에 쓴다.",
        responses={200: UnreadCountSerializer},
    )
    def get(self, request: Request) -> Response:
        user = cast(User, request.user)
        notify_arrived_letters(user)
        count = Notification.objects.filter(user=user, read_at=None).count()
        return Response({"unread_count": count})


@extend_schema(tags=["알림"])
class NotificationReadView(APIView):
    @extend_schema(
        summary="알림 읽음 처리",
        description="알림 하나를 읽음으로 바꾼다. 이미 읽은 알림이면 처음 읽은 시각을 유지한다.",
        request=None,
        responses={
            200: NotificationSerializer,
            404: error_response("`NOT_FOUND`: 없는 알림이거나 내 알림이 아님"),
        },
    )
    def post(self, request: Request, pk: int) -> Response:
        notification = get_object_or_404(Notification, pk=pk, user=cast(User, request.user))
        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=["read_at"])
        return Response(NotificationSerializer(notification).data)


@extend_schema(tags=["알림"])
class NotificationReadAllView(APIView):
    @extend_schema(
        summary="알림 모두 읽음 처리",
        request=None,
        responses={204: OpenApiResponse(description="모두 읽음 처리 완료")},
    )
    def post(self, request: Request) -> Response:
        Notification.objects.filter(user=cast(User, request.user), read_at=None).update(
            read_at=timezone.now()
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["알림"])
class PushTokenCreateView(APIView):
    @extend_schema(
        summary="푸시 토큰 등록",
        description=(
            "로그인한 기기의 푸시 토큰을 등록한다. 같은 토큰이 이미 있으면 새로 만들지 않고 "
            "지금 로그인한 계정으로 옮긴다(한 기기에서 계정을 바꿔 로그인한 경우). "
            "응답의 `id`는 로그아웃 때 토큰 삭제에 쓴다."
        ),
        request=PushTokenSerializer,
        responses={
            201: PushTokenSerializer,
            400: error_response("`VALIDATION_ERROR`: 토큰 512자 초과, 지원하지 않는 platform"),
        },
    )
    def post(self, request: Request) -> Response:
        serializer = PushTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token, _ = PushToken.objects.update_or_create(
            token=serializer.validated_data["token"],
            defaults={
                "user": cast(User, request.user),
                "platform": serializer.validated_data["platform"],
            },
        )
        return Response(PushTokenSerializer(token).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["알림"])
class PushTokenDeleteView(APIView):
    @extend_schema(
        summary="푸시 토큰 삭제",
        description=(
            "로그아웃하거나 푸시를 끈 기기의 토큰을 지운다. 경로의 `id`는 등록 응답의 id다."
        ),
        responses={
            204: OpenApiResponse(description="삭제 완료"),
            404: error_response("`NOT_FOUND`: 없는 토큰이거나 내 토큰이 아님"),
        },
    )
    def delete(self, request: Request, pk: int) -> Response:
        get_object_or_404(PushToken, pk=pk, user=cast(User, request.user)).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
