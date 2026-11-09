from django.contrib import admin

from .models import Region


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "kind", "parent", "is_metropolitan"]
    list_filter = ["kind", "parent"]
    search_fields = ["name"]
