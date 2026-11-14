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
from .verification import is_school_email, school_name_of

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
    email = SchoolEmailField(help_text="학교 메일(ac.kr). 대소문자는 구분하지 않는다.")
    purpose = serializers.ChoiceField(
        choices=EmailVerification.Purpose.choices,
        help_text="signup: 회원가입용, login: 로그인용",
    )


class EmailSendResultSerializer(serializers.Serializer[Any]):
    expires_at = serializers.DateTimeField(help_text="인증 코드 만료 시각 (발송 5분 뒤)")
    resend_available_seconds = serializers.IntegerField(
        help_text="다시 보내기 버튼을 켜기까지 기다릴 초"
    )


class EmailVerifySerializer(EmailSendSerializer):
    code = serializers.CharField(min_length=6, max_length=6, help_text="메일로 받은 6자리 숫자")


class RegionSelectionSerializer(serializers.Serializer[Any]):
    hometown_region_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Region.objects.select_related("parent"),
        allow_empty=False,
        help_text="본가 지역 id 1~3개. can_be_hometown이 true인 지역만 고를 수 있다.",
    )
    residence_region_id = serializers.PrimaryKeyRelatedField(
        queryset=Region.objects.select_related("parent"),
        help_text="지금 사는 지역 id. can_be_residence가 true인 지역만 고를 수 있다.",
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
    service = serializers.BooleanField(help_text="(필수) 서비스 이용약관 동의")
    privacy = serializers.BooleanField(help_text="(필수) 개인정보 수집·이용 동의")
    age_over_14 = serializers.BooleanField(help_text="(필수) 만 14세 이상 확인")
    marketing = serializers.BooleanField(default=False, help_text="(선택) 마케팅 정보 수신 동의")

    def validate(self, attrs: dict[str, bool]) -> dict[str, bool]:
        if not (attrs["service"] and attrs["privacy"] and attrs["age_over_14"]):
            raise ApiError("TERMS_REQUIRED", "필수 약관에 모두 동의해 주세요.")
        return attrs


class SignupSerializer(RegionSelectionSerializer):
    signup_token = serializers.CharField(help_text="인증 코드 확인(purpose=signup)에서 받은 토큰")
    nickname = serializers.CharField(help_text="2~10자 닉네임. 앞뒤 공백은 지운다.")
    terms = TermsSerializer(help_text="약관 동의 여부")

    def validate_nickname(self, value: str) -> str:
        return validate_nickname(value)


class UserSerializer(serializers.ModelSerializer[User]):
    """로그인한 본인에게만 내려주는 정보. 이메일은 다른 사용자에게 노출하지 않는다."""

    hometowns = RegionSerializer(many=True, read_only=True, help_text="본가 지역 (최대 3곳)")
    residence = RegionSerializer(read_only=True, help_text="거주 지역. 설정 전이면 null")
    school_verified = serializers.SerializerMethodField(
        help_text="학교 메일 인증 여부. 메일 인증으로만 가입하므로 항상 true"
    )
    school_name = serializers.SerializerMethodField(
        help_text="메일 도메인으로 찾은 학교 약칭(예: 성신여대). 참가 대학이 아니면 null"
    )
    first_diary_completed = serializers.SerializerMethodField(
        help_text="첫 일기를 썼는지. false면 첫 일기 작성 안내를 보여 준다."
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "nickname",
            "school_verified",
            "school_name",
            "hometowns",
            "residence",
            "first_diary_completed",
            "avatar",
        ]
        read_only_fields = fields
        extra_kwargs = {
            "email": {"help_text": "가입한 학교 메일. 본인에게만 내려준다."},
            "nickname": {"help_text": "닉네임"},
            "avatar": {"help_text": "프로필 고향이 표정 code. 예: cat-wink (가입 때 무작위)"},
        }

    def get_school_verified(self, user: User) -> bool:
        return True

    def get_school_name(self, user: User) -> str | None:
        return school_name_of(user.email)

    def get_first_diary_completed(self, user: User) -> bool:
        return UserStamp.objects.filter(user=user, stamp__code=FIRST_DIARY).exists()


class TokenPairSerializer(serializers.Serializer[Any]):
    access = serializers.CharField(help_text="API 호출용 access 토큰 (1시간 유효)")
    refresh = serializers.CharField(help_text="access 재발급용 refresh 토큰 (14일 유효)")
    user = UserSerializer(help_text="로그인한 사용자 정보")


class SignupResultSerializer(TokenPairSerializer):
    granted_stamps = StampSerializer(
        many=True, help_text="이번 요청으로 새로 받은 우표. 비어 있으면 획득 모달을 띄우지 않는다."
    )


class VerifyResultSerializer(serializers.Serializer[Any]):
    """signup이면 signup_token만, login이면 access·refresh·user만 채운다."""

    signup_token = serializers.CharField(
        required=False, help_text="(signup일 때만) 회원가입 API에 넣을 토큰"
    )
    access = serializers.CharField(required=False, help_text="(login일 때만) access 토큰")
    refresh = serializers.CharField(required=False, help_text="(login일 때만) refresh 토큰")
    user = UserSerializer(required=False, help_text="(login일 때만) 사용자 정보")


class NicknameCheckSerializer(serializers.Serializer[Any]):
    available = serializers.BooleanField(help_text="사용할 수 있으면 true")
    code = serializers.CharField(
        allow_null=True,
        help_text="쓸 수 없는 이유. INVALID_NICKNAME(2~10자 아님) / NICKNAME_TAKEN(사용 중). "
        "사용 가능하면 null",
    )


class LogoutSerializer(serializers.Serializer[Any]):
    refresh = serializers.CharField(help_text="폐기할 refresh 토큰")


class MeStatsSerializer(serializers.Serializer[Any]):
    diary_count = serializers.IntegerField(help_text="쓴 일기 수")
    letter_count = serializers.IntegerField(help_text="편지 수 (편지 기능 전까지 0)")
    stamp_count = serializers.IntegerField(help_text="모은 우표 수")
    penpal_count = serializers.IntegerField(help_text="펜팔 친구 수 (기능 전까지 0)")
    draft_count = serializers.IntegerField(help_text="임시 저장한 편지 수 (기능 전까지 0)")


class MeSerializer(UserSerializer):
    stats = serializers.SerializerMethodField(help_text="마이 페이지 활동 수")

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
    nickname = serializers.CharField(help_text="새 닉네임 (2~10자)")


class UserSettingsSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = [
            "letter_paused",
            "push_enabled",
            "daily_digest_enabled",
            "weekly_prompt_enabled",
            "letter_arrival_push_enabled",
            "letter_departure_push_enabled",
        ]
        extra_kwargs = {
            "letter_paused": {"help_text": "편지 받기 일시정지. true면 새 편지를 받지 않는다."},
            "push_enabled": {"help_text": "푸시 알림 받기"},
            "daily_digest_enabled": {"help_text": "하루 한 번 이메일 알림 받기"},
            "weekly_prompt_enabled": {"help_text": "주간 글감 알림 받기"},
            "letter_arrival_push_enabled": {"help_text": "편지 도착 알림 받기"},
            "letter_departure_push_enabled": {
                "help_text": "나에게 오는 편지가 출발했을 때 알림 받기"
            },
        }
