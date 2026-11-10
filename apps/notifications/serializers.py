from typing import Any

from rest_framework import serializers

from .models import Notification, PushToken


class NotificationSerializer(serializers.ModelSerializer[Notification]):
    class Meta:
        model = Notification
        fields = ["id", "type", "title", "body", "target_id", "read_at", "created_at"]
        read_only_fields = fields
        extra_kwargs = {
            "type": {
                "help_text": "letter_arrived: 편지 도착 / letter_location: 배송 위치 / "
                "round_trip: 왕복 완료 / prompt: 글감"
            },
            "title": {"help_text": "알림 제목"},
            "body": {"help_text": "알림 내용"},
            "target_id": {
                "help_text": "눌렀을 때 이동할 대상 id (type에 따라 편지 등). 없으면 null"
            },
            "read_at": {"help_text": "읽은 시각. 읽지 않았으면 null"},
            "created_at": {"help_text": "알림 생성 시각"},
        }


class UnreadCountSerializer(serializers.Serializer[Any]):
    unread_count = serializers.IntegerField(help_text="읽지 않은 알림 수")


class PushTokenSerializer(serializers.ModelSerializer[PushToken]):
    # 같은 기기로 다른 계정에 로그인하면 소유자를 옮겨야 하므로 unique 검사를 뷰에 맡긴다.
    token = serializers.CharField(max_length=512, help_text="기기의 푸시 토큰 (최대 512자)")

    class Meta:
        model = PushToken
        fields = ["id", "token", "platform"]
        read_only_fields = ["id"]
        extra_kwargs = {"platform": {"help_text": "기기 종류. web / ios / android"}}
