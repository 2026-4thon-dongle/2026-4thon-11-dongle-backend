from django.urls import path

from .views import MeView, MyRegionsView, MySettingsView

urlpatterns = [
    path("me/", MeView.as_view(), name="me"),
    path("me/regions/", MyRegionsView.as_view(), name="me-regions"),
    path("me/settings/", MySettingsView.as_view(), name="me-settings"),
]
