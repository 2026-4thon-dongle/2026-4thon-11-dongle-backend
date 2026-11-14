from django.urls import path

from .draft_views import DraftDetailView, DraftListCreateView
from .mailbox_views import LetterDetailView, LetterOpenView, LetterPassView
from .route_views import LetterRouteView
from .views import EstimateView, LetterSendView, MaterialsView

urlpatterns = [
    path("", LetterSendView.as_view(), name="letter-send"),
    path("materials/", MaterialsView.as_view(), name="letter-materials"),
    path("estimate/", EstimateView.as_view(), name="letter-estimate"),
    path("drafts/", DraftListCreateView.as_view(), name="letter-draft-list"),
    path("drafts/<int:pk>/", DraftDetailView.as_view(), name="letter-draft-detail"),
    path("<int:pk>/route/", LetterRouteView.as_view(), name="letter-route"),
    path("<int:pk>/", LetterDetailView.as_view(), name="letter-detail"),
    path("<int:pk>/open/", LetterOpenView.as_view(), name="letter-open"),
    path("<int:pk>/pass/", LetterPassView.as_view(), name="letter-pass"),
]
