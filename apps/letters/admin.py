from django.contrib import admin

from .models import Conversation, Draft, Letter


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ["id", "guest", "host", "diary", "created_at", "passed_at"]
    raw_id_fields = ["diary", "host", "guest"]


@admin.register(Letter)
class LetterAdmin(admin.ModelAdmin):
    """신고된 편지는 여기서 확인한다. 본문은 운영 목적으로만 본다."""

    list_display = ["id", "sender_nickname", "recipient_nickname", "band", "sent_at", "arrives_at"]
    list_filter = ["band", "is_first"]
    raw_id_fields = ["conversation", "sender", "recipient", "reply_to"]


@admin.register(Draft)
class DraftAdmin(admin.ModelAdmin):
    list_display = ["id", "owner", "diary", "reply_to", "saved_at"]
    raw_id_fields = ["owner", "diary", "reply_to"]
