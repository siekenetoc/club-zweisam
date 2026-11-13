from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.clubroom.models import Membership
from apps.clubroom.permissions import OWNER
from apps.playbook.models import CATEGORY_CHOICES, Challenge, ChallengeRun
from apps.playbook.services import (
    abort_run,
    active_run_for,
    both_owners_opted_in_stage3,
    confirm_run,
    daily_run_count,
    opt_in_stage3,
    revoke_opt_in_stage3,
    stage3_opted_in_user_ids,
    start_challenge,
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
    if membership is None or not membership.has_module_access("playbook"):
        raise PermissionDenied("Kein Zugriff auf das Playbook.")
    return membership


def index(request):
    membership = _membership_or_denied(request)
    clubroom = membership.clubroom
    active_run = active_run_for(clubroom)
    challenges = Challenge.objects.all()
    categories = []
    for code, label in CATEGORY_CHOICES:
        items = [challenge for challenge in challenges if challenge.category == code]
        if items:
            categories.append({"code": code, "label": label, "challenges": items})
    opted_ids = stage3_opted_in_user_ids(clubroom)
    from django.conf import settings

    limit = getattr(settings, "PLAYBOOK_DAILY_LIMIT", 3)
    return render(
        request,
        "playbook/index.html",
        {
            "clubroom": clubroom,
            "active_run": active_run,
            "categories": categories,
            "is_owner": membership.role == OWNER,
            "both_opted_in": both_owners_opted_in_stage3(clubroom),
            "own_opted_in": request.user.id in opted_ids,
            "daily_count": daily_run_count(clubroom),
            "daily_limit": limit,
        },
    )


@login_required
@require_POST
def start(request, challenge_id):
    membership = _membership_or_denied(request)
    challenge = get_object_or_404(Challenge, pk=challenge_id)
    try:
        run = start_challenge(clubroom=membership.clubroom, challenge=challenge, user=request.user)
    except ValidationError as exc:
        for message in exc.messages:
            messages.error(request, message)
        return redirect("playbook:index")
    return redirect("playbook:run", pk=run.pk)


def run_detail(request, pk):
    membership = _membership_or_denied(request)
    run = get_object_or_404(
        ChallengeRun.objects.select_related(
            "challenge", "clubroom", "started_by", "user_a", "user_b", "aborted_by"
        ),
        pk=pk,
        clubroom=membership.clubroom,
    )
    is_owner = membership.role == OWNER
    is_participant = request.user.id in {run.user_a_id, run.user_b_id}
    return render(
        request,
        "playbook/run.html",
        {
            "clubroom": membership.clubroom,
            "run": run,
            "is_owner": is_owner,
            "can_confirm": bool(
                is_owner
                and is_participant
                and run.is_active
                and not run.has_confirmed(request.user)
            ),
            "can_abort": bool(is_owner and is_participant and run.is_active),
            "confirmed": run.has_confirmed(request.user),
        },
    )


@login_required
@require_POST
def confirm(request, pk):
    membership = _membership_or_denied(request)
    run = get_object_or_404(ChallengeRun, pk=pk, clubroom=membership.clubroom)
    try:
        result = confirm_run(run=run, user=request.user)
    except ValidationError as exc:
        for message in exc.messages:
            messages.error(request, message)
    else:
        if result.is_completed:
            messages.success(request, "Challenge gemeinsam abgeschlossen.")
        else:
            messages.success(request, "Bestätigung gespeichert. Warte auf dein Gegenüber.")
    return redirect("playbook:run", pk=run.pk)


@login_required
@require_POST
def abort(request, pk):
    membership = _membership_or_denied(request)
    run = get_object_or_404(ChallengeRun, pk=pk, clubroom=membership.clubroom)
    try:
        abort_run(run=run, user=request.user)
    except ValidationError as exc:
        for message in exc.messages:
            messages.error(request, message)
    else:
        messages.success(request, "Challenge abgebrochen. Kein Punktverlust, kein Vorwurf.")
    return redirect("playbook:run", pk=run.pk)


@login_required
@require_POST
def opt_in(request):
    membership = _membership_or_denied(request)
    try:
        opt_in_stage3(clubroom=membership.clubroom, user=request.user)
    except ValidationError as exc:
        for message in exc.messages:
            messages.error(request, message)
    else:
        messages.success(request, "Opt-in für Stufe 3 gespeichert.")
    return redirect("playbook:index")


@login_required
@require_POST
def opt_out(request):
    membership = _membership_or_denied(request)
    try:
        revoke_opt_in_stage3(clubroom=membership.clubroom, user=request.user)
    except ValidationError as exc:
        for message in exc.messages:
            messages.error(request, message)
    else:
        messages.success(request, "Opt-in für Stufe 3 widerrufen.")
    return redirect("playbook:index")
