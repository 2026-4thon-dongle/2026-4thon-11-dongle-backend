import re
from datetime import timedelta
from typing import Any
from unittest import mock

from django.core import mail
from django.core.mail.backends.smtp import EmailBackend as SmtpEmailBackend
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.diaries.models import Diary
from apps.moderations.models import Report
from apps.regions.models import Region
from apps.stamps.models import UserStamp
from apps.stamps.services import FIRST_STEP, grant_stamp

from .models import EmailVerification, TermsAgreement, User
from .verification import mail_connection_for, school_name_of

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
        response = self.send()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["expires_at"].endswith("+09:00"))
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


@override_settings(
    DEMO_EMAIL_HOST="mailpit",
    DEMO_EMAIL_PORT=1025,
    DEMO_EMAIL_DOMAINS=["dongle-demo.ac.kr", "guest-demo.ac.kr"],
)
class DemoMailRoutingTests(AuthTestCase):
    """실제 SMTP를 켜도 시연 주소의 인증 메일은 Mailpit으로 간다."""

    def test_demo_address_uses_demo_smtp(self) -> None:
        connection = mail_connection_for("Demo1@Dongle-Demo.ac.kr")
        assert isinstance(connection, SmtpEmailBackend)
        self.assertEqual(connection.host, "mailpit")
        self.assertEqual(connection.port, 1025)
        self.assertEqual(connection.username, "")
        self.assertFalse(connection.use_tls)
        self.assertFalse(connection.use_ssl)

    def test_other_addresses_use_default_settings(self) -> None:
        self.assertIsNone(mail_connection_for("student@skuniv.ac.kr"))
        self.assertIsNone(mail_connection_for("a@sub.dongle-demo.ac.kr"))

    @override_settings(DEMO_EMAIL_HOST="")
    def test_disabled_without_demo_host(self) -> None:
        self.assertIsNone(mail_connection_for("demo1@dongle-demo.ac.kr"))

    def test_send_code_to_demo_address_uses_demo_connection(self) -> None:
        locmem = mail.get_connection("django.core.mail.backends.locmem.EmailBackend")
        with mock.patch(
            "apps.users.verification.get_connection", return_value=locmem
        ) as get_connection:
            response = self.send("judge01@guest-demo.ac.kr")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_connection.call_args.kwargs["host"], "mailpit")
        self.assertEqual(mail.outbox[-1].to, ["judge01@guest-demo.ac.kr"])

    def test_send_code_to_school_address_uses_default_connection(self) -> None:
        with mock.patch("apps.users.verification.get_connection") as get_connection:
            response = self.send()
        self.assertEqual(response.status_code, 200)
        get_connection.assert_not_called()
        self.assertEqual(mail.outbox[-1].to, [NORMALIZED_EMAIL])


@override_settings(EXTRA_ALLOWED_EMAILS=["demo.sender@gmail.com"])
class ExtraAllowedEmailTests(AuthTestCase):
    """EXTRA_ALLOWED_EMAILS에 있는 주소는 학교 메일이 아니어도 가입·로그인할 수 있다."""

    def test_listed_address_can_sign_up_and_log_in(self) -> None:
        email = "Demo.Sender@Gmail.com"
        self.assertEqual(self.send(email).status_code, 200)
        token = self.verify(self.last_code(), email=email).data["signup_token"]
        response = self.client.post(
            reverse("auth-signup"), self.signup_payload(str(token)), format="json"
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(User.objects.filter(email="demo.sender@gmail.com").exists())

        self.assertEqual(self.send(email, purpose="login").status_code, 200)
        response = self.verify(self.last_code(), email=email, purpose="login")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("access", response.data)

    def test_unlisted_non_school_address_is_rejected(self) -> None:
        response = self.send("someone.else@gmail.com")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "INVALID_SCHOOL_EMAIL")

    @override_settings(EXTRA_ALLOWED_EMAILS=[])
    def test_only_school_email_without_list(self) -> None:
        self.assertEqual(self.send("demo.sender@gmail.com").data["code"], "INVALID_SCHOOL_EMAIL")


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

    def test_blank_nickname_is_invalid_nickname(self) -> None:
        response = self.signup(self.signup_payload(self.token(), nickname="   "))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "INVALID_NICKNAME")

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

    def test_refresh_after_account_deleted_is_401(self) -> None:
        user = make_user()
        refresh = str(RefreshToken.for_user(user))
        user.delete()
        response = self.client.post(
            reverse("auth-token-refresh"), {"refresh": refresh}, format="json"
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["code"], "TOKEN_NOT_VALID")

    def test_logout_rejects_other_users_token(self) -> None:
        mine = make_user()
        other = make_user(email="b@skuniv.ac.kr", nickname="다른사람")
        self.client.force_authenticate(mine)
        response = self.client.post(
            reverse("auth-logout"), {"refresh": str(RefreshToken.for_user(other))}, format="json"
        )
        self.assertEqual(response.data["code"], "INVALID_REFRESH_TOKEN")


class MeTests(TestCase):
    def setUp(self) -> None:
        self.user = make_user()
        self.client: APIClient = APIClient()
        self.client.force_authenticate(self.user)

    def test_me_requires_login(self) -> None:
        response = APIClient().get(reverse("me"))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["code"], "NOT_AUTHENTICATED")

    def test_me_profile_and_stats(self) -> None:
        grant_stamp(self.user, FIRST_STEP)
        response = self.client.get(reverse("me"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["hometowns"][0]["name"], "서울특별시")
        self.assertTrue(response.data["school_verified"])
        self.assertEqual(response.data["school_name"], "서경대")
        self.assertEqual(response.data["stats"]["stamp_count"], 1)
        self.assertEqual(response.data["stats"]["diary_count"], 0)

    def test_school_name_by_email_domain(self) -> None:
        self.assertEqual(school_name_of("a@cs.sungshin.ac.kr"), "성신여대")
        self.assertEqual(school_name_of("a@SKUNIV.AC.KR"), "서경대")
        self.assertIsNone(school_name_of("a@snu.ac.kr"))
        self.assertIsNone(school_name_of("a@notsungshin.ac.kr"))

    def test_nickname_change(self) -> None:
        make_user("b@skuniv.ac.kr", "사용중")
        url = reverse("me")
        self.assertEqual(self.client.patch(url, {"nickname": "사용중"}).status_code, 409)
        self.assertEqual(self.client.patch(url, {"nickname": "가"}).status_code, 400)
        self.assertEqual(self.client.patch(url, {"nickname": "민호"}).status_code, 200)
        self.assertEqual(self.client.patch(url, {"nickname": "새이름"}).data["nickname"], "새이름")

    def test_blank_nickname_change_is_invalid_nickname(self) -> None:
        response = self.client.patch(reverse("me"), {"nickname": "   "}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "INVALID_NICKNAME")

    def test_region_update_keeps_old_diary_region(self) -> None:
        diary = Diary.objects.create(author=self.user, region=regions()[1], body="x")
        gu = Region.objects.get(parent__name="서울특별시", name="성북구")
        busan = Region.objects.get(name="부산광역시")
        response = self.client.put(
            reverse("me-regions"),
            {"hometown_region_ids": [busan.id], "residence_region_id": gu.id},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["residence"]["full_name"], "서울 성북구")
        self.assertEqual(response.data["hometowns"][0]["name"], "부산광역시")
        diary.refresh_from_db()
        self.assertEqual(diary.region.name, "천안시")

    def test_settings(self) -> None:
        url = reverse("me-settings")
        self.assertFalse(self.client.get(url).data["letter_paused"])
        response = self.client.patch(url, {"letter_paused": True}, format="json")
        self.assertTrue(response.data["letter_paused"])
        self.assertTrue(response.data["weekly_prompt_enabled"])

    def test_settings_letter_push_toggles(self) -> None:
        url = reverse("me-settings")
        data = self.client.get(url).data
        self.assertTrue(data["letter_arrival_push_enabled"])
        self.assertTrue(data["letter_departure_push_enabled"])
        response = self.client.patch(url, {"letter_departure_push_enabled": False}, format="json")
        self.assertFalse(response.data["letter_departure_push_enabled"])
        self.assertTrue(response.data["letter_arrival_push_enabled"])

    def test_withdraw_removes_data_and_invalidates_tokens(self) -> None:
        grant_stamp(self.user, FIRST_STEP)
        Diary.objects.create(author=self.user, region=regions()[1], body="x")
        token = str(RefreshToken.for_user(self.user).access_token)
        self.assertEqual(self.client.delete(reverse("me")).status_code, 204)
        self.assertFalse(User.objects.filter(email="a@skuniv.ac.kr").exists())
        self.assertFalse(Diary.objects.exists())

        fresh = APIClient()
        fresh.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(fresh.get(reverse("me")).status_code, 401)

    def test_withdraw_keeps_report_with_null_target(self) -> None:
        reporter = make_user("c@skuniv.ac.kr", "신고자")
        report = Report.objects.create(
            reporter=reporter,
            target_user=self.user,
            target_type="user",
            target_id=self.user.id,
            reason="spam",
        )
        self.client.delete(reverse("me"))
        report.refresh_from_db()
        self.assertIsNone(report.target_user)
