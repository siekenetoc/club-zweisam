from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.clubroom.models import Membership
from apps.deep_talk.models import MODE_REPAIR, MODE_TALK, TalkSession
from apps.deep_talk.services import (
    active_session,
    end_session,
    history,
    pause_session,
    resume_session,
    start_session,
    toggle_prompt,
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
    if membership is None or not membership.has_module_access("deep_talk"):
        raise PermissionDenied("Kein Zugriff auf Deep Talk.")
    return membership


def index(request):
    membership = _membership_or_denied(request)
    clubroom = membership.clubroom
    return render(
        request,
        "deep_talk/index.html",
        {
            "clubroom": clubroom,
            "talk_session": active_session(clubroom, MODE_TALK),
            "repair_session": active_session(clubroom, MODE_REPAIR),
            "sessions": history(clubroom),
            "can_moderate": membership.role in {"owner", "advisor", "mediator"},
        },
    )


@login_required
@require_POST
def start(request, mode):
    membership = _membership_or_denied(request)
    if mode not in {MODE_TALK, MODE_REPAIR}:
        raise PermissionDenied("Unbekannter Modus.")
    try:
        session = start_session(clubroom=membership.clubroom, user=request.user, mode=mode)
    except ValidationError as exc:
        for message in exc.messages:
            messages.error(request, message)
        return redirect("deep_talk:index")
    return redirect("deep_talk:session", pk=session.pk)


def session_detail(request, pk):
    membership = _membership_or_denied(request)
    session = get_object_or_404(
        TalkSession.objects.select_related("clubroom", "started_by", "timeout_by"),
        pk=pk,
        clubroom=membership.clubroom,
        mode__in=[MODE_TALK, MODE_REPAIR],
    )
    return render(
        request,
        "deep_talk/session.html",
        {
            "clubroom": membership.clubroom,
            "session": session,
            "prompts": session.prompts.all(),
            "is_active": session.is_active,
        },
    )


@login_required
@require_POST
def toggle_prompt_view(request, pk, prompt_id):
    membership = _membership_or_denied(request)
    session = get_object_or_404(
        TalkSession, pk=pk, clubroom=membership.clubroom, mode__in=[MODE_TALK, MODE_REPAIR]
    )
    try:
        toggle_prompt(session=session, prompt_id=prompt_id, user=request.user)
    except ValidationError as exc:
        for message in exc.messages:
            messages.error(request, message)
    return redirect("deep_talk:session", pk=session.pk)


@login_required
@require_POST
def timeout(request, pk):
    membership = _membership_or_denied(request)
    session = get_object_or_404(TalkSession, pk=pk, clubroom=membership.clubroom)
    try:
        pause_session(session=session, user=request.user)
    except ValidationError as exc:
        for message in exc.messages:
            messages.error(request, message)
    else:
        messages.success(request, "Time-out. Pause ohne Begründung.")
    return redirect("deep_talk:session", pk=session.pk)


@login_required
@require_POST
def resume(request, pk):
    membership = _membership_or_denied(request)
    session = get_object_or_404(TalkSession, pk=pk, clubroom=membership.clubroom)
    try:
        resume_session(session=session, user=request.user)
    except ValidationError as exc:
        for message in exc.messages:
            messages.error(request, message)
    else:
        messages.success(request, "Weiter im Gespräch.")
    return redirect("deep_talk:session", pk=session.pk)


@login_required
@require_POST
def end(request, pk):
    membership = _membership_or_denied(request)
    session = get_object_or_404(TalkSession, pk=pk, clubroom=membership.clubroom)
    try:
        end_session(session=session, user=request.user)
    except ValidationError as exc:
        for message in exc.messages:
            messages.error(request, message)
    else:
        messages.success(request, "Sitzung beendet.")
    return redirect("deep_talk:index")
