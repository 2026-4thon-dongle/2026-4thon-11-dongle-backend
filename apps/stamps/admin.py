from django.contrib import admin

from .models import Stamp, UserStamp

admin.site.register(Stamp)
admin.site.register(UserStamp)
