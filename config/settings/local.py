"""로컬 개발 설정. .env가 없어도 manage.py check와 mypy가 돌도록 기본값을 둔다."""

from .base import *

SECRET_KEY = env("SECRET_KEY", default="django-insecure-local-only")
DEBUG = env.bool("DEBUG", default=True)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

DATABASES = {
    "default": env.db("DATABASE_URL", default="postgres://postgres:postgres@localhost:5432/dongle"),
}

# .env에 EMAIL_HOST가 있으면 그 SMTP(가상 메일함 Mailpit 등)로 보내고,
# 없으면 인증 코드를 runserver 콘솔에 출력한다.
if env("EMAIL_HOST", default=""):
    EMAIL_HOST = env("EMAIL_HOST")
    EMAIL_PORT = env.int("EMAIL_PORT", default=1025)
    EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
    EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
    EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=False)
    EMAIL_TIMEOUT = 10
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
