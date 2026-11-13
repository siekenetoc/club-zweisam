from django.db import models

from apps.clubroom.models import Clubroom
from apps.core.models import TimestampedModel

SOURCE_MATCH = "match"
SOURCE_WISH = "wish"
SOURCE_CHALLENGE = "challenge"
SOURCE_REWARD = "reward"

SOURCE_CHOICES = (
    (SOURCE_MATCH, "Match"),
    (SOURCE_WISH, "Wunsch"),
    (SOURCE_CHALLENGE, "Challenge"),
    (SOURCE_REWARD, "Belohnung"),
)


class Commonality(TimestampedModel):
    clubroom = models.ForeignKey(Clubroom, on_delete=models.CASCADE, related_name="commonalities")
    source_type = models.CharField(max_length=16, choices=SOURCE_CHOICES)
    source_id = models.PositiveBigIntegerField()
    category = models.CharField(max_length=120)

    class Meta:
        verbose_name = "Gemeinsamkeit"
        verbose_name_plural = "Gemeinsamkeiten"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["clubroom", "source_type", "source_id"],
                name="unique_commonality_source",
            )
        ]

    def __str__(self) -> str:
        return f"{self.get_source_type_display()}: {self.category}"
