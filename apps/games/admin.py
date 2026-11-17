from django.contrib import admin

from .models import GameRun


@admin.register(GameRun)
class GameRunAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "letter", "status", "stars", "reduced_seconds", "started_at"]
    list_filter = ["status", "stars"]
    search_fields = ["user__nickname", "user__email"]
    readonly_fields = ["course", "seed", "granted_stamps"]
    raw_id_fields = ["user", "letter"]
