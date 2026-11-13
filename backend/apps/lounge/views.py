from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.clubroom.models import Membership
from apps.lounge.forms import CheckInForm
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
    return render(
        request,
        "lounge/index.html",
        {
            "clubroom": clubroom,
            "membership": membership,
            "form": CheckInForm() if can_write and today_check_in is None else None,
            "today_check_in": today_check_in,
            "can_write": can_write,
            "barometer": barometer(clubroom),
            "review_opt_in": review_opt_in,
            "review": review,
            "notifications": recent_notifications(request.user),
            "queued_count": queued_count(request.user),
            "safe_mode_active": request.user.is_safe_mode_active,
            "has_feed": membership.has_module_access("feed"),
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
