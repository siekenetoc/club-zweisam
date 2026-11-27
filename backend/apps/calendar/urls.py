from django.urls import path

from apps.calendar import views

app_name = "calendar"

urlpatterns = [
    path("", views.index, name="index"),
    path("eintrag/<int:pk>/loeschen/", views.delete_entry, name="delete"),
    path("eintrag/<int:pk>/erledigt/", views.toggle_task, name="toggle_task"),
    path("abo/erneuern/", views.regenerate_feed, name="regenerate_feed"),
    path("feed/<str:token>.ics", views.feed, name="feed"),
]
