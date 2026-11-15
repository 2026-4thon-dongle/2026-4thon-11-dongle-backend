import random
from typing import Any

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.regions.models import Region

# 프로필 자리에 쓰는 고향이 표정 (5-3, 5-14, 7-12). 가입 때 무작위로 정해 고정한다(가정).
AVATARS = [
    "cat-basic",
    "cat-smile",
    "cat-sparkle",
    "cat-shy",
    "cat-wink",
    "cat-heart",
    "cat-curious",
]


def random_avatar() -> str:
    return random.choice(AVATARS)


class UserManager(BaseUserManager["User"]):
    def create_user(self, email: str, nickname: str, **extra: Any) -> "User":
        """일반 사용자는 메일 코드로만 로그인하므로 비밀번호가 없다 (AUTH-10)."""
        user = self.model(email=email.lower(), nickname=nickname, **extra)
        user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, nickname: str, password: str, **extra: Any) -> "User":
        user = self.model(
            email=email.lower(), nickname=nickname, is_staff=True, is_superuser=True, **extra
        )
        user.set_password(password)
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    nickname = models.CharField(max_length=10, unique=True)
    avatar = models.CharField(max_length=20, default=random_avatar)
    hometowns = models.ManyToManyField(Region, related_name="hometown_users", blank=True)
    residence = models.ForeignKey(
        Region, null=True, blank=True, on_delete=models.PROTECT, related_name="residents"
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    letter_paused = models.BooleanField(default=False)
    push_enabled = models.BooleanField(default=True)
    daily_digest_enabled = models.BooleanField(default=False)
    weekly_prompt_enabled = models.BooleanField(default=True)
    letter_arrival_push_enabled = models.BooleanField(default=True)
    letter_departure_push_enabled = models.BooleanField(default=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nickname"]

    def __str__(self) -> str:
        return self.nickname


class TermsAgreement(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="terms_agreement")
    version = models.CharField(max_length=20)
    marketing = models.BooleanField(default=False)
    agreed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.user} v{self.version}"


class EmailVerification(models.Model):
    class Purpose(models.TextChoices):
        SIGNUP = "signup", "회원가입"
        LOGIN = "login", "로그인"

    email = models.EmailField()
    purpose = models.CharField(max_length=10, choices=Purpose.choices)
    code_hash = models.CharField(max_length=64)
    attempts_left = models.PositiveSmallIntegerField()
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["email", "purpose"], name="uniq_verification_target"),
        ]

    def __str__(self) -> str:
        return f"{self.email} ({self.purpose})"
