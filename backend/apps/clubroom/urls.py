from django.urls import path

from apps.clubroom import views

app_name = "clubroom"

urlpatterns = [
    path("", views.home, name="home"),
    path("clubraum/neu/", views.clubroom_create, name="create"),
    path("clubraum/einstellungen/", views.clubroom_settings, name="settings"),
    path("clubraum/einladen/", views.invitation_create, name="invite"),
    path(
        "einladung/<str:token>/",
        views.invitation_accept,
        name="invitation_accept",
    ),
    path(
        "clubraum/einladung/<int:pk>/widerrufen/",
        views.invitation_revoke,
        name="invitation_revoke",
    ),
    path(
        "clubraum/einladung/<int:pk>/erneut-senden/",
        views.invitation_resend,
        name="invitation_resend",
    ),
    path(
        "clubraum/mitglied/<int:pk>/entfernen/",
        views.membership_revoke,
        name="membership_revoke",
    ),
]
