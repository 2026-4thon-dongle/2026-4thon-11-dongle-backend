from django.urls import path

from .mailbox_views import (
    ArchiveView,
    ConversationDetailView,
    ConversationListView,
    InTransitView,
    NewLettersView,
    SummaryView,
)

urlpatterns = [
    path("summary/", SummaryView.as_view(), name="mailbox-summary"),
    path("new/", NewLettersView.as_view(), name="mailbox-new"),
    path("conversations/", ConversationListView.as_view(), name="mailbox-conversations"),
    path(
        "conversations/<int:pk>/",
        ConversationDetailView.as_view(),
        name="mailbox-conversation-detail",
    ),
    path("in-transit/", InTransitView.as_view(), name="mailbox-in-transit"),
    path("archive/", ArchiveView.as_view(), name="mailbox-archive"),
]
