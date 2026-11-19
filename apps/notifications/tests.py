from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.diaries.models import DiaryPrompt
from apps.users.models import User

from .models import Notification, PushToken
from .services import notify


class NotificationTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user("a@skuniv.ac.kr", "민호")
        self.other = User.objects.create_user("b@skuniv.ac.kr", "상대")
        self.client: APIClient = APIClient()
        self.client.force_authenticate(self.user)

    def test_list_read_and_unread_count(self) -> None:
        mine = notify(self.user, Notification.Type.LETTER_ARRIVED, "편지 도착", target_id=7)
        notify(self.user, Notification.Type.ROUND_TRIP, "왕복 완료")
        notify(self.other, Notification.Type.ROUND_TRIP, "상대 것")

        self.assertEqual(self.client.get(reverse("notification-list")).data["count"], 2)
        count_url = reverse("notification-unread-count")
        self.assertEqual(self.client.get(count_url).data["unread_count"], 2)

        response = self.client.post(reverse("notification-read", args=[mine.id]))
        self.assertIsNotNone(response.data["read_at"])
        self.assertEqual(self.client.get(count_url).data["unread_count"], 1)

        self.client.post(reverse("notification-read-all"))
        self.assertEqual(self.client.get(count_url).data["unread_count"], 0)

    def test_cannot_read_other_users_notification(self) -> None:
        theirs = notify(self.other, Notification.Type.ROUND_TRIP, "상대 것")
        response = self.client.post(reverse("notification-read", args=[theirs.id]))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["code"], "NOT_FOUND")

    def test_push_token_moves_to_latest_account(self) -> None:
        url = reverse("push-token-create")
        payload = {"token": "device-1", "platform": "web"}
        other_client = APIClient()
        other_client.force_authenticate(self.other)
        self.assertEqual(other_client.post(url, payload).status_code, 201)
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(PushToken.objects.get(token="device-1").user, self.user)

        delete_url = reverse("push-token-delete", args=[response.data["id"]])
        self.assertEqual(other_client.delete(delete_url).status_code, 404)
        self.assertEqual(self.client.delete(delete_url).status_code, 204)

    def test_weekly_prompt_command_respects_setting_and_is_idempotent(self) -> None:
        self.other.weekly_prompt_enabled = False
        self.other.save()
        call_command("create_weekly_prompt_notifications", verbosity=0, stdout=StringIO())
        call_command("create_weekly_prompt_notifications", verbosity=0, stdout=StringIO())
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)
        self.assertFalse(Notification.objects.filter(user=self.other).exists())

    def test_weekly_prompt_target_is_prompt_id(self) -> None:
        call_command("create_weekly_prompt_notifications", verbosity=0, stdout=StringIO())
        notification = Notification.objects.get(user=self.user, type=Notification.Type.PROMPT)
        self.assertIsNotNone(notification.target_id)
        prompt = DiaryPrompt.objects.get(pk=notification.target_id or 0, is_active=True)
        self.assertEqual(notification.body, prompt.text)
        listed = self.client.get(reverse("notification-list")).data["results"][0]
        self.assertEqual(listed["target_id"], prompt.id)
