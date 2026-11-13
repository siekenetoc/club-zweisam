from django.urls import path

from apps.roulette import views

app_name = "roulette"

urlpatterns = [
    path("", views.index, name="index"),
    path("start/<int:deck_id>/", views.start, name="start"),
    path("opt-in/<int:deck_id>/", views.opt_in_deck, name="opt_in"),
    path("runde/<int:pk>/", views.round_detail, name="round"),
    path(
        "runde/<int:round_pk>/antwort/<int:question_id>/",
        views.answer,
        name="answer",
    ),
    path("freigabe/<int:pk>/", views.release, name="release"),
    path("runde/<int:pk>/beenden/", views.close_round, name="close"),
]
