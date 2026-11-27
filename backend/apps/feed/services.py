from django.db import transaction
from django.utils import timezone

from apps.feed.delivery import dispatch_notification
from apps.feed.models import (
    FeedEvent,
    Notification,
    notification_allowed,
    sanitize_metadata,
)


def record_event(
    *,
    clubroom,
    event_type: str,
    actor=None,
    target_type: str = "",
    target_id: str | int = "",
    metadata: dict | None = None,
    notify: bool = True,
) -> FeedEvent:
    event = FeedEvent.objects.create(
        clubroom=clubroom,
        event_type=event_type,
        actor=actor,
        target_type=target_type,
        target_id=str(target_id),
        metadata=sanitize_metadata(metadata),
    )
    if notify:
        notify_members(clubroom=clubroom, event_type=event_type, exclude_user=actor)
    return event


def notify_members(*, clubroom, event_type: str, exclude_user=None) -> int:
    now = timezone.now()
    notifications = []
    memberships = clubroom.memberships.filter(revoked_at__isnull=True).select_related("user")
    for membership in memberships:
        if exclude_user is not None and membership.user_id == exclude_user.id:
            continue
        if not notification_allowed(membership.user, clubroom, event_type, "inapp"):
            continue
        if not notification_allowed(membership.user, clubroom, event_type, "email"):
            # Externe Zustellung wird in delivery.py kanalweise geprüft;
            # die In-App-Zeile bleibt trotzdem erhalten.
            pass
        queued = membership.user.is_safe_mode_active
        notifications.append(
            Notification(
                user=membership.user,
                clubroom=clubroom,
                event_type=event_type,
                queued_during_safe_mode=queued,
                delivered_at=None if queued else now,
            )
        )
    created = Notification.objects.bulk_create(notifications)
    if created:
        transaction.on_commit(
            lambda: [dispatch_notification(notification) for notification in created]
        )
    return len(created)


def deliver_queued_notifications(user) -> int:
    delivered = 0
    with transaction.atomic():
        queued = list(
            Notification.objects.select_for_update().filter(user=user, delivered_at__isnull=True)
        )
        for notification in queued:
            notification.delivered_at = timezone.now()
            notification.save(update_fields=["delivered_at", "updated_at"])
            dispatch_notification(notification)
            delivered += 1
    return delivered


def delivered_notifications(user, limit: int = 10):
    return Notification.objects.filter(user=user, delivered_at__isnull=False).order_by(
        "-created_at", "-id"
    )[:limit]


def queued_notification_count(user) -> int:
    return Notification.objects.filter(user=user, delivered_at__isnull=True).count()
