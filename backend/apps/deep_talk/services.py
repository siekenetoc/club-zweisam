from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.clubroom.models import Membership
from apps.deep_talk.models import (
    MODE_REPAIR,
    MODE_TALK,
    PROMPTS_BY_MODE,
    TalkPrompt,
    TalkSession,
)


def _require_module(clubroom, user, module: str = "deep_talk") -> Membership:
    membership = Membership.objects.filter(
        clubroom=clubroom, user=user, revoked_at__isnull=True
    ).first()
    if membership is None or not membership.has_module_access(module):
        raise ValidationError("Kein Zugriff auf dieses Modul.")
    return membership


def active_session(clubroom, mode: str):
    return (
        TalkSession.objects.filter(clubroom=clubroom, mode=mode, ended_at__isnull=True)
        .select_related("started_by")
        .first()
    )


def active_sessions(clubroom):
    return TalkSession.objects.filter(clubroom=clubroom, ended_at__isnull=True).select_related(
        "started_by"
    )


def start_session(*, clubroom, user, mode: str) -> TalkSession:
    _require_module(clubroom, user)
    if mode not in {MODE_TALK, MODE_REPAIR}:
        raise ValidationError("Unbekannter Modus.")
    with transaction.atomic():
        existing = active_session(clubroom, mode)
        if existing is not None:
            return existing
        session = TalkSession.objects.create(clubroom=clubroom, mode=mode, started_by=user)
        TalkPrompt.objects.bulk_create(
            [TalkPrompt(session=session, text=text) for text in PROMPTS_BY_MODE[mode]]
        )
        return session


def toggle_prompt(*, session: TalkSession, prompt_id: int, user) -> TalkPrompt:
    _require_module(session.clubroom, user)
    if not session.is_active:
        raise ValidationError("Diese Sitzung ist bereits beendet.")
    prompt = session.prompts.filter(pk=prompt_id).first()
    if prompt is None:
        raise ValidationError("Diese Leitfrage gehört nicht zur Sitzung.")
    prompt.answered = not prompt.answered
    prompt.save(update_fields=["answered"])
    return prompt


def pause_session(*, session: TalkSession, user) -> TalkSession:
    _require_module(session.clubroom, user)
    if not session.is_active:
        raise ValidationError("Diese Sitzung ist bereits beendet.")
    if session.is_paused:
        return session
    session.timeout_at = timezone.now()
    session.timeout_by = user
    session.save(update_fields=["timeout_at", "timeout_by", "updated_at"])
    return session


def resume_session(*, session: TalkSession, user) -> TalkSession:
    _require_module(session.clubroom, user)
    if not session.is_active:
        raise ValidationError("Diese Sitzung ist bereits beendet.")
    session.timeout_at = None
    session.timeout_by = None
    session.save(update_fields=["timeout_at", "timeout_by", "updated_at"])
    return session


def end_session(*, session: TalkSession, user) -> TalkSession:
    _require_module(session.clubroom, user)
    if not session.is_active:
        return session
    session.ended_at = timezone.now()
    session.save(update_fields=["ended_at", "updated_at"])
    return session


def history(clubroom, limit: int = 10):
    return TalkSession.objects.filter(clubroom=clubroom, mode__in=[MODE_TALK, MODE_REPAIR])[:limit]


def crisis_access(clubroom, user) -> Membership:
    return _require_module(clubroom, user, module="lounge")
