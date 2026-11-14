import secrets

from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.clubroom.models import (
    Clubroom,
    Invitation,
    Membership,
    default_invitation_expiry,
    hash_token,
)
from apps.clubroom.permissions import OWNER, ROLE_CHOICES, ROLE_LABELS
from apps.core.audit import AuditEntry
from apps.feed.models import EVENT_CLUBROOM_CREATED, EVENT_MEMBER_JOINED, EVENT_MEMBER_REMOVED
from apps.feed.services import record_event


def _audit(action, *, actor, target_type, target_id, **metadata):
    return AuditEntry.objects.create(
        actor=actor,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        metadata=metadata,
    )


def active_membership_for(user):
    if not getattr(user, "is_authenticated", False):
        return None
    return (
        Membership.objects.filter(
            user=user, revoked_at__isnull=True, clubroom__deleted_at__isnull=True
        )
        .select_related("clubroom", "user")
        .first()
    )


def pending_invitations_for_email(email: str):
    return Invitation.objects.filter(
        email__iexact=email,
        accepted_at__isnull=True,
        revoked_at__isnull=True,
        expires_at__gt=timezone.now(),
        clubroom__deleted_at__isnull=True,
    ).select_related("clubroom", "invited_by")


def create_clubroom(*, user, name: str, safe_word: str, rules: str = "") -> Clubroom:
    if active_membership_for(user) is not None:
        raise ValidationError("Du bist bereits Mitglied eines Clubraums.")
    with transaction.atomic():
        clubroom = Clubroom.objects.create(
            name=name.strip(),
            created_by=user,
            safe_word=safe_word,
            rules=rules,
        )
        Membership.objects.create(
            clubroom=clubroom,
            user=user,
            role=OWNER,
            invited_by=user,
            invited_at=timezone.now(),
        )
        _audit(
            "clubroom.create",
            actor=user,
            target_type="clubroom.clubroom",
            target_id=clubroom.pk,
        )
        record_event(
            clubroom=clubroom,
            event_type=EVENT_CLUBROOM_CREATED,
            actor=user,
            target_type="clubroom.clubroom",
            target_id=clubroom.pk,
            notify=False,
        )
    return clubroom


def _active_owner_count(clubroom: Clubroom) -> int:
    return clubroom.memberships.filter(role=OWNER, revoked_at__isnull=True).count()


def _pending_owner_invitations(clubroom: Clubroom) -> int:
    return clubroom.invitations.filter(
        role=OWNER,
        accepted_at__isnull=True,
        revoked_at__isnull=True,
        expires_at__gt=timezone.now(),
    ).count()


def invite_member(
    *, clubroom: Clubroom, email: str, role: str, invited_by
) -> tuple[Invitation, str]:
    with transaction.atomic():
        clubroom = Clubroom.objects.select_for_update().get(pk=clubroom.pk)
        membership = Membership.objects.filter(
            clubroom=clubroom, user=invited_by, revoked_at__isnull=True
        ).first()
        if membership is None or membership.role != OWNER:
            raise ValidationError("Nur Hauptmitglieder dürfen einladen.")

        if role not in dict(ROLE_CHOICES):
            raise ValidationError("Unbekannte Rolle.")

        email = email.strip().lower()
        existing_user = User.objects.filter(email__iexact=email).first()
        if existing_user is not None:
            existing_membership = Membership.objects.filter(
                user=existing_user, revoked_at__isnull=True
            ).first()
            if existing_membership is not None:
                raise ValidationError("Diese Person ist bereits Mitglied eines Clubraums.")

        if clubroom.invitations.filter(
            email__iexact=email,
            accepted_at__isnull=True,
            revoked_at__isnull=True,
            expires_at__gt=timezone.now(),
        ).exists():
            raise ValidationError("Für diese E-Mail-Adresse liegt bereits eine Einladung vor.")

        if (
            role == OWNER
            and _active_owner_count(clubroom) + _pending_owner_invitations(clubroom) >= 2
        ):
            raise ValidationError(
                "Ein Clubraum hat höchstens zwei Hauptmitglieder. "
                "Widerrufe zuerst eine offene Einladung."
            )

        invitation, raw_token = Invitation.issue(
            clubroom=clubroom, email=email, role=role, invited_by=invited_by
        )
        _audit(
            "invitation.create",
            actor=invited_by,
            target_type="clubroom.invitation",
            target_id=invitation.pk,
            role=role,
        )
        return invitation, raw_token


def send_invitation_email(*, invitation: Invitation, accept_url: str) -> None:
    recipient = User.objects.filter(email__iexact=invitation.email).first()
    recipient_name = (
        recipient.first_name.strip()
        if recipient and recipient.first_name.strip()
        else invitation.email
    )
    inviter_name = invitation.invited_by.get_full_name().strip()
    if not inviter_name:
        inviter_name = invitation.invited_by.username
    subject = f"Einladung von {inviter_name} in den Clubraum „{invitation.clubroom.name}“"
    body = (
        f"Hallo {recipient_name},\n\n"
        f"{inviter_name} (@{invitation.invited_by.username}) hat dich in den "
        f"Clubraum „{invitation.clubroom.name}“ eingeladen.\n\n"
        f"Deine Rolle: {ROLE_LABELS.get(invitation.role, invitation.role)}\n"
        f"Einladung für: {invitation.email}\n\n"
        "So nimmst du teil:\n"
        f"1. Öffne diesen Link: {accept_url}\n"
        f"2. Melde dich mit {invitation.email} an oder registriere dich damit.\n"
        "3. Klicke auf „Einladung annehmen“.\n\n"
        f"Der Link ist bis {invitation.expires_at:%d.%m.%Y %H:%M} gültig.\n"
        "Wenn du nicht möchtest, ignoriere diese E-Mail einfach.\n\n"
        "Club Zweisam\n"
    )
    send_mail(subject, body, None, [invitation.email])


def accept_invitation(*, raw_token: str, user) -> Membership:
    token_hash = hash_token(raw_token)

    with transaction.atomic():
        invitation = (
            Invitation.objects.select_for_update()
            .select_related("clubroom")
            .filter(token_hash=token_hash)
            .first()
        )
        if invitation is None:
            raise ValidationError("Diese Einladung ist nicht gültig.")
        if invitation.revoked_at is not None:
            raise ValidationError("Diese Einladung wurde widerrufen.")
        if invitation.accepted_at is not None:
            raise ValidationError("Diese Einladung wurde bereits angenommen.")
        if invitation.is_expired:
            raise ValidationError("Diese Einladung ist abgelaufen.")
        if invitation.email.lower() != (user.email or "").lower():
            raise ValidationError("Diese Einladung ist an eine andere E-Mail-Adresse gebunden.")
        if Membership.objects.filter(user=user, revoked_at__isnull=True).exists():
            raise ValidationError("Du bist bereits Mitglied eines Clubraums.")

        clubroom = Clubroom.objects.select_for_update().get(pk=invitation.clubroom_id)
        if invitation.role == OWNER and _active_owner_count(clubroom) >= 2:
            raise ValidationError("Dieser Clubraum hat bereits zwei Hauptmitglieder.")

        try:
            membership = Membership.objects.create(
                clubroom=clubroom,
                user=user,
                role=invitation.role,
                invited_by=invitation.invited_by,
                invited_at=invitation.created_at,
            )
        except IntegrityError as exc:
            raise ValidationError("Du bist bereits Mitglied eines Clubraums.") from exc

        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=["accepted_at", "updated_at"])
        _audit(
            "invitation.accept",
            actor=user,
            target_type="clubroom.membership",
            target_id=membership.pk,
            role=membership.role,
        )
        record_event(
            clubroom=clubroom,
            event_type=EVENT_MEMBER_JOINED,
            actor=user,
            target_type="clubroom.membership",
            target_id=membership.pk,
            metadata={"role": membership.role},
        )
        return membership


def resend_invitation(*, invitation: Invitation, actor) -> tuple[Invitation, str]:
    membership = Membership.objects.filter(
        clubroom=invitation.clubroom, user=actor, revoked_at__isnull=True
    ).first()
    if membership is None or membership.role != OWNER:
        raise ValidationError("Nur Hauptmitglieder dürfen Einladungen erneut senden.")
    if invitation.accepted_at is not None:
        raise ValidationError(
            "Bereits angenommene Einladungen können nicht erneut gesendet werden."
        )
    if invitation.revoked_at is not None:
        raise ValidationError("Widerrufene Einladungen können nicht erneut gesendet werden.")
    raw_token = secrets.token_urlsafe(32)
    invitation.token_hash = hash_token(raw_token)
    invitation.expires_at = default_invitation_expiry()
    invitation.save(update_fields=["token_hash", "expires_at", "updated_at"])
    _audit(
        "invitation.resend",
        actor=actor,
        target_type="clubroom.invitation",
        target_id=invitation.pk,
        role=invitation.role,
    )
    return invitation, raw_token


def revoke_invitation(*, invitation: Invitation, actor) -> None:
    membership = Membership.objects.filter(
        clubroom=invitation.clubroom, user=actor, revoked_at__isnull=True
    ).first()
    if membership is None or membership.role != OWNER:
        raise ValidationError("Nur Hauptmitglieder dürfen Einladungen widerrufen.")
    if invitation.accepted_at is not None:
        raise ValidationError("Bereits angenommene Einladungen können nicht widerrufen werden.")
    invitation.revoke()
    _audit(
        "invitation.revoke",
        actor=actor,
        target_type="clubroom.invitation",
        target_id=invitation.pk,
    )


def revoke_membership(*, membership: Membership, actor) -> None:
    actor_membership = Membership.objects.filter(
        clubroom=membership.clubroom, user=actor, revoked_at__isnull=True
    ).first()
    if actor_membership is None or actor_membership.role != OWNER:
        raise ValidationError("Nur Hauptmitglieder dürfen Mitglieder entfernen.")
    if membership.user_id == actor.id:
        raise ValidationError("Du kannst dich nicht selbst entfernen.")
    if membership.role == OWNER:
        raise ValidationError("Hauptmitglieder können nicht entfernt werden.")
    membership.revoke()
    _audit(
        "membership.revoke",
        actor=actor,
        target_type="clubroom.membership",
        target_id=membership.pk,
        role=membership.role,
    )
    record_event(
        clubroom=membership.clubroom,
        event_type=EVENT_MEMBER_REMOVED,
        actor=actor,
        target_type="clubroom.membership",
        target_id=membership.pk,
        metadata={"role": membership.role},
    )
