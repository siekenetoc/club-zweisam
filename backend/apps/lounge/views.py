from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.clubroom.models import Membership
from apps.feed.models import (
    PROVIDER_GOTIFY,
    NotificationChannel,
    NotificationSubscription,
)
from apps.lounge.forms import CheckInForm
from apps.lounge.models import CheckIn
from apps.lounge.services import (
    barometer,
    check_in_today,
    create_check_in,
    has_weekly_review,
    queued_count,
    recent_notifications,
    set_safe_mode,
    toggle_weekly_review,
    weekly_review,
)


def _membership_or_denied(request) -> Membership:
    membership = (
        Membership.objects.filter(
            user=request.user,
            revoked_at__isnull=True,
            clubroom__deleted_at__isnull=True,
        )
        .select_related("clubroom")
        .first()
    )
    if membership is None or not membership.has_module_access("lounge"):
        raise PermissionDenied("Kein Zugriff auf die Lounge.")
    return membership


def index(request):
    membership = _membership_or_denied(request)
    clubroom = membership.clubroom
    today_check_in = check_in_today(clubroom, request.user)
    can_write = membership.can_write_module("lounge")
    review_opt_in = has_weekly_review(clubroom, request.user)
    review = weekly_review(clubroom, request.user) if review_opt_in else None
    mood_data = barometer(clubroom)
    course = mood_data["overall"].get("mood")
    if course is None:
        course_label = "Noch keine Daten"
        course_class = "text-stone-400"
    elif course < 2:
        course_label = "belastet"
        course_class = "text-rose-300"
    elif course < 3:
        course_label = "gemischt"
        course_class = "text-amber-300"
    elif course < 4:
        course_label = "stabil"
        course_class = "text-emerald-300"
    else:
        course_label = "gut"
        course_class = "text-emerald-300"
    channels = list(NotificationChannel.objects.filter(clubroom=clubroom, is_enabled=True))
    subscriptions = {
        subscription.channel_id: subscription
        for subscription in NotificationSubscription.objects.filter(
            user=request.user, channel__in=channels
        )
    }
    channel_entries = [
        {
            "channel": channel,
            "subscription": subscriptions.get(channel.pk),
            "destination": (
                subscriptions[channel.pk].destination if channel.pk in subscriptions else ""
            ),
        }
        for channel in channels
    ]
    return render(
        request,
        "lounge/index.html",
        {
            "clubroom": clubroom,
            "membership": membership,
            "form": CheckInForm() if can_write and today_check_in is None else None,
            "today_check_in": today_check_in,
            "can_write": can_write,
            "barometer": mood_data,
            "course_label": course_label,
            "course_class": course_class,
            "review_opt_in": review_opt_in,
            "review": review,
            "notifications": recent_notifications(request.user),
            "queued_count": queued_count(request.user),
            "safe_mode_active": request.user.is_safe_mode_active,
            "has_feed": membership.has_module_access("feed"),
            "notification_channels": channel_entries,
        },
    )


def mood_dashboard(request):
    membership = (
        Membership.objects.filter(
            user=request.user,
            revoked_at__isnull=True,
            clubroom__deleted_at__isnull=True,
        )
        .select_related("clubroom")
        .first()
    )
    if membership is None or not membership.has_module_access("lounge"):
        raise Http404
    clubroom = membership.clubroom
    days = 30
    try:
        days = int(request.GET.get("tage", "30"))
    except ValueError:
        pass
    if days not in {7, 30, 90}:
        days = 30
    start = timezone.localdate() - timedelta(days=days - 1)
    check_ins = list(
        CheckIn.objects.filter(clubroom=clubroom, date__gte=start)
        .select_related("user")
        .order_by("date", "user_id")
    )
    dates = [start + timedelta(days=index) for index in range(days)]
    by_user = {}
    for check_in in check_ins:
        by_user.setdefault(check_in.user.username, {})[check_in.date] = check_in.mood
    width, height, left, top = 760, 260, 40, 20
    chart_width = width - left * 2
    chart_height = height - top * 2

    def points(values):
        rendered = []
        for index, day in enumerate(dates):
            value = values.get(day)
            if value is None:
                continue
            x = left + (index / max(1, days - 1)) * chart_width
            y = top + chart_height - ((value - 1) / 4) * chart_height
            rendered.append(f"{x:.1f},{y:.1f}")
        return " ".join(rendered)

    palette = ["#f5b942", "#8bd8bd", "#f08a7a", "#93c5fd"]
    series = [
        {
            "name": username,
            "color": palette[index % len(palette)],
            "points": points(values),
            "values": values,
        }
        for index, (username, values) in enumerate(by_user.items())
    ]
    return render(
        request,
        "lounge/mood.html",
        {
            "clubroom": clubroom,
            "days": days,
            "start": start,
            "end": timezone.localdate(),
            "series": series,
            "width": width,
            "height": height,
            "left": left,
            "top": top,
            "chart_width": chart_width,
            "chart_height": chart_height,
        },
    )


@login_required
@require_POST
def check_in(request):
    membership = _membership_or_denied(request)
    form = CheckInForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Bitte alle Werte zwischen 1 und 5 wählen.")
        return redirect("lounge:index")
    try:
        create_check_in(
            clubroom=membership.clubroom,
            user=request.user,
            mood=form.cleaned_data["mood"],
            energy=form.cleaned_data["energy"],
            closeness=form.cleaned_data["closeness"],
        )
    except ValidationError as exc:
        for message in exc.messages:
            messages.error(request, message)
    else:
        messages.success(request, "Check-in gespeichert.")
    return redirect("lounge:index")


@login_required
@require_POST
def toggle_review(request):
    membership = _membership_or_denied(request)
    try:
        enabled = toggle_weekly_review(clubroom=membership.clubroom, user=request.user)
    except ValidationError as exc:
        for message in exc.messages:
            messages.error(request, message)
    else:
        if enabled:
            messages.success(request, "Wochenrückblick aktiviert.")
        else:
            messages.success(request, "Wochenrückblick deaktiviert.")
    return redirect("lounge:index")


@login_required
@require_POST
def notification_subscription(request):
    membership = _membership_or_denied(request)
    channel = NotificationChannel.objects.filter(
        pk=request.POST.get("channel_id"),
        clubroom=membership.clubroom,
        is_enabled=True,
    ).first()
    if channel is None:
        messages.error(request, "Dieser Kanal ist nicht verfügbar.")
        return redirect("lounge:index")

    action = request.POST.get("action")
    destination = request.POST.get("destination", "").strip()
    if len(destination) > 255:
        messages.error(request, "Ziel ist zu lang.")
        return redirect("lounge:index")

    subscription, _ = NotificationSubscription.objects.get_or_create(
        channel=channel, user=request.user
    )
    if action == "disable":
        subscription.is_enabled = False
        subscription.save(update_fields=["is_enabled", "updated_at"])
        messages.success(request, "Push-Benachrichtigung deaktiviert.")
        return redirect("lounge:index")

    config = channel.get_config()
    if not destination and not config.get("default_target") and channel.provider != PROVIDER_GOTIFY:
        messages.error(
            request,
            "Für diesen Kanal wird ein Ziel benötigt (Telefonnummer, Chat-ID oder Raum-ID).",
        )
        return redirect("lounge:index")

    if destination:
        subscription.destination = destination
    subscription.is_enabled = True
    subscription.save(update_fields=["destination", "is_enabled", "updated_at"])
    messages.success(request, "Push-Benachrichtigung aktiviert. Nur ein Link, kein Inhalt.")
    return redirect("lounge:index")


@login_required
@require_POST
def safe_mode_sync(request):
    _membership_or_denied(request)
    active = request.POST.get("active") == "1"
    delivered = set_safe_mode(user=request.user, active=active)
    return JsonResponse(
        {
            "active": request.user.is_safe_mode_active,
            "delivered": delivered,
        }
    )


@login_required
@require_POST
def safe_mode(request):
    _membership_or_denied(request)
    active = request.POST.get("active") == "1"
    delivered = set_safe_mode(user=request.user, active=active)
    if active:
        messages.success(request, "Safe Mode aktiviert. Benachrichtigungen werden gepuffert.")
    else:
        messages.success(
            request,
            f"Safe Mode deaktiviert. {delivered} gepufferte Benachrichtigungen "
            "wurden ohne Inhalt zugestellt.",
        )
    return redirect("lounge:index")
