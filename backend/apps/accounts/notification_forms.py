from django import forms
from django.core.exceptions import ValidationError

from apps.clubroom.forms import StyledFormMixin
from apps.feed.models import PersonalNotificationChannel


class PersonalChannelForm(StyledFormMixin, forms.Form):
    channel_id = forms.IntegerField(required=False, widget=forms.HiddenInput)
    provider = forms.ChoiceField(
        label="Messenger",
        choices=(
            ("telegram", "Telegram Bot"),
            ("whatsapp", "WhatsApp Cloud API"),
        ),
    )
    label = forms.CharField(label="Bezeichnung", max_length=80)
    default_target = forms.CharField(label="Ziel (Telefonnummer oder Chat-ID)", max_length=255)
    is_enabled = forms.BooleanField(label="Kanal aktiv", required=False)

    telegram_bot_token = forms.CharField(
        label="Telegram Bot-Token",
        required=False,
        widget=forms.PasswordInput(render_value=True),
    )
    whatsapp_access_token = forms.CharField(
        label="WhatsApp Access Token",
        required=False,
        widget=forms.PasswordInput(render_value=True),
    )
    whatsapp_phone_number_id = forms.CharField(label="WhatsApp Phone Number ID", required=False)
    whatsapp_template_name = forms.CharField(
        label="WhatsApp Template-Name (optional)", required=False
    )
    whatsapp_template_language = forms.CharField(
        label="Template-Sprache", required=False, initial="de"
    )
    whatsapp_api_version = forms.CharField(
        label="Graph-API-Version", required=False, initial="v23.0"
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self._style_fields()

    def clean_label(self):
        label = self.cleaned_data["label"].strip()
        existing = PersonalNotificationChannel.objects.filter(user=self.user, label=label)
        if self.cleaned_data.get("channel_id"):
            existing = existing.exclude(pk=self.cleaned_data["channel_id"])
        if existing.exists():
            raise ValidationError("Diese Bezeichnung ist bereits vergeben.")
        return label

    def clean(self):
        cleaned = super().clean()
        provider = cleaned.get("provider")
        if not cleaned.get("default_target", "").strip():
            self.add_error("default_target", "Ein Ziel ist erforderlich.")
        if provider == "telegram":
            if not cleaned.get("telegram_bot_token"):
                self.add_error("telegram_bot_token", "Bot-Token ist erforderlich.")
            cleaned["config"] = {
                "bot_token": cleaned.get("telegram_bot_token", ""),
                "default_target": cleaned.get("default_target", "").strip(),
            }
        elif provider == "whatsapp":
            for field in ("whatsapp_access_token", "whatsapp_phone_number_id"):
                if not cleaned.get(field):
                    self.add_error(field, "Pflichtfeld für WhatsApp.")
            cleaned["config"] = {
                "access_token": cleaned.get("whatsapp_access_token", ""),
                "phone_number_id": cleaned.get("whatsapp_phone_number_id", ""),
                "template_name": cleaned.get("whatsapp_template_name", ""),
                "template_language": cleaned.get("whatsapp_template_language") or "de",
                "api_version": cleaned.get("whatsapp_api_version") or "v23.0",
                "default_target": cleaned.get("default_target", "").strip(),
            }
        return cleaned


def initial_from_personal_channel(channel):
    config = channel.get_config()
    initial = {
        "channel_id": channel.pk,
        "provider": channel.provider,
        "label": channel.label,
        "default_target": config.get("default_target", ""),
        "is_enabled": channel.is_enabled,
    }
    if channel.provider == "telegram":
        initial["telegram_bot_token"] = config.get("bot_token", "")
    elif channel.provider == "whatsapp":
        initial.update(
            {
                "whatsapp_access_token": config.get("access_token", ""),
                "whatsapp_phone_number_id": config.get("phone_number_id", ""),
                "whatsapp_template_name": config.get("template_name", ""),
                "whatsapp_template_language": config.get("template_language", "de"),
                "whatsapp_api_version": config.get("api_version", "v23.0"),
            }
        )
    return initial


class ProfileEditForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        from apps.accounts.models import User

        model = User
        fields = ("username", "first_name", "last_name")
        labels = {
            "username": "Benutzername",
            "first_name": "Vorname",
            "last_name": "Nachname",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()
