from django.contrib import admin

from apps.admin_panel.models import BreakGlassRequest
from apps.core.audit import AuditEntry


@admin.register(AuditEntry)
class AuditEntryAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "target_type", "target_id")
    list_filter = ("action",)
    search_fields = ("action", "target_type", "target_id", "actor__username")
    readonly_fields = (
        "actor",
        "action",
        "target_type",
        "target_id",
        "reason",
        "metadata",
        "created_at",
        "prev_hash",
        "hash",
    )
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BreakGlassRequest)
class BreakGlassRequestAdmin(admin.ModelAdmin):
    list_display = (
        "requested_by",
        "target_type",
        "target_id",
        "status",
        "created_at",
    )
    readonly_fields = (
        "requested_by",
        "approved_by",
        "target_type",
        "target_id",
        "reason",
        "approved_at",
        "expires_at",
        "used_at",
        "users_notified",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
