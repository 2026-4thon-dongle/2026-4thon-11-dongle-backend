from django.urls import path

from .mailbox_views import LetterDetailView, LetterOpenView, LetterPassView
from .views import EstimateView, LetterSendView, MaterialsView

urlpatterns = [
    path("", LetterSendView.as_view(), name="letter-send"),
    path("materials/", MaterialsView.as_view(), name="letter-materials"),
    path("estimate/", EstimateView.as_view(), name="letter-estimate"),
    path("<int:pk>/", LetterDetailView.as_view(), name="letter-detail"),
    path("<int:pk>/open/", LetterOpenView.as_view(), name="letter-open"),
    path("<int:pk>/pass/", LetterPassView.as_view(), name="letter-pass"),
]
