from django.db import migrations

CHALLENGES = [
    (
        "alltag",
        "Zehn Minuten ohne Handy",
        "Legt beide die Geräte weg und seid zehn Minuten nur füreinander da.",
        10,
        1,
        1,
        1,
    ),
    (
        "alltag",
        "Kleine Alltagsaufgabe gemeinsam",
        "Erledigt eine Aufgabe zusammen, die sonst allein bleibt. Kein Wettkampf.",
        15,
        1,
        1,
        1,
    ),
    (
        "naehe",
        "Drei Minuten umarmen",
        "Eine stille Umarmung ohne Ziel. Jederzeit abbrechbar.",
        3,
        1,
        1,
        1,
    ),
    (
        "naehe",
        "Hand in Hand spazieren",
        "Zwanzig Minuten gemeinsam gehen, ohne To-do-Liste.",
        20,
        2,
        2,
        1,
    ),
    (
        "neugier",
        "Eine neue Frage",
        "Stellt euch gegenseitig eine Frage, die ihr noch nie gestellt habt.",
        10,
        2,
        2,
        1,
    ),
    (
        "neugier",
        "Drei geschätzte Dinge",
        "Schreibt je drei Dinge auf, die ihr am anderen schätzt, und lest sie euch vor.",
        10,
        1,
        1,
        1,
    ),
    (
        "spiel",
        "Würfel entscheidet",
        "Eine Runde Würfel entscheidet, wer den nächsten gemeinsamen Abend plant.",
        5,
        1,
        1,
        1,
    ),
    (
        "spiel",
        "Gemeinsame Playlist",
        "Baut zusammen eine Playlist für einen Abend, den ihr noch vor euch habt.",
        15,
        1,
        1,
        1,
    ),
    (
        "kommunikation",
        "Zehn Minuten nur zuhören",
        "Eine Person spricht, die andere hört zu und unterbricht nicht. Danach wechseln.",
        10,
        2,
        2,
        1,
    ),
    (
        "kommunikation",
        "Unausgesprochenes ansprechen",
        "Ein Thema ansprechen, das ihr beide kennt, aber selten benennt. Vorher Safeword vereinbaren.",
        20,
        3,
        3,
        2,
    ),
    (
        "abenteuer",
        "Neuer Ort in der Nähe",
        "Erkundet einen Ort, an dem ihr noch nicht wart. Dauer und Ziel gemeinsam festlegen.",
        60,
        2,
        2,
        2,
    ),
    (
        "abenteuer",
        "Kleine Überraschung planen",
        "Plant eine kleine, alltagstaugliche Überraschung für die andere Person.",
        30,
        2,
        2,
        1,
    ),
    (
        "erholung",
        "Bildschirmfreie Pause",
        "Zwanzig Minuten ohne Bildschirm. Tee, Musik oder Stille – was euch gut tut.",
        20,
        1,
        1,
        1,
    ),
    (
        "erholung",
        "Ruhige Stunde",
        "Eine Stunde ohne Anforderungen. Jede Person darf tun, was ihr guttut.",
        45,
        2,
        2,
        1,
    ),
    (
        "sinnlichkeit",
        "Langsame Berührung",
        "Nur mit vorheriger Absprache: langsame, respektvolle Berührung. Safeword gilt jederzeit.",
        15,
        3,
        3,
        2,
    ),
    (
        "sinnlichkeit",
        "Sinnesübung",
        "Nur mit Opt-in: eine Sinnesübung mit klarer Grenze, Safeword und sofortigem Abbruchrecht.",
        15,
        3,
        3,
        2,
    ),
]


def seed_challenges(apps, schema_editor):
    Challenge = apps.get_model("playbook", "Challenge")
    for category, title, description, duration, intensity, stage, points in CHALLENGES:
        Challenge.objects.get_or_create(
            category=category,
            title=title,
            defaults={
                "description": description,
                "duration_min": duration,
                "intensity": intensity,
                "consent_stage": stage,
                "points": points,
            },
        )


def unseed_challenges(apps, schema_editor):
    Challenge = apps.get_model("playbook", "Challenge")
    Challenge.objects.filter(title__in=[challenge[1] for challenge in CHALLENGES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("playbook", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_challenges, unseed_challenges),
    ]
