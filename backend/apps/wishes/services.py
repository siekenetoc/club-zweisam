from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.clubroom.models import Membership
from apps.clubroom.permissions import OWNER
from apps.core.audit import AuditEntry
from apps.vitrine.models import SOURCE_WISH
from apps.vitrine.services import record_commonality
from apps.wishes.models import (
    ACTION_ACCEPT,
    ACTION_ALTERNATIVE,
    ACTION_BOUNDARY,
    ACTION_CHOICES,
    ACTION_PARTIAL,
    ACTION_POSTPONE,
    ACTION_REJECT,
    ACTION_TALK,
    NOTE_REQUIRED_ACTIONS,
    STATUS_AGREED,
    STATUS_BOUNDARY,
    STATUS_CONFIRMED,
    STATUS_DRAFT,
    STATUS_PENDING,
    STATUS_PLACED,
    STATUS_POSTPONED,
    STATUS_REJECTED,
    STATUS_REPLIED,
    TIMEFRAME_CHOICES,
    TYPE_CHOICES,
    Wish,
    WishResponse,
)


def _audit(event, *, actor, target_type, target_id, **metadata):
    return AuditEntry.objects.create(
        actor=actor,
        action=event,
        target_type=target_type,
        target_id=str(target_id),
        metadata=metadata,
    )


def _require_owner(clubroom, user) -> Membership:
    membership = Membership.objects.filter(
        clubroom=clubroom, user=user, revoked_at__isnull=True
    ).first()
    if membership is None or membership.role != OWNER:
        raise ValidationError("Nur Hauptmitglieder nutzen den Concierge.")
    if not membership.has_module_access("wishes"):
        raise ValidationError("Kein Zugriff auf den Concierge.")
    return membership


def create_wish(
    *,
    clubroom,
    user,
    wish_type: str,
    title: str,
    body: str,
    category: str = "",
    intensity: int = 1,
    timeframe: str = "offen",
    is_private: bool = False,
) -> Wish:
    _require_owner(clubroom, user)
    if wish_type not in dict(TYPE_CHOICES):
        raise ValidationError("Unbekannter Wunschtyp.")
    if timeframe not in dict(TIMEFRAME_CHOICES):
        raise ValidationError("Unbekannter Zeitrahmen.")
    if intensity not in (1, 2, 3):
        raise ValidationError("Ungültige Intensität.")
    title = title.strip()
    body = body.strip()
    if not title or not body:
        raise ValidationError("Titel und Inhalt sind erforderlich.")

    with transaction.atomic():
        wish = Wish.objects.create(
            clubroom=clubroom,
            created_by=user,
            type=wish_type,
            category=category.strip(),
            intensity=intensity,
            timeframe=timeframe,
            title=title,
            body=body,
            is_private=is_private,
            status=STATUS_DRAFT if is_private else STATUS_PLACED,
        )
        _audit(
            "wish.create",
            actor=user,
            target_type="wishes.wish",
            target_id=wish.pk,
            type=wish_type,
            private=is_private,
        )
        return wish


def share_wish(*, wish: Wish, user) -> Wish:
    _require_owner(wish.clubroom, user)
    with transaction.atomic():
        wish = Wish.objects.select_for_update().get(pk=wish.pk)
        if wish.created_by_id != user.id:
            raise ValidationError("Nur die verfassende Person kann den Wunsch teilen.")
        if wish.status != STATUS_DRAFT or not wish.is_private:
            raise ValidationError("Dieser Wunsch ist nicht privat.")
        wish.is_private = False
        wish.status = STATUS_PLACED
        wish.save(update_fields=["is_private", "status", "updated_at"])
        _audit(
            "wish.share",
            actor=user,
            target_type="wishes.wish",
            target_id=wish.pk,
        )
        return wish


def respond_to_wish(*, wish: Wish, user, action: str, note: str = "") -> WishResponse:
    _require_owner(wish.clubroom, user)
    if action not in dict(ACTION_CHOICES):
        raise ValidationError("Unbekannte Antwort.")
    note = note.strip()
    if action in NOTE_REQUIRED_ACTIONS and not note:
        raise ValidationError("Für diese Antwort ist eine Notiz erforderlich.")

    with transaction.atomic():
        wish = Wish.objects.select_for_update().get(pk=wish.pk)
        if wish.is_private:
            raise ValidationError("Ein privater Wunsch kann nicht beantwortet werden.")
        if wish.status != STATUS_PLACED:
            raise ValidationError("Auf diesen Wunsch kann nicht mehr geantwortet werden.")
        if wish.created_by_id == user.id:
            raise ValidationError("Du kannst deinen eigenen Wunsch nicht beantworten.")
        if WishResponse.objects.filter(wish=wish, responded_by=user).exists():
            raise ValidationError("Du hast bereits geantwortet.")
        if not wish.clubroom.memberships.filter(user=user, revoked_at__isnull=True).exists():
            raise ValidationError("Du bist kein aktives Mitglied.")

        try:
            response = WishResponse.objects.create(
                wish=wish, responded_by=user, action=action, note=note
            )
        except IntegrityError as exc:
            raise ValidationError("Du hast bereits geantwortet.") from exc

        now = timezone.now()
        wish.responded_at = now
        if action == ACTION_ACCEPT:
            wish.status = STATUS_AGREED
            wish.agreed_at = now
        elif action in {ACTION_PARTIAL, ACTION_ALTERNATIVE}:
            wish.status = STATUS_REPLIED
        elif action == ACTION_TALK:
            wish.status = STATUS_POSTPONED
        elif action == ACTION_POSTPONE:
            wish.status = STATUS_POSTPONED
        elif action == ACTION_REJECT:
            wish.status = STATUS_REJECTED
        elif action == ACTION_BOUNDARY:
            wish.status = STATUS_BOUNDARY
        wish.save(update_fields=["responded_at", "status", "agreed_at", "updated_at"])
        _audit(
            "wish.respond",
            actor=user,
            target_type="wishes.wish",
            target_id=wish.pk,
            action=action,
        )
        return response


def requester_decide(*, wish: Wish, user, accept: bool) -> Wish:
    _require_owner(wish.clubroom, user)
    with transaction.atomic():
        wish = Wish.objects.select_for_update().get(pk=wish.pk)
        if wish.created_by_id != user.id:
            raise ValidationError("Nur die verfassende Person entscheidet über die Alternative.")
        if wish.status != STATUS_REPLIED:
            raise ValidationError("Es liegt keine Alternative zur Entscheidung vor.")
        if accept:
            wish.status = STATUS_AGREED
            wish.agreed_at = timezone.now()
        else:
            wish.status = STATUS_REJECTED
        wish.save(update_fields=["status", "agreed_at", "updated_at"])
        _audit(
            "wish.requester_decide",
            actor=user,
            target_type="wishes.wish",
            target_id=wish.pk,
            accepted=accept,
        )
        return wish


def mark_fulfilled(*, wish: Wish, user) -> Wish:
    _require_owner(wish.clubroom, user)
    with transaction.atomic():
        wish = Wish.objects.select_for_update().get(pk=wish.pk)
        if wish.created_by_id != user.id:
            raise ValidationError("Nur die verfassende Person markiert die Erfüllung.")
        if wish.status != STATUS_AGREED:
            raise ValidationError("Dieser Wunsch ist nicht vereinbart.")
        wish.status = STATUS_PENDING
        wish.fulfilled_at = timezone.now()
        wish.save(update_fields=["status", "fulfilled_at", "updated_at"])
        _audit(
            "wish.fulfilled",
            actor=user,
            target_type="wishes.wish",
            target_id=wish.pk,
        )
        return wish


def confirm_fulfilled(*, wish: Wish, user) -> Wish:
    _require_owner(wish.clubroom, user)
    with transaction.atomic():
        wish = Wish.objects.select_for_update().get(pk=wish.pk)
        if wish.created_by_id == user.id:
            raise ValidationError("Die Bestätigung muss von der anderen Person kommen.")
        if wish.status != STATUS_PENDING:
            raise ValidationError("Für diesen Wunsch steht keine Bestätigung aus.")
        response = wish.responses.order_by("-created_at").first()
        if response is None or response.responded_by_id != user.id:
            raise ValidationError("Nur die antwortende Person kann bestätigen.")
        wish.status = STATUS_CONFIRMED
        wish.confirmed_at = timezone.now()
        wish.save(update_fields=["status", "confirmed_at", "updated_at"])
        if not wish.is_private:
            record_commonality(
                clubroom=wish.clubroom,
                source_type=SOURCE_WISH,
                source_id=wish.pk,
                category=wish.type_label,
            )
        _audit(
            "wish.confirm",
            actor=user,
            target_type="wishes.wish",
            target_id=wish.pk,
        )
        return wish
