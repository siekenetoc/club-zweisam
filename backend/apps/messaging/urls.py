from django.urls import path

from apps.messaging import views

app_name = "messaging"

urlpatterns = [
    path("", views.index, name="index"),
    path("quick/", views.send_quick, name="quick"),
    path("<int:pk>/loeschen/", views.delete_message, name="delete"),
]
