from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.admin_panel.models import (
    ALLOWED_TARGET_LABELS,
    BREAK_GLASS_HOURS,
    BreakGlassRequest,
    _audit,
)
from apps.clubroom.models import Clubroom, Membership
from apps.core.permissions import is_sensitive_label
from apps.feed.models import EVENT_BREAK_GLASS_ACCESS, FeedEvent
from apps.feed.services import notify_members
from apps.roulette.models import Match


def _resolve_clubroom(target_type: str, target_id: str) -> Clubroom:
    try:
        object_id = int(target_id)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Ungültige Ziel-ID.") from exc
    if target_type == "clubroom.clubroom":
        clubroom = Clubroom.objects.filter(pk=object_id).first()
    elif target_type == "clubroom.membership":
        membership = Membership.objects.filter(pk=object_id).first()
        clubroom = membership.clubroom if membership else None
    elif target_type == "feed.feedevent":
        event = FeedEvent.objects.filter(pk=object_id).first()
        clubroom = event.clubroom if event else None
    elif target_type == "roulette.match":
        match = Match.objects.filter(pk=object_id).select_related("round").first()
        if match is not None and not match.is_released:
            raise ValidationError("Nicht freigegebene Matches sind für Break-Glass gesperrt.")
        clubroom = match.round.clubroom if match else None
    else:
        clubroom = None
    if clubroom is None:
        raise ValidationError("Ziel nicht gefunden.")
    return clubroom


def validate_target(target_type: str, target_id: str) -> Clubroom:
    if is_sensitive_label(target_type):
        raise ValidationError("Diese Datenklasse ist für Break-Glass gesperrt.")
    if target_type not in ALLOWED_TARGET_LABELS:
        raise ValidationError("Für dieses Ziel ist Break-Glass nicht vorgesehen.")
    return _resolve_clubroom(target_type, target_id)


def request_break_glass(*, user, target_type: str, target_id: str, reason: str):
    if not user.is_superuser:
        raise ValidationError("Nur Super-Admins dürfen Break-Glass beantragen.")
    reason = reason.strip()
    if not reason:
        raise ValidationError("Begründung ist erforderlich.")
    validate_target(target_type, target_id)
    with transaction.atomic():
        request_obj = BreakGlassRequest.objects.create(
            requested_by=user,
            target_type=target_type,
            target_id=str(target_id),
            reason=reason,
        )
        _audit("break_glass.request", actor=user, request_obj=request_obj)
        return request_obj


def approve_break_glass(*, request_obj: BreakGlassRequest, user):
    if not user.is_superuser:
        raise ValidationError("Nur Super-Admins dürfen bestätigen.")
    if request_obj.requested_by_id == user.id:
        raise ValidationError("Vier-Augen-Prinzip: Bestätigung durch eine zweite Person.")
    with transaction.atomic():
        request_obj = BreakGlassRequest.objects.select_for_update().get(pk=request_obj.pk)
        if request_obj.status != "pending":
            raise ValidationError("Dieser Antrag ist nicht offen.")
        validate_target(request_obj.target_type, request_obj.target_id)
        request_obj.approved_by = user
        request_obj.approved_at = timezone.now()
        request_obj.expires_at = request_obj.approved_at + timedelta(hours=BREAK_GLASS_HOURS)
        request_obj.save(update_fields=["approved_by", "approved_at", "expires_at", "updated_at"])
        _audit("break_glass.approve", actor=user, request_obj=request_obj)
        return request_obj


def use_break_glass(*, request_obj: BreakGlassRequest, user):
    if not user.is_superuser:
        raise ValidationError("Nur Super-Admins dürfen Break-Glass nutzen.")
    if user.id not in {request_obj.requested_by_id, request_obj.approved_by_id}:
        raise ValidationError("Nur am Antrag Beteiligte dürfen zugreifen.")
    with transaction.atomic():
        request_obj = BreakGlassRequest.objects.select_for_update().get(pk=request_obj.pk)
        if request_obj.status == "used":
            raise ValidationError("Dieser Antrag wurde bereits genutzt.")
        if request_obj.status != "approved":
            raise ValidationError("Dieser Antrag ist nicht gültig oder abgelaufen.")
        clubroom = validate_target(request_obj.target_type, request_obj.target_id)
        request_obj.used_at = timezone.now()
        request_obj.users_notified = True
        request_obj.save(update_fields=["used_at", "users_notified", "updated_at"])
        notify_members(clubroom=clubroom, event_type=EVENT_BREAK_GLASS_ACCESS)
        _audit("break_glass.use", actor=user, request_obj=request_obj)
        return request_obj
