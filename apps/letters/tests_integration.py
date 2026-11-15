"""편지와 기존 기능(알림, 통계, 신고, 탈퇴)의 연결 테스트."""

from io import StringIO
from typing import Any

from django.core.management import call_command
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.diaries.serializers import DiarySerializer
from apps.moderations.models import Block, Report
from apps.notifications.models import Notification

from .models import Conversation, Letter
from .testing import arrive, client_for, make_diary, make_user, region, send

Type = Notification.Type


class LetterIntegrationTestCase(APITestCase):
    def setUp(self) -> None:
        self.host = make_user("하늘빛", region("충남", "천안시"))
        self.guest = make_user("다인", region("서울", "성북구"))
        self.diary = make_diary(self.host)
        self.host_api = client_for(self.host)
        self.guest_api = client_for(self.guest)

    def first_letter(self) -> dict[str, Any]:
        response = send(self.guest_api, diary_id=self.diary.id)
        self.assertEqual(response.status_code, 201, response.data)
        return dict(response.data)

    def reply(self, api: Any, to: int) -> dict[str, Any]:
        arrive(to)
        response = send(api, reply_to=to)
        self.assertEqual(response.status_code, 201, response.data)
        return dict(response.data)

    def types(self, user: Any) -> list[tuple[str, int | None]]:
        return list(
            Notification.objects.filter(user=user).order_by("id").values_list("type", "target_id")
        )


class LetterNotificationTests(LetterIntegrationTestCase):
    def test_departure_then_arrival_once(self) -> None:
        first = self.first_letter()
        self.assertEqual(self.types(self.host), [(Type.LETTER_DEPARTED, first["id"])])
        departed = Notification.objects.get(user=self.host)
        self.assertEqual(departed.title, "다인님의 편지가 출발했어요")

        # 도착 전에는 도착 알림이 없다.
        self.host_api.get(reverse("notification-list"))
        self.assertEqual(len(self.types(self.host)), 1)

        arrive(first["id"])
        response = self.host_api.get(reverse("notification-unread-count"))
        self.assertEqual(response.data["unread_count"], 2)
        self.host_api.get(reverse("notification-list"))
        self.assertEqual(
            self.types(self.host),
            [(Type.LETTER_DEPARTED, first["id"]), (Type.LETTER_ARRIVED, first["id"])],
        )
        self.assertIsNotNone(Letter.objects.get(id=first["id"]).arrival_notified_at)

    def test_command_and_round_trip(self) -> None:
        first = self.first_letter()
        reply = self.reply(self.host_api, first["id"])
        arrive(reply["id"])

        out = StringIO()
        call_command("notify_arrived_letters", stdout=out)
        self.assertIn("2건", out.getvalue())
        guest_types = self.types(self.guest)
        self.assertIn((Type.LETTER_ARRIVED, reply["id"]), guest_types)
        self.assertIn((Type.ROUND_TRIP, first["conversation_id"]), guest_types)
        round_trip = Notification.objects.get(user=self.guest, type=Type.ROUND_TRIP)
        self.assertEqual(round_trip.title, "첫 왕복 완료! 하늘빛님과 우표를 주고받았어요")

        # 다시 실행해도 중복으로 만들지 않는다. 두 번째 답장에는 왕복 알림이 없다.
        call_command("notify_arrived_letters", stdout=StringIO())
        second = self.reply(self.guest_api, reply["id"])
        arrive(second["id"])
        call_command("notify_arrived_letters", stdout=StringIO())
        self.assertEqual(
            Notification.objects.filter(user=self.host, type=Type.ROUND_TRIP).count(), 0
        )
        self.assertEqual(
            Notification.objects.filter(user=self.host, type=Type.LETTER_ARRIVED).count(), 2
        )

    def test_blocked_sender_gets_no_arrival_notification(self) -> None:
        first = self.first_letter()
        Block.objects.create(blocker=self.host, blocked=self.guest)
        arrive(first["id"])
        self.host_api.get(reverse("notification-list"))
        self.assertNotIn(Type.LETTER_ARRIVED, [t for t, _ in self.types(self.host)])


class LetterStatsTests(LetterIntegrationTestCase):
    def stats(self, api: Any) -> dict[str, int]:
        return dict(api.get(reverse("me")).data["stats"])

    def test_letter_and_penpal_count(self) -> None:
        first = self.first_letter()
        self.assertEqual(self.stats(self.guest_api)["letter_count"], 1)
        # 배송 중인 받은 편지는 세지 않는다.
        self.assertEqual(self.stats(self.host_api)["letter_count"], 0)

        last = first["id"]
        apis = [self.host_api, self.guest_api]
        for i in range(5):
            last = self.reply(apis[i % 2], last)["id"]
        arrive(last)
        stats = self.stats(self.host_api)
        self.assertEqual(stats["letter_count"], 6)
        self.assertEqual(stats["penpal_count"], 1)
        self.assertEqual(stats["draft_count"], 0)

    def test_received_letter_count(self) -> None:
        first = self.first_letter()
        self.assertEqual(DiarySerializer(self.diary).data["received_letter_count"], 0)
        arrive(first["id"])
        self.assertEqual(DiarySerializer(self.diary).data["received_letter_count"], 1)
        # 답장은 일기로 받은 편지가 아니다.
        reply = self.reply(self.host_api, first["id"])
        arrive(reply["id"])
        self.assertEqual(DiarySerializer(self.diary).data["received_letter_count"], 1)


class LetterReportTests(LetterIntegrationTestCase):
    def report(self, api: Any, letter_id: int) -> Any:
        payload = {"target_type": "letter", "target_id": letter_id, "reason": "abuse"}
        return api.post(reverse("report-create"), payload, format="json")

    def test_report_received_letter(self) -> None:
        first = self.first_letter()
        self.assertEqual(self.report(self.host_api, first["id"]).status_code, 404)
        arrive(first["id"])
        # 내가 보낸 편지는 신고할 수 없다.
        self.assertEqual(self.report(self.guest_api, first["id"]).status_code, 404)

        response = self.report(self.host_api, first["id"])
        self.assertEqual(response.status_code, 201, response.data)
        report = Report.objects.get(id=response.data["id"])
        self.assertEqual(report.target_user, self.guest)
        self.assertEqual(self.report(self.host_api, first["id"]).status_code, 409)


class WithdrawalTests(LetterIntegrationTestCase):
    def test_withdrawal_removes_letters(self) -> None:
        first = self.first_letter()
        self.reply(self.host_api, first["id"])
        self.assertEqual(self.guest_api.delete(reverse("me")).status_code, 204)
        self.assertFalse(Letter.objects.exists())
        self.assertFalse(Conversation.objects.exists())
        self.assertEqual(self.host_api.get(reverse("me")).data["stats"]["letter_count"], 0)
