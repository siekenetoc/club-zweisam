from django.db import migrations

REWARDS = [
    (
        "romantisch",
        "Frühstück ans Bett",
        "Ein gemeinsames Frühstück, das die andere Person vorbereitet.",
        3,
        1,
    ),
    (
        "romantisch",
        "Picknick zu zweit",
        "Ein kleines Picknick, Zeit und Ort gemeinsam gewählt.",
        5,
        1,
    ),
    (
        "neckisch",
        "Tanzeinlage für dich",
        "Eine kurze, freiwillige Tanzeinlage nur für euch.",
        2,
        1,
    ),
    (
        "neckisch",
        "Massage nach Wahl",
        "Eine Massage nach Absprache, mit klarer Grenze.",
        4,
        2,
    ),
    (
        "erotisch",
        "Sinnliche Stunde nach Absprache",
        "Nur mit vorheriger Absprache, Safeword und jederzeitiger Rückzugsmöglichkeit.",
        8,
        2,
    ),
    (
        "erotisch",
        "Gemeinsames Bad",
        "Ein ruhiges Bad zu zweit, nur wenn beide mögen.",
        6,
        2,
    ),
    (
        "alltag",
        "Kleine Aufmerksamkeit",
        "Eine kleine Geste, die den Tag leichter macht.",
        1,
        1,
    ),
    (
        "alltag",
        "Ich übernehme deine Aufgabe",
        "Eine Alltagsaufgabe wird für die andere Person erledigt.",
        3,
        1,
    ),
    (
        "erlebnis",
        "Ausflug deiner Wahl",
        "Ein gemeinsamer Ausflug, Ziel von der einlösenden Person gewählt.",
        10,
        2,
    ),
    (
        "erlebnis",
        "Kinobesuch mit Überraschung",
        "Gemeinsam ins Kino, Film und kleine Überraschung inklusive.",
        6,
        1,
    ),
]


def seed_rewards(apps, schema_editor):
    Reward = apps.get_model("points", "Reward")
    for category, title, description, cost, consent_stage in REWARDS:
        Reward.objects.get_or_create(
            category=category,
            title=title,
            defaults={
                "description": description,
                "cost": cost,
                "consent_stage": consent_stage,
            },
        )


def unseed_rewards(apps, schema_editor):
    Reward = apps.get_model("points", "Reward")
    Reward.objects.filter(title__in=[reward[1] for reward in REWARDS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("points", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_rewards, unseed_rewards),
    ]
