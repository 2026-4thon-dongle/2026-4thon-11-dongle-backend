"""로컬 개발 설정. .env가 없어도 manage.py check와 mypy가 돌도록 기본값을 둔다."""

from .base import *

SECRET_KEY = env("SECRET_KEY", default="django-insecure-local-only")
DEBUG = env.bool("DEBUG", default=True)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

DATABASES = {
    "default": env.db("DATABASE_URL", default="postgres://postgres:postgres@localhost:5432/dongle"),
}
