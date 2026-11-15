from datetime import timedelta
from typing import Any

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.moderations.models import Block
from apps.users.models import AVATARS

from .models import Letter
from .testing import arrive, client_for, make_diary, make_user, region, send


class MailboxTests(TestCase):
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

    def get(self, api: APIClient, name: str, **params: Any) -> Any:
        response = api.get(reverse(name), params)
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def test_requires_login(self) -> None:
        self.assertEqual(APIClient().get(reverse("mailbox-new")).status_code, 401)

    def test_in_transit_hides_content(self) -> None:
        letter = self.first_letter()
        sent = self.get(self.guest_api, "mailbox-in-transit")["results"]
        self.assertEqual((sent[0]["direction"], sent[0]["partner"]["nickname"]), ("sent", "하늘빛"))
        incoming = self.get(self.host_api, "mailbox-in-transit", direction="incoming")["results"]
        self.assertEqual(incoming[0]["direction"], "incoming")
        self.assertNotIn("body", incoming[0])
        self.assertEqual(self.get(self.host_api, "mailbox-new")["count"], 0)

        early = self.host_api.get(reverse("letter-detail", args=[letter["id"]]))
        self.assertEqual((early.status_code, early.data["code"]), (403, "NOT_ARRIVED"))
        mine = self.guest_api.get(reverse("letter-detail", args=[letter["id"]]))
        self.assertEqual((mine.status_code, mine.data["direction"]), (200, "sent"))

        guest_conversations = self.get(self.guest_api, "mailbox-conversations")["results"]
        self.assertEqual(guest_conversations[0]["status"], "in_transit")
        self.assertEqual(self.get(self.host_api, "mailbox-conversations")["count"], 0)

    def test_new_letter_open_and_summary(self) -> None:
        letter = self.first_letter()
        arrive(letter["id"])
        new = self.get(self.host_api, "mailbox-new")["results"]
        self.assertEqual(len(new), 1)
        self.assertEqual(new[0]["sender"]["nickname"], "다인")
        self.assertFalse(new[0]["is_read"])
        self.assertEqual(new[0]["diary"]["id"], self.diary.id)
        self.assertEqual(self.get(self.host_api, "mailbox-summary")["new_unread_count"], 1)

        opened = self.host_api.post(reverse("letter-open", args=[letter["id"]]))
        self.assertEqual(opened.status_code, 200, opened.data)
        self.assertTrue(
            opened.data["is_read"] and opened.data["can_reply"] and opened.data["can_pass"]
        )
        self.assertEqual(opened.data["sender_nickname"], "다인")
        read_at = Letter.objects.get(id=letter["id"]).read_at
        self.host_api.post(reverse("letter-open", args=[letter["id"]]))
        self.assertEqual(Letter.objects.get(id=letter["id"]).read_at, read_at)
        summary = self.get(self.host_api, "mailbox-summary")
        self.assertEqual((summary["new_count"], summary["new_unread_count"]), (1, 0))

        not_mine = self.guest_api.post(reverse("letter-open", args=[letter["id"]]))
        self.assertEqual(not_mine.status_code, 404)
        self.assertEqual(
            self.get(self.guest_api, "mailbox-conversations")["results"][0]["status"], "waiting"
        )

    def test_reply_moves_to_conversations(self) -> None:
        letter = self.first_letter()
        arrive(letter["id"])
        reply = send(self.host_api, reply_to=letter["id"]).data
        self.assertEqual(self.get(self.host_api, "mailbox-new")["count"], 0)
        host_item = self.get(self.host_api, "mailbox-conversations")["results"][0]
        self.assertEqual((host_item["status"], host_item["round_trips"]), ("in_transit", 1))
        self.assertIsNone(host_item["last_letter"]["preview"])

        arrive(reply["id"])
        guest_item = self.get(self.guest_api, "mailbox-conversations")["results"][0]
        self.assertEqual(guest_item["status"], "my_turn")
        self.assertTrue(guest_item["last_letter"]["preview"])
        self.assertIn(guest_item["partner"]["avatar"], AVATARS)
        self.assertEqual(guest_item["partner"]["region"]["sido"], "충남")
        self.assertEqual(
            self.get(self.host_api, "mailbox-conversations")["results"][0]["status"], "waiting"
        )
        self.assertEqual(self.get(self.guest_api, "mailbox-summary")["my_turn_count"], 1)

        detail = self.get_detail(self.guest_api, guest_item["id"])
        self.assertEqual(detail["letter_count"], 2)
        self.assertEqual([lt["direction"] for lt in detail["letters"]], ["sent", "received"])
        self.assertEqual(detail["reply_to"], reply["id"])
        self.assertEqual(detail["diary"]["author"]["nickname"], "하늘빛")
        stranger = make_user("갈매기", region("부산", "해운대구"))
        hidden = client_for(stranger).get(
            reverse("mailbox-conversation-detail", args=[guest_item["id"]])
        )
        self.assertEqual(hidden.status_code, 404)

    def get_detail(self, api: APIClient, conversation_id: int) -> Any:
        response = api.get(reverse("mailbox-conversation-detail", args=[conversation_id]))
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def test_pass(self) -> None:
        letter = self.first_letter()
        arrive(letter["id"])
        self.assertEqual(
            self.host_api.post(reverse("letter-pass", args=[letter["id"]])).status_code, 204
        )
        self.assertEqual(self.get(self.host_api, "mailbox-new")["count"], 0)
        archive = self.get(self.host_api, "mailbox-archive")["results"]
        self.assertEqual(
            (archive[0]["kind"], archive[0]["letter_id"]), ("passed_letter", letter["id"])
        )
        again = self.host_api.post(reverse("letter-pass", args=[letter["id"]]))
        self.assertEqual((again.status_code, again.data["code"]), (409, "NOT_PASSABLE"))
        reply = send(self.host_api, reply_to=letter["id"])
        self.assertEqual(reply.data["code"], "CONVERSATION_CLOSED")
        # 상대에게는 넘긴 사실이 드러나지 않는다
        self.assertEqual(
            self.get(self.guest_api, "mailbox-conversations")["results"][0]["status"], "waiting"
        )

    def test_closed_after_seven_days(self) -> None:
        letter = self.first_letter()
        arrive(letter["id"], ago=timedelta(days=8))
        item = self.get(self.guest_api, "mailbox-conversations")["results"][0]
        self.assertEqual(item["status"], "closed")
        self.assertIsNotNone(item["closed_at"])
        archive = self.get(self.guest_api, "mailbox-archive")["results"]
        self.assertEqual(archive[0]["kind"], "closed_conversation")
        detail = self.host_api.get(reverse("letter-detail", args=[letter["id"]])).data
        self.assertFalse(detail["can_reply"])

    def test_status_order(self) -> None:
        old = self.first_letter()
        arrive(old["id"], ago=timedelta(days=8))
        other_host = make_user("귤껍질", region("제주", "제주시"))
        newer = send(self.guest_api, diary_id=make_diary(other_host).id).data
        statuses = [
            i["status"] for i in self.get(self.guest_api, "mailbox-conversations")["results"]
        ]
        self.assertEqual(statuses, ["in_transit", "closed"])
        self.assertEqual(newer["band"], "far")

    def test_new_filters(self) -> None:
        busan = make_user("갈매기", region("부산", "해운대구"))
        first = self.first_letter()
        second = send(client_for(busan), diary_id=self.diary.id).data
        arrive(first["id"], ago=timedelta(hours=2))
        arrive(second["id"])
        self.host_api.post(reverse("letter-open", args=[second["id"]]))

        latest = [i["id"] for i in self.get(self.host_api, "mailbox-new")["results"]]
        self.assertEqual(latest, [second["id"], first["id"]])
        unread = [
            i["id"] for i in self.get(self.host_api, "mailbox-new", ordering="unread")["results"]
        ]
        self.assertEqual(unread[0], first["id"])
        seoul = region("서울").id
        filtered = self.get(self.host_api, "mailbox-new", sido=seoul)["results"]
        self.assertEqual([i["id"] for i in filtered], [first["id"]])
        bad = self.host_api.get(reverse("mailbox-new"), {"ordering": "x"})
        self.assertEqual(bad.status_code, 400)

    def test_blocked_hidden(self) -> None:
        letter = self.first_letter()
        arrive(letter["id"])
        Block.objects.create(blocker=self.host, blocked=self.guest)
        self.assertEqual(self.get(self.host_api, "mailbox-new")["count"], 0)
        self.assertEqual(self.get(self.guest_api, "mailbox-conversations")["count"], 0)
        hidden = self.host_api.get(reverse("letter-detail", args=[letter["id"]]))
        self.assertEqual(hidden.status_code, 404)

    def test_penpals(self) -> None:
        letter = self.first_letter()
        apis = [self.host_api, self.guest_api]
        for turn in range(5):
            arrive(letter["id"])
            letter = send(apis[turn % 2], reply_to=letter["id"]).data
        self.assertEqual(
            self.get(self.host_api, "mailbox-conversations")["results"][0]["round_trips"], 3
        )
        pals = self.get(self.guest_api, "penpal-list")["results"]
        self.assertEqual(pals[0]["partner"]["nickname"], "하늘빛")
        self.assertEqual(pals[0]["letter_count"], 6)
        self.assertEqual(self.get(self.host_api, "penpal-list")["count"], 1)
        self.assertTrue(self.get(self.host_api, "mailbox-conversations")["results"][0]["is_penpal"])

    def test_me_has_avatar(self) -> None:
        self.assertIn(self.get(self.guest_api, "me")["avatar"], AVATARS)
