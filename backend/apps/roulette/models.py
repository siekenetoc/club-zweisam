from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.clubroom.models import Clubroom
from apps.core.crypto import EncryptedTextField
from apps.core.models import TimestampedModel

YES = "ja"
MAYBE = "vielleicht"
NO = "nein"

ANSWER_CHOICES = (
    (YES, "Ja"),
    (MAYBE, "Vielleicht"),
    (NO, "Nein"),
)

ANSWER_LABELS = dict(ANSWER_CHOICES)

RESULT_FULL = "full"
RESULT_PARTIAL = "partial"
RESULT_NONE = "none"

RESULT_CHOICES = (
    (RESULT_FULL, "Vollständiger Match"),
    (RESULT_PARTIAL, "Teilweiser Match"),
    (RESULT_NONE, "Kein Match"),
)

RESULT_LABELS = dict(RESULT_CHOICES)

DEFAULT_MATCH_RULE = {
    "full": [[YES, YES]],
    "partial": [
        [YES, MAYBE],
        [MAYBE, YES],
        [MAYBE, MAYBE],
    ],
}


class Deck(TimestampedModel):
    code = models.CharField(max_length=1, unique=True)
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    intensity = models.PositiveSmallIntegerField(default=1)
    requires_opt_in = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Deck"
        verbose_name_plural = "Decks"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"Deck {self.code} – {self.title}"


class Question(TimestampedModel):
    deck = models.ForeignKey(Deck, on_delete=models.CASCADE, related_name="questions")
    order = models.PositiveSmallIntegerField()
    text = models.TextField()
    answer_type = models.CharField(
        max_length=16,
        choices=(("choice", "Vorgegebene Antworten"),),
        default="choice",
    )
    match_rule = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Frage"
        verbose_name_plural = "Fragen"
        ordering = ["deck__code", "order"]
        constraints = [
            models.UniqueConstraint(fields=["deck", "order"], name="unique_question_order_per_deck")
        ]

    def __str__(self) -> str:
        return f"{self.deck.code}{self.order}: {self.text[:60]}"

    @property
    def answer_choices(self):
        return ANSWER_CHOICES

    def rule(self) -> dict:
        return self.match_rule or DEFAULT_MATCH_RULE


class Round(TimestampedModel):
    clubroom = models.ForeignKey(Clubroom, on_delete=models.CASCADE, related_name="roulette_rounds")
    deck = models.ForeignKey(Deck, on_delete=models.PROTECT, related_name="rounds")
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="started_roulette_rounds",
    )
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Runde"
        verbose_name_plural = "Runden"
        ordering = ["-started_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["clubroom"],
                condition=models.Q(ended_at__isnull=True),
                name="unique_active_roulette_round_per_clubroom",
            )
        ]

    def __str__(self) -> str:
        return f"{self.clubroom} – {self.deck}"

    @property
    def is_active(self) -> bool:
        return self.ended_at is None

    def participant_answers(self, question):
        return {answer.user_id: answer for answer in self.answers.filter(question=question)}


class SecretAnswer(models.Model):
    round = models.ForeignKey(Round, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="secret_answers")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="roulette_answers",
    )
    answer = EncryptedTextField(blank=True)
    is_boundary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Geheimantwort"
        verbose_name_plural = "Geheimantworten"
        constraints = [
            models.UniqueConstraint(
                fields=["round", "question", "user"],
                name="unique_answer_per_round_question_user",
            )
        ]

    def __str__(self) -> str:
        return f"Antwort {self.pk}"

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class Match(TimestampedModel):
    round = models.ForeignKey(Round, on_delete=models.CASCADE, related_name="matches")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="matches")
    user_a = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="matches_as_a",
    )
    user_b = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="matches_as_b",
    )
    result = models.CharField(max_length=16, choices=RESULT_CHOICES)
    boundary_a = models.BooleanField(default=False)
    boundary_b = models.BooleanField(default=False)
    released_by_a = models.BooleanField(default=False)
    released_by_b = models.BooleanField(default=False)
    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Match"
        verbose_name_plural = "Matches"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["round", "question"], name="unique_match_per_round_question"
            )
        ]

    def __str__(self) -> str:
        return f"Match {self.result} ({self.round_id}/{self.question_id})"

    @property
    def is_released(self) -> bool:
        return self.released_at is not None

    @property
    def has_boundary(self) -> bool:
        return self.boundary_a or self.boundary_b

    def release_flag_for(self, user):
        if user.id == self.user_a_id:
            return "a"
        if user.id == self.user_b_id:
            return "b"
        return None

    def released_by(self, user) -> bool:
        flag = self.release_flag_for(user)
        if flag == "a":
            return self.released_by_a
        if flag == "b":
            return self.released_by_b
        return False


class DeckOptIn(TimestampedModel):
    clubroom = models.ForeignKey(Clubroom, on_delete=models.CASCADE, related_name="deck_opt_ins")
    deck = models.ForeignKey(Deck, on_delete=models.CASCADE, related_name="opt_ins")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="deck_opt_ins",
    )

    class Meta:
        verbose_name = "Deck-Opt-in"
        verbose_name_plural = "Deck-Opt-ins"
        constraints = [
            models.UniqueConstraint(
                fields=["clubroom", "deck", "user"],
                name="unique_deck_opt_in_per_user",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user} – {self.deck}"
