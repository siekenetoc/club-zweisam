from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.clubroom.models import Clubroom, Membership
from apps.clubroom.permissions import OWNER
from apps.core.audit import AuditEntry
from apps.playbook.models import Challenge, ChallengeRun, PlaybookOptIn


def _audit(action, *, actor, target_type, target_id, **metadata):
    return AuditEntry.objects.create(
        actor=actor,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        metadata=metadata,
    )


def _require_owner(clubroom, user) -> Membership:
    membership = Membership.objects.filter(
        clubroom=clubroom, user=user, revoked_at__isnull=True
    ).first()
    if membership is None or membership.role != OWNER:
        raise ValidationError("Nur Hauptmitglieder starten Challenges.")
    if not membership.has_module_access("playbook"):
        raise ValidationError("Kein Zugriff auf das Playbook.")
    return membership


def active_owner_ids(clubroom: Clubroom) -> list[int]:
    return list(
        clubroom.memberships.filter(role=OWNER, revoked_at__isnull=True)
        .order_by("user_id")
        .values_list("user_id", flat=True)
    )


def stage3_opted_in_user_ids(clubroom: Clubroom) -> set[int]:
    return set(PlaybookOptIn.objects.filter(clubroom=clubroom).values_list("user_id", flat=True))


def both_owners_opted_in_stage3(clubroom: Clubroom) -> bool:
    owners = set(active_owner_ids(clubroom))
    return bool(owners) and owners.issubset(stage3_opted_in_user_ids(clubroom))


def opt_in_stage3(*, clubroom: Clubroom, user) -> PlaybookOptIn:
    _require_owner(clubroom, user)
    opt_in_obj, created = PlaybookOptIn.objects.get_or_create(clubroom=clubroom, user=user)
    if created:
        _audit(
            "playbook.opt_in",
            actor=user,
            target_type="playbook.optin",
            target_id=opt_in_obj.pk,
        )
    return opt_in_obj


def revoke_opt_in_stage3(*, clubroom: Clubroom, user) -> None:
    _require_owner(clubroom, user)
    PlaybookOptIn.objects.filter(clubroom=clubroom, user=user).delete()
    _audit(
        "playbook.opt_out",
        actor=user,
        target_type="playbook.optin",
        target_id=user.pk,
    )


def active_run_for(clubroom: Clubroom):
    return (
        ChallengeRun.objects.filter(
            clubroom=clubroom, completed_at__isnull=True, aborted_at__isnull=True
        )
        .select_related("challenge", "started_by", "user_a", "user_b")
        .first()
    )


def daily_run_count(clubroom: Clubroom) -> int:
    return ChallengeRun.objects.filter(
        clubroom=clubroom, started_at__date=timezone.localdate()
    ).count()


def start_challenge(*, clubroom: Clubroom, challenge: Challenge, user) -> ChallengeRun:
    _require_owner(clubroom, user)
    if challenge.requires_opt_in and not both_owners_opted_in_stage3(clubroom):
        raise ValidationError("Stufe 3 erfordert das Opt-in beider Hauptmitglieder.")
    daily_limit = getattr(settings, "PLAYBOOK_DAILY_LIMIT", 3)
    with transaction.atomic():
        clubroom = Clubroom.objects.select_for_update().get(pk=clubroom.pk)
        if active_run_for(clubroom) is not None:
            raise ValidationError("Es läuft bereits eine Challenge.")
        if daily_run_count(clubroom) >= daily_limit:
            raise ValidationError(
                f"Tages-Deckel erreicht ({daily_limit} Challenges pro Tag). "
                "Morgen geht es weiter."
            )
        owner_ids = active_owner_ids(clubroom)
        user_a_id = owner_ids[0]
        user_b_id = owner_ids[1] if len(owner_ids) > 1 else None
        run = ChallengeRun.objects.create(
            challenge=challenge,
            clubroom=clubroom,
            started_by=user,
            user_a_id=user_a_id,
            user_b_id=user_b_id,
        )
        _audit(
            "playbook.run.start",
            actor=user,
            target_type="playbook.challengerun",
            target_id=run.pk,
            challenge_id=challenge.pk,
            stage=challenge.consent_stage,
        )
        return run


def confirm_run(*, run: ChallengeRun, user) -> ChallengeRun:
    _require_owner(run.clubroom, user)
    with transaction.atomic():
        run = ChallengeRun.objects.select_for_update().get(pk=run.pk)
        if not run.is_active:
            raise ValidationError("Diese Challenge ist bereits beendet.")
        if user.id not in {run.user_a_id, run.user_b_id}:
            raise ValidationError("Du bist nicht Teil dieser Challenge.")
        if run.has_confirmed(user):
            raise ValidationError("Du hast bereits bestätigt.")
        if user.id == run.user_a_id:
            run.confirmed_by_a = True
        else:
            run.confirmed_by_b = True

        participants = run.participants()
        confirmed_all = all(run.confirmation_for(participant) for participant in participants)
        if confirmed_all:
            run.completed_at = timezone.now()
        run.save(
            update_fields=[
                "confirmed_by_a",
                "confirmed_by_b",
                "completed_at",
                "updated_at",
            ]
        )
        _audit(
            "playbook.run.confirm",
            actor=user,
            target_type="playbook.challengerun",
            target_id=run.pk,
            completed=run.is_completed,
        )
        return run


def abort_run(*, run: ChallengeRun, user) -> ChallengeRun:
    _require_owner(run.clubroom, user)
    with transaction.atomic():
        run = ChallengeRun.objects.select_for_update().get(pk=run.pk)
        if not run.is_active:
            raise ValidationError("Diese Challenge ist bereits beendet.")
        if user.id not in {run.user_a_id, run.user_b_id}:
            raise ValidationError("Du bist nicht Teil dieser Challenge.")
        run.aborted_at = timezone.now()
        run.aborted_by = user
        run.save(update_fields=["aborted_at", "aborted_by", "updated_at"])
        _audit(
            "playbook.run.abort",
            actor=user,
            target_type="playbook.challengerun",
            target_id=run.pk,
        )
        return run
