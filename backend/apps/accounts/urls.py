from django.urls import path

from apps.accounts import views

app_name = "accounts"

urlpatterns = [
    path("registrieren/", views.register, name="register"),
    path("anmelden/", views.ClubLoginView.as_view(), name="login"),
    path("abmelden/", views.ClubLogoutView.as_view(), name="logout"),
    path("konto/export/", views.data_export, name="export"),
    path("konto/loeschen/", views.delete_account, name="delete"),
]
