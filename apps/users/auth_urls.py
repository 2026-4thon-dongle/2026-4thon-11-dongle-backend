from django.urls import path
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework_simplejwt.views import TokenRefreshView

from config.schema import error_response

from .serializers import SafeTokenRefreshSerializer
from .views import EmailSendView, EmailVerifyView, LogoutView, NicknameCheckView, SignupView


class SafeTokenRefreshView(TokenRefreshView):
    """탈퇴한 계정의 refresh 토큰을 401로 거절하는 재발급 뷰."""

    serializer_class = SafeTokenRefreshSerializer


# simplejwt 기본 뷰를 감싼 것이라 Swagger 설명만 여기서 붙인다.
DocumentedTokenRefreshView = extend_schema_view(
    post=extend_schema(
        tags=["인증"],
        summary="토큰 재발급",
        description=(
            "refresh 토큰으로 새 access 토큰을 받는다. access는 1시간, refresh는 14일 유효하다. "
            "재발급할 때마다 refresh도 새로 나오고 이전 refresh는 폐기되므로, "
            "응답의 `refresh`로 저장된 값을 바꿔야 한다."
        ),
        responses={
            200: SafeTokenRefreshSerializer,
            400: error_response("`VALIDATION_ERROR`: refresh 값이 없음"),
            401: error_response(
                "`TOKEN_NOT_VALID`: 만료·폐기된 refresh 토큰이거나 탈퇴한 계정. "
                "다시 로그인해야 한다"
            ),
        },
    )
)(SafeTokenRefreshView)

urlpatterns = [
    path("email/send/", EmailSendView.as_view(), name="auth-email-send"),
    path("email/verify/", EmailVerifyView.as_view(), name="auth-email-verify"),
    path("nickname/check/", NicknameCheckView.as_view(), name="auth-nickname-check"),
    path("signup/", SignupView.as_view(), name="auth-signup"),
    path("token/refresh/", DocumentedTokenRefreshView.as_view(), name="auth-token-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
]
