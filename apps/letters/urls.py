from django.urls import path

from .views import EstimateView, LetterSendView, MaterialsView

urlpatterns = [
    path("", LetterSendView.as_view(), name="letter-send"),
    path("materials/", MaterialsView.as_view(), name="letter-materials"),
    path("estimate/", EstimateView.as_view(), name="letter-estimate"),
]
