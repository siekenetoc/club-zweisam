from django import forms

from apps.clubroom.forms import StyledFormMixin
from apps.insights.models import Insight


class InsightForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Insight
        fields = ("title", "body")
        widgets = {"body": forms.Textarea(attrs={"rows": 6})}
        labels = {"title": "Titel", "body": "Gedanke"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()
