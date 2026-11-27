from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.clubroom.models import Clubroom
from apps.core.crypto import EncryptedTextField
from apps.core.models import TimestampedModel

QUESTIONS = (
    "Wann hast du dich zuletzt von mir gesehen gefühlt?",
    "Was brauchst du gerade, um dich sicher zu fühlen?",
    "Welche kleine Geste von mir bleibt dir im Kopf?",
    "Was möchtest du mir diese Woche sagen?",
    "Wobei fühlst du dich mit mir am meisten du selbst?",
    "Was hilft dir, wenn du dich zurückziehst?",
    "Welche Erinnerung an uns möchtest du öfter haben?",
    "Was schätzt du an uns, das nicht offensichtlich ist?",
    "Wann hast du zuletzt Neugier auf mich gespürt?",
    "Was brauchst du nach einem langen Tag?",
)


def question_for(day) -> str:
    return QUESTIONS[day.toordinal() % len(QUESTIONS)]


class DailyAnswer(TimestampedModel):
    clubroom = models.ForeignKey(Clubroom, on_delete=models.CASCADE, related_name="daily_answers")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="daily_answers"
    )
    date = models.DateField(default=timezone.localdate)
    answer = EncryptedTextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["clubroom", "user", "date"], name="unique_daily_answer")
        ]

    def __str__(self) -> str:
        return f"{self.user} – {self.date}"
