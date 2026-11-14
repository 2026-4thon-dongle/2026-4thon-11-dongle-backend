from django.contrib import admin

from .models import FeedSeen


@admin.register(FeedSeen)
class FeedSeenAdmin(admin.ModelAdmin):
    list_display = ["user", "seen_at"]
    search_fields = ["user__nickname", "user__email"]
