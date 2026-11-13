from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count

from apps.clubroom.models import Membership
from apps.feed.models import EVENT_CHECKIN_CREATED
from apps.feed.services import deliver_queued_notifications, record_event
from apps.lounge.models import CheckIn, WeeklyReviewOptIn, today


def _require_lounge_member(clubroom, user, write: bool = False) -> Membership:
    membership = Membership.objects.filter(
        clubroom=clubroom, user=user, revoked_at__isnull=True
    ).first()
    if membership is None or not membership.has_module_access("lounge"):
        raise ValidationError("Kein Zugriff auf die Lounge.")
    if write and not membership.can_write_module("lounge"):
        raise ValidationError("Lesender Zugriff – kein Check-in möglich.")
    return membership


def create_check_in(*, clubroom, user, mood: int, energy: int, closeness: int) -> CheckIn:
    _require_lounge_member(clubroom, user, write=True)
    if any(value not in range(1, 6) for value in (mood, energy, closeness)):
        raise ValidationError("Alle Werte müssen zwischen 1 und 5 liegen.")
    try:
        with transaction.atomic():
            check_in = CheckIn.objects.create(
                clubroom=clubroom,
                user=user,
                date=today(),
                mood=mood,
                energy=energy,
                closeness=closeness,
            )
            record_event(
                clubroom=clubroom,
                event_type=EVENT_CHECKIN_CREATED,
                actor=user,
                target_type="lounge.checkin",
                target_id=check_in.pk,
            )
            return check_in
    except IntegrityError as exc:
        raise ValidationError("Für heute liegt bereits ein Check-in vor.") from exc


def barometer(clubroom, days: int = 3):
    start = today() - timedelta(days=days - 1)
    check_ins = CheckIn.objects.filter(clubroom=clubroom, date__gte=start)
    overall = check_ins.aggregate(
        mood=Avg("mood"), energy=Avg("energy"), closeness=Avg("closeness")
    )
    per_user = (
        check_ins.values("user_id", "user__username")
        .annotate(
            mood=Avg("mood"),
            energy=Avg("energy"),
            closeness=Avg("closeness"),
            count=Count("id"),
        )
        .order_by("user__username")
    )
    return {
        "start": start,
        "end": today(),
        "overall": overall,
        "per_user": list(per_user),
    }


def weekly_review(clubroom, user, days: int = 7):
    start = today() - timedelta(days=days - 1)
    check_ins = CheckIn.objects.filter(clubroom=clubroom, user=user, date__gte=start)
    return {
        "start": start,
        "end": today(),
        "count": check_ins.count(),
        "averages": check_ins.aggregate(
            mood=Avg("mood"), energy=Avg("energy"), closeness=Avg("closeness")
        ),
    }


def toggle_weekly_review(*, clubroom, user) -> bool:
    _require_lounge_member(clubroom, user, write=True)
    opt_in, created = WeeklyReviewOptIn.objects.get_or_create(clubroom=clubroom, user=user)
    if not created:
        opt_in.delete()
        return False
    return True


def has_weekly_review(clubroom, user) -> bool:
    return WeeklyReviewOptIn.objects.filter(clubroom=clubroom, user=user).exists()


def set_safe_mode(*, user, active: bool) -> int:
    user.is_safe_mode_active = active
    user.save(update_fields=["is_safe_mode_active"])
    if not active:
        return deliver_queued_notifications(user)
    return 0


def check_in_today(clubroom, user):
    return CheckIn.objects.filter(clubroom=clubroom, user=user, date=today()).first()


def recent_notifications(user, limit: int = 10):
    from apps.feed.services import delivered_notifications

    return delivered_notifications(user, limit)


def queued_count(user) -> int:
    from apps.feed.services import queued_notification_count

    return queued_notification_count(user)
