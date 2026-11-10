from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .models import Region


class RegionTests(TestCase):
    def test_seed_counts(self) -> None:
        self.assertEqual(Region.objects.filter(parent__isnull=True).count(), 17)
        self.assertEqual(Region.objects.filter(parent__isnull=False).count(), 228)

    def test_hometown_and_residence_rules(self) -> None:
        seoul = Region.objects.get(name="서울특별시")
        seongbuk = Region.objects.get(parent=seoul, name="성북구")
        chungnam = Region.objects.get(name="충청남도")
        cheonan = Region.objects.get(parent=chungnam, name="천안시")
        sejong = Region.objects.get(name="세종특별자치시")

        self.assertTrue(seoul.can_be_hometown)
        self.assertFalse(seongbuk.can_be_hometown)
        self.assertFalse(chungnam.can_be_hometown)
        self.assertTrue(cheonan.can_be_hometown)
        self.assertTrue(sejong.can_be_hometown)

        self.assertFalse(seoul.can_be_residence)
        self.assertTrue(seongbuk.can_be_residence)
        self.assertFalse(chungnam.can_be_residence)
        self.assertTrue(cheonan.can_be_residence)
        self.assertTrue(sejong.can_be_residence)
        self.assertEqual(seongbuk.full_name, "서울 성북구")

    def test_list_is_public_tree(self) -> None:
        response = APIClient().get(reverse("region-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 17)
        self.assertEqual(len(response.data[0]["children"]), 25)
