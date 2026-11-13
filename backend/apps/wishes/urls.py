from django.urls import path

from apps.wishes import views

app_name = "wishes"

urlpatterns = [
    path("", views.index, name="index"),
    path("neu/", views.create, name="create"),
    path("<int:pk>/", views.detail, name="detail"),
    path("<int:pk>/antwort/", views.respond, name="respond"),
    path("<int:pk>/entscheidung/", views.decide, name="decide"),
    path("<int:pk>/erfuellt/", views.fulfill, name="fulfill"),
    path("<int:pk>/bestaetigen/", views.confirm, name="confirm"),
    path("<int:pk>/teilen/", views.share, name="share"),
]
