from django.conf import settings
from django.db import models

from apps.clubroom.models import Clubroom
from apps.core.models import TimestampedModel

SCOPE_DYAD = "dyad"
SCOPE_GUEST = "guest"

SCOPE_CHOICES = (
    (SCOPE_DYAD, "Dyade"),
    (SCOPE_GUEST, "Gast (isoliert)"),
)

REASON_CHALLENGE = "challenge.completed"
REASON_WISH = "wish.confirmed"
REASON_REDEEM = "reward.redeem"
REASON_REFUND = "reward.refund"
REASON_RECOGNITION = "guest.recognition"

REASON_CHOICES = (
    (REASON_CHALLENGE, "Challenge abgeschlossen"),
    (REASON_WISH, "Wunsch bestätigt"),
    (REASON_REDEEM, "Belohnung eingelöst"),
    (REASON_REFUND, "Belohnung zurückgebucht"),
    (REASON_RECOGNITION, "Anerkennung"),
)

REWARD_CATEGORY_CHOICES = (
    ("romantisch", "Romantisch"),
    ("neckisch", "Neckisch"),
    ("erotisch", "Erotisch"),
    ("alltag", "Alltag"),
    ("erlebnis", "Erlebnisse"),
)

REDEMPTION_REQUESTED = "requested"
REDEMPTION_ACCEPTED = "accepted"
REDEMPTION_COMPLETED = "completed"
REDEMPTION_DECLINED = "declined"
REDEMPTION_CANCELLED = "cancelled"
REDEMPTION_REFUNDED = "refunded"

REDEMPTION_STATUS_CHOICES = (
    (REDEMPTION_REQUESTED, "Angefragt"),
    (REDEMPTION_ACCEPTED, "Angenommen"),
    (REDEMPTION_COMPLETED, "Abgeschlossen"),
    (REDEMPTION_DECLINED, "Abgelehnt"),
    (REDEMPTION_CANCELLED, "Zurückgezogen"),
    (REDEMPTION_REFUNDED, "Zurückgebucht"),
)


class Ledger(TimestampedModel):
    clubroom = models.ForeignKey(Clubroom, on_delete=models.CASCADE, related_name="ledgers")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ledgers"
    )
    scope = models.CharField(max_length=16, choices=SCOPE_CHOICES, default=SCOPE_DYAD)
    balance = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Punkte-Ledger"
        verbose_name_plural = "Punkte-Ledger"
        constraints = [
            models.UniqueConstraint(fields=["clubroom", "owner"], name="unique_ledger_per_owner")
        ]

    def __str__(self) -> str:
        return f"{self.owner} ({self.scope}): {self.balance}"


class Entry(TimestampedModel):
    ledger = models.ForeignKey(Ledger, on_delete=models.CASCADE, related_name="entries")
    delta = models.IntegerField()
    reason = models.CharField(max_length=32, choices=REASON_CHOICES)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="point_entries",
    )
    confirmed_by_other = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Punkte-Eintrag"
        verbose_name_plural = "Punkte-Einträge"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["ledger", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.delta:+d} ({self.get_reason_display()})"


class Reward(TimestampedModel):
    category = models.CharField(max_length=32, choices=REWARD_CATEGORY_CHOICES)
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    cost = models.PositiveIntegerField(default=1)
    consent_stage = models.PositiveSmallIntegerField(default=1)

    class Meta:
        verbose_name = "Belohnung"
        verbose_name_plural = "Belohnungen"
        ordering = ["category", "cost", "title"]

    def __str__(self) -> str:
        return f"{self.title} ({self.cost})"

    @property
    def category_label(self) -> str:
        return dict(REWARD_CATEGORY_CHOICES).get(self.category, self.category)


class Redemption(TimestampedModel):
    clubroom = models.ForeignKey(Clubroom, on_delete=models.CASCADE, related_name="redemptions")
    reward = models.ForeignKey(Reward, on_delete=models.PROTECT, related_name="redemptions")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requested_redemptions",
    )
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="accepted_redemptions",
    )
    status = models.CharField(
        max_length=16,
        choices=REDEMPTION_STATUS_CHOICES,
        default=REDEMPTION_REQUESTED,
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    refund_requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="refund_requested_redemptions",
    )
    refund_requested_at = models.DateTimeField(null=True, blank=True)
    refund_confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="refund_confirmed_redemptions",
    )
    refunded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Einlösung"
        verbose_name_plural = "Einlösungen"
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.reward} – {self.get_status_display()}"

    @property
    def refund_pending(self) -> bool:
        return self.refund_requested_at is not None and self.refunded_at is None

    def is_participant(self, user) -> bool:
        return user.id in {self.requested_by_id, self.accepted_by_id}
