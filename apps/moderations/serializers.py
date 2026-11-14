from typing import Any

from rest_framework import serializers

from apps.regions.serializers import RegionSerializer
from apps.users.models import User

from .models import Block, Report


class ReportCreateSerializer(serializers.Serializer[Any]):
    target_type = serializers.ChoiceField(
        choices=Report.TargetType.choices,
        help_text="신고 대상 종류. diary: 일기 / user: 사용자 / letter: 받은 편지",
    )
    target_id = serializers.IntegerField(min_value=1, help_text="신고 대상(일기·사용자·편지)의 id")
    reason = serializers.ChoiceField(
        choices=Report.Reason.choices,
        help_text="abuse: 욕설 · 비하 / sexual: 성적인 내용 / "
        "personal_info: 연락처 · 개인정보 요구 / spam: 광고 · 도배 / etc: 기타 (직접 입력)",
    )
    detail = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
        default="",
        help_text="상세 사유 (최대 200자). reason이 etc면 필수",
    )
    block_user = serializers.BooleanField(default=False, help_text="true면 대상 사용자도 함께 차단")

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["reason"] == Report.Reason.ETC and not attrs["detail"].strip():
            raise serializers.ValidationError({"detail": "기타 사유를 입력해 주세요."})
        return attrs


class ReportResultSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField(help_text="신고 id")
    blocked = serializers.BooleanField(help_text="함께 차단했는지")


class BlockCreateSerializer(serializers.Serializer[Any]):
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), help_text="차단할 사용자 id"
    )


class BlockedUserSerializer(serializers.ModelSerializer[User]):
    residence = RegionSerializer(
        read_only=True, help_text="상대의 거주 지역. 차단 카드의 「경북 경주」. 설정 전이면 null"
    )

    class Meta:
        model = User
        fields = ["id", "nickname", "residence"]
        read_only_fields = fields


class BlockSerializer(serializers.ModelSerializer[Block]):
    user = BlockedUserSerializer(source="blocked", read_only=True, help_text="차단한 사용자")

    class Meta:
        model = Block
        fields = ["user", "created_at"]
        read_only_fields = fields
        extra_kwargs = {"created_at": {"help_text": "차단한 시각"}}


class ContactCheckSerializer(serializers.Serializer[Any]):
    text = serializers.CharField(allow_blank=True, trim_whitespace=False, help_text="검사할 본문")


class ContactCheckResultSerializer(serializers.Serializer[Any]):
    has_contact = serializers.BooleanField(help_text="연락처가 하나라도 있으면 true")
    types = serializers.ListField(
        child=serializers.CharField(),
        help_text="찾은 연락처 종류. phone / email / kakao / instagram",
    )
