from django import forms

from apps.clubroom.forms import StyledFormMixin


class DailyAnswerForm(StyledFormMixin, forms.Form):
    answer = forms.CharField(
        label="Deine Antwort",
        max_length=2000,
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": "Deine Antwort bleibt verborgen, bis beide geantwortet haben.",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()
