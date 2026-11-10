from django.contrib import admin

from .models import TermsAgreement, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["id", "email", "nickname", "residence", "is_active", "date_joined"]
    search_fields = ["email", "nickname"]
    exclude = ["password"]
    filter_horizontal = ["hometowns", "groups", "user_permissions"]
    raw_id_fields = ["residence"]


@admin.register(TermsAgreement)
class TermsAgreementAdmin(admin.ModelAdmin):
    list_display = ["user", "version", "marketing", "agreed_at"]
