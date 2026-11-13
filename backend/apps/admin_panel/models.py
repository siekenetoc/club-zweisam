from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.audit import AuditEntry
from apps.core.models import TimestampedModel

TARGET_CLUBROOM = "clubroom.clubroom"
TARGET_MEMBERSHIP = "clubroom.membership"
TARGET_FEED_EVENT = "feed.feedevent"
TARGET_MATCH = "roulette.match"

ALLOWED_TARGET_TYPES = (
    (TARGET_CLUBROOM, "Clubraum (Metadaten)"),
    (TARGET_MEMBERSHIP, "Mitgliedschaft (Metadaten)"),
    (TARGET_FEED_EVENT, "Geteilter Logbuch-Eintrag"),
    (TARGET_MATCH, "Freigegebener Match"),
)

ALLOWED_TARGET_LABELS = {value for value, _ in ALLOWED_TARGET_TYPES}

STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_USED = "used"
STATUS_EXPIRED = "expired"
STATUS_REJECTED = "rejected"

BREAK_GLASS_HOURS = 24


class BreakGlassRequest(TimestampedModel):
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="break_glass_requests",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="approved_break_glass_requests",
    )
    target_type = models.CharField(max_length=64)
    target_id = models.CharField(max_length=64)
    reason = models.TextField()
    approved_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    used_at = models.DateTimeField(null=True, blank=True)
    users_notified = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Break-Glass-Antrag"
        verbose_name_plural = "Break-Glass-Anträge"
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"Break-Glass {self.target_type}:{self.target_id}"

    @property
    def status(self) -> str:
        if self.used_at is not None:
            return STATUS_USED
        if self.approved_at is None:
            return STATUS_PENDING
        if self.is_expired:
            return STATUS_EXPIRED
        return STATUS_APPROVED

    @property
    def is_expired(self) -> bool:
        return self.expires_at is not None and timezone.now() >= self.expires_at

    @property
    def is_usable(self) -> bool:
        return self.status == STATUS_APPROVED


def _audit(action, *, actor, request_obj: BreakGlassRequest, **metadata):
    return AuditEntry.objects.create(
        actor=actor,
        action=action,
        target_type=request_obj.target_type,
        target_id=request_obj.target_id,
        metadata={"request_id": request_obj.pk, **metadata},
    )
