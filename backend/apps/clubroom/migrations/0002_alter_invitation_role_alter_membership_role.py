from django.db import migrations, models
from django.utils import timezone

MODULES = (
    "lounge",
    "roulette",
    "vitrine",
    "wishes",
    "playbook",
    "feed",
    "deep_talk",
    "points",
)
GUEST_PERMISSIONS = {module: module == "lounge" for module in MODULES}


def remove_sex_partner_role(apps, schema_editor):
    Membership = apps.get_model("clubroom", "Membership")
    Invitation = apps.get_model("clubroom", "Invitation")
    now = timezone.now()

    for membership in Membership.objects.filter(role="sex_partner"):
        membership.role = "guest"
        membership.module_permissions = GUEST_PERMISSIONS
        membership.save(update_fields=["role", "module_permissions", "updated_at"])

    for invitation in Invitation.objects.filter(role="sex_partner"):
        invitation.role = "guest"
        update_fields = ["role", "updated_at"]
        if invitation.accepted_at is None and invitation.revoked_at is None:
            invitation.revoked_at = now
            update_fields.append("revoked_at")
        invitation.save(update_fields=update_fields)


class Migration(migrations.Migration):
    dependencies = [
        ("clubroom", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(remove_sex_partner_role, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="invitation",
            name="role",
            field=models.CharField(
                choices=[
                    ("owner", "Hauptmitglied"),
                    ("moderator", "Moderator"),
                    ("advisor", "Berater"),
                    ("mediator", "Mediator"),
                    ("guest", "Gast/Beobachter"),
                ],
                max_length=32,
            ),
        ),
        migrations.AlterField(
            model_name="membership",
            name="role",
            field=models.CharField(
                choices=[
                    ("owner", "Hauptmitglied"),
                    ("moderator", "Moderator"),
                    ("advisor", "Berater"),
                    ("mediator", "Mediator"),
                    ("guest", "Gast/Beobachter"),
                ],
                max_length=32,
            ),
        ),
    ]
