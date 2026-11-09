from typing import Any

from django.core.files.uploadedfile import UploadedFile
from rest_framework import serializers

from apps.regions.serializers import RegionSerializer
from apps.stamps.serializers import StampSerializer
from apps.users.models import User

from .models import BODY_MAX_LENGTH, Diary, DiaryPrompt

IMAGE_MAX_BYTES = 5 * 1024 * 1024
IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}


class AuthorSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = ["id", "nickname"]
        read_only_fields = fields


class DiarySerializer(serializers.ModelSerializer[Diary]):
    author = AuthorSerializer(read_only=True)
    region = RegionSerializer(read_only=True)
    received_letter_count = serializers.SerializerMethodField()

    class Meta:
        model = Diary
        fields = [
            "id",
            "author",
            "region",
            "body",
            "image",
            "accepts_letters",
            "visibility",
            "received_letter_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_received_letter_count(self, diary: Diary) -> int:
        # letters 앱이 생기면 일기별 받은 편지 수로 바꾼다 (DIARY-07).
        return 0


class DiaryWriteSerializer(serializers.ModelSerializer[Diary]):
    body = serializers.CharField(max_length=BODY_MAX_LENGTH)
    remove_image = serializers.BooleanField(write_only=True, required=False, default=False)
    # multipart에서 값이 빠지면 DRF가 False로 읽으므로 기본값을 명시한다 (DIARY-02: 기본 ON).
    accepts_letters = serializers.BooleanField(required=False, default=True)

    class Meta:
        model = Diary
        fields = ["body", "image", "remove_image", "accepts_letters", "visibility"]

    def validate_image(self, image: UploadedFile | None) -> UploadedFile | None:
        if image is None:
            return image
        if image.size is not None and image.size > IMAGE_MAX_BYTES:
            raise serializers.ValidationError("사진은 5MB까지 올릴 수 있습니다.")
        if getattr(getattr(image, "image", None), "format", None) not in IMAGE_FORMATS:
            raise serializers.ValidationError("JPEG, PNG, WEBP 사진만 올릴 수 있습니다.")
        return image

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs.get("remove_image") and attrs.get("image"):
            raise serializers.ValidationError("사진 업로드와 삭제를 함께 요청할 수 없습니다.")
        return attrs


class DiaryCreateResultSerializer(DiarySerializer):
    granted_stamps = StampSerializer(many=True, read_only=True)

    class Meta(DiarySerializer.Meta):
        fields = [*DiarySerializer.Meta.fields, "granted_stamps"]
        read_only_fields = fields


class DiaryPromptSerializer(serializers.ModelSerializer[DiaryPrompt]):
    class Meta:
        model = DiaryPrompt
        fields = ["id", "text"]
        read_only_fields = fields
