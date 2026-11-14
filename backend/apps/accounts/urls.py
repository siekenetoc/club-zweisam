from allauth.account.views import LoginView, LogoutView, SignupView
from django.urls import path

from apps.accounts import views

app_name = "accounts"

urlpatterns = [
    path("registrieren/", SignupView.as_view(), name="register"),
    path("anmelden/", LoginView.as_view(), name="login"),
    path("abmelden/", LogoutView.as_view(), name="logout"),
    path("konto/", views.profile, name="profile"),
    path("konto/export/", views.data_export, name="export"),
    path("konto/loeschen/", views.delete_account, name="delete"),
]
