import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from apps.clubroom.permissions import (
    MODULES,
    OWNER,
    ROLE_CHOICES,
    default_permissions_for,
    role_can_write,
)
from apps.core.crypto import EncryptedTextField
from apps.core.models import SoftDeleteModel, TimestampedModel


def default_invitation_expiry():
    days = getattr(settings, "INVITATION_TTL_DAYS", 7)
    return timezone.now() + timedelta(days=days)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class Clubroom(TimestampedModel, SoftDeleteModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="founded_clubrooms",
    )
    safe_word = EncryptedTextField()
    rules = models.TextField(blank=True)

    class Meta:
        verbose_name = "Clubraum"
        verbose_name_plural = "Clubräume"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._unique_slug()
        super().save(*args, **kwargs)

    def _unique_slug(self) -> str:
        base = slugify(self.name)[:120] or "clubraum"
        candidate = base
        suffix = 2
        while Clubroom.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
            candidate = f"{base}-{suffix}"
            suffix += 1
        return candidate

    def active_memberships(self):
        return self.memberships.filter(revoked_at__isnull=True).select_related("user")

    def active_owners(self):
        return self.active_memberships().filter(role=OWNER)


class Membership(TimestampedModel):
    clubroom = models.ForeignKey(Clubroom, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=32, choices=ROLE_CHOICES)
    module_permissions = models.JSONField(default=dict, blank=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sent_memberships",
    )
    invited_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(default=timezone.now)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Mitgliedschaft"
        verbose_name_plural = "Mitgliedschaften"
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(revoked_at__isnull=True),
                name="unique_active_membership_per_user",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user} in {self.clubroom} ({self.role})"

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None

    def save(self, *args, **kwargs):
        if not self.module_permissions:
            self.module_permissions = default_permissions_for(self.role)
        super().save(*args, **kwargs)

    def has_module_access(self, module: str) -> bool:
        if module not in MODULES or not self.is_active:
            return False
        return bool(self.module_permissions.get(module, False))

    def can_write_module(self, module: str) -> bool:
        return self.has_module_access(module) and role_can_write(self.role)

    def revoke(self):
        self.revoked_at = timezone.now()
        self.save(update_fields=["revoked_at", "updated_at"])


class Invitation(TimestampedModel):
    clubroom = models.ForeignKey(Clubroom, on_delete=models.CASCADE, related_name="invitations")
    email = models.EmailField()
    role = models.CharField(max_length=32, choices=ROLE_CHOICES)
    token_hash = models.CharField(max_length=64, unique=True, editable=False)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sent_invitations",
    )
    expires_at = models.DateTimeField(default=default_invitation_expiry)
    accepted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Einladung"
        verbose_name_plural = "Einladungen"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["clubroom", "email"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self) -> str:
        return f"Einladung an {self.email} ({self.clubroom})"

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @property
    def is_pending(self) -> bool:
        return self.accepted_at is None and self.revoked_at is None and not self.is_expired

    @classmethod
    def issue(cls, *, clubroom, email, role, invited_by) -> tuple["Invitation", str]:
        raw_token = secrets.token_urlsafe(32)
        invitation = cls.objects.create(
            clubroom=clubroom,
            email=email,
            role=role,
            invited_by=invited_by,
            token_hash=hash_token(raw_token),
        )
        return invitation, raw_token

    def revoke(self):
        self.revoked_at = timezone.now()
        self.save(update_fields=["revoked_at", "updated_at"])
