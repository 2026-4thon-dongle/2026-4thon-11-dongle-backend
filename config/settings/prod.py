"""배포 설정. 모든 비밀값은 환경변수로만 받는다."""

from .base import *

SECRET_KEY = env("SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

DATABASES = {"default": env.db("DATABASE_URL")}

# 정적 파일(admin, Swagger)은 whitenoise가 준다. collectstatic은 이미지를 빌드할 때 돌린다.
MIDDLEWARE = [MIDDLEWARE[0], "whitenoise.middleware.WhiteNoiseMiddleware", *MIDDLEWARE[1:]]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HTTPS는 앞단(Cloudflare 터널)에서 끝난다. 헬스체크는 http://127.0.0.1:8000 으로 들어오므로
# SECURE_SSL_REDIRECT를 켜면 헬스체크가 301을 받아 배포가 실패한다. 켜지 않고 경고(W008)만 끈다.
# 배포 도메인(*.dev)은 브라우저의 HSTS preload 목록에 있어 브라우저는 처음부터 https로 접속한다.
# HSTS의 includeSubDomains·preload는 도메인 전체에 영향을 주므로 켜지 않는다(W005·W021).
SILENCED_SYSTEM_CHECKS = ["security.W005", "security.W008", "security.W021"]
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=86400)

# 기본은 가상 메일함 Mailpit(인증 없음, TLS 없음, 1025). 실제 SMTP를 쓰면 아래 값을 모두 넣는다.
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = env.int("EMAIL_PORT", default=1025)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=False)
EMAIL_TIMEOUT = 10
