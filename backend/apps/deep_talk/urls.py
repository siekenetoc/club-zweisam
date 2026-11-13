from django.urls import path

from apps.deep_talk import views

app_name = "deep_talk"

urlpatterns = [
    path("", views.index, name="index"),
    path("start/<str:mode>/", views.start, name="start"),
    path("<int:pk>/", views.session_detail, name="session"),
    path("<int:pk>/frage/<int:prompt_id>/", views.toggle_prompt_view, name="toggle_prompt"),
    path("<int:pk>/timeout/", views.timeout, name="timeout"),
    path("<int:pk>/weiter/", views.resume, name="resume"),
    path("<int:pk>/beenden/", views.end, name="end"),
]
