from django.urls import path

from apps.admin_panel import views

app_name = "admin_panel"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("content/", views.content_overview, name="content"),
    path("content/<str:kind>/<int:pk>/", views.content_edit, name="content_edit"),
    path(
        "content/landing/", views.content_edit, {"kind": "landing", "pk": 1}, name="content_landing"
    ),
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
