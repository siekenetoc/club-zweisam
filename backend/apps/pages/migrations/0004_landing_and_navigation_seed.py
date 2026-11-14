from django.db import migrations

SECTIONS = [
    (
        "Diskretion",
        "Feldverschlüsselung at-rest, Audit-Log append-only.",
        "",
        "",
        1,
    ),
    (
        "Freiwilligkeit",
        "Safeword, Grenzen und Opt-in statt Druck.",
        "",
        "",
        2,
    ),
    (
        "Rollen",
        "Hauptmitglieder, Moderator, Berater, Mediator, Gast.",
        "",
        "",
        3,
    ),
    (
        "Grenze",
        "Kein Therapieersatz, keine Währung für Sex.",
        "",
        "",
        4,
    ),
]

FOOTER = [
    ("AGB", "/seite/agb/"),
    ("Impressum", "/seite/impressum/"),
    ("Datenschutz", "/seite/datenschutz/"),
    ("Partner", "/seite/partner/"),
    ("Disclaimer", "/seite/disclaimer/"),
]


def seed_landing(apps, schema_editor):
    LandingSettings = apps.get_model("pages", "LandingSettings")
    LandingSection = apps.get_model("pages", "LandingSection")
    NavigationItem = apps.get_model("pages", "NavigationItem")

    LandingSettings.objects.get_or_create(
        pk=1,
        defaults={
            "hero_kicker": "Privater Raum für zwei",
            "hero_title": "Der Raum steht.",
            "hero_text": (
                "Club Zweisam ist ein geschützter Kommunikations- und Spielraum "
                "für Paare. Consent vor Spiel, Nein ist neutral, Geheimnis schützt."
            ),
            "primary_cta_label": "Clubraum gründen",
            "primary_cta_url": "/clubraum/neu/",
            "secondary_cta_label": "Anmelden",
            "secondary_cta_url": "/anmelden/",
        },
    )
    for title, body, link_label, link_url, order in SECTIONS:
        LandingSection.objects.get_or_create(
            title=title,
            defaults={
                "body_html": body,
                "link_label": link_label,
                "link_url": link_url,
                "order": order,
                "is_active": True,
            },
        )
    for order, (label, url) in enumerate(FOOTER, start=1):
        NavigationItem.objects.get_or_create(
            label=label,
            location="footer",
            defaults={"url": url, "order": order, "is_active": True},
        )


def unseed_landing(apps, schema_editor):
    LandingSettings = apps.get_model("pages", "LandingSettings")
    LandingSection = apps.get_model("pages", "LandingSection")
    NavigationItem = apps.get_model("pages", "NavigationItem")
    LandingSettings.objects.filter(pk=1).delete()
    LandingSection.objects.filter(title__in=[item[0] for item in SECTIONS]).delete()
    NavigationItem.objects.filter(label__in=[item[0] for item in FOOTER]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("pages", "0003_landingsection_landingsettings_navigationitem"),
    ]

    operations = [
        migrations.RunPython(seed_landing, unseed_landing),
    ]
