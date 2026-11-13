from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.clubroom.models import Membership
from apps.deep_talk.models import MODE_CRISIS, TalkSession


def _require_member(clubroom, user) -> Membership:
    membership = Membership.objects.filter(
        clubroom=clubroom, user=user, revoked_at__isnull=True
    ).first()
    if membership is None or not membership.has_module_access("lounge"):
        raise ValidationError("Kein Zugriff auf den Krisenmodus.")
    return membership


def active_crisis_session(clubroom):
    return (
        TalkSession.objects.filter(clubroom=clubroom, mode=MODE_CRISIS, ended_at__isnull=True)
        .select_related("started_by")
        .first()
    )


def start_crisis_session(*, clubroom, user) -> TalkSession:
    _require_member(clubroom, user)
    with transaction.atomic():
        existing = active_crisis_session(clubroom)
        if existing is not None:
            return existing
        return TalkSession.objects.create(clubroom=clubroom, mode=MODE_CRISIS, started_by=user)


def end_crisis_session(*, session: TalkSession, user) -> TalkSession:
    _require_member(session.clubroom, user)
    if session.ended_at is not None:
        return session
    session.ended_at = timezone.now()
    session.save(update_fields=["ended_at", "updated_at"])
    return session
