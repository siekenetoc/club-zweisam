from django.conf import settings
from django.db import models

from apps.clubroom.models import Clubroom
from apps.core.crypto import EncryptedTextField
from apps.core.models import TimestampedModel

STATUS_PRIVATE = "private"
STATUS_SHARED = "shared"
STATUS_CHOICES = ((STATUS_PRIVATE, "Privat"), (STATUS_SHARED, "Geteilt"))

VOTE_AGREE = "agree"
VOTE_UNSURE = "unsure"
VOTE_DISAGREE = "disagree"
VOTE_CHOICES = (
    (VOTE_AGREE, "Stimme zu"),
    (VOTE_UNSURE, "Unsicher"),
    (VOTE_DISAGREE, "Widerspruch"),
)


class Insight(TimestampedModel):
    clubroom = models.ForeignKey(Clubroom, on_delete=models.CASCADE, related_name="insights")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="insights"
    )
    title = models.CharField(max_length=160)
    body = EncryptedTextField()
    status = models.CharField(max_length=8, choices=STATUS_CHOICES, default=STATUS_PRIVATE)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title


class InsightVote(TimestampedModel):
    insight = models.ForeignKey(Insight, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="insight_votes"
    )
    value = models.CharField(max_length=10, choices=VOTE_CHOICES)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["insight", "user"], name="unique_insight_vote")
        ]
