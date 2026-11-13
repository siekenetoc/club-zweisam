from django.urls import path

from apps.crisis import views

app_name = "crisis"

urlpatterns = [
    path("", views.index, name="index"),
    path("start/", views.start, name="start"),
    path("<int:pk>/", views.session_detail, name="session"),
    path("<int:pk>/beenden/", views.end, name="end"),
]
