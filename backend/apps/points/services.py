from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.clubroom.models import Membership
from apps.clubroom.permissions import OWNER
from apps.points.models import (
    REASON_CHALLENGE,
    REASON_RECOGNITION,
    REASON_REDEEM,
    REASON_REFUND,
    REDEMPTION_ACCEPTED,
    REDEMPTION_CANCELLED,
    REDEMPTION_COMPLETED,
    REDEMPTION_DECLINED,
    REDEMPTION_REFUNDED,
    REDEMPTION_REQUESTED,
    SCOPE_DYAD,
    SCOPE_GUEST,
    Entry,
    Ledger,
    Redemption,
    Reward,
)


def _require_owner(clubroom, user, module: str = "points") -> Membership:
    membership = Membership.objects.filter(
        clubroom=clubroom, user=user, revoked_at__isnull=True
    ).first()
    if membership is None or membership.role != OWNER:
        raise ValidationError("Nur Hauptmitglieder verwalten Punkte.")
    if not membership.has_module_access(module):
        raise ValidationError("Kein Zugriff auf Punkte.")
    return membership


def scope_for_user(clubroom, user) -> str:
    membership = Membership.objects.filter(
        clubroom=clubroom, user=user, revoked_at__isnull=True
    ).first()
    if membership is not None and membership.role == OWNER:
        return SCOPE_DYAD
    return SCOPE_GUEST


def get_or_create_ledger(clubroom, user) -> Ledger:
    return Ledger.objects.get_or_create(
        clubroom=clubroom,
        owner=user,
        defaults={"scope": scope_for_user(clubroom, user)},
    )[0]


def earned_today(ledger: Ledger, challenge_only: bool = False) -> int:
    entries = Entry.objects.filter(
        ledger=ledger,
        created_at__date=timezone.localdate(),
        delta__gt=0,
    )
    if challenge_only:
        entries = entries.filter(reason=REASON_CHALLENGE)
    return sum(entry.delta for entry in entries)


def daily_cap() -> int:
    return getattr(settings, "POINTS_DAILY_CAP", 10)


def challenge_daily_cap() -> int:
    return getattr(settings, "POINTS_CHALLENGE_DAILY_CAP", 3)


def _record_entry(
    *,
    ledger: Ledger,
    delta: int,
    reason: str,
    actor=None,
    confirmed_by_other: bool = False,
) -> Entry:
    with transaction.atomic():
        ledger = Ledger.objects.select_for_update().get(pk=ledger.pk)
        if delta < 0 and ledger.balance + delta < 0:
            raise ValidationError("Nicht genügend Punkte.")
        entry = Entry.objects.create(
            ledger=ledger,
            delta=delta,
            reason=reason,
            actor=actor,
            confirmed_by_other=confirmed_by_other,
        )
        ledger.balance = ledger.balance + delta
        ledger.save(update_fields=["balance", "updated_at"])
        return entry


def award_points(
    *,
    clubroom,
    user,
    amount: int,
    reason: str,
    actor=None,
    confirmed_by_other: bool = True,
    challenge: bool = False,
):
    if amount <= 0:
        raise ValidationError("Punkte müssen positiv sein.")
    with transaction.atomic():
        ledger = get_or_create_ledger(clubroom, user)
        ledger = Ledger.objects.select_for_update().get(pk=ledger.pk)
        if ledger.scope != SCOPE_DYAD:
            raise ValidationError("Gast-Ledger sind isoliert und erhalten keine Dyaden-Punkte.")
        remaining = daily_cap() - earned_today(ledger)
        if challenge:
            remaining = min(
                remaining,
                challenge_daily_cap() - earned_today(ledger, challenge_only=True),
            )
        amount = min(amount, remaining)
        if amount <= 0:
            return None
        return _record_entry(
            ledger=ledger,
            delta=amount,
            reason=reason,
            actor=actor,
            confirmed_by_other=confirmed_by_other,
        )


def grant_recognition(*, clubroom, guest_user, actor, amount: int = 1) -> Entry:
    _require_owner(clubroom, actor)
    membership = Membership.objects.filter(
        clubroom=clubroom, user=guest_user, revoked_at__isnull=True
    ).first()
    if membership is None or membership.role == OWNER:
        raise ValidationError("Anerkennung ist nur für Gäste möglich.")
    if amount not in (1, 2, 3):
        raise ValidationError("Anerkennung zwischen 1 und 3 Punkten.")
    ledger = get_or_create_ledger(clubroom, guest_user)
    if ledger.scope != SCOPE_GUEST:
        raise ValidationError("Kein Gast-Ledger.")
    return _record_entry(
        ledger=ledger,
        delta=amount,
        reason=REASON_RECOGNITION,
        actor=actor,
    )


def guest_ledgers(clubroom):
    return (
        Ledger.objects.filter(clubroom=clubroom, scope=SCOPE_GUEST)
        .select_related("owner")
        .order_by("owner__username")
    )


def request_redemption(*, clubroom, user, reward: Reward) -> Redemption:
    _require_owner(clubroom, user)
    ledger = get_or_create_ledger(clubroom, user)
    if ledger.balance < reward.cost:
        raise ValidationError("Nicht genügend Punkte für diese Belohnung.")
    return Redemption.objects.create(
        clubroom=clubroom,
        reward=reward,
        requested_by=user,
        status=REDEMPTION_REQUESTED,
    )


def accept_redemption(*, redemption: Redemption, user) -> Redemption:
    _require_owner(redemption.clubroom, user)
    with transaction.atomic():
        redemption = Redemption.objects.select_for_update().get(pk=redemption.pk)
        if redemption.status != REDEMPTION_REQUESTED:
            raise ValidationError("Diese Einlösung ist nicht mehr offen.")
        if redemption.requested_by_id == user.id:
            raise ValidationError("Die Annahme muss von der anderen Person kommen.")
        ledger = get_or_create_ledger(redemption.clubroom, redemption.requested_by)
        if ledger.balance < redemption.reward.cost:
            raise ValidationError("Nicht genügend Punkte für diese Belohnung.")
        _record_entry(
            ledger=ledger,
            delta=-redemption.reward.cost,
            reason=REASON_REDEEM,
            actor=user,
            confirmed_by_other=True,
        )
        redemption.status = REDEMPTION_ACCEPTED
        redemption.accepted_by = user
        redemption.save(update_fields=["status", "accepted_by", "updated_at"])
        return redemption


def decline_redemption(*, redemption: Redemption, user) -> Redemption:
    _require_owner(redemption.clubroom, user)
    with transaction.atomic():
        redemption = Redemption.objects.select_for_update().get(pk=redemption.pk)
        if redemption.status != REDEMPTION_REQUESTED:
            raise ValidationError("Diese Einlösung ist nicht mehr offen.")
        if redemption.requested_by_id == user.id:
            raise ValidationError("Ablehnung durch die andere Person.")
        redemption.status = REDEMPTION_DECLINED
        redemption.accepted_by = user
        redemption.save(update_fields=["status", "accepted_by", "updated_at"])
        return redemption


def cancel_redemption(*, redemption: Redemption, user) -> Redemption:
    _require_owner(redemption.clubroom, user)
    with transaction.atomic():
        redemption = Redemption.objects.select_for_update().get(pk=redemption.pk)
        if redemption.status != REDEMPTION_REQUESTED:
            raise ValidationError("Nur offene Anfragen können zurückgezogen werden.")
        if redemption.requested_by_id != user.id:
            raise ValidationError("Nur die anfragende Person kann zurückziehen.")
        redemption.status = REDEMPTION_CANCELLED
        redemption.save(update_fields=["status", "updated_at"])
        return redemption


def complete_redemption(*, redemption: Redemption, user) -> Redemption:
    _require_owner(redemption.clubroom, user)
    if not redemption.is_participant(user):
        raise ValidationError("Nur Beteiligte können abschließen.")
    with transaction.atomic():
        redemption = Redemption.objects.select_for_update().get(pk=redemption.pk)
        if redemption.status != REDEMPTION_ACCEPTED:
            raise ValidationError("Diese Einlösung ist nicht angenommen.")
        redemption.status = REDEMPTION_COMPLETED
        redemption.completed_at = timezone.now()
        redemption.save(update_fields=["status", "completed_at", "updated_at"])
        return redemption


def request_refund(*, redemption: Redemption, user) -> Redemption:
    _require_owner(redemption.clubroom, user)
    if not redemption.is_participant(user):
        raise ValidationError("Nur Beteiligte können eine Rückbuchung anfragen.")
    with transaction.atomic():
        redemption = Redemption.objects.select_for_update().get(pk=redemption.pk)
        if redemption.status not in {REDEMPTION_ACCEPTED, REDEMPTION_COMPLETED}:
            raise ValidationError("Rückbuchung ist nur nach Annahme möglich.")
        if redemption.refund_requested_at is not None:
            raise ValidationError("Es liegt bereits eine Rückbuchungsanfrage vor.")
        redemption.refund_requested_by = user
        redemption.refund_requested_at = timezone.now()
        redemption.save(
            update_fields=[
                "refund_requested_by",
                "refund_requested_at",
                "updated_at",
            ]
        )
        return redemption


def confirm_refund(*, redemption: Redemption, user) -> Redemption:
    _require_owner(redemption.clubroom, user)
    with transaction.atomic():
        redemption = (
            Redemption.objects.select_for_update().select_related("reward").get(pk=redemption.pk)
        )
        if redemption.refund_requested_at is None or redemption.refunded_at is not None:
            raise ValidationError("Keine offene Rückbuchung.")
        if not redemption.is_participant(user):
            raise ValidationError("Nur Beteiligte können bestätigen.")
        if redemption.refund_requested_by_id == user.id:
            raise ValidationError("Rückbuchung erfordert die zweite Person.")
        ledger = get_or_create_ledger(redemption.clubroom, redemption.requested_by)
        _record_entry(
            ledger=ledger,
            delta=redemption.reward.cost,
            reason=REASON_REFUND,
            actor=user,
            confirmed_by_other=True,
        )
        redemption.status = REDEMPTION_REFUNDED
        redemption.refund_confirmed_by = user
        redemption.refunded_at = timezone.now()
        redemption.save(
            update_fields=[
                "status",
                "refund_confirmed_by",
                "refunded_at",
                "updated_at",
            ]
        )
        return redemption


def dyad_ledgers(clubroom):
    return (
        Ledger.objects.filter(clubroom=clubroom, scope=SCOPE_DYAD)
        .select_related("owner")
        .order_by("owner__username")
    )
