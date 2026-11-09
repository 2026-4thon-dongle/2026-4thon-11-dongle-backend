from django.contrib import admin

from .models import Diary, DiaryPrompt


@admin.register(Diary)
class DiaryAdmin(admin.ModelAdmin):
    list_display = ["id", "author", "region", "visibility", "is_hidden", "created_at"]
    list_filter = ["is_hidden", "visibility"]
    raw_id_fields = ["author", "region"]


@admin.register(DiaryPrompt)
class DiaryPromptAdmin(admin.ModelAdmin):
    list_display = ["id", "text", "is_active"]
