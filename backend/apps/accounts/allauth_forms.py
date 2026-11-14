from allauth.account.forms import SignupForm
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.models import User


class ClubSignupForm(SignupForm):
    age_confirmed = forms.BooleanField(
        label="Ich bin mindestens 18 Jahre alt.",
    )
    tos_accepted = forms.BooleanField(
        label="Ich akzeptiere AGB und Datenschutzhinweise.",
    )

    field_order = [
        "username",
        "email",
        "password1",
        "password2",
        "age_confirmed",
        "tos_accepted",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault(
                    "class",
                    "mt-1 h-4 w-4 rounded border-stone-600 bg-stone-900 text-amber-500 focus:ring-amber-500",
                )
            else:
                field.widget.attrs.setdefault(
                    "class",
                    "w-full rounded-md border border-stone-700 bg-stone-900 px-3 py-2 "
                    "text-stone-100 placeholder-stone-500 focus:border-amber-500 focus:outline-none",
                )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Diese E-Mail-Adresse ist bereits registriert.")
        return email

    def save(self, request):
        user = super().save(request)
        user.age_verified = True
        user.tos_accepted_at = timezone.now()
        user.save(update_fields=["age_verified", "tos_accepted_at"])
        return user
