from django.contrib import admin

from apps.points.models import Reward


@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "cost", "consent_stage")
    list_filter = ("category", "consent_stage")
    search_fields = ("title", "description")
