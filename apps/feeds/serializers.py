from typing import Any

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.diaries.models import Diary
from apps.diaries.serializers import AuthorSerializer
from apps.letters.serializers import EstimateSerializer
from apps.regions.serializers import RegionWithSidoSerializer

from .queries import reply_block_reason


class FeedDiarySerializer(serializers.ModelSerializer[Diary]):
    author = AuthorSerializer(read_only=True, help_text="작성자")
    region = RegionWithSidoSerializer(read_only=True, help_text="일기를 쓴 지역 (sido는 소인용)")
    can_reply = serializers.SerializerMethodField(
        help_text="내가 이 일기에 첫 편지를 보낼 수 있는지"
    )

    class Meta:
        model = Diary
        fields = [
            "id",
            "author",
            "region",
            "body",
            "image",
            "accepts_letters",
            "can_reply",
            "created_at",
        ]
        read_only_fields = fields
        extra_kwargs = {
            "image": {"help_text": "사진 URL. 없으면 null (프론트가 지역 기본 이미지)"},
        }

    def get_can_reply(self, diary: Diary) -> bool:
        return reply_block_reason(diary, self.context["request"].user) is None


class DraftBriefSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    body_preview = serializers.CharField()
    saved_at = serializers.DateTimeField()


class FeedDiaryDetailSerializer(FeedDiarySerializer):
    reply_block_reason = serializers.SerializerMethodField(
        help_text="can_reply가 false인 이유. own_diary / letters_off / recipient_paused / "
        "already_sent. 보낼 수 있으면 null"
    )
    delivery = serializers.SerializerMethodField(
        help_text="내 거주지 → 작성자 거주지 예상 배송. 내 일기거나 계산할 수 없으면 null"
    )
    my_draft = serializers.SerializerMethodField(
        help_text="이 일기에 임시저장한 편지. 없으면 null (4-9 이어 쓰기 배너)"
    )

    class Meta(FeedDiarySerializer.Meta):
        fields = [*FeedDiarySerializer.Meta.fields, "reply_block_reason", "delivery", "my_draft"]
        read_only_fields = fields

    def get_reply_block_reason(self, diary: Diary) -> str | None:
        return reply_block_reason(diary, self.context["request"].user)

    @extend_schema_field(EstimateSerializer(allow_null=True))
    def get_delivery(self, diary: Diary) -> dict[str, Any] | None:
        return self.context.get("delivery")

    @extend_schema_field(DraftBriefSerializer(allow_null=True))
    def get_my_draft(self, diary: Diary) -> dict[str, Any] | None:
        return self.context.get("my_draft")


class FeedSummarySerializer(serializers.Serializer[Any]):
    hometowns = RegionWithSidoSerializer(many=True, help_text="내 본가 지역 (칩 필터용)")
    new_count = serializers.IntegerField(help_text="마지막 확인 이후 올라온 고향 일기 수")
    last_seen_at = serializers.DateTimeField(allow_null=True, help_text="마지막 확인 시각")
