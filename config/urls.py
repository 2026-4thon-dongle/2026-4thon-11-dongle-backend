from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
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
    path("api/regions/", include("apps.regions.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

# DEBUG일 때만 동작한다. 배포 환경의 사진 서빙은 별도로 정한다.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
