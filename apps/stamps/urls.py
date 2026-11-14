from django.urls import path

from .views import RewardListView, RewardSeenView, StampBookView, StampDetailView

urlpatterns = [
    path("", StampBookView.as_view(), name="stamp-book"),
    path("rewards/", RewardListView.as_view(), name="stamp-rewards"),
    path("rewards/<slug:code>/seen/", RewardSeenView.as_view(), name="stamp-reward-seen"),
    path("<slug:code>/", StampDetailView.as_view(), name="stamp-detail"),
]
