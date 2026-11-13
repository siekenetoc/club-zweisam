from django.core.management.base import BaseCommand

from apps.roulette.services import purge_expired_answers


class Command(BaseCommand):
    help = "Löscht Geheimantworten nach Ablauf der Aufbewahrungsfrist und alte Nicht-Matches."

    def handle(self, *args, **options):
        result = purge_expired_answers()
        self.stdout.write(
            self.style.SUCCESS(
                "Bereinigt: "
                f"{result['cleared_answers']} Antworten, "
                f"{result['deleted_non_matches']} Nicht-Matches."
            )
        )
