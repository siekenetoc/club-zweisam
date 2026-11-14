import hashlib
import json

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

GENESIS_HASH = "0" * 64


class AuditAppendOnlyError(RuntimeError):
    pass


class AuditEntry(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="audit_entries",
    )
    action = models.CharField(max_length=64)
    target_type = models.CharField(max_length=128, blank=True)
    target_id = models.CharField(max_length=128, blank=True)
    reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    prev_hash = models.CharField(max_length=64, editable=False)
    hash = models.CharField(max_length=64, editable=False, unique=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = "Audit-Eintrag"
        verbose_name_plural = "Audit-Einträge"
        indexes = [
            models.Index(fields=["target_type", "target_id"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} {self.target_type}:{self.target_id}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise AuditAppendOnlyError(
                "AuditEntry ist append-only und darf nicht verändert werden."
            )
        with transaction.atomic():
            last = AuditEntry.objects.select_for_update().order_by("-id").first()
            self.prev_hash = last.hash if last else GENESIS_HASH
            self.hash = self.compute_hash(self.prev_hash)
            return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise AuditAppendOnlyError("AuditEntry darf nicht gelöscht werden.")

    def payload(self, prev_hash: str) -> str:
        return json.dumps(
            {
                "actor_id": self.actor_id,
                "action": self.action,
                "target_type": self.target_type,
                "target_id": self.target_id,
                "reason": self.reason,
                "metadata": self.metadata,
                "created_at": self.created_at.isoformat(),
                "prev_hash": prev_hash,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        )

    def compute_hash(self, prev_hash: str) -> str:
        return hashlib.sha256((prev_hash + self.payload(prev_hash)).encode("utf-8")).hexdigest()

    @classmethod
    def verify_chain(cls) -> tuple[bool, int | None, str]:
        prev_hash = GENESIS_HASH
        for entry in cls.objects.order_by("id").iterator():
            if entry.prev_hash != prev_hash:
                return False, entry.pk, "prev_hash"
            if entry.hash != entry.compute_hash(prev_hash):
                return False, entry.pk, "hash"
            prev_hash = entry.hash
        return True, None, ""


class AuditedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def audit(self, action: str, *, actor=None, reason: str = "", **metadata):
        return AuditEntry.objects.create(
            actor=actor,
            action=action,
            target_type=self._meta.label_lower,
            target_id=str(self.pk or ""),
            reason=reason,
            metadata=metadata,
        )
