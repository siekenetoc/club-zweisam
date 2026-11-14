from django.core.management.base import BaseCommand, CommandError

from apps.feed.delivery import send_via_channel
from apps.feed.models import NotificationChannel


class Command(BaseCommand):
    help = "Sendet eine inhaltslose Test-Push-Nachricht über einen Kanal."

    def add_arguments(self, parser):
        parser.add_argument("--channel", required=True, type=int)
        parser.add_argument("--destination", default="")

    def handle(self, *args, **options):
        channel = NotificationChannel.objects.filter(pk=options["channel"]).first()
        if channel is None:
            raise CommandError("Kanal nicht gefunden.")
        config = channel.get_config()
        destination = (
            options["destination"]
            or config.get("default_target", "")
            or (config.get("app_token", "") if channel.provider == "gotify" else "")
        )
        if send_via_channel(channel, destination):
            self.stdout.write(self.style.SUCCESS("Test-Push gesendet."))
        else:
            raise CommandError("Test-Push fehlgeschlagen. Konfiguration/Logs prüfen.")
