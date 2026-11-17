"""목록 API의 쿼리 수가 데이터 수에 따라 늘지 않는지 본다 (QA 18회차)."""

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.letters.testing import arrive, client_for, make_diary, make_user, region, send
from apps.users.models import User


class ListQueryCountTests(TestCase):
    def setUp(self) -> None:
        self.me = make_user("나", region("서울", "성북구"), region("부산"))
        self.client_me = client_for(self.me)
        self.partners = 0

    def queries(self, url: str) -> int:
        with CaptureQueriesContext(connection) as ctx:
            response = self.client_me.get(url)
        self.assertEqual(response.status_code, 200, response.data)
        return len(ctx.captured_queries)

    def add_partner(self) -> User:
        """상대 한 명: 내 일기에 첫 편지(도착) → 내 답장(도착), 상대 일기에 내 첫 편지(배송 중)."""
        self.partners += 1
        partner = make_user(f"상대{self.partners}", region("부산", "해운대구"), region("서울"))
        my_diary = make_diary(self.me)
        first = send(client_for(partner), diary_id=my_diary.id).data
        arrive(first["id"])
        reply = send(self.client_me, reply_to=first["id"]).data
        arrive(reply["id"])
        send(self.client_me, diary_id=make_diary(partner).id)
        return partner

    def assert_constant(self, url: str) -> None:
        self.add_partner()
        small = self.queries(url)
        for _ in range(4):
            self.add_partner()
        self.assertEqual(self.queries(url), small, url)

    def test_conversation_tab(self) -> None:
        self.assert_constant(reverse("mailbox-conversations"))

    def test_game_home(self) -> None:
        self.assert_constant(reverse("game-home"))

    def test_my_diaries(self) -> None:
        self.assert_constant(reverse("diary-my-list"))

    def test_my_diaries_received_count_unchanged(self) -> None:
        self.add_partner()
        diaries = self.client_me.get(reverse("diary-my-list")).data["results"]
        self.assertEqual([d["received_letter_count"] for d in diaries], [1])
        detail = self.client_me.get(reverse("diary-detail", args=[diaries[0]["id"]])).data
        self.assertEqual(detail["received_letter_count"], 1)
