from rest_framework.permissions import BasePermission

from apps.clubroom.models import Membership


class ClubroomMember(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated or request.user.is_staff:
            return False
        return Membership.objects.filter(
            user=request.user,
            revoked_at__isnull=True,
            clubroom__deleted_at__isnull=True,
        ).exists()

    def membership(self, request):
        return (
            Membership.objects.filter(
                user=request.user,
                revoked_at__isnull=True,
                clubroom__deleted_at__isnull=True,
            )
            .select_related("clubroom")
            .first()
        )
