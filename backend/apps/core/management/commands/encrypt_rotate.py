from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.clubroom.models import Clubroom
from apps.core.audit import AuditEntry
from apps.feed.models import (
    NotificationChannel,
    NotificationSubscription,
    PersonalNotificationChannel,
)
from apps.roulette.models import SecretAnswer
from apps.wishes.models import Wish, WishResponse

TARGETS = (
    (Clubroom, "safe_word"),
    (SecretAnswer, "answer"),
    (Wish, "body"),
    (WishResponse, "note"),
    (NotificationChannel, "config"),
    (NotificationSubscription, "destination"),
    (PersonalNotificationChannel, "config"),
)


class Command(BaseCommand):
    help = "Verschlüsselt sensible Felder mit dem aktuellen Schlüssel neu."

    def handle(self, *args, **options):
        if not getattr(settings, "FIELD_ENCRYPTION_KEY_OLD", ""):
            raise CommandError(
                "FIELD_ENCRYPTION_KEY_OLD muss gesetzt sein, damit der alte "
                "Schlüssel gelesen werden kann."
            )
        rotated = 0
        with transaction.atomic():
            for model, field_name in TARGETS:
                for obj in model.objects.only("pk", field_name).iterator():
                    value = getattr(obj, field_name)
                    if not value:
                        continue
                    setattr(obj, field_name, value)
                    obj.save(update_fields=[field_name])
                    rotated += 1
            AuditEntry.objects.create(
                actor=None,
                action="crypto.rotate",
                target_type="core.encryption",
                target_id="field-encryption",
                metadata={"rotated_fields": rotated},
            )
        self.stdout.write(self.style.SUCCESS(f"Rotation abgeschlossen: {rotated} Felder."))
