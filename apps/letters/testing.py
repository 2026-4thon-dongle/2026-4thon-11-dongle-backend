"""letters 테스트 공용 도구. 테스트에서만 쓴다."""

from datetime import timedelta
from typing import Any

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.diaries.models import Diary
from apps.regions.models import Region
from apps.stamps.services import FIRST_STEP, grant_stamp
from apps.users.models import User

from .models import Letter


def region(sido: str, name: str | None = None) -> Region:
    if name is None:
        return Region.objects.get(parent__isnull=True, short_name=sido)
    return Region.objects.get(parent__short_name=sido, name=name)


def make_user(name: str, residence: Region, hometown: Region | None = None) -> User:
    user = User.objects.create_user(f"{name}@kookmin.ac.kr", name, residence=residence)
    if hometown is not None:
        user.hometowns.set([hometown])
    grant_stamp(user, FIRST_STEP)
    return user


def make_diary(author: User, **fields: Any) -> Diary:
    assert author.residence is not None
    fields.setdefault("body", "오늘 학교 앞 호수 색이 유난히 예뻤다")
    return Diary.objects.create(author=author, region=author.residence, **fields)


def client_for(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def send(client: APIClient, fmt: str = "json", **data: Any) -> Any:
    data.setdefault("body", "그 호수, 제가 고등학생 때 매일 지나던 곳이에요!")
    data.setdefault("stationery", "basic")
    data.setdefault("stamp", FIRST_STEP)
    return client.post(reverse("letter-send"), data, format=fmt)


def arrive(letter_id: int, ago: timedelta = timedelta(minutes=1)) -> None:
    """편지를 이미 도착한 것으로 만든다."""
    Letter.objects.filter(id=letter_id).update(arrives_at=timezone.now() - ago)
