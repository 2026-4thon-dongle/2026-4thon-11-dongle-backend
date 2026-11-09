from django.urls import path

from .views import DiaryCreateView, DiaryPromptView, MyDiaryDetailView, MyDiaryListView

urlpatterns = [
    path("", DiaryCreateView.as_view(), name="diary-create"),
    path("me/", MyDiaryListView.as_view(), name="diary-my-list"),
    path("prompts/", DiaryPromptView.as_view(), name="diary-prompt"),
    path("<int:pk>/", MyDiaryDetailView.as_view(), name="diary-detail"),
]
