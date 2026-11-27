from django import forms

from apps.calendar.models import CalendarEntry
from apps.clubroom.forms import StyledFormMixin


class CalendarEntryForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = CalendarEntry
        fields = (
            "kind",
            "title",
            "description",
            "start_at",
            "end_at",
            "all_day",
        )
        labels = {
            "kind": "Art",
            "title": "Titel",
            "description": "Beschreibung (optional)",
            "start_at": "Beginn",
            "end_at": "Ende (optional)",
            "all_day": "Ganztägig",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "start_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "end_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_at")
        end = cleaned.get("end_at")
        if start and end and end < start:
            self.add_error("end_at", "Das Ende muss nach dem Beginn liegen.")
        return cleaned
