from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.clubroom.models import Membership
from apps.clubroom.permissions import OWNER
from apps.points.models import (
    REWARD_CATEGORY_CHOICES,
    Redemption,
    Reward,
)
from apps.points.services import (
    accept_redemption,
    cancel_redemption,
    complete_redemption,
    confirm_refund,
    daily_cap,
    decline_redemption,
    dyad_ledgers,
    earned_today,
    get_or_create_ledger,
    grant_recognition,
    guest_ledgers,
    request_redemption,
    request_refund,
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
    if membership is None:
        raise PermissionDenied("Kein Clubraum.")
    return membership


def _owner_or_denied(request) -> Membership:
    membership = _membership_or_denied(request)
    if membership.role != OWNER or not membership.has_module_access("points"):
        raise PermissionDenied("Kein Zugriff auf Punkte.")
    return membership


def index(request):
    membership = _owner_or_denied(request)
    clubroom = membership.clubroom
    for owner_membership in clubroom.memberships.filter(
        role=OWNER, revoked_at__isnull=True
    ).select_related("user"):
        get_or_create_ledger(clubroom, owner_membership.user)
    ledgers = list(dyad_ledgers(clubroom))
    own_ledger = next((ledger for ledger in ledgers if ledger.owner_id == request.user.id), None)
    rewards = list(Reward.objects.all())
    categories = []
    for code, label in REWARD_CATEGORY_CHOICES:
        items = [reward for reward in rewards if reward.category == code]
        if items:
            categories.append({"code": code, "label": label, "rewards": items})
    guest_members = (
        clubroom.memberships.filter(revoked_at__isnull=True)
        .exclude(role=OWNER)
        .select_related("user")
    )
    return render(
        request,
        "points/index.html",
        {
            "clubroom": clubroom,
            "ledgers": ledgers,
            "own_ledger": own_ledger,
            "daily_earned": earned_today(own_ledger) if own_ledger else 0,
            "daily_cap": daily_cap(),
            "categories": categories,
            "guest_ledgers": list(guest_ledgers(clubroom)),
            "guest_members": guest_members,
            "redemptions": Redemption.objects.filter(clubroom=clubroom)
            .select_related("reward", "requested_by", "accepted_by")
            .order_by("-created_at")[:30],
        },
    )


def my_points(request):
    membership = _membership_or_denied(request)
    if membership.role == OWNER:
        return redirect("points:index")
    ledger = get_or_create_ledger(membership.clubroom, request.user)
    return render(
        request,
        "points/my.html",
        {
            "clubroom": membership.clubroom,
            "ledger": ledger,
            "entries": ledger.entries.select_related("actor")[:30],
        },
    )


@login_required
@require_POST
def redeem(request, reward_id):
    membership = _owner_or_denied(request)
    reward = get_object_or_404(Reward, pk=reward_id)
    try:
        request_redemption(clubroom=membership.clubroom, user=request.user, reward=reward)
    except ValidationError as exc:
        for message in exc.messages:
            messages.error(request, message)
    else:
        messages.success(request, "Belohnung angefragt. Die andere Person entscheidet.")
    return redirect("points:index")


@login_required
@require_POST
def redemption_action(request, pk, action):
    membership = _owner_or_denied(request)
    redemption = get_object_or_404(Redemption, pk=pk, clubroom=membership.clubroom)
    handlers = {
        "accept": accept_redemption,
        "decline": decline_redemption,
        "cancel": cancel_redemption,
        "complete": complete_redemption,
        "refund_request": request_refund,
        "refund_confirm": confirm_refund,
    }
    handler = handlers.get(action)
    if handler is None:
        raise PermissionDenied("Unbekannte Aktion.")
    try:
        handler(redemption=redemption, user=request.user)
    except ValidationError as exc:
        for message in exc.messages:
            messages.error(request, message)
    else:
        messages.success(request, "Einlösung aktualisiert.")
    return redirect("points:index")


@login_required
@require_POST
def recognize(request):
    membership = _owner_or_denied(request)
    guest = get_object_or_404(
        Membership.objects.select_related("user"),
        pk=request.POST.get("membership_id"),
        clubroom=membership.clubroom,
        revoked_at__isnull=True,
    )
    try:
        amount = int(request.POST.get("amount", "1"))
        grant_recognition(
            clubroom=membership.clubroom,
            guest_user=guest.user,
            actor=request.user,
            amount=amount,
        )
    except (TypeError, ValueError):
        messages.error(request, "Ungültiger Betrag.")
    except ValidationError as exc:
        for message in exc.messages:
            messages.error(request, message)
    else:
        messages.success(request, f"Anerkennung für {guest.user.username} gespeichert.")
    return redirect("points:index")
