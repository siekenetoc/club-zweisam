from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.models import User
from apps.clubroom.models import Clubroom
from apps.clubroom.permissions import INVITABLE_ROLE_CHOICES, ROLE_LABELS

INPUT_CLASSES = (
    "w-full rounded-md border border-stone-700 bg-stone-900 px-3 py-2 "
    "text-stone-100 placeholder-stone-500 focus:border-amber-500 focus:outline-none"
)
CHECKBOX_CLASSES = (
    "mt-1 h-4 w-4 rounded border-stone-600 bg-stone-900 text-amber-500 " "focus:ring-amber-500"
)


class StyledFormMixin:
    def _style_fields(self):
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", CHECKBOX_CLASSES)
            else:
                widget.attrs.setdefault("class", INPUT_CLASSES)


class RegistrationForm(StyledFormMixin, UserCreationForm):
    email = forms.EmailField(label="E-Mail-Adresse")
    age_confirmed = forms.BooleanField(
        label="Ich bin mindestens 18 Jahre alt.",
    )
    tos_accepted = forms.BooleanField(
        label="Ich akzeptiere AGB und Datenschutzhinweise.",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Diese E-Mail-Adresse ist bereits registriert.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.age_verified = True
        user.tos_accepted_at = timezone.now()
        if commit:
            user.save()
        return user


class LoginForm(StyledFormMixin, AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()


class ClubroomForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Clubroom
        fields = ("name", "rules", "safe_word")
        labels = {
            "name": "Name des Clubraums",
            "rules": "Hausregeln (optional)",
            "safe_word": "Safeword",
        }
        widgets = {
            "rules": forms.Textarea(attrs={"rows": 4}),
            "safe_word": forms.PasswordInput(render_value=False),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()

    def clean_safe_word(self):
        safe_word = self.cleaned_data["safe_word"].strip()
        if len(safe_word) < 3:
            raise ValidationError("Das Safeword braucht mindestens drei Zeichen.")
        return safe_word


class InvitationForm(StyledFormMixin, forms.Form):
    email = forms.EmailField(label="E-Mail-Adresse")
    role = forms.ChoiceField(
        label="Rolle",
        choices=[(value, ROLE_LABELS[value]) for value, _ in INVITABLE_ROLE_CHOICES],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()


class ClubroomSettingsForm(StyledFormMixin, forms.ModelForm):
    safe_word = forms.CharField(
        label="Neues Safeword (leer lassen = unverändert)",
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Mindestens drei Zeichen, falls du es änderst.",
    )

    class Meta:
        model = Clubroom
        fields = ("name", "rules")
        labels = {"name": "Name des Clubraums", "rules": "Hausregeln"}
        widgets = {"rules": forms.Textarea(attrs={"rows": 5})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()

    def clean_safe_word(self):
        value = (self.cleaned_data.get("safe_word") or "").strip()
        if value and len(value) < 3:
            raise forms.ValidationError("Das Safeword braucht mindestens drei Zeichen.")
        return value

    def save(self, commit=True):
        clubroom = super().save(commit=False)
        safe_word = self.cleaned_data.get("safe_word")
        if safe_word:
            clubroom.safe_word = safe_word
        if commit:
            clubroom.save()
        return clubroom
