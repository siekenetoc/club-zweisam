from django.urls import path

from apps.admin_panel import views

app_name = "admin_panel"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("messenger/", views.messenger_setup, name="messenger_setup"),
    path("break-glass/", views.break_glass, name="break_glass"),
    path(
        "break-glass/<int:pk>/approve/",
        views.break_glass_approve,
        name="break_glass_approve",
    ),
    path(
        "break-glass/<int:pk>/use/",
        views.break_glass_use,
        name="break_glass_use",
    ),
]
