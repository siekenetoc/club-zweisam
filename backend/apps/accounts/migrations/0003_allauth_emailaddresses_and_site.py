from django.db import migrations

PLATFORM_DOMAIN = "club-zweisam.localhost"


def backfill_allauth(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    EmailAddress = apps.get_model("account", "EmailAddress")
    Site = apps.get_model("sites", "Site")
    Site.objects.update_or_create(
        pk=1,
        defaults={"domain": PLATFORM_DOMAIN, "name": "Club Zweisam"},
    )
    for user in User.objects.exclude(email=""):
        EmailAddress.objects.get_or_create(
            user=user,
            email=user.email.lower(),
            defaults={"verified": True, "primary": True},
        )


def unbackfill(apps, schema_editor):
    EmailAddress = apps.get_model("account", "EmailAddress")
    EmailAddress.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_user_unique_user_email_ci"),
        ("account", "0009_emailaddress_unique_primary_email"),
        ("sites", "0002_alter_domain_unique"),
    ]

    operations = [
        migrations.RunPython(backfill_allauth, unbackfill),
    ]
