from django.urls import path

from .views import (
    NotificationListView,
    NotificationReadAllView,
    NotificationReadView,
    PushTokenCreateView,
    PushTokenDeleteView,
    UnreadCountView,
)

urlpatterns = [
    path("", NotificationListView.as_view(), name="notification-list"),
    path("unread-count/", UnreadCountView.as_view(), name="notification-unread-count"),
    path("read-all/", NotificationReadAllView.as_view(), name="notification-read-all"),
    path("<int:pk>/read/", NotificationReadView.as_view(), name="notification-read"),
    path("push-tokens/", PushTokenCreateView.as_view(), name="push-token-create"),
    path("push-tokens/<int:pk>/", PushTokenDeleteView.as_view(), name="push-token-delete"),
]
