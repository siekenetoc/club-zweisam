from django.contrib import admin

from apps.clubroom.models import Clubroom, Invitation, Membership


@admin.register(Clubroom)
class ClubroomAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_by", "created_at")
    search_fields = ("name", "slug", "created_by__username")
    exclude = ("safe_word",)
    readonly_fields = ("created_at", "updated_at")

    def has_add_permission(self, request):
        return False


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "clubroom", "role", "revoked_at", "created_at")
    list_filter = ("role", "revoked_at")
    search_fields = ("user__username", "clubroom__name")
    readonly_fields = (
        "clubroom",
        "user",
        "role",
        "module_permissions",
        "invited_by",
        "invited_at",
        "accepted_at",
        "revoked_at",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("email", "clubroom", "role", "expires_at", "accepted_at", "revoked_at")
    list_filter = ("role",)
    search_fields = ("email", "clubroom__name")
    exclude = ("token_hash",)
    readonly_fields = (
        "clubroom",
        "email",
        "role",
        "invited_by",
        "expires_at",
        "accepted_at",
        "revoked_at",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
