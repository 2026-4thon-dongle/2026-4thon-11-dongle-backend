FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

# 호스팅 플랫폼의 저장공간 소유자(1000)와 맞춘다.
RUN useradd --uid 1000 --create-home app
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY --chown=app:app . .

# 정적 파일은 이미지를 만들 때 모은다. collectstatic은 DB에 연결하지 않으므로 값은 자리표시다.
RUN SECRET_KEY=build-only ALLOWED_HOSTS=build DATABASE_URL=sqlite:////tmp/build.db EMAIL_HOST=build \
    python manage.py collectstatic --noinput \
    && mkdir -p /app/media \
    && chown -R app:app /app/staticfiles /app/media

USER app
EXPOSE 8000

# ALLOWED_HOSTS에 127.0.0.1이 들어 있어야 한다. 지역 목록은 공개 API라 로그인 없이 확인된다.
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/regions/', timeout=4)"

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-"]
