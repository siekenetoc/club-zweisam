from django.urls import path

from apps.insights import views

app_name = "insights"

urlpatterns = [
    path("", views.index, name="index"),
    path("<int:pk>/teilen/", views.share, name="share"),
    path("<int:pk>/vote/", views.vote, name="vote"),
    path("<int:pk>/loeschen/", views.delete, name="delete"),
]
