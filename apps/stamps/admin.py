from django.contrib import admin

from .models import RewardSeen, Stamp, UserStamp


@admin.register(Stamp)
class StampAdmin(admin.ModelAdmin):
    list_display = ["number", "name", "code", "kind", "grade"]
    list_filter = ["kind", "grade"]


@admin.register(UserStamp)
class UserStampAdmin(admin.ModelAdmin):
    """꾸미기 우표·시즌 우표는 운영자가 여기서 지급한다."""

    list_display = ["user", "stamp", "granted_at", "granted_with"]
    list_filter = ["stamp__kind", "stamp"]
    raw_id_fields = ["user", "granted_with"]


admin.site.register(RewardSeen)
