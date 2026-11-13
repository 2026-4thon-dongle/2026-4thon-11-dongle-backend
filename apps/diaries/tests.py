import io
import shutil
import tempfile
from typing import Any

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient

from apps.moderations.models import Block, Report
from apps.regions.models import Region
from apps.stamps.models import UserStamp
from apps.users.models import User

from .models import Diary, DiaryPrompt

MEDIA = tempfile.mkdtemp()


def png(name: str = "a.png", fmt: str = "PNG") -> SimpleUploadedFile:
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2)).save(buffer, fmt)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=f"image/{fmt.lower()}")


def cheonan() -> Region:
    return Region.objects.get(parent__name="충청남도", name="천안시")


def make_user(name: str, hometown: str = "서울특별시") -> User:
    user = User.objects.create_user(f"{name}@skuniv.ac.kr", name, residence=cheonan())
    user.hometowns.set([Region.objects.get(name=hometown)])
    return user


@override_settings(MEDIA_ROOT=MEDIA)
class DiaryApiTests(TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self) -> None:
        self.user = make_user("민호")
        self.client: APIClient = APIClient()
        self.client.force_authenticate(self.user)

    def create(self, **data: Any) -> Any:
        data.setdefault("body", "오늘 바다 색이 예뻤다")
        return self.client.post(reverse("diary-create"), data, format="multipart")

    def test_requires_login(self) -> None:
        self.assertEqual(APIClient().get(reverse("diary-my-list")).status_code, 401)

    def test_first_diary_grants_stamp_once(self) -> None:
        first = self.create()
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(first.data["granted_stamps"][0]["number"], 2)
        self.assertEqual(first.data["region"]["full_name"], "충남 천안시")
        self.assertTrue(first.data["accepts_letters"])
        self.assertEqual(self.create().data["granted_stamps"], [])
        self.assertEqual(UserStamp.objects.filter(user=self.user, stamp__number=2).count(), 1)

    def test_body_length(self) -> None:
        self.assertEqual(self.create(body="가" * 500).status_code, 201)
        self.assertEqual(self.create(body="가" * 501).status_code, 400)
        self.assertEqual(self.create(body="   ").status_code, 400)

    def test_region_is_snapshot_of_residence(self) -> None:
        diary_id = self.create().data["id"]
        self.user.residence = Region.objects.get(parent__name="서울특별시", name="성북구")
        self.user.save()
        self.assertEqual(Diary.objects.get(id=diary_id).region.name, "천안시")
        self.assertEqual(self.create().data["region"]["full_name"], "서울 성북구")

    def test_image_upload_replace_remove(self) -> None:
        created = self.create(image=png())
        self.assertEqual(created.status_code, 201, created.data)
        self.assertIn("/media/diaries/", created.data["image"])
        url = reverse("diary-detail", args=[created.data["id"]])
        diary = Diary.objects.get(id=created.data["id"])
        storage, old = diary.image.storage, diary.image.name

        with self.captureOnCommitCallbacks(execute=True):
            replaced = self.client.patch(url, {"image": png("b.png")}, format="multipart")
        self.assertEqual(replaced.status_code, 200, replaced.data)
        self.assertFalse(storage.exists(str(old)))

        with self.captureOnCommitCallbacks(execute=True):
            removed = self.client.patch(url, {"remove_image": True}, format="multipart")
        self.assertIsNone(removed.data["image"])

    def test_multipart_patch_keeps_accepts_letters(self) -> None:
        diary_id = self.create(accepts_letters=False).data["id"]
        url = reverse("diary-detail", args=[diary_id])
        response = self.client.patch(url, {"body": "고침"}, format="multipart")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data["accepts_letters"])

    def test_rejects_bad_image(self) -> None:
        fake = SimpleUploadedFile("a.png", b"not image", content_type="image/png")
        self.assertEqual(self.create(image=fake).status_code, 400)
        self.assertEqual(self.create(image=png("a.gif", "GIF")).status_code, 400)

    def test_update_delete_only_own(self) -> None:
        other = make_user("다른사람")
        diary = Diary.objects.create(author=other, region=cheonan(), body="x")
        url = reverse("diary-detail", args=[diary.id])
        self.assertEqual(self.client.patch(url, {"body": "y"}, format="json").status_code, 404)
        self.assertEqual(self.client.delete(url).status_code, 404)
        self.assertTrue(Diary.objects.filter(id=diary.id).exists())

    def test_update_fields_and_delete(self) -> None:
        diary_id = self.create().data["id"]
        url = reverse("diary-detail", args=[diary_id])
        response = self.client.patch(
            url,
            {"body": "고침", "visibility": "private", "accepts_letters": False},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["body"], "고침")
        self.assertEqual(response.data["visibility"], "private")
        self.assertFalse(response.data["accepts_letters"])
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_my_list_is_paginated_and_own_only(self) -> None:
        other = make_user("다른사람")
        Diary.objects.create(author=other, region=cheonan(), body="x")
        self.create()
        response = self.client.get(reverse("diary-my-list"))
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["received_letter_count"], 0)

    def test_prompt_today_and_exclude(self) -> None:
        url = reverse("diary-prompt")
        today = self.client.get(url).data
        self.assertEqual(self.client.get(url).data["id"], today["id"])
        for _ in range(10):
            self.assertNotEqual(
                self.client.get(url, {"exclude": today["id"]}).data["id"], today["id"]
            )

    def test_prompts_are_figma_list(self) -> None:
        active = DiaryPrompt.objects.filter(is_active=True)
        self.assertEqual(active.count(), 14)
        self.assertTrue(active.filter(text="오늘 고향 생각이 났던 순간").exists())
        self.assertIn(
            self.client.get(reverse("diary-prompt")).data["text"],
            set(active.values_list("text", flat=True)),
        )


class VisibleToTests(TestCase):
    def setUp(self) -> None:
        self.viewer = make_user("읽는사람")
        self.author = make_user("쓴사람")
        self.stranger = make_user("먼사람", hometown="부산광역시")

    def diary(self, author: User | None = None, **kwargs: Any) -> Diary:
        author = author or self.author
        return Diary.objects.create(author=author, region=cheonan(), body="x", **kwargs)

    def visible(self, diary: Diary, viewer: User | None = None) -> bool:
        return Diary.objects.visible_to(viewer or self.viewer).filter(id=diary.id).exists()

    def test_visibility_levels(self) -> None:
        same = self.diary(visibility=Diary.Visibility.SAME_HOMETOWN)
        private = self.diary(visibility=Diary.Visibility.PRIVATE)
        self.assertTrue(self.visible(self.diary()))
        self.assertTrue(self.visible(same))
        self.assertFalse(self.visible(same, self.stranger))
        self.assertFalse(self.visible(private))
        self.assertTrue(self.visible(private, self.author))

    def test_block_hides_both_directions(self) -> None:
        diary = self.diary()
        mine = self.diary(self.viewer)
        Block.objects.create(blocker=self.viewer, blocked=self.author)
        self.assertFalse(self.visible(diary))
        self.assertFalse(self.visible(mine, self.author))

    def test_reported_diary_hidden_only_for_reporter(self) -> None:
        diary = self.diary()
        Report.objects.create(
            reporter=self.viewer,
            target_user=self.author,
            target_type="diary",
            target_id=diary.id,
            reason="spam",
        )
        self.assertFalse(self.visible(diary))
        self.assertTrue(self.visible(diary, self.stranger))

    def test_hidden_diary_visible_only_to_author(self) -> None:
        diary = self.diary(is_hidden=True)
        self.assertFalse(self.visible(diary))
        self.assertTrue(self.visible(diary, self.author))

    def test_no_duplicates_with_many_shared_hometowns(self) -> None:
        cities = list(Region.objects.filter(parent__name="경기도")[:3])
        self.viewer.hometowns.set(cities)
        self.author.hometowns.set(cities)
        self.diary(visibility=Diary.Visibility.SAME_HOMETOWN)
        self.assertEqual(Diary.objects.visible_to(self.viewer).count(), 1)
