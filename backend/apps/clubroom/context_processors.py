from apps.clubroom.services import active_membership_for
from apps.core.permissions import is_platform_admin
from apps.messaging.models import Message


def navigation(request):
    if not request.user.is_authenticated:
        return {"nav_membership": None, "nav_modules": {}}
    if request.user.is_staff:
        return {
            "nav_membership": None,
            "nav_modules": {},
            "nav_admin_account": True,
        }
    membership = active_membership_for(request.user)
    unread_messages = 0
    if membership is not None and membership.has_module_access("messages"):
        unread_messages = (
            Message.objects.filter(
                clubroom=membership.clubroom,
                deleted_at__isnull=True,
                read_at__isnull=True,
            )
            .exclude(sender=request.user)
            .count()
        )
    return {
        "nav_membership": membership,
        "nav_modules": (
            membership.effective_module_permissions() if membership is not None else {}
        ),
        "nav_unread_messages": unread_messages,
        "nav_is_platform_admin": is_platform_admin(request.user),
    }
