from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import EmailSendView, EmailVerifyView, LogoutView, NicknameCheckView, SignupView

urlpatterns = [
    path("email/send/", EmailSendView.as_view(), name="auth-email-send"),
    path("email/verify/", EmailVerifyView.as_view(), name="auth-email-verify"),
    path("nickname/check/", NicknameCheckView.as_view(), name="auth-nickname-check"),
    path("signup/", SignupView.as_view(), name="auth-signup"),
    path("token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
]
