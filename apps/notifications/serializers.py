from typing import Any

from rest_framework import serializers

from .models import Notification, PushToken


class NotificationSerializer(serializers.ModelSerializer[Notification]):
    class Meta:
        model = Notification
        fields = ["id", "type", "title", "body", "target_id", "read_at", "created_at"]
        read_only_fields = fields


class UnreadCountSerializer(serializers.Serializer[Any]):
    unread_count = serializers.IntegerField()


class PushTokenSerializer(serializers.ModelSerializer[PushToken]):
    # 같은 기기로 다른 계정에 로그인하면 소유자를 옮겨야 하므로 unique 검사를 뷰에 맡긴다.
    token = serializers.CharField(max_length=512)

    class Meta:
        model = PushToken
        fields = ["id", "token", "platform"]
        read_only_fields = ["id"]
