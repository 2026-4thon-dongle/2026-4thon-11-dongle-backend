from django.urls import path

from .views import BlockDeleteView, BlockListCreateView, ContactCheckView, ReportCreateView

urlpatterns = [
    path("reports/", ReportCreateView.as_view(), name="report-create"),
    path("blocks/", BlockListCreateView.as_view(), name="block-list"),
    path("blocks/<int:user_id>/", BlockDeleteView.as_view(), name="block-delete"),
    path("safety/contact-check/", ContactCheckView.as_view(), name="contact-check"),
]
