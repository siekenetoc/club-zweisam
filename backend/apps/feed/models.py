from django.conf import settings
from django.db import models

from apps.clubroom.models import Clubroom
from apps.core.crypto import EncryptedTextField
from apps.core.models import SoftDeleteModel, TimestampedModel

EVENT_CLUBROOM_CREATED = "clubroom.created"
EVENT_MEMBER_JOINED = "member.joined"
EVENT_MEMBER_REMOVED = "member.removed"
EVENT_WISH_CREATED = "wish.created"
EVENT_WISH_SHARED = "wish.shared"
EVENT_WISH_DECIDED = "wish.decided"
EVENT_WISH_RESPONDED = "wish.responded"
EVENT_WISH_FULFILLED = "wish.fulfilled"
EVENT_WISH_CONFIRMED = "wish.confirmed"
EVENT_MATCH_RELEASED = "match.released"
EVENT_ROUND_STARTED = "roulette.round.started"
EVENT_ROUND_ENDED = "roulette.round.ended"
EVENT_CHALLENGE_STARTED = "challenge.started"
EVENT_CHALLENGE_COMPLETED = "challenge.completed"
EVENT_CHALLENGE_ABORTED = "challenge.aborted"
EVENT_CHECKIN_CREATED = "checkin.created"
EVENT_BREAK_GLASS_ACCESS = "break_glass.access"

EVENT_CHOICES = (
    (EVENT_CLUBROOM_CREATED, "Clubraum gegründet"),
    (EVENT_MEMBER_JOINED, "Mitglied beigetreten"),
    (EVENT_MEMBER_REMOVED, "Mitglied entfernt"),
    (EVENT_WISH_CREATED, "Wunsch gestellt"),
    (EVENT_WISH_SHARED, "Wunsch geteilt"),
    (EVENT_WISH_DECIDED, "Wunsch-Entscheidung"),
    (EVENT_WISH_RESPONDED, "Wunsch beantwortet"),
    (EVENT_WISH_FULFILLED, "Wunsch erfüllt gemeldet"),
    (EVENT_WISH_CONFIRMED, "Wunsch bestätigt"),
    (EVENT_MATCH_RELEASED, "Match freigegeben"),
    (EVENT_ROUND_STARTED, "Séparée-Runde gestartet"),
    (EVENT_ROUND_ENDED, "Séparée-Runde beendet"),
    (EVENT_CHALLENGE_STARTED, "Challenge gestartet"),
    (EVENT_CHALLENGE_COMPLETED, "Challenge abgeschlossen"),
    (EVENT_CHALLENGE_ABORTED, "Challenge abgebrochen"),
    (EVENT_CHECKIN_CREATED, "Check-in"),
    (EVENT_BREAK_GLASS_ACCESS, "Admin-Zugriff protokolliert"),
)

SENSITIVE_METADATA_KEYS = frozenset(
    {
        "title",
        "body",
        "note",
        "answer",
        "answers",
        "safe_word",
        "email",
        "token",
        "reason",
    }
)


def sanitize_metadata(metadata: dict | None) -> dict:
    if not metadata:
        return {}
    return {key: value for key, value in metadata.items() if key not in SENSITIVE_METADATA_KEYS}


class FeedEvent(TimestampedModel, SoftDeleteModel):
    clubroom = models.ForeignKey(Clubroom, on_delete=models.CASCADE, related_name="feed_events")
    event_type = models.CharField(max_length=48, choices=EVENT_CHOICES)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="feed_events",
    )
    target_type = models.CharField(max_length=64, blank=True)
    target_id = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Logbuch-Eintrag"
        verbose_name_plural = "Logbuch-Einträge"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["clubroom", "-created_at"]),
            models.Index(fields=["clubroom", "event_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_event_type_display()} ({self.clubroom_id})"

    def soft_delete(self):
        from django.utils import timezone

        self.metadata = {}
        self.deleted_at = timezone.now()
        self.save(update_fields=["metadata", "deleted_at", "updated_at"])


PROVIDER_WHATSAPP = "whatsapp"
PROVIDER_TELEGRAM = "telegram"
PROVIDER_SIGNAL = "signal"
PROVIDER_ELEMENT = "element"
PROVIDER_GOTIFY = "gotify"

PROVIDER_CHOICES = (
    (PROVIDER_WHATSAPP, "WhatsApp Cloud API"),
    (PROVIDER_TELEGRAM, "Telegram Bot"),
    (PROVIDER_SIGNAL, "Signal (signal-cli REST)"),
    (PROVIDER_ELEMENT, "Element/Matrix"),
    (PROVIDER_GOTIFY, "Gotify"),
)


class NotificationChannel(TimestampedModel):
    clubroom = models.ForeignKey(
        Clubroom, on_delete=models.CASCADE, related_name="notification_channels"
    )
    provider = models.CharField(max_length=16, choices=PROVIDER_CHOICES)
    label = models.CharField(max_length=80)
    config = EncryptedTextField(blank=True)
    is_enabled = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_notification_channels",
    )

    class Meta:
        verbose_name = "Benachrichtigungskanal"
        verbose_name_plural = "Benachrichtigungskanäle"
        ordering = ["clubroom", "provider", "label"]
        constraints = [
            models.UniqueConstraint(
                fields=["clubroom", "label"], name="unique_channel_label_per_clubroom"
            )
        ]

    def __str__(self) -> str:
        return f"{self.get_provider_display()} – {self.label}"

    def get_config(self) -> dict:
        import json

        try:
            value = json.loads(self.config or "{}")
        except (TypeError, ValueError):
            return {}
        return value if isinstance(value, dict) else {}

    def set_config(self, value: dict) -> None:
        import json

        self.config = json.dumps(value, ensure_ascii=False)


class NotificationSubscription(TimestampedModel):
    channel = models.ForeignKey(
        NotificationChannel, on_delete=models.CASCADE, related_name="subscriptions"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_subscriptions",
    )
    destination = EncryptedTextField(blank=True)
    is_enabled = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Push-Abonnement"
        verbose_name_plural = "Push-Abonnements"
        constraints = [
            models.UniqueConstraint(
                fields=["channel", "user"], name="unique_subscription_per_channel"
            )
        ]

    def __str__(self) -> str:
        return f"{self.user} – {self.channel}"


class Notification(TimestampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    clubroom = models.ForeignKey(
        Clubroom,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    event_type = models.CharField(max_length=48, choices=EVENT_CHOICES)
    queued_during_safe_mode = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Benachrichtigung"
        verbose_name_plural = "Benachrichtigungen"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "delivered_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_event_type_display()} für {self.user_id}"

    def mark_delivered(self):
        from django.utils import timezone

        self.delivered_at = timezone.now()
        self.save(update_fields=["delivered_at", "updated_at"])

    @property
    def is_delivered(self) -> bool:
        return self.delivered_at is not None
