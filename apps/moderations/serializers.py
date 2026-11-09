from typing import Any

from rest_framework import serializers

from apps.users.models import User

from .models import Block, Report


class ReportCreateSerializer(serializers.Serializer[Any]):
    target_type = serializers.ChoiceField(choices=Report.TargetType.choices)
    target_id = serializers.IntegerField(min_value=1)
    reason = serializers.ChoiceField(choices=Report.Reason.choices)
    detail = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    block_user = serializers.BooleanField(default=False)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["reason"] == Report.Reason.ETC and not attrs["detail"].strip():
            raise serializers.ValidationError({"detail": "기타 사유를 입력해 주세요."})
        return attrs


class ReportResultSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    blocked = serializers.BooleanField()


class BlockCreateSerializer(serializers.Serializer[Any]):
    user_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())


class BlockedUserSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = ["id", "nickname"]
        read_only_fields = fields


class BlockSerializer(serializers.ModelSerializer[Block]):
    user = BlockedUserSerializer(source="blocked", read_only=True)

    class Meta:
        model = Block
        fields = ["user", "created_at"]
        read_only_fields = fields


class ContactCheckSerializer(serializers.Serializer[Any]):
    text = serializers.CharField(allow_blank=True, trim_whitespace=False)


class ContactCheckResultSerializer(serializers.Serializer[Any]):
    has_contact = serializers.BooleanField()
    types = serializers.ListField(child=serializers.CharField())
