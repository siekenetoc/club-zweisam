from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Sendet eine Test-E-Mail über den konfigurierten SMTP-Server."

    def add_arguments(self, parser):
        parser.add_argument("--to", required=True, help="Empfängeradresse")

    def handle(self, *args, **options):
        recipient = options["to"]
        try:
            sent = send_mail(
                "Club Zweisam – SMTP-Test",
                "Diese E-Mail bestätigt die SMTP-Konfiguration von Club Zweisam.",
                settings.DEFAULT_FROM_EMAIL,
                [recipient],
                fail_silently=False,
            )
        except Exception as exc:
            raise CommandError(
                f"SMTP-Versand fehlgeschlagen: {exc.__class__.__name__}: {exc}"
            ) from exc
        if sent != 1:
            raise CommandError("SMTP-Versand hat keine Nachricht zugestellt.")
        self.stdout.write(
            self.style.SUCCESS(
                f"Test-E-Mail an {recipient} gesendet. Absender: " f"{settings.DEFAULT_FROM_EMAIL}"
            )
        )
