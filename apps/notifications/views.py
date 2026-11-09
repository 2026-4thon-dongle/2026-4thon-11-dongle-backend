from typing import cast

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.models import User

from .models import Notification, PushToken
from .serializers import NotificationSerializer, PushTokenSerializer, UnreadCountSerializer


class NotificationListView(generics.ListAPIView[Notification]):
    serializer_class = NotificationSerializer

    def get_queryset(self) -> QuerySet[Notification]:
        return Notification.objects.filter(user=cast(User, self.request.user))


class UnreadCountView(APIView):
    @extend_schema(responses={200: UnreadCountSerializer})
    def get(self, request: Request) -> Response:
        count = Notification.objects.filter(user=cast(User, request.user), read_at=None).count()
        return Response({"unread_count": count})


class NotificationReadView(APIView):
    @extend_schema(request=None, responses={200: NotificationSerializer})
    def post(self, request: Request, pk: int) -> Response:
        notification = get_object_or_404(Notification, pk=pk, user=cast(User, request.user))
        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=["read_at"])
        return Response(NotificationSerializer(notification).data)


class NotificationReadAllView(APIView):
    @extend_schema(request=None, responses={204: None})
    def post(self, request: Request) -> Response:
        Notification.objects.filter(user=cast(User, request.user), read_at=None).update(
            read_at=timezone.now()
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class PushTokenCreateView(APIView):
    @extend_schema(request=PushTokenSerializer, responses={201: PushTokenSerializer})
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


class PushTokenDeleteView(APIView):
    @extend_schema(responses={204: None})
    def delete(self, request: Request, pk: int) -> Response:
        get_object_or_404(PushToken, pk=pk, user=cast(User, request.user)).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
