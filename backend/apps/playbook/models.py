from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.clubroom.models import Clubroom
from apps.core.models import TimestampedModel

CATEGORY_CHOICES = (
    ("alltag", "Alltag"),
    ("naehe", "Nähe"),
    ("neugier", "Neugier"),
    ("spiel", "Spiel"),
    ("kommunikation", "Kommunikation"),
    ("abenteuer", "Abenteuer"),
    ("erholung", "Erholung"),
    ("sinnlichkeit", "Sinnlichkeit"),
)

CATEGORY_LABELS = dict(CATEGORY_CHOICES)

CONSENT_STAGE_CHOICES = (
    (1, "Stufe 1 – niedrigschwellig"),
    (2, "Stufe 2 – bewusst"),
    (3, "Stufe 3 – nur mit Opt-in"),
)


class Challenge(TimestampedModel):
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES)
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    duration_min = models.PositiveSmallIntegerField(default=10)
    intensity = models.PositiveSmallIntegerField(choices=CONSENT_STAGE_CHOICES, default=1)
    consent_stage = models.PositiveSmallIntegerField(choices=CONSENT_STAGE_CHOICES, default=1)
    points = models.PositiveSmallIntegerField(default=1)

    class Meta:
        verbose_name = "Challenge"
        verbose_name_plural = "Challenges"
        ordering = ["category", "intensity", "title"]

    def __str__(self) -> str:
        return self.title

    @property
    def category_label(self) -> str:
        return CATEGORY_LABELS.get(self.category, self.category)

    @property
    def requires_opt_in(self) -> bool:
        return self.consent_stage >= 3


class PlaybookOptIn(TimestampedModel):
    clubroom = models.ForeignKey(
        Clubroom, on_delete=models.CASCADE, related_name="playbook_opt_ins"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="playbook_opt_ins",
    )

    class Meta:
        verbose_name = "Playbook-Opt-in (Stufe 3)"
        verbose_name_plural = "Playbook-Opt-ins (Stufe 3)"
        constraints = [
            models.UniqueConstraint(fields=["clubroom", "user"], name="unique_playbook_opt_in")
        ]

    def __str__(self) -> str:
        return f"{self.user} – Stufe 3"


class ChallengeRun(TimestampedModel):
    challenge = models.ForeignKey(Challenge, on_delete=models.PROTECT, related_name="runs")
    clubroom = models.ForeignKey(Clubroom, on_delete=models.CASCADE, related_name="challenge_runs")
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="started_challenge_runs",
    )
    user_a = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="challenge_runs_as_a",
    )
    user_b = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="challenge_runs_as_b",
    )
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    confirmed_by_a = models.BooleanField(default=False)
    confirmed_by_b = models.BooleanField(default=False)
    aborted_at = models.DateTimeField(null=True, blank=True)
    aborted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="aborted_challenge_runs",
    )

    class Meta:
        verbose_name = "Challenge-Lauf"
        verbose_name_plural = "Challenge-Läufe"
        ordering = ["-started_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["clubroom"],
                condition=models.Q(completed_at__isnull=True) & models.Q(aborted_at__isnull=True),
                name="unique_active_challenge_run_per_clubroom",
            )
        ]

    def __str__(self) -> str:
        return f"{self.challenge} ({self.clubroom})"

    @property
    def is_active(self) -> bool:
        return self.completed_at is None and self.aborted_at is None

    @property
    def is_aborted(self) -> bool:
        return self.aborted_at is not None

    @property
    def is_completed(self) -> bool:
        return self.completed_at is not None

    def participants(self):
        return [user for user in (self.user_a, self.user_b) if user is not None]

    def confirmation_for(self, user) -> bool:
        if user.id == self.user_a_id:
            return self.confirmed_by_a
        if self.user_b_id is not None and user.id == self.user_b_id:
            return self.confirmed_by_b
        return False

    def has_confirmed(self, user) -> bool:
        return self.confirmation_for(user)
