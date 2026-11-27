from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.clubroom.models import Clubroom
from apps.core.crypto import EncryptedTextField
from apps.core.models import TimestampedModel

KIND_TEXT = "text"
KIND_QUICK = "quick"
KIND_CHOICES = ((KIND_TEXT, "Text"), (KIND_QUICK, "Kurzsignal"))

QUICK_MESSAGES = (
    ("danke", "Danke"),
    ("herz", "Herz"),
    ("umarmung", "Umarmung"),
    ("pause", "Pause"),
    ("vermissen", "Vermisse dich"),
    ("stolz", "Stolz auf dich"),
    ("denke", "Denke an dich"),
    ("naehe", "Brauche Nähe"),
)
QUICK_LABELS = dict(QUICK_MESSAGES)


class Message(TimestampedModel):
    clubroom = models.ForeignKey(Clubroom, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages",
    )
    body = EncryptedTextField(blank=True)
    kind = models.CharField(max_length=8, choices=KIND_CHOICES, default=KIND_TEXT)
    quick_key = models.CharField(max_length=32, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Nachricht"
        verbose_name_plural = "Nachrichten"
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["clubroom", "created_at"])]

    def __str__(self) -> str:
        return f"{self.sender} – {self.get_kind_display()}"

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @property
    def quick_label(self) -> str:
        return QUICK_LABELS.get(self.quick_key, self.quick_key)

    def mark_read(self):
        if self.read_at is None:
            self.read_at = timezone.now()
            self.save(update_fields=["read_at", "updated_at"])
