from apps.clubroom.services import active_membership_for
from apps.core.permissions import is_platform_admin


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
    return {
        "nav_membership": membership,
        "nav_modules": (membership.module_permissions if membership is not None else {}),
        "nav_is_platform_admin": is_platform_admin(request.user),
    }
