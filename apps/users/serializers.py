from typing import Any

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers, status

from apps.regions.models import Region
from apps.regions.serializers import RegionSerializer
from apps.stamps.models import UserStamp
from apps.stamps.serializers import StampSerializer
from apps.stamps.services import FIRST_DIARY
from config.exceptions import ApiError

from .models import EmailVerification, User
from .verification import is_school_email

NICKNAME_MIN_LENGTH = 2
NICKNAME_MAX_LENGTH = 10
MAX_HOMETOWNS = 3


def validate_nickname(value: str, exclude_user_id: int | None = None) -> str:
    nickname = value.strip()
    if not NICKNAME_MIN_LENGTH <= len(nickname) <= NICKNAME_MAX_LENGTH:
        raise ApiError("INVALID_NICKNAME", "닉네임은 2~10자로 입력해 주세요.")
    taken = User.objects.filter(nickname=nickname)
    if exclude_user_id is not None:
        taken = taken.exclude(id=exclude_user_id)
    if taken.exists():
        raise ApiError("NICKNAME_TAKEN", "이미 사용 중인 닉네임입니다.", status.HTTP_409_CONFLICT)
    return nickname


class SchoolEmailField(serializers.EmailField):
    def to_internal_value(self, data: Any) -> str:
        email = super().to_internal_value(data).lower()
        if not is_school_email(email):
            raise ApiError("INVALID_SCHOOL_EMAIL", "학교 메일(ac.kr)만 사용할 수 있습니다.")
        return str(email)


class EmailSendSerializer(serializers.Serializer[Any]):
    email = SchoolEmailField()
    purpose = serializers.ChoiceField(choices=EmailVerification.Purpose.choices)


class EmailSendResultSerializer(serializers.Serializer[Any]):
    expires_at = serializers.DateTimeField()
    resend_available_seconds = serializers.IntegerField()


class EmailVerifySerializer(EmailSendSerializer):
    code = serializers.CharField(min_length=6, max_length=6)


class RegionSelectionSerializer(serializers.Serializer[Any]):
    hometown_region_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Region.objects.select_related("parent"), allow_empty=False
    )
    residence_region_id = serializers.PrimaryKeyRelatedField(
        queryset=Region.objects.select_related("parent")
    )

    def validate_hometown_region_ids(self, regions: list[Region]) -> list[Region]:
        unique = list({region.id: region for region in regions}.values())
        if len(unique) > MAX_HOMETOWNS:
            raise serializers.ValidationError("본가 지역은 최대 3곳까지 고를 수 있습니다.")
        if not all(region.can_be_hometown for region in unique):
            raise serializers.ValidationError("광역시·특별시 또는 시·군만 본가로 고를 수 있습니다.")
        return unique

    def validate_residence_region_id(self, region: Region) -> Region:
        if not region.can_be_residence:
            raise serializers.ValidationError("시·군·구 단위로 거주 지역을 골라 주세요.")
        return region


class TermsSerializer(serializers.Serializer[Any]):
    service = serializers.BooleanField()
    privacy = serializers.BooleanField()
    age_over_14 = serializers.BooleanField()
    marketing = serializers.BooleanField(default=False)

    def validate(self, attrs: dict[str, bool]) -> dict[str, bool]:
        if not (attrs["service"] and attrs["privacy"] and attrs["age_over_14"]):
            raise ApiError("TERMS_REQUIRED", "필수 약관에 모두 동의해 주세요.")
        return attrs


class SignupSerializer(RegionSelectionSerializer):
    signup_token = serializers.CharField()
    nickname = serializers.CharField()
    terms = TermsSerializer()

    def validate_nickname(self, value: str) -> str:
        return validate_nickname(value)


class UserSerializer(serializers.ModelSerializer[User]):
    """로그인한 본인에게만 내려주는 정보. 이메일은 다른 사용자에게 노출하지 않는다."""

    hometowns = RegionSerializer(many=True, read_only=True)
    residence = RegionSerializer(read_only=True)
    school_verified = serializers.SerializerMethodField()
    first_diary_completed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "nickname",
            "school_verified",
            "hometowns",
            "residence",
            "first_diary_completed",
        ]
        read_only_fields = fields

    def get_school_verified(self, user: User) -> bool:
        return True

    def get_first_diary_completed(self, user: User) -> bool:
        return UserStamp.objects.filter(user=user, stamp__code=FIRST_DIARY).exists()


class TokenPairSerializer(serializers.Serializer[Any]):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()


class SignupResultSerializer(TokenPairSerializer):
    granted_stamps = StampSerializer(many=True)


class VerifyResultSerializer(serializers.Serializer[Any]):
    """signup이면 signup_token만, login이면 access·refresh·user만 채운다."""

    signup_token = serializers.CharField(required=False)
    access = serializers.CharField(required=False)
    refresh = serializers.CharField(required=False)
    user = UserSerializer(required=False)


class NicknameCheckSerializer(serializers.Serializer[Any]):
    available = serializers.BooleanField()
    code = serializers.CharField(allow_null=True)


class LogoutSerializer(serializers.Serializer[Any]):
    refresh = serializers.CharField()


class MeStatsSerializer(serializers.Serializer[Any]):
    diary_count = serializers.IntegerField()
    letter_count = serializers.IntegerField()
    stamp_count = serializers.IntegerField()
    penpal_count = serializers.IntegerField()
    draft_count = serializers.IntegerField()


class MeSerializer(UserSerializer):
    stats = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = [*UserSerializer.Meta.fields, "stats"]
        read_only_fields = fields

    @extend_schema_field(MeStatsSerializer)
    def get_stats(self, user: User) -> dict[str, int]:
        return {
            "diary_count": user.diaries.count(),
            "stamp_count": user.stamps.count(),
            # letters 앱이 생기면 실제 값으로 바꾼다 (SET-01).
            "letter_count": 0,
            "penpal_count": 0,
            "draft_count": 0,
        }


class NicknameUpdateSerializer(serializers.Serializer[Any]):
    nickname = serializers.CharField()


class UserSettingsSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = [
            "letter_paused",
            "push_enabled",
            "daily_digest_enabled",
            "weekly_prompt_enabled",
        ]
