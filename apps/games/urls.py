from django.urls import path

from .views import GameHomeView, GameLetterView, RunFinishView, RunStartView

urlpatterns = [
    path("", GameHomeView.as_view(), name="game-home"),
    path("letters/<int:pk>/", GameLetterView.as_view(), name="game-letter"),
    path("runs/", RunStartView.as_view(), name="game-run-start"),
    path("runs/<int:pk>/finish/", RunFinishView.as_view(), name="game-run-finish"),
]
