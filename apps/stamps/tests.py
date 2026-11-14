from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.users.models import User

from .models import RewardSeen, Stamp, UserStamp
from .services import grant_stamp, grant_stamps, is_item_unlocked


def make_user(name: str = "재민") -> User:
    return User.objects.create_user(f"{name}@kookmin.ac.kr", name)


def give(user: User, count: int) -> None:
    """번호순으로 우표 count개를 준다 (수집가 제외)."""
    codes = list(
        Stamp.objects.exclude(code="stamp-collector").values_list("code", flat=True)[:count]
    )
    for code in codes:
        UserStamp.objects.create(user=user, stamp=Stamp.objects.get(code=code))


class StampSeedTests(TestCase):
    def test_twenty_stamps(self) -> None:
        self.assertEqual(Stamp.objects.count(), 20)
        self.assertEqual(Stamp.objects.filter(kind=Stamp.Kind.DECORATION).count(), 8)
        roundtrip = Stamp.objects.get(code="first-roundtrip")
        self.assertEqual((roundtrip.number, roundtrip.grade), (4, Stamp.Grade.RARE))
        self.assertEqual(Stamp.objects.get(code="stamp-collector").grade, Stamp.Grade.LEGENDARY)


class GrantTests(TestCase):
    def setUp(self) -> None:
        self.user = make_user()

    def test_grant_once(self) -> None:
        self.assertEqual(grant_stamp(self.user, "first-letter").code, "first-letter")  # type: ignore[union-attr]
        self.assertIsNone(grant_stamp(self.user, "first-letter"))

    def test_collector_on_tenth(self) -> None:
        give(self.user, 9)
        granted = grant_stamps(self.user, ["rainbow-letter"])
        self.assertEqual([s.code for s in granted], ["rainbow-letter", "stamp-collector"])
        self.assertEqual(UserStamp.objects.filter(user=self.user).count(), 11)

    def test_granted_with(self) -> None:
        partner = make_user("하늘빛")
        grant_stamps(self.user, ["first-roundtrip"], granted_with=partner)
        self.assertEqual(UserStamp.objects.get(user=self.user).granted_with, partner)

    def test_item_unlock(self) -> None:
        self.assertTrue(is_item_unlocked("stationery", "basic", 0))
        self.assertFalse(is_item_unlocked("stationery", "night-sky", 4))
        self.assertTrue(is_item_unlocked("stationery", "night-sky", 5))
        self.assertFalse(is_item_unlocked("sticker", "cat-wink", 2))
        self.assertTrue(is_item_unlocked("font", "mom-letter", 10))


class StampApiTests(TestCase):
    def setUp(self) -> None:
        self.user = make_user()
        self.client: APIClient = APIClient()
        self.client.force_authenticate(self.user)

    def test_requires_login(self) -> None:
        self.assertEqual(APIClient().get(reverse("stamp-book")).status_code, 401)

    def test_book(self) -> None:
        give(self.user, 5)
        data = self.client.get(reverse("stamp-book")).data
        self.assertEqual((data["owned_count"], data["total_count"]), (5, 20))
        self.assertEqual(data["next_reward"]["code"], "collector-and-font")
        self.assertEqual(data["next_reward"]["remaining"], 5)
        self.assertEqual(
            [r["code"] for r in data["received_rewards"]],
            ["stickers-cat", "stationery-night-sky"],
        )
        self.assertEqual(len(data["stamps"]), 20)
        self.assertTrue(data["stamps"][0]["owned"])
        self.assertFalse(data["stamps"][5]["owned"])
        self.assertIsNone(data["stamps"][5]["granted_at"])

    def test_book_kind_filter(self) -> None:
        response = self.client.get(reverse("stamp-book"), {"kind": "decoration"})
        self.assertEqual(len(response.data["stamps"]), 8)
        self.assertEqual(response.data["total_count"], 20)
        self.assertEqual(self.client.get(reverse("stamp-book"), {"kind": "x"}).status_code, 400)

    def test_detail(self) -> None:
        partner = make_user("하늘빛")
        grant_stamps(self.user, ["first-roundtrip"], granted_with=partner)
        data = self.client.get(reverse("stamp-detail", args=["first-roundtrip"])).data
        self.assertTrue(data["owned"])
        self.assertEqual(data["granted_with"]["nickname"], "하늘빛")
        self.assertEqual(data["grade"], "rare")
        not_owned = self.client.get(reverse("stamp-detail", args=["tulip"])).data
        self.assertFalse(not_owned["owned"])
        self.assertIsNone(not_owned["granted_with"])
        missing = self.client.get(reverse("stamp-detail", args=["nope"]))
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.data["code"], "NOT_FOUND")

    def test_rewards_and_seen(self) -> None:
        give(self.user, 3)
        rewards = self.client.get(reverse("stamp-rewards")).data["rewards"]
        self.assertEqual([r["unlocked"] for r in rewards], [True, False, False, False])
        self.assertFalse(rewards[0]["seen"])
        self.assertIsNotNone(rewards[0]["unlocked_at"])
        self.assertEqual(len(rewards[0]["items"]), 5)

        seen_url = reverse("stamp-reward-seen", args=["stickers-cat"])
        self.assertEqual(self.client.post(seen_url).status_code, 204)
        self.assertEqual(self.client.post(seen_url).status_code, 204)
        self.assertEqual(RewardSeen.objects.filter(user=self.user).count(), 1)
        self.assertTrue(self.client.get(reverse("stamp-rewards")).data["rewards"][0]["seen"])

        locked = reverse("stamp-reward-seen", args=["stationery-night-sky"])
        self.assertEqual(self.client.post(locked).status_code, 404)
