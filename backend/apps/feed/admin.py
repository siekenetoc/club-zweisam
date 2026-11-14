import json

from django import forms
from django.contrib import admin

from apps.core.permissions import is_platform_admin
from apps.feed.models import NotificationChannel, NotificationSubscription


class NotificationChannelAdminForm(forms.ModelForm):
    config = forms.CharField(
        label="Konfiguration (JSON)",
        required=False,
        widget=forms.Textarea(attrs={"rows": 10, "cols": 80}),
        help_text=(
            "Secrets und Ziel-IDs werden verschlüsselt gespeichert. "
            "Beispiele: WhatsApp {access_token, phone_number_id, template_name, "
            "template_language, default_target, api_version}; Telegram {bot_token, "
            "default_target}; Signal {api_url, sender_number, default_target, "
            "authorization, insecure_tls}; Element {homeserver_url, access_token, "
            "default_target, insecure_tls}; Gotify {server_url, app_token, "
            "insecure_tls}."
        ),
    )

    class Meta:
        model = NotificationChannel
        fields = ("clubroom", "provider", "label", "config", "is_enabled")

    def clean_config(self):
        raw = self.cleaned_data.get("config") or "{}"
        try:
            value = json.loads(raw)
        except ValueError as exc:
            raise forms.ValidationError("Ungültiges JSON.") from exc
        if not isinstance(value, dict):
            raise forms.ValidationError("Konfiguration muss ein JSON-Objekt sein.")
        return json.dumps(value, ensure_ascii=False)


class PlatformAdminMixin:
    def has_module_permission(self, request):
        return is_platform_admin(request.user)

    def has_view_permission(self, request, obj=None):
        return is_platform_admin(request.user)

    def has_add_permission(self, request):
        return is_platform_admin(request.user)

    def has_change_permission(self, request, obj=None):
        return is_platform_admin(request.user)

    def has_delete_permission(self, request, obj=None):
        return is_platform_admin(request.user)


@admin.register(NotificationChannel)
class NotificationChannelAdmin(PlatformAdminMixin, admin.ModelAdmin):
    form = NotificationChannelAdminForm
    list_display = ("label", "provider", "clubroom", "is_enabled", "updated_at")
    list_filter = ("provider", "is_enabled")
    search_fields = ("label", "clubroom__name")
    exclude = ("created_by",)

    def save_model(self, request, obj, form, change):
        obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(NotificationSubscription)
class NotificationSubscriptionAdmin(PlatformAdminMixin, admin.ModelAdmin):
    list_display = ("user", "channel", "is_enabled", "updated_at")
    list_filter = ("is_enabled", "channel__provider")
    search_fields = ("user__username", "user__email", "channel__label")
    fields = ("channel", "user", "destination", "is_enabled")
