from django import forms

from apps.clubroom.forms import StyledFormMixin
from apps.wishes.models import (
    ACTION_CHOICES,
    INTENSITY_CHOICES,
    TIMEFRAME_CHOICES,
    TYPE_CHOICES,
)


class WishForm(StyledFormMixin, forms.Form):
    type = forms.ChoiceField(label="Art des Wunsches", choices=TYPE_CHOICES)
    category = forms.CharField(label="Kategorie (optional)", max_length=80, required=False)
    intensity = forms.ChoiceField(label="Intensität", choices=INTENSITY_CHOICES)
    timeframe = forms.ChoiceField(label="Zeitrahmen", choices=TIMEFRAME_CHOICES)
    title = forms.CharField(label="Titel", max_length=160)
    body = forms.CharField(
        label="Wunsch",
        widget=forms.Textarea(attrs={"rows": 6}),
    )
    is_private = forms.BooleanField(
        label="Privat halten – nur ich sehe diesen Wunsch",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()


class WishResponseForm(StyledFormMixin, forms.Form):
    action = forms.ChoiceField(label="Antwort", choices=ACTION_CHOICES)
    note = forms.CharField(
        label="Notiz (bei Alternative, Teilannahme oder Gespräch nötig)",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()
