from django.contrib import admin

from .models import Notification, PushToken


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "type", "title", "read_at", "created_at"]
    raw_id_fields = ["user"]


@admin.register(PushToken)
class PushTokenAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "platform", "updated_at"]
    raw_id_fields = ["user"]
