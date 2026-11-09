from functools import partial
from typing import Any, cast

from django.conf import settings
from django.db import IntegrityError, transaction
from drf_spectacular.utils import OpenApiParameter, extend_schema
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


class EmailSendView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=EmailSendSerializer, responses={200: EmailSendResultSerializer})
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


class EmailVerifyView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=EmailVerifySerializer, responses={200: VerifyResultSerializer})
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


class NicknameCheckView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[OpenApiParameter("nickname", str, required=True)],
        responses={200: NicknameCheckSerializer},
    )
    def get(self, request: Request) -> Response:
        try:
            validate_nickname(request.query_params.get("nickname", ""))
        except ApiError as exc:
            return Response({"available": False, "code": exc.error_code})
        return Response({"available": True, "code": None})


class SignupView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=SignupSerializer, responses={201: SignupResultSerializer})
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


class LogoutView(APIView):
    @extend_schema(request=LogoutSerializer, responses={204: None})
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


class MeView(APIView):
    @extend_schema(responses={200: MeSerializer})
    def get(self, request: Request) -> Response:
        return Response(MeSerializer(cast(User, request.user)).data)

    @extend_schema(request=NicknameUpdateSerializer, responses={200: MeSerializer})
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

    @extend_schema(responses={204: None})
    def delete(self, request: Request) -> Response:
        """탈퇴하면 일기·우표 등 소유 데이터를 함께 지운다 (AUTH-11)."""
        user = cast(User, request.user)
        images = [diary.image for diary in user.diaries.exclude(image="").exclude(image=None)]
        with transaction.atomic():
            for image in images:
                storage, name = image.storage, str(image.name)
                transaction.on_commit(partial(storage.delete, name))
            user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyRegionsView(APIView):
    @extend_schema(request=RegionSelectionSerializer, responses={200: MeSerializer})
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


class MySettingsView(APIView):
    @extend_schema(responses={200: UserSettingsSerializer})
    def get(self, request: Request) -> Response:
        return Response(UserSettingsSerializer(cast(User, request.user)).data)

    @extend_schema(request=UserSettingsSerializer, responses={200: UserSettingsSerializer})
    def patch(self, request: Request) -> Response:
        serializer = UserSettingsSerializer(
            cast(User, request.user), data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
