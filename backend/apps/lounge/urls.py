from django.urls import path

from apps.lounge import views

app_name = "lounge"

urlpatterns = [
    path("", views.index, name="index"),
    path("check-in/", views.check_in, name="check_in"),
    path("wochenrueckblick/", views.toggle_review, name="toggle_review"),
    path("safe-mode/", views.safe_mode, name="safe_mode"),
]
