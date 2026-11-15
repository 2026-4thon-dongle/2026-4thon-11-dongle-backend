from django.urls import path

from .views import (
    FeedDiaryDetailView,
    HometownFeedView,
    HometownSeenView,
    HometownSummaryView,
    OthersFeedView,
)

urlpatterns = [
    path("hometown/", HometownFeedView.as_view(), name="feed-hometown"),
    path("hometown/summary/", HometownSummaryView.as_view(), name="feed-hometown-summary"),
    path("hometown/seen/", HometownSeenView.as_view(), name="feed-hometown-seen"),
    path("others/", OthersFeedView.as_view(), name="feed-others"),
    path("diaries/<int:pk>/", FeedDiaryDetailView.as_view(), name="feed-diary-detail"),
]
