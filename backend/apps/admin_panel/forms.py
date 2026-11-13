from django import forms

from apps.admin_panel.models import ALLOWED_TARGET_TYPES


class BreakGlassRequestForm(forms.Form):
    target_type = forms.ChoiceField(label="Zielklasse", choices=ALLOWED_TARGET_TYPES)
    target_id = forms.CharField(label="Ziel-ID", max_length=64)
    reason = forms.CharField(
        label="Begründung (Pflicht)",
        widget=forms.Textarea(attrs={"rows": 4}),
    )
