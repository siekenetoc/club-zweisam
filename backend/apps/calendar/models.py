import hashlib
import secrets

from django.conf import settings
from django.db import models

from apps.clubroom.models import Clubroom
from apps.core.crypto import EncryptedTextField
from apps.core.models import TimestampedModel

KIND_EVENT = "event"
KIND_TASK = "task"
KIND_CHOICES = ((KIND_EVENT, "Termin"), (KIND_TASK, "Aufgabe"))


class CalendarEntry(TimestampedModel):
    clubroom = models.ForeignKey(
        Clubroom, on_delete=models.CASCADE, related_name="calendar_entries"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="calendar_entries",
    )
    kind = models.CharField(max_length=8, choices=KIND_CHOICES, default=KIND_EVENT)
    title = models.CharField(max_length=160)
    description = EncryptedTextField(blank=True)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField(null=True, blank=True)
    all_day = models.BooleanField(default=False)
    is_done = models.BooleanField(default=False)
    done_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Kalendereintrag"
        verbose_name_plural = "Kalendereinträge"
        ordering = ["start_at", "id"]
        indexes = [models.Index(fields=["clubroom", "start_at"])]

    def __str__(self) -> str:
        return self.title


class CalendarFeedToken(TimestampedModel):
    clubroom = models.ForeignKey(
        Clubroom, on_delete=models.CASCADE, related_name="calendar_feed_tokens"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="calendar_feed_tokens",
    )
    token_hash = models.CharField(max_length=64, unique=True)
    include_details = models.BooleanField(default=False)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["clubroom", "user"], name="unique_calendar_feed_per_user"
            )
        ]

    @classmethod
    def issue(cls, *, clubroom, user, include_details=False):
        raw = secrets.token_urlsafe(32)
        obj, _ = cls.objects.update_or_create(
            clubroom=clubroom,
            user=user,
            defaults={
                "token_hash": hashlib.sha256(raw.encode()).hexdigest(),
                "include_details": include_details,
                "revoked_at": None,
            },
        )
        return obj, raw

    @staticmethod
    def hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None
