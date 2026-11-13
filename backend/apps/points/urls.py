from django.urls import path

from apps.points import views

app_name = "points"

urlpatterns = [
    path("", views.index, name="index"),
    path("mein/", views.my_points, name="my"),
    path("einloesen/<int:reward_id>/", views.redeem, name="redeem"),
    path(
        "einloesung/<int:pk>/<str:action>/",
        views.redemption_action,
        name="redemption_action",
    ),
    path("anerkennung/", views.recognize, name="recognize"),
]
