from django.urls import path

from apps.calendar import datenight_views

app_name = "datenight"

urlpatterns = [
    path("", datenight_views.index, name="index"),
    path("<int:pk>/antwort/", datenight_views.respond, name="respond"),
    path("<int:pk>/absagen/", datenight_views.cancel, name="cancel"),
]
