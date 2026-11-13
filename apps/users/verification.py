"""학교 메일 인증 코드 발송·검증과 가입 토큰 (AUTH-04, 05, 10)."""

import re
import secrets
from datetime import timedelta
from smtplib import SMTPException

from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac
from rest_framework import status

from config.exceptions import ApiError

from .models import EmailVerification

SCHOOL_EMAIL_RE = re.compile(r"^[^@\s]+@([a-z0-9-]+\.)+ac\.kr$")
CODE_LIFETIME = timedelta(minutes=5)
RESEND_INTERVAL = timedelta(seconds=60)
MAX_ATTEMPTS = 5
SIGNUP_TOKEN_MAX_AGE_SECONDS = 30 * 60
SIGNUP_TOKEN_SALT = "dongle.signup-token"

# 마이 페이지 「OO 인증 완료」에 쓰는 학교 약칭 (SET-01). 4호선톤 참가 대학만 둔다.
SCHOOL_NAMES = {
    "kookmin.ac.kr": "국민대",
    "duksung.ac.kr": "덕성여대",
    "dongguk.ac.kr": "동국대",
    "dgu.ac.kr": "동국대",
    "skuniv.ac.kr": "서경대",
    "seoultech.ac.kr": "서울과기대",
    "sungshin.ac.kr": "성신여대",
    "sookmyung.ac.kr": "숙명여대",
    "sm.ac.kr": "숙명여대",
    "hansung.ac.kr": "한성대",
}


def is_school_email(email: str) -> bool:
    return SCHOOL_EMAIL_RE.match(email) is not None


def school_name_of(email: str) -> str | None:
    """메일 도메인으로 학교 약칭을 찾는다. 하위 도메인도 같은 학교로 본다. 모르면 None."""
    domain = email.rsplit("@", 1)[-1].lower()
    for school_domain, name in SCHOOL_NAMES.items():
        if domain == school_domain or domain.endswith(f".{school_domain}"):
            return name
    return None


def _hash_code(email: str, purpose: str, code: str) -> str:
    return salted_hmac("dongle.email-code", f"{email}:{purpose}:{code}").hexdigest()


def send_code(email: str, purpose: str) -> EmailVerification:
    now = timezone.now()
    previous = EmailVerification.objects.filter(email=email, purpose=purpose).first()
    if previous is not None:
        wait = previous.created_at + RESEND_INTERVAL - now
        if wait > timedelta(0):
            raise ApiError(
                "CODE_RESEND_TOO_SOON",
                "잠시 후 다시 요청해 주세요.",
                status.HTTP_429_TOO_MANY_REQUESTS,
                retry_after_seconds=int(wait.total_seconds()) + 1,
            )

    code = f"{secrets.randbelow(1_000_000):06d}"
    with transaction.atomic():
        EmailVerification.objects.filter(email=email, purpose=purpose).delete()
        verification = EmailVerification.objects.create(
            email=email,
            purpose=purpose,
            code_hash=_hash_code(email, purpose, code),
            attempts_left=MAX_ATTEMPTS,
            expires_at=now + CODE_LIFETIME,
        )
    try:
        send_mail(
            subject="[동글] 인증 코드",
            message=f"인증 코드는 {code} 입니다. 5분 안에 입력해 주세요.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
        )
    except (SMTPException, OSError) as exc:
        verification.delete()
        raise ApiError(
            "EMAIL_SEND_FAILED",
            "인증 메일을 보내지 못했습니다. 잠시 후 다시 시도해 주세요.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc
    return verification


def verify_code(email: str, purpose: str, code: str) -> None:
    """코드를 확인하고 소모한다. 시도 횟수 차감이 롤백되지 않도록 에러는 트랜잭션 밖에서 낸다."""
    error: ApiError | None = None
    with transaction.atomic():
        verification = (
            EmailVerification.objects.select_for_update()
            .filter(email=email, purpose=purpose)
            .first()
        )
        if verification is None:
            error = ApiError("CODE_NOT_FOUND", "인증 코드를 먼저 요청해 주세요.")
        elif verification.expires_at <= timezone.now():
            error = ApiError("CODE_EXPIRED", "인증 코드가 만료되었습니다.")
        elif verification.attempts_left == 0:
            error = ApiError(
                "CODE_ATTEMPTS_EXCEEDED", "입력 횟수를 넘었습니다. 코드를 다시 받아 주세요."
            )
        elif constant_time_compare(verification.code_hash, _hash_code(email, purpose, code)):
            verification.delete()
        else:
            verification.attempts_left -= 1
            verification.save(update_fields=["attempts_left"])
            error = ApiError(
                "INVALID_CODE",
                "인증 코드가 일치하지 않습니다.",
                remaining_attempts=verification.attempts_left,
            )
    if error is not None:
        raise error


def make_signup_token(email: str) -> str:
    return signing.dumps({"email": email}, salt=SIGNUP_TOKEN_SALT)


def read_signup_token(token: str) -> str:
    try:
        payload = signing.loads(token, salt=SIGNUP_TOKEN_SALT, max_age=SIGNUP_TOKEN_MAX_AGE_SECONDS)
    except signing.BadSignature as exc:
        raise ApiError("INVALID_SIGNUP_TOKEN", "메일 인증을 다시 진행해 주세요.") from exc
    return str(payload["email"])
