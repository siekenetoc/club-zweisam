from django import forms

from apps.clubroom.forms import StyledFormMixin


class MessageForm(StyledFormMixin, forms.Form):
    body = forms.CharField(
        label="Nachricht",
        max_length=4000,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Etwas für euch …"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()
