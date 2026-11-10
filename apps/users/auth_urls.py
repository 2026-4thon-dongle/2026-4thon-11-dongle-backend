from django.urls import path
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.views import TokenRefreshView

from config.schema import error_response

from .views import EmailSendView, EmailVerifyView, LogoutView, NicknameCheckView, SignupView

# simplejwt 기본 뷰라서 Swagger 설명만 여기서 붙인다.
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
            200: TokenRefreshSerializer,
            400: error_response("`VALIDATION_ERROR`: refresh 값이 없음"),
            401: error_response(
                "`TOKEN_NOT_VALID`: 만료·폐기된 refresh 토큰. 다시 로그인해야 한다"
            ),
        },
    )
)(TokenRefreshView)

urlpatterns = [
    path("email/send/", EmailSendView.as_view(), name="auth-email-send"),
    path("email/verify/", EmailVerifyView.as_view(), name="auth-email-verify"),
    path("nickname/check/", NicknameCheckView.as_view(), name="auth-nickname-check"),
    path("signup/", SignupView.as_view(), name="auth-signup"),
    path("token/refresh/", DocumentedTokenRefreshView.as_view(), name="auth-token-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
]
