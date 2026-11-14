from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.gdpr import delete_user_data, export_user_data
from apps.accounts.notification_forms import (
    PersonalChannelForm,
    initial_from_personal_channel,
)
from apps.clubroom.models import Membership
from apps.feed.delivery import send_via_channel
from apps.feed.models import PersonalNotificationChannel


@login_required
def profile(request):
    membership = (
        Membership.objects.filter(user=request.user, revoked_at__isnull=True)
        .select_related("clubroom")
        .first()
    )
    channels = PersonalNotificationChannel.objects.filter(user=request.user)
    channel = None
    channel_id = request.POST.get("channel_id") or request.GET.get("channel")
    if channel_id:
        channel = get_object_or_404(PersonalNotificationChannel, pk=channel_id, user=request.user)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "delete" and channel is not None:
            channel.delete()
            messages.success(request, "Persönlicher Push-Kanal gelöscht.")
            return redirect("accounts:profile")
        if action == "test" and channel is not None:
            config = channel.get_config()
            if send_via_channel(channel, config.get("default_target", "")):
                messages.success(request, "Testnachricht gesendet.")
            else:
                messages.error(request, "Testnachricht fehlgeschlagen. Logs prüfen.")
            return redirect("accounts:profile")

        form = PersonalChannelForm(request.POST, user=request.user)
        if form.is_valid():
            if channel is None:
                if channels.count() >= 5:
                    messages.error(request, "Maximal fünf persönliche Kanäle.")
                    return redirect("accounts:profile")
                channel = PersonalNotificationChannel(user=request.user)
            channel.provider = form.cleaned_data["provider"]
            channel.label = form.cleaned_data["label"]
            channel.is_enabled = form.cleaned_data["is_enabled"]
            channel.set_config(form.cleaned_data["config"])
            channel.save()
            messages.success(request, "Persönlicher Push-Kanal gespeichert.")
            return redirect("accounts:profile")
    else:
        form = PersonalChannelForm(
            initial=initial_from_personal_channel(channel) if channel else None,
            user=request.user,
        )

    return render(
        request,
        "accounts/profile.html",
        {
            "membership": membership,
            "channels": channels,
            "form": form,
            "editing": channel,
        },
    )


@login_required
def data_export(request):
    payload = export_user_data(request.user)
    response = JsonResponse(
        payload,
        encoder=DjangoJSONEncoder,
        json_dumps_params={"ensure_ascii": False, "indent": 2},
    )
    response["Content-Disposition"] = 'attachment; filename="club-zweisam-export.json"'
    return response


@login_required
def delete_account(request):
    if request.method == "POST":
        password = request.POST.get("password", "")
        if not request.user.check_password(password):
            messages.error(request, "Passwort ist nicht korrekt.")
            return redirect("accounts:delete")
        if request.POST.get("confirm") != "1":
            messages.error(request, "Löschung muss bestätigt werden.")
            return redirect("accounts:delete")
        user = request.user
        logout(request)
        delete_user_data(user)
        messages.success(
            request,
            "Konto anonymisiert und personenbezogene Inhalte gelöscht. "
            "Audit-Einträge bleiben aus Sicherheitsgründen pseudonym erhalten.",
        )
        return redirect("clubroom:home")
    return render(request, "accounts/delete.html")
