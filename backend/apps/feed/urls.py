from django.urls import path

from apps.feed import views

app_name = "feed"

urlpatterns = [
    path("", views.index, name="index"),
    path("<int:pk>/entfernen/", views.remove, name="remove"),
]
