from django.conf import settings
from django.db import models

from apps.clubroom.models import Clubroom
from apps.core.audit import AuditedModel
from apps.core.crypto import EncryptedTextField
from apps.core.models import SoftDeleteModel

TYPE_OPEN = "offen"
TYPE_CONCRETE = "konkret"
TYPE_FANTASY = "fantasie"
TYPE_TEST = "test"
TYPE_BOUNDARY = "grenz"

TYPE_CHOICES = (
    (TYPE_OPEN, "Offen"),
    (TYPE_CONCRETE, "Konkret"),
    (TYPE_FANTASY, "Fantasie"),
    (TYPE_TEST, "Test"),
    (TYPE_BOUNDARY, "Grenze"),
)

TYPE_LABELS = dict(TYPE_CHOICES)

STATUS_DRAFT = "draft"
STATUS_PLACED = "placed"
STATUS_REPLIED = "replied"
STATUS_AGREED = "agreed"
STATUS_FULFILLED = "fulfilled"
STATUS_PENDING = "pending"
STATUS_CONFIRMED = "confirmed"
STATUS_REJECTED = "rejected"
STATUS_BOUNDARY = "boundary"
STATUS_POSTPONED = "postponed"
STATUS_EXPIRED = "expired"

STATUS_CHOICES = (
    (STATUS_DRAFT, "Entwurf (privat)"),
    (STATUS_PLACED, "Gestellt"),
    (STATUS_REPLIED, "Beantwortet"),
    (STATUS_AGREED, "Vereinbart"),
    (STATUS_FULFILLED, "Erfüllt"),
    (STATUS_PENDING, "Bestätigung ausstehend"),
    (STATUS_CONFIRMED, "Bestätigt"),
    (STATUS_REJECTED, "Abgelehnt"),
    (STATUS_BOUNDARY, "Grenze respektiert"),
    (STATUS_POSTPONED, "Verschoben"),
    (STATUS_EXPIRED, "Abgelaufen"),
)

STATUS_LABELS = dict(STATUS_CHOICES)

TIMEFRAME_CHOICES = (
    ("heute", "Heute"),
    ("woche", "Diese Woche"),
    ("monat", "Diesen Monat"),
    ("offen", "Ohne Frist"),
)

INTENSITY_CHOICES = (
    (1, "1 – leicht"),
    (2, "2 – mittel"),
    (3, "3 – intensiv"),
)

ACTION_ACCEPT = "accept"
ACTION_PARTIAL = "partial"
ACTION_ALTERNATIVE = "alternative"
ACTION_POSTPONE = "postpone"
ACTION_REJECT = "reject"
ACTION_BOUNDARY = "boundary"
ACTION_TALK = "talk"

ACTION_CHOICES = (
    (ACTION_ACCEPT, "Annehmen"),
    (ACTION_PARTIAL, "Teilweise annehmen"),
    (ACTION_ALTERNATIVE, "Alternative vorschlagen"),
    (ACTION_POSTPONE, "Verschieben"),
    (ACTION_REJECT, "Ablehnen"),
    (ACTION_BOUNDARY, "Grenze setzen"),
    (ACTION_TALK, "Erst darüber sprechen"),
)

ACTION_LABELS = dict(ACTION_CHOICES)

NOTE_REQUIRED_ACTIONS = frozenset({ACTION_PARTIAL, ACTION_ALTERNATIVE, ACTION_TALK})


class Wish(AuditedModel, SoftDeleteModel):
    clubroom = models.ForeignKey(Clubroom, on_delete=models.CASCADE, related_name="wishes")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_wishes",
    )
    type = models.CharField(max_length=16, choices=TYPE_CHOICES)
    category = models.CharField(max_length=80, blank=True)
    intensity = models.PositiveSmallIntegerField(choices=INTENSITY_CHOICES, default=1)
    timeframe = models.CharField(max_length=16, choices=TIMEFRAME_CHOICES, default="offen")
    title = models.CharField(max_length=160)
    body = EncryptedTextField()
    is_private = models.BooleanField(default=False)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    responded_at = models.DateTimeField(null=True, blank=True)
    agreed_at = models.DateTimeField(null=True, blank=True)
    fulfilled_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Wunsch"
        verbose_name_plural = "Wünsche"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["clubroom", "status"]),
            models.Index(fields=["clubroom", "created_at"]),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def type_label(self) -> str:
        return TYPE_LABELS.get(self.type, self.type)

    @property
    def status_label(self) -> str:
        return STATUS_LABELS.get(self.status, self.status)

    def can_view(self, user) -> bool:
        if self.created_by_id == user.id:
            return True
        return not self.is_private


class WishResponse(models.Model):
    wish = models.ForeignKey(Wish, on_delete=models.CASCADE, related_name="responses")
    responded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="wish_responses",
    )
    action = models.CharField(max_length=16, choices=ACTION_CHOICES)
    note = EncryptedTextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Wunsch-Antwort"
        verbose_name_plural = "Wunsch-Antworten"
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["wish", "responded_by"],
                name="unique_response_per_user_per_wish",
            )
        ]

    def __str__(self) -> str:
        return f"{self.get_action_display()} auf {self.wish_id}"

    @property
    def action_label(self) -> str:
        return ACTION_LABELS.get(self.action, self.action)
