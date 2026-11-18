from typing import Any

from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.diaries.models import Diary
from apps.regions.models import Region
from apps.users.models import User

from .models import Block, Report
from .services import blocked_user_ids, detect_contact_patterns


def cheonan() -> Region:
    return Region.objects.get(parent__name="충청남도", name="천안시")


def make_user(name: str) -> User:
    user = User.objects.create_user(f"{name}@skuniv.ac.kr", name, residence=cheonan())
    user.hometowns.set([Region.objects.get(name="서울특별시")])
    return user


def client_for(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


class ReportTests(TestCase):
    def setUp(self) -> None:
        self.author = make_user("쓴사람")
        self.reporter = make_user("신고자")
        self.diary = Diary.objects.create(author=self.author, region=cheonan(), body="x")

    def report(self, user: User | None = None, **overrides: Any) -> Any:
        payload = {"target_type": "diary", "target_id": self.diary.id, "reason": "spam"}
        payload.update(overrides)
        return client_for(user or self.reporter).post(
            reverse("report-create"), payload, format="json"
        )

    def test_report_hides_for_reporter_and_blocks_on_request(self) -> None:
        response = self.report(block_user=True)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(response.data["blocked"])
        self.assertTrue(Block.objects.filter(blocker=self.reporter, blocked=self.author).exists())
        self.assertFalse(Diary.objects.visible_to(self.reporter).filter(id=self.diary.id).exists())

    def test_report_hides_all_diaries_of_author_for_reporter(self) -> None:
        other_diary = Diary.objects.create(author=self.author, region=cheonan(), body="y")
        self.assertEqual(self.report().status_code, 201)
        visible = Diary.objects.visible_to(self.reporter)
        self.assertFalse(visible.filter(author=self.author).exists())
        self.assertTrue(
            Diary.objects.visible_to(make_user("남남")).filter(id=other_diary.id).exists()
        )

    def test_letter_report_hides_sender_diaries(self) -> None:
        Report.objects.create(
            reporter=self.reporter,
            target_user=self.author,
            target_type=Report.TargetType.LETTER,
            target_id=1,
            reason=Report.Reason.SPAM,
        )
        self.assertFalse(Diary.objects.visible_to(self.reporter).filter(id=self.diary.id).exists())

    def test_report_on_withdrawn_user_hides_nothing_else(self) -> None:
        Report.objects.create(
            reporter=self.reporter,
            target_user=None,
            target_type=Report.TargetType.USER,
            target_id=999999,
            reason=Report.Reason.SPAM,
        )
        self.assertTrue(Diary.objects.visible_to(self.reporter).filter(id=self.diary.id).exists())

    def test_three_reports_hide_globally(self) -> None:
        self.report(make_user("가가"))
        self.report(make_user("나나"))
        self.diary.refresh_from_db()
        self.assertFalse(self.diary.is_hidden)
        self.report(make_user("다다"))
        self.diary.refresh_from_db()
        self.assertTrue(self.diary.is_hidden)
        self.assertEqual(Report.objects.filter(status=Report.Status.PENDING).count(), 3)

    def test_duplicate_report_conflicts_for_user_target(self) -> None:
        kwargs: dict[str, Any] = {"target_type": "user", "target_id": self.author.id}
        self.assertEqual(self.report(**kwargs).status_code, 201)
        response = self.report(**kwargs)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "ALREADY_REPORTED")

    def test_second_report_on_same_diary_is_not_found(self) -> None:
        self.report()
        self.assertEqual(self.report().data["code"], "TARGET_NOT_FOUND")

    def test_cannot_report_self(self) -> None:
        self.assertEqual(self.report(self.author).data["code"], "CANNOT_REPORT_SELF")

    def test_etc_requires_detail(self) -> None:
        self.assertEqual(self.report(reason="etc").status_code, 400)
        self.assertEqual(self.report(reason="etc", detail="이유").status_code, 201)

    def test_unknown_letter_is_not_found(self) -> None:
        # 편지 신고 동작은 apps/letters/tests_integration.py에서 확인한다.
        response = self.report(target_type="letter", target_id=999999)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["code"], "TARGET_NOT_FOUND")

    def test_private_diary_is_not_found(self) -> None:
        self.diary.visibility = Diary.Visibility.PRIVATE
        self.diary.save()
        self.assertEqual(self.report().status_code, 404)


class BlockTests(TestCase):
    def setUp(self) -> None:
        self.me = make_user("나")
        self.other = make_user("상대")
        self.client: APIClient = client_for(self.me)

    def test_block_list_unblock(self) -> None:
        url = reverse("block-list")
        self.assertEqual(self.client.post(url, {"user_id": self.other.id}).status_code, 201)
        self.assertEqual(self.client.post(url, {"user_id": self.other.id}).status_code, 201)
        response = self.client.get(url)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["user"]["nickname"], "상대")
        self.assertNotIn("email", response.data["results"][0]["user"])
        self.assertEqual(
            response.data["results"][0]["user"]["residence"]["full_name"], "충남 천안시"
        )
        self.assertEqual(blocked_user_ids(self.other), {self.me.id})

        delete_url = reverse("block-delete", args=[self.other.id])
        self.assertEqual(self.client.delete(delete_url).status_code, 204)
        self.assertEqual(self.client.delete(delete_url).status_code, 404)

    def test_cannot_block_self(self) -> None:
        response = self.client.post(reverse("block-list"), {"user_id": self.me.id})
        self.assertEqual(response.data["code"], "CANNOT_BLOCK_SELF")


class ContactPatternTests(SimpleTestCase):
    def test_detects(self) -> None:
        cases = {
            "제 번호는 010-1234-5678 이에요": "phone",
            "01012345678로 연락": "phone",
            "+82 10 1234 5678": "phone",
            "메일 hello@naver.com": "email",
            "카톡 아이디: dongle_01": "kakao",
            "kakao id abc123": "kakao",
            "https://open.kakao.com/o/abc": "kakao",
            "인스타 @dongle.kr 팔로우": "instagram",
        }
        for text, kind in cases.items():
            with self.subTest(text=text):
                self.assertIn(kind, detect_contact_patterns(text))

    def test_ignores_plain_text(self) -> None:
        for text in [
            "오늘 바다 색이 예뻤어요",
            "2026년 11월 22일 10시",
            "카톡 보내고 싶어요",
            "학번 2022305011",
        ]:
            with self.subTest(text=text):
                self.assertEqual(detect_contact_patterns(text), [])
