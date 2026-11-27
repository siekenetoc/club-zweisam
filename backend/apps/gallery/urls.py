from django.urls import path

from apps.gallery import views

app_name = "gallery"

urlpatterns = [
    path("", views.index, name="index"),
    path("bild/<int:pk>/", views.image_file, name="image"),
    path("bild/<int:pk>/thumb/", views.thumb_file, name="thumb"),
    path("bild/<int:pk>/loeschen/", views.delete_image, name="delete"),
]
