from io import StringIO

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.diaries.models import Diary
from apps.games.models import GameRun
from apps.letters.models import Conversation, Draft, Letter
from apps.letters.services import PENPAL_ROUND_TRIPS, pair_round_trips
from apps.letters.testing import client_for, make_diary, make_user, region, send
from apps.moderations.models import Block, Report
from apps.stamps.models import UserStamp

from .demo_seed import DEMO_DOMAIN, demo_users
from .models import User


def run(*args: str) -> str:
    out = StringIO()
    call_command("seed_demo", *args, stdout=out)
    return out.getvalue()


def demo(key: str) -> User:
    return User.objects.get(email=f"{key}@{DEMO_DOMAIN}")


class SeedDemoTests(TestCase):
    def counts(self) -> tuple[int, int, int, int]:
        users = demo_users()
        return (
            users.count(),
            Diary.objects.filter(author__in=users).count(),
            Letter.objects.filter(sender__in=users).count(),
            UserStamp.objects.filter(user__in=users).count(),
        )

    def test_creates_demo_scenario(self) -> None:
        run()
        # 편지: 기존 장면 7통 + 펜팔 6통 + 넘긴 편지 1통
        self.assertEqual(self.counts()[:3], (5, 10, 14))
        hero = client_for(demo("demo1"))
        new = hero.get(reverse("mailbox-new")).json()
        received = [i for i in new["results"] if i["direction"] == "received"]
        self.assertEqual(len(received), 1)
        in_transit = hero.get(reverse("mailbox-in-transit")).json()
        self.assertGreaterEqual(len(in_transit["results"]), 1)
        # 우표 5개 이상이라 「밤하늘」 편지지와 스티커가 열려 있다
        self.assertGreaterEqual(UserStamp.objects.filter(user=demo("demo1")).count(), 5)
        self.assertEqual(hero.get(reverse("feed-hometown")).status_code, 200)

    def test_penpal_archive_and_draft(self) -> None:
        run()
        hero = client_for(demo("demo1"))
        self.assertGreaterEqual(
            pair_round_trips(demo("demo1").pk, demo("demo5").pk), PENPAL_ROUND_TRIPS
        )
        penpals = hero.get(reverse("penpal-list")).json()["results"]
        self.assertIn("강릉커피", [item["partner"]["nickname"] for item in penpals])
        chats = hero.get(reverse("mailbox-conversations")).json()["results"]
        coffee = next(c for c in chats if c["partner"]["nickname"] == "강릉커피")
        self.assertTrue(coffee["is_penpal"])
        self.assertEqual(coffee["status"], "my_turn")
        archive = hero.get(reverse("mailbox-archive")).json()["results"]
        self.assertEqual([item["kind"] for item in archive], ["passed_letter"])
        drafts = hero.get(reverse("letter-draft-list")).json()["results"]
        self.assertEqual(len(drafts), 1)
        # 시연1은 실행 시각과 관계없이 우표 9개라 1개만 더 받으면 「우표 수집가」 보상이 열린다
        stamps = hero.get(reverse("stamp-book")).json()
        self.assertEqual(stamps["owned_count"], 9)
        self.assertEqual(stamps["next_reward"]["remaining"], 1)

    def test_reset_clears_demo_activity(self) -> None:
        run()
        hero_user, other = demo("demo1"), demo("demo2")
        hero = client_for(hero_user)
        outsider = make_user("손님", region("서울", "종로구"), region("부산"))
        self.assertEqual(hero.post(reverse("game-run-start"), {}, format="json").status_code, 201)
        self.assertEqual(
            hero.post(reverse("block-list"), {"user_id": other.pk}, format="json").status_code, 201
        )
        diary = Diary.objects.filter(author=demo("demo3")).first()
        assert diary is not None
        report = {"target_type": "diary", "target_id": diary.pk, "reason": "spam"}
        self.assertEqual(
            hero.post(reverse("report-create"), report, format="json").status_code, 201
        )
        client_for(outsider).post(reverse("block-list"), {"user_id": hero_user.pk}, format="json")
        User.objects.filter(pk=hero_user.pk).update(push_enabled=False, daily_digest_enabled=True)

        run()

        self.assertFalse(GameRun.objects.filter(user=hero_user).exists())
        self.assertFalse(Block.objects.filter(blocker=hero_user).exists())
        self.assertFalse(Report.objects.filter(reporter=hero_user).exists())
        # 다른 사용자가 시연 계정을 차단한 기록은 그 사용자의 데이터라 남긴다
        self.assertTrue(Block.objects.filter(blocker=outsider, blocked=hero_user).exists())
        hero_user.refresh_from_db()
        self.assertTrue(hero_user.push_enabled)
        self.assertFalse(hero_user.daily_digest_enabled)
        self.assertEqual(Draft.objects.filter(owner=hero_user).count(), 1)

    def test_in_transit_letters_ignore_demo_mode(self) -> None:
        with override_settings(LETTER_DEMO_MODE=True):
            run("--arrive-in", "5")
        now = timezone.now()
        pending = Letter.objects.filter(arrives_at__gt=now)
        self.assertEqual(pending.count(), 3)
        soon = pending.order_by("arrives_at").first()
        assert soon is not None
        self.assertLess((soon.arrives_at - now).total_seconds(), 5 * 60 + 5)

    def test_idempotent(self) -> None:
        run()
        first_ids = sorted(demo_users().values_list("id", flat=True))
        first_counts = self.counts()
        run()
        self.assertEqual(sorted(demo_users().values_list("id", flat=True)), first_ids)
        self.assertEqual(self.counts(), first_counts)

    def test_other_users_untouched(self) -> None:
        alice = make_user("앨리스", region("서울", "성북구"), region("부산"))
        bob = make_user("밥", region("부산", "해운대구"), region("서울"))
        diary = make_diary(alice)
        self.assertEqual(send(client_for(bob), diary_id=diary.id).status_code, 201)
        stamps = UserStamp.objects.filter(user__in=[alice, bob]).count()
        run()
        run("--remove")
        self.assertTrue(Diary.objects.filter(id=diary.id).exists())
        self.assertEqual(Letter.objects.filter(sender=bob).count(), 1)
        self.assertEqual(UserStamp.objects.filter(user__in=[alice, bob]).count(), stamps)
        self.assertEqual(demo_users().count(), 0)

    def test_keeps_conversation_with_other_user(self) -> None:
        run()
        outsider = make_user("손님", region("서울", "종로구"), region("부산"))
        diary = Diary.objects.filter(author=demo("demo1")).first()
        assert diary is not None
        self.assertEqual(send(client_for(outsider), diary_id=diary.id).status_code, 201)
        output = run()
        self.assertIn("1개는 지우지 않고 남겼습니다", output)
        self.assertTrue(Diary.objects.filter(id=diary.id).exists())
        self.assertEqual(Conversation.objects.filter(guest=outsider).count(), 1)
        output = run("--remove")
        self.assertIn(f"demo1@{DEMO_DOMAIN}", output)
        self.assertEqual(
            list(demo_users().values_list("email", flat=True)), [f"demo1@{DEMO_DOMAIN}"]
        )
        self.assertEqual(Letter.objects.filter(sender=outsider).count(), 1)

    def test_nickname_taken_changes_nothing(self) -> None:
        make_user("부산갈매기", region("서울", "성북구"))
        with self.assertRaises(CommandError):
            run()
        self.assertEqual(demo_users().count(), 0)
