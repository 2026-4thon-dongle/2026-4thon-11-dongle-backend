from django.db import models


class Region(models.Model):
    """시·도와 시·군·구 마스터. 시·도는 parent가 없다."""

    class Kind(models.TextChoices):
        SIDO = "sido", "시·도"
        SIGUNGU = "sigungu", "시·군·구"

    name = models.CharField(max_length=20)
    short_name = models.CharField(max_length=10, blank=True)
    kind = models.CharField(max_length=10, choices=Kind.choices)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    is_metropolitan = models.BooleanField(default=False)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["parent", "name"], name="uniq_region_parent_name"),
        ]

    def __str__(self) -> str:
        return self.full_name

    @property
    def full_name(self) -> str:
        if self.parent is None:
            return self.name
        return f"{self.parent.short_name} {self.name}"

    @property
    def can_be_hometown(self) -> bool:
        """광역 단위는 시·도 자체, 그 외는 시·군만 본가로 고른다 (AUTH-07)."""
        if self.parent is None:
            return self.is_metropolitan
        return not self.parent.is_metropolitan

    @property
    def can_be_residence(self) -> bool:
        """하위 지역이 없는 지역만 거주지로 고른다 (AUTH-08). 세종은 시·도 자체가 해당한다."""
        return self.parent is not None or not self.children.exists()
