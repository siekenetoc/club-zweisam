from django import forms

from apps.calendar.models import DateNight
from apps.clubroom.forms import StyledFormMixin


class DateNightForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = DateNight
        fields = ("scheduled_for", "motto", "note")
        labels = {
            "scheduled_for": "Wann?",
            "motto": "Motto",
            "note": "Was schwebt euch vor?",
        }
        widgets = {
            "scheduled_for": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "note": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()
