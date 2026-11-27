import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower

from apps.core.crypto import EncryptedTextField


class User(AbstractUser):
    is_safe_mode_active = models.BooleanField(default=False)
    notification_queue_id = models.UUIDField(default=uuid.uuid4, editable=False)
    age_verified = models.BooleanField(default=False)
    tos_accepted_at = models.DateTimeField(null=True, blank=True)
    display_name = models.CharField(max_length=80, blank=True)
    pronouns = models.CharField(max_length=40, blank=True)
    timezone = models.CharField(max_length=64, blank=True, default="Europe/Berlin")
    bio = EncryptedTextField(blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True)
    avatar_thumb = models.ImageField(upload_to="avatars/thumbs/", blank=True)

    class Meta:
        verbose_name = "Nutzer"
        verbose_name_plural = "Nutzer"
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                condition=~models.Q(email=""),
                name="unique_user_email_ci",
            )
        ]

    def __str__(self) -> str:
        return self.display_name or self.get_full_name() or self.username

    @property
    def display_label(self) -> str:
        return self.display_name or self.get_full_name() or self.username
