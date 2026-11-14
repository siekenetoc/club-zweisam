from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils import timezone

from apps.admin_panel.models import BreakGlassRequest
from apps.clubroom.models import Membership
from apps.core.audit import AuditEntry
from apps.feed.models import Notification, NotificationSubscription
from apps.lounge.models import CheckIn, WeeklyReviewOptIn
from apps.playbook.models import PlaybookOptIn
from apps.points.models import Ledger, Redemption
from apps.roulette.models import DeckOptIn
from apps.wishes.models import Wish, WishResponse


def export_user_data(user) -> dict:
    memberships = user.memberships.select_related("clubroom").all()
    wishes = Wish.objects.filter(created_by=user).select_related("clubroom")
    responses = WishResponse.objects.filter(responded_by=user).select_related("wish")
    check_ins = CheckIn.objects.filter(user=user).select_related("clubroom")
    ledgers = Ledger.objects.filter(owner=user).prefetch_related("entries")
    redemptions = Redemption.objects.filter(requested_by=user).select_related("reward")
    accepted = Redemption.objects.filter(accepted_by=user).select_related("reward")
    notifications = Notification.objects.filter(user=user)
    audit = AuditEntry.objects.filter(actor=user)
    break_glass = BreakGlassRequest.objects.filter(requested_by=user)
    subscriptions = NotificationSubscription.objects.filter(user=user).select_related("channel")

    return {
        "account": {
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "date_joined": user.date_joined,
            "last_login": user.last_login,
            "age_verified": user.age_verified,
            "tos_accepted_at": user.tos_accepted_at,
        },
        "memberships": [
            {
                "clubroom": membership.clubroom.name,
                "slug": membership.clubroom.slug,
                "role": membership.role,
                "accepted_at": membership.accepted_at,
                "revoked_at": membership.revoked_at,
            }
            for membership in memberships
        ],
        "wishes_created": [
            {
                "clubroom": wish.clubroom.name,
                "type": wish.type,
                "category": wish.category,
                "intensity": wish.intensity,
                "timeframe": wish.timeframe,
                "title": wish.title,
                "body": wish.body,
                "is_private": wish.is_private,
                "status": wish.status,
                "created_at": wish.created_at,
                "updated_at": wish.updated_at,
            }
            for wish in wishes
        ],
        "wish_responses": [
            {
                "wish_id": response.wish_id,
                "wish_type": response.wish.type,
                "action": response.action,
                "note": response.note,
                "created_at": response.created_at,
            }
            for response in responses
        ],
        "check_ins": [
            {
                "clubroom": check_in.clubroom.name,
                "date": check_in.date,
                "mood": check_in.mood,
                "energy": check_in.energy,
                "closeness": check_in.closeness,
            }
            for check_in in check_ins
        ],
        "ledgers": [
            {
                "clubroom": ledger.clubroom.name,
                "scope": ledger.scope,
                "balance": ledger.balance,
                "entries": [
                    {
                        "delta": entry.delta,
                        "reason": entry.reason,
                        "created_at": entry.created_at,
                    }
                    for entry in ledger.entries.all()
                ],
            }
            for ledger in ledgers
        ],
        "redemptions_requested": [
            {
                "reward": redemption.reward.title,
                "cost": redemption.reward.cost,
                "status": redemption.status,
                "created_at": redemption.created_at,
                "completed_at": redemption.completed_at,
            }
            for redemption in redemptions
        ],
        "redemptions_accepted": [
            {
                "reward": redemption.reward.title,
                "cost": redemption.reward.cost,
                "status": redemption.status,
            }
            for redemption in accepted
        ],
        "notifications": [
            {
                "event_type": notification.event_type,
                "created_at": notification.created_at,
                "delivered_at": notification.delivered_at,
            }
            for notification in notifications
        ],
        "audit_entries": [
            {
                "action": entry.action,
                "target_type": entry.target_type,
                "target_id": entry.target_id,
                "created_at": entry.created_at,
            }
            for entry in audit
        ],
        "push_subscriptions": [
            {
                "channel": subscription.channel.label,
                "provider": subscription.channel.provider,
                "destination": subscription.destination,
                "enabled": subscription.is_enabled,
            }
            for subscription in subscriptions
        ],
        "break_glass_requests": [
            {
                "target_type": request.target_type,
                "target_id": request.target_id,
                "reason": request.reason,
                "created_at": request.created_at,
            }
            for request in break_glass
        ],
    }


@transaction.atomic
def delete_user_data(user) -> dict:
    user_id = user.pk
    now = timezone.now()

    Membership.objects.filter(user=user, revoked_at__isnull=True).update(
        revoked_at=now, updated_at=now
    )
    CheckIn.objects.filter(user=user).delete()
    WishResponse.objects.filter(responded_by=user).update(note="")
    Wish.objects.filter(created_by=user).update(title="Gelöschter Wunsch", body="", updated_at=now)
    Notification.objects.filter(user=user).delete()
    NotificationSubscription.objects.filter(user=user).delete()
    Ledger.objects.filter(owner=user).delete()
    Redemption.objects.filter(requested_by=user).delete()
    DeckOptIn.objects.filter(user=user).delete()
    PlaybookOptIn.objects.filter(user=user).delete()
    WeeklyReviewOptIn.objects.filter(user=user).delete()

    user.username = f"deleted-{user_id}"
    user.email = f"deleted-{user_id}@invalid"
    user.first_name = ""
    user.last_name = ""
    user.password = make_password(None)
    user.is_active = False
    user.is_staff = False
    user.is_superuser = False
    user.age_verified = False
    user.tos_accepted_at = None
    user.is_safe_mode_active = False
    user.last_login = None
    user.save()

    AuditEntry.objects.create(
        actor=None,
        action="gdpr.delete",
        target_type="accounts.user",
        target_id=str(user_id),
        metadata={"anonymized": True},
    )
    return {
        "user_id": user_id,
        "memberships_revoked": True,
        "wishes_redacted": True,
        "check_ins_deleted": True,
    }
