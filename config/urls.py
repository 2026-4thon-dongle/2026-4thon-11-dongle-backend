import re

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.letters.mailbox_views import PenpalListView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.users.auth_urls")),
    path("api/users/", include("apps.users.urls")),
    path("api/diaries/", include("apps.diaries.urls")),
    path("api/", include("apps.moderations.urls")),
    path("api/notifications/", include("apps.notifications.urls")),
    path("api/stamps/", include("apps.stamps.urls")),
    path("api/letters/", include("apps.letters.urls")),
    path("api/mailbox/", include("apps.letters.mailbox_urls")),
    path("api/penpals/", PenpalListView.as_view(), name="penpal-list"),
    path("api/feed/", include("apps.feeds.urls")),
    path("api/regions/", include("apps.regions.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

# DEBUG일 때만 동작한다.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# DEBUG=False인 배포 환경에서는 SERVE_MEDIA=true일 때 Django가 업로드 이미지를 직접 준다.
if settings.SERVE_MEDIA and not settings.DEBUG:
    urlpatterns += [
        re_path(
            rf"^{re.escape(settings.MEDIA_URL.lstrip('/'))}(?P<path>.*)$",
            serve,
            {"document_root": settings.MEDIA_ROOT},
        )
    ]
