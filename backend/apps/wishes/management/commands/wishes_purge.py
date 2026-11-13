from django.conf import settings
from django.core.management.base import BaseCommand

from apps.wishes.services import purge_rejected_wishes


class Command(BaseCommand):
    help = "Löscht Inhalte abgelehnter oder Grenz-Wünsche nach der Frist."

    def handle(self, *args, **options):
        days = getattr(settings, "WISH_RETENTION_DAYS", 90)
        count = purge_rejected_wishes(days=days)
        self.stdout.write(self.style.SUCCESS(f"Bereinigt: {count} Wünsche."))
