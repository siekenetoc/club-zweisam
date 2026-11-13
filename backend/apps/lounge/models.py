from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.clubroom.models import Clubroom
from apps.core.models import TimestampedModel


def today():
    return timezone.localdate()


class CheckIn(TimestampedModel):
    clubroom = models.ForeignKey(Clubroom, on_delete=models.CASCADE, related_name="check_ins")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="check_ins",
    )
    date = models.DateField(default=today)
    mood = models.PositiveSmallIntegerField()
    energy = models.PositiveSmallIntegerField()
    closeness = models.PositiveSmallIntegerField()

    class Meta:
        verbose_name = "Check-in"
        verbose_name_plural = "Check-ins"
        ordering = ["-date", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["clubroom", "user", "date"],
                name="unique_checkin_per_user_per_day",
            )
        ]

    def __str__(self) -> str:
        return f"Check-in {self.user_id} {self.date}"

    def clean(self):
        from django.core.exceptions import ValidationError

        for field in ("mood", "energy", "closeness"):
            value = getattr(self, field)
            if value < 1 or value > 5:
                raise ValidationError({field: "Wert muss zwischen 1 und 5 liegen."})


class WeeklyReviewOptIn(TimestampedModel):
    clubroom = models.ForeignKey(
        Clubroom, on_delete=models.CASCADE, related_name="weekly_review_opt_ins"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="weekly_review_opt_ins",
    )

    class Meta:
        verbose_name = "Wochenrückblick-Opt-in"
        verbose_name_plural = "Wochenrückblick-Opt-ins"
        constraints = [
            models.UniqueConstraint(fields=["clubroom", "user"], name="unique_weekly_review_opt_in")
        ]

    def __str__(self) -> str:
        return f"Wochenrückblick {self.user_id}"
