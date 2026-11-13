import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower


class User(AbstractUser):
    is_safe_mode_active = models.BooleanField(default=False)
    notification_queue_id = models.UUIDField(default=uuid.uuid4, editable=False)
    age_verified = models.BooleanField(default=False)
    tos_accepted_at = models.DateTimeField(null=True, blank=True)

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
        return self.username
