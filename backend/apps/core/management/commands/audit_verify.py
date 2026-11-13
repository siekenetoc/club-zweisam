from django.core.management.base import BaseCommand, CommandError

from apps.core.audit import AuditEntry


class Command(BaseCommand):
    help = "Prüft die Hash-Chain des Audit-Logs."

    def handle(self, *args, **options):
        ok, broken_pk, reason = AuditEntry.verify_chain()
        if ok:
            self.stdout.write(self.style.SUCCESS("Audit-Chain unversehrt."))
            return
        raise CommandError(f"Audit-Chain defekt bei Eintrag {broken_pk} ({reason}).")
