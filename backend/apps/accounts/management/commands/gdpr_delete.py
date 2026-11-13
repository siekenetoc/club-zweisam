from django.core.management.base import BaseCommand, CommandError

from apps.accounts.gdpr import delete_user_data
from apps.accounts.models import User


class Command(BaseCommand):
    help = "Anonymisiert ein Nutzerkonto und entfernt personenbezogene Inhalte."

    def add_arguments(self, parser):
        parser.add_argument("--user", required=True, help="Username oder ID")
        parser.add_argument("--confirm", action="store_true", help="Löschung bestätigen")

    def handle(self, *args, **options):
        if not options["confirm"]:
            raise CommandError("Löschung erfordert --confirm.")
        identifier = options["user"]
        user = (
            User.objects.filter(pk=identifier).first()
            if str(identifier).isdigit()
            else User.objects.filter(username=identifier).first()
        )
        if user is None:
            raise CommandError("Nutzer nicht gefunden.")
        result = delete_user_data(user)
        self.stdout.write(
            self.style.SUCCESS(f"Nutzer {result['user_id']} anonymisiert und Inhalte gelöscht.")
        )
