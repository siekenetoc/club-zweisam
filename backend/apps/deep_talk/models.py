from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.clubroom.models import Clubroom
from apps.core.models import TimestampedModel

MODE_TALK = "talk"
MODE_REPAIR = "repair"
MODE_CRISIS = "crisis"

MODE_CHOICES = (
    (MODE_TALK, "Gespräch"),
    (MODE_REPAIR, "Reparatur"),
    (MODE_CRISIS, "Krisenmodus"),
)

MODE_LABELS = dict(MODE_CHOICES)

TALK_PROMPTS = (
    "Was möchtest du sagen, ohne unterbrochen zu werden?",
    "Was brauchst du gerade von mir?",
    "Wann hast du dich zuletzt gesehen gefühlt?",
    "Welche Erwartung hast du an dieses Gespräch?",
    "Was möchtest du nicht hören?",
    "Was wäre ein gutes Ende für dieses Gespräch?",
)

REPAIR_PROMPTS = (
    "Was hat dich verletzt – ohne Bewertung?",
    "Was brauchst du, um dich wieder sicher zu fühlen?",
    "Welchen Anteil übernehme ich?",
    "Was hilft dir, mir wieder zu vertrauen?",
    "Was sollten wir beim nächsten Mal anders machen?",
    "Was ist ein kleiner nächster Schritt?",
)

PROMPTS_BY_MODE = {
    MODE_TALK: TALK_PROMPTS,
    MODE_REPAIR: REPAIR_PROMPTS,
    MODE_CRISIS: (),
}


class TalkSession(TimestampedModel):
    clubroom = models.ForeignKey(Clubroom, on_delete=models.CASCADE, related_name="talk_sessions")
    mode = models.CharField(max_length=16, choices=MODE_CHOICES)
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="started_talk_sessions",
    )
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    timeout_at = models.DateTimeField(null=True, blank=True)
    timeout_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="triggered_talk_timeouts",
    )

    class Meta:
        verbose_name = "Deep-Talk-Sitzung"
        verbose_name_plural = "Deep-Talk-Sitzungen"
        ordering = ["-started_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["clubroom", "mode"],
                condition=models.Q(ended_at__isnull=True),
                name="unique_active_talk_session_per_mode",
            )
        ]

    def __str__(self) -> str:
        return f"{self.get_mode_display()} ({self.clubroom_id})"

    @property
    def is_active(self) -> bool:
        return self.ended_at is None

    @property
    def is_paused(self) -> bool:
        return self.timeout_at is not None


class TalkPrompt(models.Model):
    session = models.ForeignKey(TalkSession, on_delete=models.CASCADE, related_name="prompts")
    text = models.TextField()
    answered = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Leitfrage"
        verbose_name_plural = "Leitfragen"
        ordering = ["id"]

    def __str__(self) -> str:
        return self.text[:60]
