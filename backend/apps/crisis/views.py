from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.clubroom.models import Membership
from apps.crisis.services import (
    active_crisis_session,
    end_crisis_session,
    start_crisis_session,
)
from apps.deep_talk.models import MODE_CRISIS, TalkSession


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
        raise PermissionDenied("Kein Zugriff auf den Krisenmodus.")
    return membership


def index(request):
    membership = _membership_or_denied(request)
    return render(
        request,
        "crisis/index.html",
        {
            "clubroom": membership.clubroom,
            "crisis_session": active_crisis_session(membership.clubroom),
        },
    )


@login_required
@require_POST
def start(request):
    membership = _membership_or_denied(request)
    try:
        session = start_crisis_session(clubroom=membership.clubroom, user=request.user)
    except ValidationError as exc:
        for message in exc.messages:
            messages.error(request, message)
        return redirect("crisis:index")
    return redirect("crisis:session", pk=session.pk)


def session_detail(request, pk):
    membership = _membership_or_denied(request)
    session = get_object_or_404(
        TalkSession,
        pk=pk,
        clubroom=membership.clubroom,
        mode=MODE_CRISIS,
    )
    return render(
        request,
        "crisis/session.html",
        {"clubroom": membership.clubroom, "session": session},
    )


@login_required
@require_POST
def end(request, pk):
    membership = _membership_or_denied(request)
    session = get_object_or_404(TalkSession, pk=pk, clubroom=membership.clubroom, mode=MODE_CRISIS)
    try:
        end_crisis_session(session=session, user=request.user)
    except ValidationError as exc:
        for message in exc.messages:
            messages.error(request, message)
    else:
        messages.success(request, "Krisenraum geschlossen. Hilfe bleibt sichtbar.")
    return redirect("crisis:index")
