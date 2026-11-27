from django.urls import path

from apps.moments import views

app_name = "moments"

urlpatterns = [
    path("", views.index, name="index"),
    path("antwort/", views.answer, name="answer"),
]
