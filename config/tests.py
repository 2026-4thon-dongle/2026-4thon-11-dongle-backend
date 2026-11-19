from unittest import mock

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.diaries.models import Diary
from apps.letters.models import Conversation
from apps.letters.testing import client_for, make_diary, make_user, region, send

from .params import MAX_ID, parse_id


class ParseIdTests(TestCase):
    def test_parse_id(self) -> None:
        self.assertEqual(parse_id("12"), 12)
        for bad in (None, "", "0", "-1", "1.5", "²", "١٢", str(MAX_ID + 1), "9" * 30):
            self.assertIsNone(parse_id(bad), bad)


class JsonErrorTests(TestCase):
    def setUp(self) -> None:
        self.user = make_user("재민", region("서울", "성북구"), region("부산"))
        self.api = client_for(self.user)

    def assert_error(self, response: object, status_code: int, code: str) -> None:
        self.assertEqual(response.status_code, status_code)  # type: ignore[attr-defined]
        self.assertEqual(response["Content-Type"], "application/json")  # type: ignore[index]
        self.assertEqual(response.json()["code"], code)  # type: ignore[attr-defined]

    def test_unicode_digits_are_validation_errors(self) -> None:
        for url in (
            reverse("feed-hometown") + "?region=%C2%B2",
            reverse("mailbox-new") + "?sido=%C2%B2",
            reverse("mailbox-new") + "?sido=" + "9" * 30,
            reverse("letter-estimate") + "?diary_id=%C2%B2",
        ):
            self.assert_error(self.api.get(url), 400, "VALIDATION_ERROR")

    def test_unknown_api_path_is_json(self) -> None:
        self.assert_error(self.api.get("/api/nope/"), 404, "NOT_FOUND")
        admin = Client().get("/admin-nope/")
        self.assertEqual(admin.status_code, 404)
        self.assertNotEqual(admin["Content-Type"], "application/json")

    def test_not_found_message_is_korean(self) -> None:
        response = self.api.get(reverse("diary-detail", args=[999999]))
        self.assert_error(response, 404, "NOT_FOUND")
        self.assertEqual(response.json()["message"], "요청한 대상을 찾을 수 없습니다.")

    @override_settings(DATA_UPLOAD_MAX_MEMORY_SIZE=100)
    def test_request_too_large(self) -> None:
        response = Client().post(
            reverse("auth-email-send"),
            {"email": "a" * 200 + "@kookmin.ac.kr", "purpose": "signup"},
            content_type="application/json",
        )
        self.assert_error(response, 413, "REQUEST_TOO_LARGE")

    def test_server_error_is_json(self) -> None:
        client = Client(raise_request_exception=False)
        with mock.patch(
            "apps.regions.views.RegionListView.get_queryset", side_effect=RuntimeError("boom")
        ):
            response = client.get(reverse("region-list"))
        self.assert_error(response, 500, "SERVER_ERROR")

    def test_malformed_json_is_bad_request(self) -> None:
        for client, url in (
            (self.api, reverse("diary-create")),
            (Client(), reverse("auth-email-send")),
        ):
            response = client.post(url, '{"body": "x",', content_type="application/json")
            self.assert_error(response, 400, "BAD_REQUEST")
            self.assertEqual(response.json()["message"], "요청 형식을 확인해 주세요.")

    def test_public_api_ignores_bad_token(self) -> None:
        client = Client(HTTP_AUTHORIZATION="Bearer expired.or.invalid")
        self.assertEqual(client.get(reverse("region-list")).status_code, 200)
        check = client.get(reverse("auth-nickname-check") + "?nickname=새닉네임")
        self.assertEqual(check.status_code, 200)
        # 인증이 필요한 API는 그대로 401이다
        self.assert_error(client.get(reverse("mailbox-new")), 401, "TOKEN_NOT_VALID")


class ConversationDiaryVisibilityTests(TestCase):
    def setUp(self) -> None:
        self.host = make_user("하늘", region("부산", "해운대구"), region("서울"))
        self.guest = make_user("재민", region("서울", "성북구"), region("부산"))
        self.diary = make_diary(self.host)
        self.assertEqual(send(client_for(self.guest), diary_id=self.diary.id).status_code, 201)
        self.url = reverse("mailbox-conversation-detail", args=[Conversation.objects.get().id])

    def diary_of(self, user: object) -> object:
        return client_for(user).get(self.url).json()["diary"]  # type: ignore[arg-type]

    def test_visible_diary_is_shown(self) -> None:
        self.assertEqual(self.diary_of(self.guest)["id"], self.diary.id)  # type: ignore[index]

    def test_private_or_hidden_diary_is_null_for_guest(self) -> None:
        for change in ({"visibility": Diary.Visibility.PRIVATE}, {"is_hidden": True}):
            Diary.objects.filter(pk=self.diary.pk).update(
                visibility=Diary.Visibility.ALL, is_hidden=False
            )
            Diary.objects.filter(pk=self.diary.pk).update(**change)
            self.assertIsNone(self.diary_of(self.guest), change)
            # 일기 주인은 계속 본다
            self.assertEqual(self.diary_of(self.host)["id"], self.diary.id)  # type: ignore[index]
