from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.clubroom.models import Clubroom, Membership
from apps.clubroom.permissions import OWNER
from apps.core.audit import AuditEntry
from apps.feed.models import (
    EVENT_MATCH_RELEASED,
    EVENT_ROUND_ENDED,
    EVENT_ROUND_STARTED,
)
from apps.feed.services import record_event
from apps.roulette.models import (
    ANSWER_LABELS,
    RESULT_FULL,
    RESULT_NONE,
    RESULT_PARTIAL,
    Deck,
    DeckOptIn,
    Match,
    Round,
    SecretAnswer,
)
from apps.vitrine.services import record_match_commonality


def _audit(action, *, actor, target_type, target_id, **metadata):
    return AuditEntry.objects.create(
        actor=actor,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        metadata=metadata,
    )


def active_round_for(clubroom: Clubroom):
    return (
        Round.objects.filter(clubroom=clubroom, ended_at__isnull=True)
        .select_related("deck", "started_by")
        .first()
    )


def _require_owner(clubroom: Clubroom, user) -> Membership:
    membership = Membership.objects.filter(
        clubroom=clubroom, user=user, revoked_at__isnull=True
    ).first()
    if membership is None or membership.role != OWNER:
        raise ValidationError("Nur Hauptmitglieder spielen Séparée.")
    if not membership.has_module_access("roulette"):
        raise ValidationError("Kein Zugriff auf Séparée.")
    return membership


def _active_owner_ids(clubroom: Clubroom) -> set[int]:
    return set(
        clubroom.memberships.filter(role=OWNER, revoked_at__isnull=True).values_list(
            "user_id", flat=True
        )
    )


def opted_in_user_ids(clubroom: Clubroom, deck: Deck) -> set[int]:
    return set(
        DeckOptIn.objects.filter(clubroom=clubroom, deck=deck).values_list("user_id", flat=True)
    )


def both_owners_opted_in(clubroom: Clubroom, deck: Deck) -> bool:
    owners = _active_owner_ids(clubroom)
    return bool(owners) and owners.issubset(opted_in_user_ids(clubroom, deck))


def opt_in(*, clubroom: Clubroom, deck: Deck, user) -> DeckOptIn:
    membership = _require_owner(clubroom, user)
    if not deck.requires_opt_in:
        raise ValidationError("Für dieses Deck ist kein Opt-in nötig.")
    opt_in_obj, created = DeckOptIn.objects.get_or_create(clubroom=clubroom, deck=deck, user=user)
    if created:
        _audit(
            "roulette.opt_in",
            actor=user,
            target_type="roulette.deck",
            target_id=deck.pk,
            membership_id=membership.pk,
        )
    return opt_in_obj


def start_round(*, clubroom: Clubroom, deck: Deck, user) -> Round:
    _require_owner(clubroom, user)
    if deck.requires_opt_in and not both_owners_opted_in(clubroom, deck):
        raise ValidationError("Dieses Deck erfordert das Opt-in beider Hauptmitglieder.")
    with transaction.atomic():
        clubroom = Clubroom.objects.select_for_update().get(pk=clubroom.pk)
        if active_round_for(clubroom) is not None:
            raise ValidationError("Es läuft bereits eine Runde.")
        round_obj = Round.objects.create(clubroom=clubroom, deck=deck, started_by=user)
        _audit(
            "roulette.round.start",
            actor=user,
            target_type="roulette.round",
            target_id=round_obj.pk,
            deck=deck.code,
        )
        record_event(
            clubroom=clubroom,
            event_type=EVENT_ROUND_STARTED,
            actor=user,
            target_type="roulette.round",
            target_id=round_obj.pk,
            metadata={"deck": deck.code},
        )
        return round_obj


def _compute_result(question, answer_a: str, answer_b: str) -> str:
    pair = sorted([answer_a, answer_b])
    rule = question.rule()
    if any(sorted(candidate) == pair for candidate in rule.get("full", [])):
        return RESULT_FULL
    if any(sorted(candidate) == pair for candidate in rule.get("partial", [])):
        return RESULT_PARTIAL
    return RESULT_NONE


def _resolve_match(round_obj: Round, question, actor):
    answers = list(
        round_obj.answers.filter(question=question).select_related("user").order_by("user_id")
    )
    if len(answers) != 2 or answers[0].user_id == answers[1].user_id:
        return None

    existing = Match.objects.filter(round=round_obj, question=question).first()
    if existing is not None:
        return existing

    answer_a, answer_b = answers
    if answer_a.is_boundary or answer_b.is_boundary:
        result = RESULT_NONE
    else:
        result = _compute_result(question, answer_a.answer, answer_b.answer)

    try:
        with transaction.atomic():
            match = Match.objects.create(
                round=round_obj,
                question=question,
                user_a=answer_a.user,
                user_b=answer_b.user,
                result=result,
                boundary_a=answer_a.is_boundary,
                boundary_b=answer_b.is_boundary,
            )
    except IntegrityError:
        return Match.objects.get(round=round_obj, question=question)

    _audit(
        "roulette.match",
        actor=actor,
        target_type="roulette.match",
        target_id=match.pk,
        result=result,
    )
    return match


def submit_answer(
    *, round_obj: Round, question, user, answer: str, is_boundary: bool
) -> SecretAnswer:
    _require_owner(round_obj.clubroom, user)
    if answer not in ANSWER_LABELS:
        raise ValidationError("Unbekannte Antwort.")
    if question.deck_id != round_obj.deck_id:
        raise ValidationError("Diese Frage gehört nicht zum Deck der Runde.")

    with transaction.atomic():
        round_obj = Round.objects.select_for_update().get(pk=round_obj.pk)
        if not round_obj.is_active:
            raise ValidationError("Diese Runde ist bereits beendet.")
        if SecretAnswer.objects.filter(round=round_obj, question=question, user=user).exists():
            raise ValidationError("Für diese Frage wurde bereits geantwortet.")

        answer_obj = SecretAnswer.objects.create(
            round=round_obj,
            question=question,
            user=user,
            answer=answer,
            is_boundary=is_boundary,
        )
        _audit(
            "roulette.answer",
            actor=user,
            target_type="roulette.secretanswer",
            target_id=answer_obj.pk,
            round_id=round_obj.pk,
            question_id=question.pk,
            boundary=is_boundary,
        )
        _resolve_match(round_obj, question, user)
        return answer_obj


def release_match(*, match: Match, user) -> Match:
    _require_owner(match.round.clubroom, user)
    with transaction.atomic():
        match = (
            Match.objects.select_for_update()
            .select_related("round", "question", "question__deck", "round__clubroom")
            .get(pk=match.pk)
        )
        if match.round.ended_at is not None:
            raise ValidationError("Diese Runde ist bereits beendet.")
        flag = match.release_flag_for(user)
        if flag is None:
            raise ValidationError("Du bist nicht Teil dieses Matches.")
        if flag == "a" and match.released_by_a:
            raise ValidationError("Du hast bereits freigegeben.")
        if flag == "b" and match.released_by_b:
            raise ValidationError("Du hast bereits freigegeben.")

        if flag == "a":
            match.released_by_a = True
        else:
            match.released_by_b = True

        if match.released_by_a and match.released_by_b:
            match.released_at = timezone.now()
            if match.result in {RESULT_FULL, RESULT_PARTIAL}:
                record_match_commonality(match=match)

        match.save(
            update_fields=[
                "released_by_a",
                "released_by_b",
                "released_at",
                "updated_at",
            ]
        )
        _audit(
            "roulette.release",
            actor=user,
            target_type="roulette.match",
            target_id=match.pk,
            released=bool(match.released_at),
        )
        if match.released_at is not None:
            record_event(
                clubroom=match.round.clubroom,
                event_type=EVENT_MATCH_RELEASED,
                actor=user,
                target_type="roulette.match",
                target_id=match.pk,
                metadata={"result": match.result},
            )
        return match


def end_round(*, round_obj: Round, user) -> Round:
    _require_owner(round_obj.clubroom, user)
    with transaction.atomic():
        round_obj = Round.objects.select_for_update().get(pk=round_obj.pk)
        if round_obj.ended_at is not None:
            return round_obj
        round_obj.ended_at = timezone.now()
        round_obj.save(update_fields=["ended_at", "updated_at"])
        round_obj.answers.filter(deleted_at__isnull=True).update(
            answer="", deleted_at=timezone.now(), updated_at=timezone.now()
        )
        _audit(
            "roulette.round.end",
            actor=user,
            target_type="roulette.round",
            target_id=round_obj.pk,
        )
        record_event(
            clubroom=round_obj.clubroom,
            event_type=EVENT_ROUND_ENDED,
            actor=user,
            target_type="roulette.round",
            target_id=round_obj.pk,
        )
        return round_obj


def purge_expired_answers() -> dict[str, int]:
    days = getattr(settings, "ROULETTE_ANSWER_RETENTION_DAYS", 30)
    cutoff = timezone.now() - timedelta(days=days)
    cleared = SecretAnswer.objects.filter(created_at__lt=cutoff, deleted_at__isnull=True).update(
        answer="", deleted_at=timezone.now(), updated_at=timezone.now()
    )
    stale_matches = Match.objects.filter(result=RESULT_NONE, created_at__lt=cutoff)
    deleted_matches = stale_matches.count()
    stale_matches.delete()
    if cleared or deleted_matches:
        _audit(
            "roulette.purge",
            actor=None,
            target_type="roulette.maintenance",
            target_id="purge",
            cleared_answers=cleared,
            deleted_non_matches=deleted_matches,
        )
    return {"cleared_answers": cleared, "deleted_non_matches": deleted_matches}
