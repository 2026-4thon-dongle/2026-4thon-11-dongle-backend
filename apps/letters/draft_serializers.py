from typing import Any

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.stamps.serializers import UserBriefSerializer

from .mailbox import preview
from .models import BODY_MAX_LENGTH, Draft
from .serializers import FONT_CODES, STATIONERY_CODES


def draft_recipient(draft: Draft) -> dict[str, Any]:
    """받을 사람. 첫 편지는 일기 작성자, 답장은 받은 편지를 보낸 사람."""
    if draft.diary is not None:
        return {"id": draft.diary.author_id, "nickname": draft.diary.author.nickname}
    assert draft.reply_to is not None
    return {"id": draft.reply_to.sender_id, "nickname": draft.reply_to.sender_nickname}


class DraftWriteSerializer(serializers.Serializer[Any]):
    diary_id = serializers.IntegerField(required=False, help_text="첫 편지 대상 일기 id")
    reply_to = serializers.IntegerField(required=False, help_text="답장 대상 받은 편지 id")
    body = serializers.CharField(
        max_length=BODY_MAX_LENGTH,
        required=False,
        allow_blank=True,
        default="",
        trim_whitespace=False,
        help_text="본문 (0~1000자)",
    )
    stationery = serializers.ChoiceField(
        STATIONERY_CODES, required=False, allow_blank=True, default="", help_text="편지지 code"
    )
    font = serializers.ChoiceField(
        FONT_CODES, required=False, allow_blank=True, default="", help_text="글씨체 code"
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if ("diary_id" in attrs) == ("reply_to" in attrs):
            raise serializers.ValidationError("diary_id와 reply_to 중 하나만 보내 주세요.")
        return attrs


class _DraftBaseSerializer(serializers.ModelSerializer[Draft]):
    kind = serializers.CharField(read_only=True, help_text="first: 첫 편지 / reply: 답장")
    diary_id = serializers.IntegerField(
        read_only=True, allow_null=True, help_text="첫 편지 대상 일기 id"
    )
    reply_to = serializers.IntegerField(
        source="reply_to_id", read_only=True, allow_null=True, help_text="답장 대상 편지 id"
    )
    recipient = serializers.SerializerMethodField(help_text="받을 사람")

    @extend_schema_field(UserBriefSerializer)
    def get_recipient(self, draft: Draft) -> dict[str, Any]:
        return draft_recipient(draft)


class DraftListItemSerializer(_DraftBaseSerializer):
    body_preview = serializers.SerializerMethodField(help_text="본문 앞부분")
    body_length = serializers.SerializerMethodField(help_text="본문 글자 수")

    class Meta:
        model = Draft
        fields = [
            "id",
            "kind",
            "diary_id",
            "reply_to",
            "recipient",
            "body_preview",
            "body_length",
            "saved_at",
        ]
        read_only_fields = fields

    def get_body_preview(self, draft: Draft) -> str:
        return preview(draft.body)

    def get_body_length(self, draft: Draft) -> int:
        return len(draft.body)


class DraftSerializer(_DraftBaseSerializer):
    class Meta:
        model = Draft
        fields = [
            "id",
            "kind",
            "diary_id",
            "reply_to",
            "recipient",
            "body",
            "stationery",
            "font",
            "saved_at",
        ]
        read_only_fields = fields
