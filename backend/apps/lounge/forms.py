from django import forms

from apps.clubroom.forms import StyledFormMixin

SCALE_CHOICES = [(value, str(value)) for value in range(1, 6)]


class CheckInForm(StyledFormMixin, forms.Form):
    mood = forms.TypedChoiceField(
        label="Stimmung",
        choices=SCALE_CHOICES,
        coerce=int,
        widget=forms.RadioSelect,
    )
    energy = forms.TypedChoiceField(
        label="Energie",
        choices=SCALE_CHOICES,
        coerce=int,
        widget=forms.RadioSelect,
    )
    closeness = forms.TypedChoiceField(
        label="Nähe",
        choices=SCALE_CHOICES,
        coerce=int,
        widget=forms.RadioSelect,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()
        for field in self.fields.values():
            field.widget.attrs.pop("class", None)
