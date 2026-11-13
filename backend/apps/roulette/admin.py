from django.contrib import admin

from apps.roulette.models import Deck, Question


@admin.register(Deck)
class DeckAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "intensity", "requires_opt_in")
    list_filter = ("requires_opt_in", "intensity")
    search_fields = ("code", "title")


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("deck", "order", "short_text", "answer_type")
    list_filter = ("deck", "answer_type")
    search_fields = ("text",)
    ordering = ("deck__code", "order")

    @admin.display(description="Frage")
    def short_text(self, obj):
        return obj.text[:80]
