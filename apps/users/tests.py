import re
from datetime import timedelta
from typing import Any

from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.regions.models import Region
from apps.stamps.models import UserStamp

from .models import EmailVerification, TermsAgreement, User

EMAIL = "Student@skuniv.ac.kr"
NORMALIZED_EMAIL = "student@skuniv.ac.kr"


def regions() -> tuple[Region, Region]:
    return Region.objects.get(name="서울특별시"), Region.objects.get(
        parent__name="충청남도", name="천안시"
    )


def make_user(email: str = "a@skuniv.ac.kr", nickname: str = "민호") -> User:
    home, residence = regions()
    user = User.objects.create_user(email=email, nickname=nickname, residence=residence)
    user.hometowns.set([home])
    return user


class AuthTestCase(TestCase):
    def setUp(self) -> None:
        self.client: APIClient = APIClient()

    def send(self, email: str = EMAIL, purpose: str = "signup") -> Any:
        return self.client.post(
            reverse("auth-email-send"), {"email": email, "purpose": purpose}, format="json"
        )

    def verify(self, code: str, email: str = EMAIL, purpose: str = "signup") -> Any:
        return self.client.post(
            reverse("auth-email-verify"),
            {"email": email, "purpose": purpose, "code": code},
            format="json",
        )

    def last_code(self) -> str:
        match = re.search(r"\d{6}", str(mail.outbox[-1].body))
        assert match is not None
        return match.group()

    def signup_payload(self, token: str, **overrides: Any) -> dict[str, Any]:
        home, residence = regions()
        payload = {
            "signup_token": token,
            "nickname": "민호",
            "hometown_region_ids": [home.id],
            "residence_region_id": residence.id,
            "terms": {"service": True, "privacy": True, "age_over_14": True, "marketing": False},
        }
        payload.update(overrides)
        return payload


class EmailCodeTests(AuthTestCase):
    def test_rejects_non_school_email(self) -> None:
        response = self.send("someone@gmail.com")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "INVALID_SCHOOL_EMAIL")
        self.assertEqual(self.send("someone@ac.kr.evil.com").data["code"], "INVALID_SCHOOL_EMAIL")

    def test_code_is_not_stored_in_plain_text(self) -> None:
        self.assertEqual(self.send().status_code, 200)
        stored = EmailVerification.objects.get(email=NORMALIZED_EMAIL)
        self.assertNotIn(self.last_code(), stored.code_hash)

    def test_resend_cooldown(self) -> None:
        self.send()
        response = self.send()
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.data["code"], "CODE_RESEND_TOO_SOON")
        self.assertGreater(response.data["retry_after_seconds"], 0)

    def test_resend_replaces_previous_code(self) -> None:
        self.send()
        old_code = self.last_code()
        EmailVerification.objects.update(created_at=timezone.now() - timedelta(minutes=2))
        self.send()
        new_code = self.last_code()
        if old_code != new_code:
            self.assertEqual(self.verify(old_code).data["code"], "INVALID_CODE")
        self.assertEqual(self.verify(new_code).status_code, 200)

    def test_wrong_code_reduces_attempts_and_persists(self) -> None:
        self.send()
        wrong = "000000" if self.last_code() != "000000" else "111111"
        response = self.verify(wrong)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["remaining_attempts"], 4)
        self.assertEqual(EmailVerification.objects.get().attempts_left, 4)
        for _ in range(4):
            self.verify(wrong)
        response = self.verify(self.last_code())
        self.assertEqual(response.data["code"], "CODE_ATTEMPTS_EXCEEDED")

    def test_expired_code(self) -> None:
        self.send()
        EmailVerification.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.verify(self.last_code()).data["code"], "CODE_EXPIRED")

    def test_code_is_single_use(self) -> None:
        self.send()
        code = self.last_code()
        self.assertEqual(self.verify(code).status_code, 200)
        self.assertEqual(self.verify(code).data["code"], "CODE_NOT_FOUND")


class SignupTests(AuthTestCase):
    def token(self) -> str:
        self.send()
        return str(self.verify(self.last_code()).data["signup_token"])

    def signup(self, payload: dict[str, Any]) -> Any:
        return self.client.post(reverse("auth-signup"), payload, format="json")

    def test_signup_creates_user_and_grants_first_stamp(self) -> None:
        response = self.signup(self.signup_payload(self.token()))
        self.assertEqual(response.status_code, 201, response.data)
        user = User.objects.get(email=NORMALIZED_EMAIL)
        self.assertFalse(user.has_usable_password())
        self.assertEqual(response.data["user"]["residence"]["full_name"], "충남 천안시")
        self.assertFalse(response.data["user"]["first_diary_completed"])
        self.assertEqual(response.data["granted_stamps"][0]["number"], 1)
        self.assertTrue(UserStamp.objects.filter(user=user, stamp__number=1).exists())
        self.assertTrue(TermsAgreement.objects.filter(user=user).exists())

    def test_required_terms(self) -> None:
        terms = {"service": True, "privacy": False, "age_over_14": True}
        response = self.signup(self.signup_payload(self.token(), terms=terms))
        self.assertEqual(response.data["code"], "TERMS_REQUIRED")
        self.assertFalse(User.objects.exists())

    def test_bad_signup_token(self) -> None:
        response = self.signup(self.signup_payload("forged"))
        self.assertEqual(response.data["code"], "INVALID_SIGNUP_TOKEN")

    def test_hometown_rules(self) -> None:
        token = self.token()
        gu = Region.objects.get(parent__name="서울특별시", name="성북구")
        response = self.signup(self.signup_payload(token, hometown_region_ids=[gu.id]))
        self.assertEqual(response.status_code, 400)
        self.assertIn("hometown_region_ids", response.data["errors"])

        cities = Region.objects.filter(parent__name="경기도")[:4]
        response = self.signup(
            self.signup_payload(token, hometown_region_ids=[c.id for c in cities])
        )
        self.assertIn("hometown_region_ids", response.data["errors"])

    def test_residence_must_be_leaf(self) -> None:
        seoul = Region.objects.get(name="서울특별시")
        response = self.signup(self.signup_payload(self.token(), residence_region_id=seoul.id))
        self.assertIn("residence_region_id", response.data["errors"])

    def test_duplicate_nickname(self) -> None:
        make_user()
        response = self.signup(self.signup_payload(self.token()))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "NICKNAME_TAKEN")

    def test_nickname_check(self) -> None:
        make_user()
        url = reverse("auth-nickname-check")
        self.assertTrue(self.client.get(url, {"nickname": "새이름"}).data["available"])
        self.assertEqual(self.client.get(url, {"nickname": "민호"}).data["code"], "NICKNAME_TAKEN")
        self.assertEqual(self.client.get(url, {"nickname": "가"}).data["code"], "INVALID_NICKNAME")


class LoginLogoutTests(AuthTestCase):
    def test_login_requires_account(self) -> None:
        self.assertEqual(self.send(purpose="login").status_code, 404)

    def test_signup_rejects_registered_email(self) -> None:
        make_user(email=NORMALIZED_EMAIL)
        self.assertEqual(self.send().data["code"], "EMAIL_ALREADY_REGISTERED")

    def test_login_refresh_logout(self) -> None:
        make_user(email=NORMALIZED_EMAIL)
        self.send(purpose="login")
        response = self.verify(self.last_code(), purpose="login")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["email"], NORMALIZED_EMAIL)

        refreshed = self.client.post(
            reverse("auth-token-refresh"), {"refresh": response.data["refresh"]}, format="json"
        )
        self.assertEqual(refreshed.status_code, 200)
        refresh = refreshed.data["refresh"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refreshed.data['access']}")
        logout = self.client.post(reverse("auth-logout"), {"refresh": refresh}, format="json")
        self.assertEqual(logout.status_code, 204)

        again = self.client.post(reverse("auth-token-refresh"), {"refresh": refresh}, format="json")
        self.assertEqual(again.status_code, 401)
        self.assertEqual(again.data["code"], "TOKEN_NOT_VALID")

    def test_logout_rejects_other_users_token(self) -> None:
        mine = make_user()
        other = make_user(email="b@skuniv.ac.kr", nickname="다른사람")
        self.client.force_authenticate(mine)
        response = self.client.post(
            reverse("auth-logout"), {"refresh": str(RefreshToken.for_user(other))}, format="json"
        )
        self.assertEqual(response.data["code"], "INVALID_REFRESH_TOKEN")
