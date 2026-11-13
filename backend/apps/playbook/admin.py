from django.contrib import admin

from apps.playbook.models import Challenge


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "intensity", "consent_stage", "duration_min", "points")
    list_filter = ("category", "consent_stage")
    search_fields = ("title", "description")
