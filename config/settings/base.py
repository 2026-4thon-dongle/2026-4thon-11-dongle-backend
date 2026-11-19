"""공통 설정. 환경별 값은 local.py / prod.py에서 정한다."""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "drf_spectacular",
]

# 도메인 앱은 apps/ 아래에 만들고 여기에 "apps.<name>" 형태로 등록한다.
LOCAL_APPS: list[str] = [
    "apps.regions",
    "apps.users",
    "apps.stamps",
    "apps.moderations",
    "apps.diaries",
    "apps.notifications",
    "apps.letters",
    "apps.feeds",
    "apps.games",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

AUTH_USER_MODEL = "users.User"

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
# 컨테이너에서는 영구 저장소 경로를 MEDIA_ROOT 환경변수로 준다.
MEDIA_ROOT = Path(env("MEDIA_ROOT", default=str(BASE_DIR / "media")))
# DEBUG=False에서도 /media/를 Django가 직접 준다(시연 규모용). 트래픽이 늘면 별도 서버로 옮긴다.
SERVE_MEDIA = env.bool("SERVE_MEDIA", default=False)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "config.renderers.LocalTimeJSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "config.exceptions.api_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Dongle Backend API",
    "DESCRIPTION": (
        "고향 교환 펜팔 서비스 동글의 백엔드 API.\n\n"
        "- 인증: 로그인·회원가입으로 받은 `access` 토큰을 "
        "`Authorization: Bearer <access>` 헤더에 담는다. "
        "오른쪽 위 **Authorize**에 access 값만 넣으면 된다.\n"
        "- 공개 API(인증 메일, 닉네임 확인, 회원가입, 토큰 재발급, 지역 목록)를 뺀 "
        "모든 API는 로그인이 필요하며, 토큰이 없거나 만료되면 401을 돌려준다.\n"
        "- 에러는 모두 `{code, message}` 형식이다. 입력값 검사 실패는 "
        "`code=VALIDATION_ERROR`이고 `errors`에 필드별 메시지가 담긴다.\n"
        "- 목록 API는 `?page=` 페이지네이션(한 페이지 20개)을 쓴다.\n"
        "- 시간은 모두 Asia/Seoul 기준 ISO 8601 문자열이다."
    ),
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "TAGS": [
        {"name": "인증", "description": "학교 메일 인증, 회원가입, 로그인, 토큰 재발급, 로그아웃"},
        {"name": "내 정보", "description": "마이 페이지, 닉네임·지역·설정 변경, 탈퇴"},
        {"name": "지역", "description": "본가·거주 지역 선택용 시·도/시·군·구 목록"},
        {"name": "일기", "description": "고향 일기 작성·조회·수정·삭제, 오늘의 글감"},
        {"name": "신고·차단", "description": "신고, 차단, 연락처 노출 검사"},
        {"name": "알림", "description": "알림 센터, 푸시 토큰"},
        {"name": "피드", "description": "고향 ↔ 타지 피드, 전체 타지 피드, 피드 일기 상세"},
        {"name": "편지", "description": "편지 쓰기 재료, 배송 시간, 편지 보내기"},
        {"name": "우체통", "description": "우체통 탭, 편지 열람·넘기기, 대화 기록, 펜팔 친구"},
        {"name": "우표", "description": "우표첩, 우표 상세, 수집 보상"},
    ],
}

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
# https 뒤에서 admin 같은 폼을 쓸 때 필요하다. 예: https://dongle-api.zanviq.dev
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="동글 <no-reply@dongle.local>")

# 시연 주소(실제로 없는 메일)로 가는 인증 메일은 실제 SMTP를 켜도
# 이 SMTP(가상 메일함 Mailpit)로 보낸다. DEMO_EMAIL_HOST가 비어 있으면 기본 메일 설정을 따른다.
DEMO_EMAIL_HOST = env("DEMO_EMAIL_HOST", default="")
DEMO_EMAIL_PORT = env.int("DEMO_EMAIL_PORT", default=1025)
DEMO_EMAIL_DOMAINS = [
    domain.lower()
    for domain in env.list("DEMO_EMAIL_DOMAINS", default=["dongle-demo.ac.kr", "guest-demo.ac.kr"])
]

# 학교 메일(ac.kr)이 아니어도 가입·로그인을 허용할 주소(실제 메일 발송 시연용). 쉼표로 구분한다.
# 주소는 저장소에 적지 않고 환경변수로 넣는다.
EXTRA_ALLOWED_EMAILS = [
    email.strip().lower() for email in env.list("EXTRA_ALLOWED_EMAILS", default=[]) if email.strip()
]

# 약관을 고치면 올린다. 동의 시점의 버전을 TermsAgreement에 저장한다.
TERMS_VERSION = "2026-11-09"

# 느린 편지 도착 시간. 같은 시·도 1시간 / 인접 3시간 / 300km 미만 6시간 / 그 이상·제주 12시간.
# 시연 때 True로 두면 모든 편지가 1분 뒤 도착한다.
LETTER_DEMO_MODE = env.bool("LETTER_DEMO_MODE", default=False)
