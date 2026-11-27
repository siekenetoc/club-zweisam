import logging
import smtplib
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.clubroom.forms import ClubroomForm, ClubroomSettingsForm, InvitationForm
from apps.clubroom.models import Invitation, Membership, hash_token
from apps.clubroom.permissions import OWNER, ROLE_LABELS
from apps.clubroom.services import (
    accept_invitation,
    active_membership_for,
    create_clubroom,
    invite_member,
    pending_invitations_for_email,
    resend_invitation,
    revoke_invitation,
    revoke_membership,
    send_invitation_email,
)

logger = logging.getLogger(__name__)


def home(request):
    if not request.user.is_authenticated:
        return render(request, "home.html")

    membership = active_membership_for(request.user)
    if membership is not None:
        clubroom = membership.clubroom
        return render(
            request,
            "clubroom/detail.html",
            {
                "clubroom": clubroom,
                "membership": membership,
                "members": clubroom.active_memberships(),
                "pending_invitations": clubroom.invitations.filter(
                    accepted_at__isnull=True,
                    revoked_at__isnull=True,
                    expires_at__gt=timezone.now(),
                ).select_related("invited_by"),
                "is_owner": membership.role == OWNER,
                "role_label": ROLE_LABELS.get(membership.role, membership.role),
            },
        )

    return render(
        request,
        "clubroom/overview.html",
        {"invitations": pending_invitations_for_email(request.user.email)},
    )


@login_required
def clubroom_create(request):
    if active_membership_for(request.user) is not None:
        messages.info(request, "Du bist bereits Mitglied eines Clubraums.")
        return redirect("clubroom:home")

    if request.method == "POST":
        form = ClubroomForm(request.POST)
        if form.is_valid():
            try:
                clubroom = create_clubroom(
                    user=request.user,
                    name=form.cleaned_data["name"],
                    safe_word=form.cleaned_data["safe_word"],
                    rules=form.cleaned_data["rules"],
                )
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(request, f"Clubraum „{clubroom.name}“ wurde gegründet.")
                return redirect("clubroom:home")
    else:
        form = ClubroomForm()

    return render(request, "clubroom/create.html", {"form": form})


@login_required
def clubroom_settings(request):
    membership = active_membership_for(request.user)
    if membership is None:
        raise Http404
    if membership.role != OWNER:
        raise PermissionDenied("Nur Hauptmitglieder dürfen den Clubraum bearbeiten.")
    clubroom = membership.clubroom
    if request.method == "POST":
        form = ClubroomSettingsForm(request.POST, instance=clubroom)
        if form.is_valid():
            form.save()
            messages.success(request, "Clubraum-Einstellungen gespeichert.")
            return redirect("clubroom:home")
    else:
        form = ClubroomSettingsForm(instance=clubroom)
    return render(
        request,
        "clubroom/settings.html",
        {"form": form, "clubroom": clubroom},
    )


@login_required
def invitation_create(request):
    membership = active_membership_for(request.user)
    if membership is None:
        raise Http404
    if membership.role != OWNER:
        raise PermissionDenied("Nur Hauptmitglieder dürfen einladen.")

    if request.method == "POST":
        form = InvitationForm(request.POST)
        if form.is_valid():
            try:
                invitation, raw_token = invite_member(
                    clubroom=membership.clubroom,
                    email=form.cleaned_data["email"],
                    role=form.cleaned_data["role"],
                    invited_by=request.user,
                )
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                accept_url = (
                    f"{settings.PORTAL_BASE_URL.rstrip('/')}"
                    f"{reverse('clubroom:invitation_accept', kwargs={'token': raw_token})}"
                )
                try:
                    send_invitation_email(invitation=invitation, accept_url=accept_url)
                except (OSError, smtplib.SMTPException):
                    logger.exception("Einladungs-E-Mail konnte nicht versendet werden.")
                    invitation.revoke()
                    form.add_error(
                        None,
                        "Die Einladung konnte nicht per E-Mail versendet werden. "
                        "Bitte später erneut versuchen.",
                    )
                else:
                    messages.success(
                        request,
                        f"Einladung an {invitation.email} wurde versendet.",
                    )
                    return redirect("clubroom:home")
    else:
        form = InvitationForm()

    return render(
        request,
        "clubroom/invite.html",
        {
            "form": form,
            "clubroom": membership.clubroom,
            "pending_invitations": membership.clubroom.invitations.filter(
                accepted_at__isnull=True,
                revoked_at__isnull=True,
                expires_at__gt=timezone.now(),
            ).select_related("invited_by"),
        },
    )


def invitation_accept(request, token):
    token_hash = hash_token(token)
    invitation = (
        Invitation.objects.select_related("clubroom", "invited_by")
        .filter(token_hash=token_hash)
        .first()
    )
    if invitation is None:
        raise Http404

    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect(f"{reverse('accounts:login')}?next={quote(request.path)}")
        try:
            membership = accept_invitation(raw_token=token, user=request.user)
        except ValidationError as exc:
            for message in exc.messages:
                messages.error(request, message)
            return redirect("clubroom:home")
        messages.success(
            request,
            f"Willkommen im Clubraum „{membership.clubroom.name}“ "
            f"als {ROLE_LABELS.get(membership.role, membership.role)}.",
        )
        return redirect("clubroom:home")

    return render(
        request,
        "clubroom/accept.html",
        {
            "invitation": invitation,
            "role_label": ROLE_LABELS.get(invitation.role, invitation.role),
            "email_matches": (
                request.user.is_authenticated
                and invitation.email.lower() == (request.user.email or "").lower()
            ),
        },
    )


@login_required
@require_POST
def invitation_resend(request, pk):
    invitation = get_object_or_404(Invitation, pk=pk)
    if active_membership_for(request.user) is None:
        raise Http404
    try:
        invitation, raw_token = resend_invitation(invitation=invitation, actor=request.user)
        accept_url = (
            f"{settings.PORTAL_BASE_URL.rstrip('/')}"
            f"{reverse('clubroom:invitation_accept', kwargs={'token': raw_token})}"
        )
        send_invitation_email(invitation=invitation, accept_url=accept_url)
    except (ValidationError, OSError, smtplib.SMTPException) as exc:
        if isinstance(exc, ValidationError):
            for message in exc.messages:
                messages.error(request, message)
        else:
            logger.exception("Einladungs-E-Mail konnte nicht erneut versendet werden.")
            messages.error(request, "Einladung konnte nicht versendet werden.")
    else:
        messages.success(request, "Einladung wurde erneut gesendet.")
    return redirect("clubroom:home")


@login_required
@require_POST
def invitation_revoke(request, pk):
    invitation = get_object_or_404(Invitation, pk=pk)
    if active_membership_for(request.user) is None:
        raise Http404
    try:
        revoke_invitation(invitation=invitation, actor=request.user)
    except ValidationError as exc:
        for message in exc.messages:
            messages.error(request, message)
    else:
        messages.success(request, "Einladung wurde widerrufen.")
    return redirect("clubroom:home")


@login_required
@require_POST
def membership_revoke(request, pk):
    target = get_object_or_404(Membership, pk=pk)
    if active_membership_for(request.user) is None:
        raise Http404
    try:
        revoke_membership(membership=target, actor=request.user)
    except ValidationError as exc:
        for message in exc.messages:
            messages.error(request, message)
    else:
        messages.success(request, f"{target.user.username} wurde entfernt.")
    return redirect("clubroom:home")
