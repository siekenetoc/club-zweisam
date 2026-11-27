from django.conf import settings
from django.db import models

from apps.clubroom.models import Clubroom
from apps.core.crypto import EncryptedTextField
from apps.core.models import TimestampedModel


class Album(TimestampedModel):
    clubroom = models.ForeignKey(Clubroom, on_delete=models.CASCADE, related_name="albums")
    title = models.CharField(max_length=160)
    description = EncryptedTextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_albums"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title


class GalleryImage(TimestampedModel):
    album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="gallery/")
    thumb = models.ImageField(upload_to="gallery/thumbs/", blank=True)
    caption = EncryptedTextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="uploaded_gallery_images"
    )
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.caption or f"Bild {self.pk}"
