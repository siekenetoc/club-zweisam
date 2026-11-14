from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.models import User
from apps.admin_panel.forms import (
    BreakGlassRequestForm,
    MessengerSetupForm,
    initial_from_channel,
)
from apps.admin_panel.models import BreakGlassRequest
from apps.admin_panel.services import (
    approve_break_glass,
    request_break_glass,
    use_break_glass,
)
from apps.clubroom.models import Clubroom, Membership
from apps.core.permissions import is_platform_admin
from apps.feed.delivery import send_via_channel
from apps.feed.models import NotificationChannel
from apps.feed.telegram import TelegramError, discover_chats
from apps.playbook.models import Challenge
from apps.roulette.models import Match
from apps.wishes.models import Wish


def _superuser_or_denied(request):
    if not request.user.is_superuser:
        raise PermissionDenied("Nur Super-Admins.")


def _platform_admin_or_denied(request):
    if not is_platform_admin(request.user):
        raise PermissionDenied("Nur Plattform-Admins.")


@staff_member_required
def dashboard(request):
    pending = BreakGlassRequest.objects.filter(approved_at__isnull=True).count()
    return render(
        request,
        "admin_panel/dashboard.html",
        {
            "user_count": User.objects.count(),
            "clubroom_count": Clubroom.objects.filter(deleted_at__isnull=True).count(),
            "active_memberships": Membership.objects.filter(revoked_at__isnull=True).count(),
            "wish_count": Wish.objects.filter(deleted_at__isnull=True).count(),
            "match_count": Match.objects.count(),
            "challenge_count": Challenge.objects.count(),
            "pending_break_glass": pending,
            "is_superuser": request.user.is_superuser,
            "is_platform_admin": is_platform_admin(request.user),
        },
    )


@staff_member_required
def messenger_setup(request):
    _platform_admin_or_denied(request)
    channel_id = request.POST.get("channel_id") or request.GET.get("channel")
    channel = None
    if channel_id:
        channel = get_object_or_404(NotificationChannel, pk=channel_id)

    if request.POST.get("action") == "telegram_discover":
        form = MessengerSetupForm(request.POST)
        token = request.POST.get("telegram_bot_token", "")
        telegram_chats = []
        try:
            telegram_chats = discover_chats(token)
        except TelegramError as exc:
            messages.error(request, f"Chat-ID-Ermittlung fehlgeschlagen: {exc}")
        if not telegram_chats:
            messages.warning(
                request,
                "Keine Chats gefunden. Bot in die Gruppe einladen, dort eine "
                "Nachricht senden oder den Bot erwähnen. Bei aktivierter "
                "Privacy-Mode in BotFather ggf. /setprivacy -> Disable und Bot "
                "neu hinzufügen.",
            )
        return render(
            request,
            "admin_panel/messenger.html",
            {
                "form": form,
                "channels": NotificationChannel.objects.select_related("clubroom").order_by(
                    "clubroom__name", "provider", "label"
                ),
                "telegram_chats": telegram_chats,
                "editing": channel,
            },
        )

    if request.POST.get("action") == "test" and channel is not None:
        config = channel.get_config()
        if send_via_channel(channel, config.get("default_target", "")):
            messages.success(request, "Testnachricht gesendet.")
        else:
            messages.error(request, "Testnachricht fehlgeschlagen. Logs prüfen.")
        return redirect("admin_panel:messenger_setup")

    if request.method == "POST":
        form = MessengerSetupForm(request.POST)
        if form.is_valid():
            if channel is None:
                channel = NotificationChannel(created_by=request.user)
            channel.clubroom = form.cleaned_data["clubroom"]
            channel.provider = form.cleaned_data["provider"]
            channel.label = form.cleaned_data["label"]
            channel.is_enabled = form.cleaned_data["is_enabled"]
            channel.set_config(form.cleaned_data["config"])
            channel.save()
            if request.POST.get("send_test") == "on":
                if send_via_channel(channel, channel.get_config().get("default_target", "")):
                    messages.success(request, "Kanal gespeichert. Testnachricht gesendet.")
                else:
                    messages.warning(
                        request,
                        "Kanal gespeichert, Testnachricht fehlgeschlagen. Logs prüfen.",
                    )
            else:
                messages.success(request, "Kanal gespeichert.")
            return redirect("admin_panel:messenger_setup")
    else:
        form = MessengerSetupForm(initial=initial_from_channel(channel) if channel else None)

    return render(
        request,
        "admin_panel/messenger.html",
        {
            "form": form,
            "channels": NotificationChannel.objects.select_related("clubroom").order_by(
                "clubroom__name", "provider", "label"
            ),
            "editing": channel,
        },
    )


@staff_member_required
def break_glass(request):
    _superuser_or_denied(request)
    if request.method == "POST":
        form = BreakGlassRequestForm(request.POST)
        if form.is_valid():
            try:
                request_break_glass(
                    user=request.user,
                    target_type=form.cleaned_data["target_type"],
                    target_id=form.cleaned_data["target_id"],
                    reason=form.cleaned_data["reason"],
                )
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(
                    request,
                    "Antrag gestellt. Eine zweite Super-Admin-Person muss bestätigen.",
                )
                return redirect("admin_panel:break_glass")
    else:
        form = BreakGlassRequestForm()

    requests = BreakGlassRequest.objects.select_related("requested_by", "approved_by")[:50]
    return render(
        request,
        "admin_panel/breakglass.html",
        {"form": form, "requests": requests},
    )


@staff_member_required
@require_POST
def break_glass_approve(request, pk):
    _superuser_or_denied(request)
    break_glass_request = get_object_or_404(BreakGlassRequest, pk=pk)
    try:
        approve_break_glass(request_obj=break_glass_request, user=request.user)
    except ValidationError as exc:
        for message in exc.messages:
            messages.error(request, message)
    else:
        messages.success(request, "Antrag bestätigt. Gültig für 24 Stunden.")
    return redirect("admin_panel:break_glass")


@staff_member_required
@require_POST
def break_glass_use(request, pk):
    _superuser_or_denied(request)
    break_glass_request = get_object_or_404(BreakGlassRequest, pk=pk)
    try:
        use_break_glass(request_obj=break_glass_request, user=request.user)
    except ValidationError as exc:
        for message in exc.messages:
            messages.error(request, message)
    else:
        messages.success(
            request,
            "Zugriff protokolliert und betroffene Nutzer benachrichtigt.",
        )
    return redirect("admin_panel:break_glass")
