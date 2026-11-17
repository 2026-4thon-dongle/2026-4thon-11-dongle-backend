from functools import partial
from typing import Any, cast

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.stamps.serializers import StampSerializer
from apps.stamps.services import FIRST_STEP, grant_stamp
from config.exceptions import ApiError
from config.schema import error_response

from . import verification
from .models import EmailVerification, TermsAgreement, User
from .serializers import (
    EmailSendResultSerializer,
    EmailSendSerializer,
    EmailVerifySerializer,
    LogoutSerializer,
    MeSerializer,
    NicknameCheckSerializer,
    NicknameUpdateSerializer,
    RegionSelectionSerializer,
    SignupResultSerializer,
    SignupSerializer,
    UserSerializer,
    UserSettingsSerializer,
    VerifyResultSerializer,
    validate_nickname,
)


def _token_payload(user: User) -> dict[str, Any]:
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": UserSerializer(user).data,
    }


@extend_schema(tags=["인증"])
class EmailSendView(APIView):
    permission_classes = [AllowAny]
    # 공개 API는 Authorization 헤더를 보지 않는다. 만료된 토큰이 붙어도 401을 내지 않는다
    authentication_classes = []

    @extend_schema(
        summary="인증 코드 메일 발송",
        description=(
            "학교 메일(`ac.kr`)로 6자리 인증 코드를 보낸다. 로그인 없이 호출한다.\n\n"
            "- `purpose=signup`: 아직 가입하지 않은 메일만 받는다.\n"
            "- `purpose=login`: 이미 가입한 메일만 받는다.\n"
            "- 코드는 5분 동안 유효하고, 같은 메일·목적으로는 60초가 지나야 다시 보낼 수 있다.\n"
            "- 다시 보내면 이전 코드는 더 이상 쓸 수 없다."
        ),
        request=EmailSendSerializer,
        responses={
            200: EmailSendResultSerializer,
            400: error_response("`INVALID_SCHOOL_EMAIL`: 학교 메일이 아님 / `VALIDATION_ERROR`"),
            404: error_response("`ACCOUNT_NOT_FOUND`: login인데 가입하지 않은 메일"),
            409: error_response("`EMAIL_ALREADY_REGISTERED`: signup인데 이미 가입한 메일"),
            429: error_response(
                "`CODE_RESEND_TOO_SOON`: 60초 안에 다시 요청함. "
                "`retry_after_seconds`(초)가 함께 내려온다."
            ),
            503: error_response("`EMAIL_SEND_FAILED`: 메일 서버 오류로 발송 실패"),
        },
    )
    def post(self, request: Request) -> Response:
        serializer = EmailSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email, purpose = serializer.validated_data["email"], serializer.validated_data["purpose"]

        exists = User.objects.filter(email=email).exists()
        if purpose == EmailVerification.Purpose.SIGNUP and exists:
            raise ApiError(
                "EMAIL_ALREADY_REGISTERED", "이미 가입한 메일입니다.", status.HTTP_409_CONFLICT
            )
        if purpose == EmailVerification.Purpose.LOGIN and not exists:
            raise ApiError(
                "ACCOUNT_NOT_FOUND", "가입하지 않은 메일입니다.", status.HTTP_404_NOT_FOUND
            )

        sent = verification.send_code(email, purpose)
        result = EmailSendResultSerializer(
            {
                "expires_at": sent.expires_at,
                "resend_available_seconds": int(verification.RESEND_INTERVAL.total_seconds()),
            }
        )
        return Response(result.data)


@extend_schema(tags=["인증"])
class EmailVerifyView(APIView):
    permission_classes = [AllowAny]
    # 공개 API는 Authorization 헤더를 보지 않는다. 만료된 토큰이 붙어도 401을 내지 않는다
    authentication_classes = []

    @extend_schema(
        summary="인증 코드 확인 (회원가입 토큰 발급 / 로그인)",
        description=(
            "메일로 받은 6자리 코드를 확인한다. 코드는 한 번 맞히면 사라진다.\n\n"
            "- `purpose=signup`: `signup_token`만 돌려준다. 이 값을 회원가입 API에 넣는다.\n"
            "- `purpose=login`: `access`, `refresh`, `user`를 돌려준다. 이것이 로그인이다.\n"
            "- 코드는 5번까지 틀릴 수 있다. 넘으면 코드를 다시 받아야 한다."
        ),
        request=EmailVerifySerializer,
        responses={
            200: VerifyResultSerializer,
            400: error_response(
                "`CODE_NOT_FOUND`: 코드를 요청한 적 없음 / `CODE_EXPIRED`: 5분 지남 / "
                "`CODE_ATTEMPTS_EXCEEDED`: 5번 넘게 틀림 / "
                "`INVALID_CODE`: 코드 불일치, `remaining_attempts`(남은 횟수)가 함께 내려온다 / "
                "`INVALID_SCHOOL_EMAIL` / `VALIDATION_ERROR`"
            ),
            404: error_response("`ACCOUNT_NOT_FOUND`: login인데 그 사이 탈퇴한 계정"),
        },
    )
    def post(self, request: Request) -> Response:
        serializer = EmailVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        verification.verify_code(data["email"], data["purpose"], data["code"])

        if data["purpose"] == EmailVerification.Purpose.SIGNUP:
            return Response({"signup_token": verification.make_signup_token(data["email"])})

        user = User.objects.filter(email=data["email"]).first()
        if user is None:
            raise ApiError(
                "ACCOUNT_NOT_FOUND", "가입하지 않은 메일입니다.", status.HTTP_404_NOT_FOUND
            )
        return Response(_token_payload(user))


@extend_schema(tags=["인증"])
class NicknameCheckView(APIView):
    permission_classes = [AllowAny]
    # 공개 API는 Authorization 헤더를 보지 않는다. 만료된 토큰이 붙어도 401을 내지 않는다
    authentication_classes = []

    @extend_schema(
        summary="닉네임 사용 가능 여부 확인",
        description=(
            "가입 화면에서 닉네임 중복·길이를 미리 확인한다. 쓸 수 없어도 에러가 아닌 200으로 "
            "`available=false`와 이유 `code`를 돌려준다. 앞뒤 공백은 빼고 검사한다."
        ),
        parameters=[
            OpenApiParameter("nickname", str, required=True, description="확인할 닉네임 (2~10자)")
        ],
        responses={200: NicknameCheckSerializer},
    )
    def get(self, request: Request) -> Response:
        try:
            validate_nickname(request.query_params.get("nickname", ""))
        except ApiError as exc:
            return Response({"available": False, "code": exc.error_code})
        return Response({"available": True, "code": None})


@extend_schema(tags=["인증"])
class SignupView(APIView):
    permission_classes = [AllowAny]
    # 공개 API는 Authorization 헤더를 보지 않는다. 만료된 토큰이 붙어도 401을 내지 않는다
    authentication_classes = []

    @extend_schema(
        summary="회원가입",
        description=(
            "메일 인증으로 받은 `signup_token`과 닉네임·지역·약관 동의로 계정을 만들고 바로 "
            "로그인 토큰을 돌려준다.\n\n"
            "- 본가 지역은 1~3곳, 광역시·특별시 또는 도의 시·군만 고를 수 있다.\n"
            "- 거주 지역은 시·군·구 단위만 고를 수 있다(세종은 시·도 자체).\n"
            "- 서비스·개인정보·만 14세 이상 약관은 모두 `true`여야 한다.\n"
            "- 가입하면 '첫 걸음' 우표가 지급되어 `granted_stamps`에 담긴다."
        ),
        request=SignupSerializer,
        responses={
            201: SignupResultSerializer,
            400: error_response(
                "`INVALID_SIGNUP_TOKEN`: 토큰이 틀렸거나 만료됨, 메일 인증부터 다시 / "
                "`INVALID_NICKNAME`: 2~10자가 아님 / `TERMS_REQUIRED`: 필수 약관 미동의 / "
                "`VALIDATION_ERROR`: 지역 선택 규칙 위반 등"
            ),
            409: error_response(
                "`NICKNAME_TAKEN`: 사용 중인 닉네임 / "
                "`ACCOUNT_CONFLICT`: 동시에 같은 메일·닉네임으로 가입됨"
            ),
        },
    )
    def post(self, request: Request) -> Response:
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        email = verification.read_signup_token(data["signup_token"])

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    email=email,
                    nickname=data["nickname"],
                    residence=data["residence_region_id"],
                )
                user.hometowns.set(data["hometown_region_ids"])
                TermsAgreement.objects.create(
                    user=user, version=settings.TERMS_VERSION, marketing=data["terms"]["marketing"]
                )
                stamp = grant_stamp(user, FIRST_STEP)
        except IntegrityError as exc:
            raise ApiError(
                "ACCOUNT_CONFLICT",
                "이미 가입한 메일이거나 사용 중인 닉네임입니다.",
                status.HTTP_409_CONFLICT,
            ) from exc

        payload = _token_payload(user)
        payload["granted_stamps"] = StampSerializer([stamp] if stamp else [], many=True).data
        return Response(payload, status=status.HTTP_201_CREATED)


@extend_schema(tags=["인증"])
class LogoutView(APIView):
    @extend_schema(
        summary="로그아웃",
        description=(
            "refresh 토큰을 폐기해 더 이상 재발급에 쓰지 못하게 한다. "
            "access 토큰은 만료(1시간)될 때까지 유효하므로 FE에서도 지운다."
        ),
        request=LogoutSerializer,
        responses={
            204: OpenApiResponse(description="로그아웃 완료"),
            400: error_response(
                "`INVALID_REFRESH_TOKEN`: 만료·폐기됐거나 다른 사용자의 refresh 토큰"
            ),
        },
    )
    def post(self, request: Request) -> Response:
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token = RefreshToken(serializer.validated_data["refresh"])
            if str(token["user_id"]) != str(request.user.pk):
                raise ApiError("INVALID_REFRESH_TOKEN", "유효하지 않은 토큰입니다.")
            token.blacklist()
        except TokenError as exc:
            raise ApiError("INVALID_REFRESH_TOKEN", "유효하지 않은 토큰입니다.") from exc
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["내 정보"])
class MeView(APIView):
    @extend_schema(
        summary="마이 페이지 조회",
        description="내 계정 정보와 활동 수(`stats`)를 돌려준다.",
        responses={200: MeSerializer},
    )
    def get(self, request: Request) -> Response:
        return Response(MeSerializer(cast(User, request.user)).data)

    @extend_schema(
        summary="닉네임 변경",
        description="닉네임만 바꾼다. 지금 내 닉네임과 같으면 그대로 성공한다.",
        request=NicknameUpdateSerializer,
        responses={
            200: MeSerializer,
            400: error_response("`INVALID_NICKNAME`: 2~10자가 아님 / `VALIDATION_ERROR`"),
            409: error_response("`NICKNAME_TAKEN`: 다른 사람이 쓰는 닉네임"),
        },
    )
    def patch(self, request: Request) -> Response:
        user = cast(User, request.user)
        serializer = NicknameUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.nickname = validate_nickname(
            serializer.validated_data["nickname"], exclude_user_id=user.pk
        )
        try:
            with transaction.atomic():
                user.save(update_fields=["nickname"])
        except IntegrityError as exc:
            raise ApiError(
                "NICKNAME_TAKEN", "이미 사용 중인 닉네임입니다.", status.HTTP_409_CONFLICT
            ) from exc
        return Response(MeSerializer(user).data)

    @extend_schema(
        summary="회원 탈퇴",
        description=(
            "계정을 바로 지운다. 내가 쓴 일기와 사진, 받은 우표, 알림 등 내 데이터도 함께 "
            "지워지며 되돌릴 수 없다. 주고받은 편지와 대화도 지워져 상대 우체통에서도 사라진다."
        ),
        responses={204: OpenApiResponse(description="탈퇴 완료")},
    )
    def delete(self, request: Request) -> Response:
        """탈퇴하면 일기·우표 등 소유 데이터를 함께 지운다 (AUTH-11)."""
        # letters가 users를 쓰므로 순환 import를 피해 여기서 불러온다.
        from apps.letters.models import Letter

        user = cast(User, request.user)
        images = [diary.image for diary in user.diaries.exclude(image="").exclude(image=None)]
        # 내가 주고받은 편지는 대화와 함께 지워지므로 손글씨 이미지도 지운다.
        letters = Letter.objects.filter(Q(sender=user) | Q(recipient=user))
        images += [
            letter.signature for letter in letters.exclude(signature="").exclude(signature=None)
        ]
        with transaction.atomic():
            for image in images:
                storage, name = image.storage, str(image.name)
                transaction.on_commit(partial(storage.delete, name))
            user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["내 정보"])
class MyRegionsView(APIView):
    @extend_schema(
        summary="본가·거주 지역 변경",
        description=(
            "본가 지역 목록과 거주 지역을 통째로 바꾼다(부분 수정 아님). 선택 규칙은 회원가입과 "
            "같다. 이미 쓴 일기의 지역은 바뀌지 않고, 앞으로 쓰는 일기부터 새 거주 지역이 붙는다."
        ),
        request=RegionSelectionSerializer,
        responses={
            200: MeSerializer,
            400: error_response("`VALIDATION_ERROR`: 없는 지역이거나 지역 선택 규칙 위반"),
        },
    )
    def put(self, request: Request) -> Response:
        """이미 쓴 일기의 지역은 바뀌지 않는다 (SET-07)."""
        user = cast(User, request.user)
        serializer = RegionSelectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            user.residence = serializer.validated_data["residence_region_id"]
            user.save(update_fields=["residence"])
            user.hometowns.set(serializer.validated_data["hometown_region_ids"])
        return Response(MeSerializer(user).data)


@extend_schema(tags=["내 정보"])
class MySettingsView(APIView):
    @extend_schema(
        summary="설정 조회",
        description="편지 받기 일시정지와 알림 설정을 돌려준다.",
        responses={200: UserSettingsSerializer},
    )
    def get(self, request: Request) -> Response:
        return Response(UserSettingsSerializer(cast(User, request.user)).data)

    @extend_schema(
        summary="설정 변경",
        description="보낸 항목만 바꾼다(부분 수정).",
        request=UserSettingsSerializer,
        responses={
            200: UserSettingsSerializer,
            400: error_response("`VALIDATION_ERROR`: boolean이 아닌 값"),
        },
    )
    def patch(self, request: Request) -> Response:
        serializer = UserSettingsSerializer(
            cast(User, request.user), data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
