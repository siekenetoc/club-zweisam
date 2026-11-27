from django import forms

from apps.admin_panel.models import ALLOWED_TARGET_TYPES
from apps.pages.admin import TinyMCETextarea
from apps.pages.models import LandingSection, LandingSettings, NavigationItem, StaticPage


class BreakGlassRequestForm(forms.Form):
    target_type = forms.ChoiceField(label="Zielklasse", choices=ALLOWED_TARGET_TYPES)
    target_id = forms.CharField(label="Ziel-ID", max_length=64)
    reason = forms.CharField(
        label="Begründung (Pflicht)",
        widget=forms.Textarea(attrs={"rows": 4}),
    )


class MessengerSetupForm(forms.Form):
    channel_id = forms.IntegerField(required=False, widget=forms.HiddenInput)
    clubroom = forms.ModelChoiceField(
        queryset=None,
        label="Clubraum",
    )
    provider = forms.ChoiceField(label="Messenger", choices=[])
    label = forms.CharField(label="Bezeichnung", max_length=80)
    default_target = forms.CharField(
        label="Standardziel (Telefonnummer, Chat-ID, Raum-ID; optional)",
        max_length=255,
        required=False,
    )
    is_enabled = forms.BooleanField(label="Kanal aktiv", required=False)

    whatsapp_access_token = forms.CharField(label="WhatsApp Access Token", required=False)
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

    telegram_bot_token = forms.CharField(label="Telegram Bot-Token", required=False)

    signal_api_url = forms.CharField(
        label="signal-cli API-URL", required=False, initial="http://signal-cli:8080"
    )
    signal_sender_number = forms.CharField(label="Signal-Absendernummer", required=False)
    signal_authorization = forms.CharField(
        label="Signal Authorization-Header (optional)", required=False
    )

    element_homeserver_url = forms.CharField(label="Matrix Homeserver-URL", required=False)
    element_access_token = forms.CharField(label="Matrix Access Token", required=False)

    gotify_server_url = forms.CharField(label="Gotify Server-URL", required=False)
    gotify_app_token = forms.CharField(label="Gotify App-Token", required=False)

    insecure_tls = forms.BooleanField(
        label="Selbstsigniertes TLS akzeptieren (nur Testsysteme)",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.clubroom.models import Clubroom
        from apps.feed.models import PROVIDER_CHOICES

        self.fields["clubroom"].queryset = Clubroom.objects.filter(
            deleted_at__isnull=True
        ).order_by("name")
        self.fields["provider"].choices = PROVIDER_CHOICES
        self._style_fields()

    def _style_fields(self):
        for field in self.fields.values():
            if isinstance(field.widget, forms.HiddenInput | forms.CheckboxInput):
                continue
            field.widget.attrs.setdefault(
                "class",
                "w-full rounded-md border border-stone-700 bg-stone-900 px-3 py-2 "
                "text-stone-100 focus:border-amber-500 focus:outline-none",
            )

    def clean(self):
        cleaned = super().clean()
        provider = cleaned.get("provider")
        config = {}
        target = (cleaned.get("default_target") or "").strip()
        if target:
            config["default_target"] = target

        def add(field, key=None):
            value = cleaned.get(field)
            if value:
                config[key or field] = value

        if provider == "whatsapp":
            for field in ("whatsapp_access_token", "whatsapp_phone_number_id"):
                if not cleaned.get(field):
                    self.add_error(field, "Pflichtfeld für WhatsApp.")
            config.update(
                {
                    "access_token": cleaned.get("whatsapp_access_token", ""),
                    "phone_number_id": cleaned.get("whatsapp_phone_number_id", ""),
                    "template_name": cleaned.get("whatsapp_template_name", ""),
                    "template_language": cleaned.get("whatsapp_template_language") or "de",
                    "api_version": cleaned.get("whatsapp_api_version") or "v23.0",
                }
            )
        elif provider == "telegram":
            if not cleaned.get("telegram_bot_token"):
                self.add_error("telegram_bot_token", "Pflichtfeld für Telegram.")
            config["bot_token"] = cleaned.get("telegram_bot_token", "")
        elif provider == "signal":
            for field in ("signal_api_url", "signal_sender_number"):
                if not cleaned.get(field):
                    self.add_error(field, "Pflichtfeld für Signal.")
            config.update(
                {
                    "api_url": cleaned.get("signal_api_url", ""),
                    "sender_number": cleaned.get("signal_sender_number", ""),
                }
            )
            add("signal_authorization", "authorization")
        elif provider == "element":
            for field in ("element_homeserver_url", "element_access_token"):
                if not cleaned.get(field):
                    self.add_error(field, "Pflichtfeld für Element/Matrix.")
            config.update(
                {
                    "homeserver_url": cleaned.get("element_homeserver_url", ""),
                    "access_token": cleaned.get("element_access_token", ""),
                }
            )
        elif provider == "gotify":
            for field in ("gotify_server_url", "gotify_app_token"):
                if not cleaned.get(field):
                    self.add_error(field, "Pflichtfeld für Gotify.")
            config.update(
                {
                    "server_url": cleaned.get("gotify_server_url", ""),
                    "app_token": cleaned.get("gotify_app_token", ""),
                }
            )
        if cleaned.get("insecure_tls"):
            config["insecure_tls"] = True
        cleaned["config"] = config
        return cleaned


def initial_from_channel(channel):
    config = channel.get_config()
    initial = {
        "channel_id": channel.pk,
        "clubroom": channel.clubroom_id,
        "provider": channel.provider,
        "label": channel.label,
        "default_target": config.get("default_target", ""),
        "is_enabled": channel.is_enabled,
        "insecure_tls": bool(config.get("insecure_tls")),
    }
    if channel.provider == "whatsapp":
        initial.update(
            {
                "whatsapp_access_token": config.get("access_token", ""),
                "whatsapp_phone_number_id": config.get("phone_number_id", ""),
                "whatsapp_template_name": config.get("template_name", ""),
                "whatsapp_template_language": config.get("template_language", "de"),
                "whatsapp_api_version": config.get("api_version", "v23.0"),
            }
        )
    elif channel.provider == "telegram":
        initial["telegram_bot_token"] = config.get("bot_token", "")
    elif channel.provider == "signal":
        initial.update(
            {
                "signal_api_url": config.get("api_url", ""),
                "signal_sender_number": config.get("sender_number", ""),
                "signal_authorization": config.get("authorization", ""),
            }
        )
    elif channel.provider == "element":
        initial.update(
            {
                "element_homeserver_url": config.get("homeserver_url", ""),
                "element_access_token": config.get("access_token", ""),
            }
        )
    elif channel.provider == "gotify":
        initial.update(
            {
                "gotify_server_url": config.get("server_url", ""),
                "gotify_app_token": config.get("app_token", ""),
            }
        )
    return initial


class ContentStaticPageForm(forms.ModelForm):
    class Meta:

        model = StaticPage
        fields = ("title", "slug", "content_html", "is_published")
        widgets = {"content_html": TinyMCETextarea()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.HiddenInput):
                field.widget.attrs.setdefault(
                    "class",
                    "w-full rounded-md border border-stone-700 bg-stone-900 px-3 py-2 text-stone-100",
                )


class ContentLandingSettingsForm(forms.ModelForm):
    class Meta:

        model = LandingSettings
        fields = (
            "hero_kicker",
            "hero_title",
            "hero_text",
            "primary_cta_label",
            "primary_cta_url",
            "secondary_cta_label",
            "secondary_cta_url",
        )


class ContentLandingSectionForm(forms.ModelForm):
    class Meta:

        model = LandingSection
        fields = ("title", "body_html", "link_label", "link_url", "order", "is_active")
        widgets = {
            "body_html": __import__(
                "apps.pages.admin", fromlist=["TinyMCETextarea"]
            ).TinyMCETextarea()
        }


class ContentNavigationForm(forms.ModelForm):
    class Meta:

        model = NavigationItem
        fields = ("label", "url", "location", "order", "is_active", "requires_authentication")
