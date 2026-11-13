import json

from django.core.management.base import BaseCommand, CommandError
from django.core.serializers.json import DjangoJSONEncoder

from apps.accounts.gdpr import export_user_data
from apps.accounts.models import User


class Command(BaseCommand):
    help = "Exportiert die personenbezogenen Daten eines Nutzers als JSON."

    def add_arguments(self, parser):
        parser.add_argument("--user", required=True, help="Username oder ID")
        parser.add_argument("--output", default="", help="Zieldatei (optional)")

    def handle(self, *args, **options):
        identifier = options["user"]
        user = (
            User.objects.filter(pk=identifier).first()
            if str(identifier).isdigit()
            else User.objects.filter(username=identifier).first()
        )
        if user is None:
            raise CommandError("Nutzer nicht gefunden.")
        payload = json.dumps(
            export_user_data(user), cls=DjangoJSONEncoder, ensure_ascii=False, indent=2
        )
        if options["output"]:
            with open(options["output"], "w", encoding="utf-8") as handle:
                handle.write(payload)
            self.stdout.write(self.style.SUCCESS(f"Export geschrieben: {options['output']}"))
        else:
            self.stdout.write(payload)
