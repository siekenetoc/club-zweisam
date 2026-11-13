from django import forms

from apps.clubroom.forms import StyledFormMixin
from apps.roulette.models import ANSWER_CHOICES


class AnswerForm(StyledFormMixin, forms.Form):
    answer = forms.ChoiceField(
        label="Deine Antwort",
        choices=ANSWER_CHOICES,
        widget=forms.RadioSelect,
    )
    is_boundary = forms.BooleanField(
        label="Das ist meine Grenze – Inhalt nicht teilen",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()
        self.fields["answer"].widget.attrs.pop("class", None)
