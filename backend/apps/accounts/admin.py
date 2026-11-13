from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.accounts.models import User


@admin.register(User)
class ClubUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (
            "Club Zweisam",
            {
                "fields": (
                    "is_safe_mode_active",
                    "age_verified",
                    "tos_accepted_at",
                )
            },
        ),
    )
    list_display = ("username", "email", "is_staff", "is_safe_mode_active", "age_verified")
