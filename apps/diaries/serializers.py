from typing import Any

from django.core.files.uploadedfile import UploadedFile
from django.utils import timezone
from rest_framework import serializers

from apps.regions.serializers import RegionSerializer
from apps.stamps.serializers import StampSerializer
from apps.users.models import User

from .models import BODY_MAX_LENGTH, Diary, DiaryPrompt

IMAGE_MAX_BYTES = 5 * 1024 * 1024
# 휴대폰 카메라 JPEG 중 여러 장 그림 정보(MPF)가 든 파일은 Pillow가 MPO로 읽는다. 파일은 JPEG다.
IMAGE_FORMATS = {"JPEG", "MPO", "PNG", "WEBP"}


class AuthorSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = ["id", "nickname"]
        read_only_fields = fields
        extra_kwargs = {"nickname": {"help_text": "작성자 닉네임"}}


class DiarySerializer(serializers.ModelSerializer[Diary]):
    author = AuthorSerializer(read_only=True, help_text="작성자")
    region = RegionSerializer(read_only=True, help_text="일기를 쓴 지역 (작성 당시 거주 지역)")
    received_letter_count = serializers.SerializerMethodField(
        help_text="이 일기로 받은 편지 수 (도착한 첫 편지만 센다)"
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
            "visibility",
            "received_letter_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
        extra_kwargs = {
            "body": {"help_text": "일기 본문 (최대 500자)"},
            "image": {"help_text": "사진 URL. 사진이 없으면 null"},
            "accepts_letters": {"help_text": "이 일기로 편지를 받을지"},
            "visibility": {
                "help_text": "공개 범위. all: 모두에게 / same_hometown: 같은 고향 사람에게만 / "
                "private: 나만 보기"
            },
            "created_at": {"help_text": "작성 시각"},
            "updated_at": {"help_text": "마지막 수정 시각"},
        }

    def get_received_letter_count(self, diary: Diary) -> int:
        # 내 일기 목록은 queryset에서 미리 센 값을 쓴다.
        annotated = getattr(diary, "received_letters_annotated", None)
        if annotated is not None:
            return int(annotated)
        # letters가 diaries를 쓰므로 순환 import를 피해 여기서 불러온다.
        from apps.letters.models import Letter

        # 이 일기에 도착한 첫 편지 수. 배송 중인 편지는 세지 않는다 (DIARY-07).
        return Letter.objects.filter(
            conversation__diary=diary, is_first=True, arrives_at__lte=timezone.now()
        ).count()


class DiaryWriteSerializer(serializers.ModelSerializer[Diary]):
    body = serializers.CharField(max_length=BODY_MAX_LENGTH, help_text="일기 본문 (최대 500자)")
    remove_image = serializers.BooleanField(
        write_only=True,
        required=False,
        default=False,
        help_text="(수정 때만) true면 지금 사진을 지운다. image와 함께 보낼 수 없다.",
    )
    # multipart에서 값이 빠지면 DRF가 False로 읽으므로 기본값을 명시한다 (DIARY-02: 기본 ON).
    accepts_letters = serializers.BooleanField(
        required=False, default=True, help_text="이 일기로 편지를 받을지 (기본 true)"
    )

    class Meta:
        model = Diary
        fields = ["body", "image", "remove_image", "accepts_letters", "visibility"]
        extra_kwargs = {
            "image": {"help_text": "사진 1장. JPEG·PNG·WEBP, 5MB 이하"},
            "visibility": {
                "help_text": "공개 범위 (기본 all). all: 모두에게 / "
                "same_hometown: 같은 고향 사람에게만 / private: 나만 보기"
            },
        }

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
    granted_stamps = StampSerializer(
        many=True,
        read_only=True,
        help_text="이번 요청으로 새로 받은 우표. 비어 있으면 획득 모달을 띄우지 않는다.",
    )

    class Meta(DiarySerializer.Meta):
        fields = [*DiarySerializer.Meta.fields, "granted_stamps"]
        read_only_fields = fields


class DiaryPromptSerializer(serializers.ModelSerializer[DiaryPrompt]):
    class Meta:
        model = DiaryPrompt
        fields = ["id", "text"]
        read_only_fields = fields
        extra_kwargs = {"text": {"help_text": "글감 문구"}}
