from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.diaries.models import Diary
from apps.letters.testing import client_for, make_diary, make_user, region, send
from apps.moderations.models import Block, Report

from .models import FeedSeen


def ids(response: object) -> list[int]:
    return [item["id"] for item in response.data["results"]]  # type: ignore[attr-defined]


class FeedTestCase(APITestCase):
    def setUp(self) -> None:
        # 서울 성북구에 살고 본가가 천안시(시·군)와 부산(광역시)인 사용자
        self.viewer = make_user("다인", region("서울", "성북구"))
        self.viewer.hometowns.set([region("충남", "천안시"), region("부산")])
        self.api = client_for(self.viewer)

        self.cheonan = make_user("하늘빛", region("충남", "천안시"))
        self.busan = make_user("갈매기", region("부산", "해운대구"))
        self.suwon = make_user("수원댁", region("경기", "수원시"))
        self.jongno = make_user("종로", region("서울", "종로구"))
        self.neighbor = make_user("이웃", region("서울", "성북구"))

        self.d_cheonan = make_diary(self.cheonan)
        self.d_busan = make_diary(self.busan)
        self.d_suwon = make_diary(self.suwon)
        self.d_jongno = make_diary(self.jongno)
        self.d_neighbor = make_diary(self.neighbor)
        self.d_own = make_diary(self.viewer)


class HometownFeedTests(FeedTestCase):
    def test_hometown_feed_matches_city_and_metropolitan(self) -> None:
        response = self.api.get(reverse("feed-hometown"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ids(response), [self.d_busan.id, self.d_cheonan.id])
        item = response.data["results"][0]
        self.assertEqual(item["region"]["sido"], "부산")
        self.assertTrue(item["can_reply"])

    def test_region_filter(self) -> None:
        cheonan = region("충남", "천안시")
        response = self.api.get(reverse("feed-hometown"), {"region": cheonan.id})
        self.assertEqual(ids(response), [self.d_cheonan.id])

    def test_region_filter_must_be_my_hometown(self) -> None:
        response = self.api.get(reverse("feed-hometown"), {"region": region("경기").id})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "VALIDATION_ERROR")

    def test_hidden_diaries_are_excluded(self) -> None:
        Diary.objects.filter(id=self.d_busan.id).update(visibility=Diary.Visibility.PRIVATE)
        Block.objects.create(blocker=self.viewer, blocked=self.cheonan)
        response = self.api.get(reverse("feed-hometown"))
        self.assertEqual(ids(response), [])

    def test_reported_diary_is_excluded(self) -> None:
        Report.objects.create(
            reporter=self.viewer,
            target_user=self.cheonan,
            target_type=Report.TargetType.DIARY,
            target_id=self.d_cheonan.id,
            reason=Report.Reason.SPAM,
        )
        response = self.api.get(reverse("feed-hometown"))
        self.assertEqual(ids(response), [self.d_busan.id])

    def test_already_sent_disables_reply(self) -> None:
        response = send(self.api, diary_id=self.d_cheonan.id)
        self.assertEqual(response.status_code, 201, response.data)
        response = self.api.get(reverse("feed-hometown"))
        by_id = {item["id"]: item for item in response.data["results"]}
        self.assertFalse(by_id[self.d_cheonan.id]["can_reply"])
        self.assertTrue(by_id[self.d_busan.id]["can_reply"])


class HometownSummaryTests(FeedTestCase):
    def test_new_count_since_today_then_since_seen(self) -> None:
        response = self.api.get(reverse("feed-hometown-summary"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["new_count"], 2)
        self.assertIsNone(response.data["last_seen_at"])
        self.assertEqual(len(response.data["hometowns"]), 2)

        self.assertEqual(self.api.post(reverse("feed-hometown-seen")).status_code, 204)
        self.assertTrue(FeedSeen.objects.filter(user=self.viewer).exists())
        response = self.api.get(reverse("feed-hometown-summary"))
        self.assertEqual(response.data["new_count"], 0)
        self.assertIsNotNone(response.data["last_seen_at"])

        make_diary(self.cheonan)
        response = self.api.get(reverse("feed-hometown-summary"))
        self.assertEqual(response.data["new_count"], 1)

    def test_own_diary_in_hometown_is_not_new(self) -> None:
        self.viewer.hometowns.add(region("서울"))
        response = self.api.get(reverse("feed-hometown"))
        self.assertIn(self.d_own.id, ids(response))
        response = self.api.get(reverse("feed-hometown-summary"))
        # 서울이 본가가 되어 종로·이웃 일기는 새 일기로 세지만 내 일기는 세지 않는다
        self.assertEqual(response.data["new_count"], 4)

    def test_old_diaries_are_not_new(self) -> None:
        Diary.objects.update(created_at=timezone.now() - timedelta(days=2))
        response = self.api.get(reverse("feed-hometown-summary"))
        self.assertEqual(response.data["new_count"], 0)


class OthersFeedTests(FeedTestCase):
    def test_excludes_hometown_and_residence(self) -> None:
        response = self.api.get(reverse("feed-others"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ids(response), [self.d_own.id, self.d_jongno.id, self.d_suwon.id])

    def test_own_diary_is_shown_without_reply(self) -> None:
        response = self.api.get(reverse("feed-others"))
        by_id = {item["id"]: item for item in response.data["results"]}
        self.assertNotIn(self.d_neighbor.id, by_id)
        self.assertFalse(by_id[self.d_own.id]["can_reply"])
        response = self.api.get(reverse("feed-others"), {"sido": region("서울").id})
        self.assertEqual(ids(response), [self.d_own.id, self.d_jongno.id])

    def test_sido_filter(self) -> None:
        response = self.api.get(reverse("feed-others"), {"sido": region("경기").id})
        self.assertEqual(ids(response), [self.d_suwon.id])

    def test_sido_filter_rejects_sigungu(self) -> None:
        response = self.api.get(reverse("feed-others"), {"sido": region("경기", "수원시").id})
        self.assertEqual(response.status_code, 400)

    def test_invalid_sido(self) -> None:
        response = self.api.get(reverse("feed-others"), {"sido": "abc"})
        self.assertEqual(response.status_code, 400)


class FeedDiaryDetailTests(FeedTestCase):
    def url(self, diary: Diary) -> str:
        return reverse("feed-diary-detail", args=[diary.id])

    def test_detail_has_delivery(self) -> None:
        response = self.api.get(self.url(self.d_busan))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["can_reply"])
        self.assertIsNone(response.data["reply_block_reason"])
        self.assertIsNone(response.data["my_draft"])
        delivery = response.data["delivery"]
        self.assertEqual(delivery["band"], "far")
        self.assertEqual(delivery["from_region"]["name"], "성북구")
        self.assertEqual(delivery["to_region"]["name"], "해운대구")

    def test_own_diary(self) -> None:
        response = self.api.get(self.url(self.d_own))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["reply_block_reason"], "own_diary")
        self.assertIsNone(response.data["delivery"])

    def test_block_reasons(self) -> None:
        Diary.objects.filter(id=self.d_suwon.id).update(accepts_letters=False)
        self.cheonan.letter_paused = True
        self.cheonan.save(update_fields=["letter_paused"])
        self.assertEqual(
            self.api.get(self.url(self.d_suwon)).data["reply_block_reason"], "letters_off"
        )
        self.assertEqual(
            self.api.get(self.url(self.d_cheonan)).data["reply_block_reason"],
            "recipient_paused",
        )

    def test_not_visible_is_404(self) -> None:
        Diary.objects.filter(id=self.d_jongno.id).update(is_hidden=True)
        Block.objects.create(blocker=self.busan, blocked=self.viewer)
        for diary in (self.d_jongno, self.d_busan):
            response = self.api.get(self.url(diary))
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.data["code"], "NOT_FOUND")
        self.assertEqual(self.api.get("/api/feed/diaries/999999/").status_code, 404)
