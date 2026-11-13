from django.urls import path

from apps.vitrine import views

app_name = "vitrine"

urlpatterns = [
    path("", views.index, name="index"),
]
