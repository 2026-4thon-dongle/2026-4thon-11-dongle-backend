import json
import math
from typing import Any

from django.core.files.uploadedfile import UploadedFile
from rest_framework import serializers

from apps.regions.serializers import RegionWithSidoSerializer
from apps.stamps.rewards import FONTS, STATIONERIES, STICKERS
from apps.stamps.serializers import RewardSerializer, StampSerializer, UserBriefSerializer

from .models import BODY_MAX_LENGTH, Letter

SIGNATURE_MAX_BYTES = 1024 * 1024
STICKERS_MAX = 5
STICKER_DEFAULT_SCALE = 0.18
STICKER_SCALE_MIN = 0.05
STICKER_SCALE_MAX = 0.5
DEFAULT_FONT = "nanum-pen"
STATIONERY_CODES = [item.code for item in STATIONERIES]
FONT_CODES = [item.code for item in FONTS]
STICKER_CODES = {item.code for item in STICKERS}


class StampBriefSerializer(StampSerializer):
    class Meta(StampSerializer.Meta):
        fields = ["code", "number", "name"]
        read_only_fields = fields


class LetterWriteSerializer(serializers.Serializer[Any]):
    diary_id = serializers.IntegerField(required=False, help_text="첫 편지를 보낼 일기 id")
    reply_to = serializers.IntegerField(required=False, help_text="답장할 받은 편지 id")
    body = serializers.CharField(max_length=BODY_MAX_LENGTH, help_text="본문 (1~1000자)")
    stationery = serializers.ChoiceField(STATIONERY_CODES, help_text="편지지 code")
    font = serializers.ChoiceField(
        FONT_CODES, required=False, default=DEFAULT_FONT, help_text="글씨체 code (기본 nanum-pen)"
    )
    signature = serializers.ImageField(
        required=False, allow_null=True, help_text="손글씨 서명 PNG, 1MB 이하"
    )
    stickers = serializers.JSONField(
        required=False,
        default=list,
        help_text='붙인 스티커. [{"code": "cat-wink", "x": 0.7, "y": 0.8, "rotation": -8, '
        '"scale": 0.18}] 최대 5개. `scale`은 편지지 너비 대비 스티커 너비 비율(0.05~0.5, '
        "생략하면 0.18). multipart로 보낼 때는 JSON 문자열",
    )
    stamp = serializers.CharField(help_text="붙일 우표 code (보유한 우표)")
    draft_id = serializers.IntegerField(
        required=False, help_text="이어 쓴 임시저장 id. 발송하면 지운다"
    )

    def validate_signature(self, image: UploadedFile | None) -> UploadedFile | None:
        if image is None:
            return image
        if image.size is not None and image.size > SIGNATURE_MAX_BYTES:
            raise serializers.ValidationError("서명 이미지는 1MB까지 올릴 수 있습니다.")
        if getattr(getattr(image, "image", None), "format", None) != "PNG":
            raise serializers.ValidationError("서명은 PNG만 올릴 수 있습니다.")
        return image

    def validate_stickers(self, value: Any) -> list[dict[str, Any]]:
        if isinstance(value, str):
            try:
                value = json.loads(value or "[]")
            except json.JSONDecodeError as exc:
                raise serializers.ValidationError("스티커 형식이 올바르지 않습니다.") from exc
        if not isinstance(value, list) or len(value) > STICKERS_MAX:
            raise serializers.ValidationError(f"스티커는 {STICKERS_MAX}개까지 붙일 수 있습니다.")
        cleaned = []
        for sticker in value:
            try:
                code, x, y = sticker["code"], float(sticker["x"]), float(sticker["y"])
                rotation = float(sticker.get("rotation", 0))
                scale = float(sticker.get("scale", STICKER_DEFAULT_SCALE))
            except (TypeError, KeyError, ValueError) as exc:
                raise serializers.ValidationError("스티커 형식이 올바르지 않습니다.") from exc
            # code가 리스트·객체면 set 검사에서 TypeError가 나고, nan·inf는 JSON으로 저장할 수 없다
            if not isinstance(code, str) or not all(
                math.isfinite(number) for number in (x, y, rotation, scale)
            ):
                raise serializers.ValidationError("스티커 형식이 올바르지 않습니다.")
            if code not in STICKER_CODES or not (0 <= x <= 1 and 0 <= y <= 1):
                raise serializers.ValidationError("스티커 형식이 올바르지 않습니다.")
            if not (STICKER_SCALE_MIN <= scale <= STICKER_SCALE_MAX):
                raise serializers.ValidationError(
                    f"스티커 크기(scale)는 {STICKER_SCALE_MIN}~{STICKER_SCALE_MAX} 사이여야 합니다."
                )
            cleaned.append({"code": code, "x": x, "y": y, "rotation": rotation, "scale": scale})
        return cleaned

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if ("diary_id" in attrs) == ("reply_to" in attrs):
            raise serializers.ValidationError("diary_id와 reply_to 중 하나만 보내 주세요.")
        if not attrs["body"].strip():
            raise serializers.ValidationError({"body": ["본문을 입력해 주세요."]})
        return attrs


class LetterSentSerializer(serializers.ModelSerializer[Letter]):
    conversation_id = serializers.IntegerField(help_text="대화 id")
    recipient = UserBriefSerializer(help_text="받는 사람")
    from_region = RegionWithSidoSerializer(help_text="출발 지역 (내 거주지)")
    to_region = RegionWithSidoSerializer(help_text="도착 지역 (받는 사람 거주지)")
    stamp = StampBriefSerializer(help_text="붙인 우표")
    granted_stamps = StampSerializer(many=True, help_text="새로 받은 우표")
    unlocked_rewards = RewardSerializer(many=True, help_text="새로 열린 수집 보상")

    class Meta:
        model = Letter
        fields = [
            "id",
            "conversation_id",
            "is_first",
            "recipient",
            "from_region",
            "to_region",
            "band",
            "duration_minutes",
            "sent_at",
            "arrives_at",
            "stamp",
            "granted_stamps",
            "unlocked_rewards",
        ]
        read_only_fields = fields


class MaterialItemSerializer(serializers.Serializer[Any]):
    code = serializers.CharField()
    name = serializers.CharField()
    unlocked = serializers.BooleanField()
    unlock_condition = serializers.CharField(
        allow_null=True, help_text="잠겼을 때 문구. 예: 우표 15개"
    )


class StationeryItemSerializer(MaterialItemSerializer):
    is_new = serializers.BooleanField(help_text="보상으로 열렸고 아직 해금 모달을 확인하지 않음")


class OwnedStampSerializer(StampBriefSerializer):
    class Meta(StampSerializer.Meta):
        fields = ["code", "number", "name", "kind"]
        read_only_fields = fields


class MaterialsSerializer(serializers.Serializer[Any]):
    stationeries = StationeryItemSerializer(many=True)
    fonts = MaterialItemSerializer(many=True)
    stickers = MaterialItemSerializer(many=True)
    stamps = OwnedStampSerializer(many=True, help_text="보유 우표 (받은 순)")


class EstimateSerializer(serializers.Serializer[Any]):
    from_region = RegionWithSidoSerializer()
    to_region = RegionWithSidoSerializer()
    band = serializers.ChoiceField(Letter.Band.choices)
    duration_minutes = serializers.IntegerField(help_text="소요 시간(분). 데모 모드면 1")
    arrives_at = serializers.DateTimeField(help_text="지금 보내면 도착하는 시각")
