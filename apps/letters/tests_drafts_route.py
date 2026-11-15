from typing import Any

from django.urls import reverse
from rest_framework.test import APITestCase

from apps.moderations.models import Block

from .models import Draft
from .route import map_theme, path_sidos
from .testing import arrive, client_for, make_diary, make_user, region, send


class DraftTests(APITestCase):
    def setUp(self) -> None:
        self.host = make_user("하늘빛", region("충남", "천안시"))
        self.guest = make_user("다인", region("서울", "성북구"))
        self.diary = make_diary(self.host)
        self.host_api = client_for(self.host)
        self.guest_api = client_for(self.guest)

    def save(self, api: Any, **data: Any) -> Any:
        return api.post(reverse("letter-draft-list"), data, format="json")

    def test_save_overwrites_same_target(self) -> None:
        first = self.save(
            self.guest_api, diary_id=self.diary.id, body="그 호수", stationery="basic"
        )
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(first.data["kind"], "first")
        self.assertEqual(first.data["recipient"], {"id": self.host.id, "nickname": "하늘빛"})

        again = self.save(self.guest_api, diary_id=self.diary.id, body="그 호수, 저도 알아요")
        self.assertEqual(again.status_code, 200)
        self.assertEqual(again.data["id"], first.data["id"])
        self.assertEqual(again.data["body"], "그 호수, 저도 알아요")
        self.assertEqual(Draft.objects.count(), 1)

        listed = self.guest_api.get(reverse("letter-draft-list"))
        self.assertEqual(listed.data["count"], 1)
        item = listed.data["results"][0]
        self.assertEqual(
            (item["body_length"], item["diary_id"], item["reply_to"]), (12, self.diary.id, None)
        )
        self.assertEqual(self.guest_api.get(reverse("me")).data["stats"]["draft_count"], 1)

    def test_validation_and_not_found(self) -> None:
        self.assertEqual(self.save(self.guest_api, body="x").status_code, 400)
        both = self.save(self.guest_api, diary_id=self.diary.id, reply_to=1)
        self.assertEqual(both.status_code, 400)
        self.assertEqual(self.save(self.guest_api, diary_id=999999).status_code, 404)
        self.assertEqual(self.save(self.host_api, diary_id=self.diary.id).status_code, 400)
        bad = self.save(self.guest_api, diary_id=self.diary.id, stationery="nope")
        self.assertEqual(bad.status_code, 400)

    def test_reply_draft_needs_arrived_received_letter(self) -> None:
        letter = send(self.guest_api, diary_id=self.diary.id).data
        self.assertEqual(self.save(self.host_api, reply_to=letter["id"]).status_code, 404)
        self.assertEqual(self.save(self.guest_api, reply_to=letter["id"]).status_code, 404)
        arrive(letter["id"])
        response = self.save(self.host_api, reply_to=letter["id"], body="반가워요")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["kind"], "reply")
        self.assertEqual(response.data["recipient"]["id"], self.guest.id)

    def test_detail_and_delete_only_mine(self) -> None:
        draft_id = self.save(self.guest_api, diary_id=self.diary.id, body="안녕").data["id"]
        url = reverse("letter-draft-detail", args=[draft_id])
        self.assertEqual(self.guest_api.get(url).data["body"], "안녕")
        self.assertEqual(self.host_api.get(url).status_code, 404)
        self.assertEqual(self.host_api.delete(url).status_code, 404)
        self.assertEqual(self.guest_api.delete(url).status_code, 204)
        self.assertFalse(Draft.objects.exists())

    def test_feed_detail_and_send_clear_draft(self) -> None:
        draft_id = self.save(self.guest_api, diary_id=self.diary.id, body="쓰는 중").data["id"]
        detail = self.guest_api.get(reverse("feed-diary-detail", args=[self.diary.id]))
        self.assertEqual(detail.data["my_draft"]["id"], draft_id)
        self.assertEqual(detail.data["my_draft"]["body_preview"], "쓰는 중")

        response = send(self.guest_api, diary_id=self.diary.id, draft_id=draft_id)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertFalse(Draft.objects.exists())
        detail = self.guest_api.get(reverse("feed-diary-detail", args=[self.diary.id]))
        self.assertIsNone(detail.data["my_draft"])


class RouteTests(APITestCase):
    def setUp(self) -> None:
        self.host = make_user("갈매기", region("부산", "해운대구"))
        self.guest = make_user("다인", region("서울", "성북구"))
        self.diary = make_diary(self.host)
        self.host_api = client_for(self.host)
        self.guest_api = client_for(self.guest)
        self.letter = send(self.guest_api, diary_id=self.diary.id).data

    def url(self) -> str:
        return reverse("letter-route", args=[self.letter["id"]])

    def test_path_sidos(self) -> None:
        self.assertEqual(path_sidos("서울", "서울"), [])
        stops = path_sidos("서울", "부산")
        names = [name for name, _ in stops]
        # 출발·도착 시·도는 빠지고, 지나는 순서대로 나온다.
        self.assertEqual(names, ["경기", "충북", "대전", "대구"])
        progress = [p for _, p in stops]
        self.assertEqual(progress, sorted(progress))
        self.assertTrue(all(0 < p < 1 for p in progress))

    def test_route_for_sender_and_recipient(self) -> None:
        # 지나는 지역에 쓴 일기가 이야기로 붙는다.
        daejeon_user = make_user("한밭", region("대전", "유성구"))
        story = make_diary(daejeon_user, body="빵집 앞 줄이 오늘도 길었다")

        sent = self.guest_api.get(self.url())
        self.assertEqual(sent.status_code, 200)
        self.assertEqual(sent.data["direction"], "sent")
        self.assertEqual(sent.data["partner"], {"id": self.host.id, "nickname": "갈매기"})
        self.assertEqual(sent.data["to_region"]["sido"], "부산")
        self.assertIn(sent.data["map_theme"], ["city", "sea", "mountain", "field", "river"])
        stories = {w["region"]["sido"]: w["story"] for w in sent.data["waypoints"]}
        self.assertEqual(stories["대전"], {"diary_id": story.id, "body_preview": story.body})
        self.assertIsNone(stories["충북"])
        self.assertNotIn("body", sent.data)

        # 받는 사람은 도착 전에도 볼 수 있다.
        incoming = self.host_api.get(self.url())
        self.assertEqual(incoming.data["direction"], "incoming")
        self.assertEqual(incoming.data["partner"]["nickname"], "다인")
        self.assertEqual(incoming.data["map_theme"], sent.data["map_theme"])

    def test_others_and_blocked_get_404(self) -> None:
        stranger = make_user("낯선이", region("서울", "종로구"))
        self.assertEqual(client_for(stranger).get(self.url()).status_code, 404)
        Block.objects.create(blocker=self.host, blocked=self.guest)
        self.assertEqual(self.guest_api.get(self.url()).status_code, 404)

    def test_map_theme_is_fixed(self) -> None:
        from .models import Letter

        letter = Letter.objects.get(id=self.letter["id"])
        self.assertEqual(map_theme(letter), map_theme(letter))
