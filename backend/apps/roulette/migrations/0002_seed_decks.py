import json

from django.db import migrations

DEFAULT_RULE = {
    "full": [["ja", "ja"]],
    "partial": [
        ["ja", "vielleicht"],
        ["vielleicht", "ja"],
        ["vielleicht", "vielleicht"],
    ],
}

DECKS = [
    ("A", "Reden", "Gespräche, Nähe im Alltag und unausgesprochene Themen.", 1, False),
    ("B", "Kuscheln", "Körperkontakt, Nähe und Grenzen ohne Leistungsdruck.", 2, False),
    ("C", "Rollenspiel", "Szenen, Rollen und Absprachen mit klaren Grenzen.", 3, False),
    (
        "D",
        "Sexuelle Vorlieben",
        "Offene Wünsche und Grenzen – nur mit Opt-in beider Hauptmitglieder.",
        4,
        True,
    ),
]

QUESTIONS = {
    "A": [
        "Möchtest du einmal pro Woche ein Gespräch ohne Handy führen?",
        "Wünschst du dir, dass ich öfter von meinem Tag erzähle?",
        "Möchtest du über unausgesprochene Themen offener sprechen?",
        "Hilft dir ein festes Zeichen, wenn du Nähe brauchst?",
        "Möchtest du nach einem Streit zuerst kurz Zeit für dich?",
        "Wünschst du dir mehr Fragen, die nichts mit Alltag zu tun haben?",
        "Möchtest du mir öfter sagen, was du an mir schätzt?",
        "Sprichst du lieber abends als morgens über Beziehungsthemen?",
        "Möchtest du, dass wir Geheimnisse bewusst als Schutz verstehen?",
        "Wünschst du dir ein regelmäßiges kurzes Check-in-Gespräch?",
    ],
    "B": [
        "Möchtest du öfter ohne Ziel kuscheln?",
        "Hilft dir Körperkontakt beim Runterkommen?",
        "Möchtest du mehr Nähe im Alltag, nicht nur abends?",
        "Ist für dich Händchenhalten in der Öffentlichkeit schön?",
        "Möchtest du eine feste Kuschelzeit pro Woche?",
        "Magst du es, wenn ich dich ungefragt kurz umarme?",
        "Hilft dir eine Decke oder ein bestimmter Ort beim Entspannen?",
        "Möchtest du nach dem Aufwachen Nähe statt sofort Aufstehen?",
        "Ist langsames Kuscheln für dich erholsamer als schnelle Nähe?",
        "Möchtest du über deine Grenzen bei Berührungen sprechen?",
    ],
    "C": [
        "Reizt dich eine klare Szene mit verteilten Rollen?",
        "Möchtest du vorher ein Safeword und eine Grenze festlegen?",
        "Reizt dich eine Szene, die mit einem Gespräch beginnt?",
        "Möchtest du ein Rollenspiel lieber zu Hause als woanders?",
        "Reizt dich ein langsamer Aufbau mehr als eine schnelle Szene?",
        "Möchtest du nach einer Szene ausführlich darüber sprechen?",
        "Reizt dich ein Rollenspiel mit Verkleidung oder Requisiten?",
        "Möchtest du Szenen vorher schriftlich absprechen?",
        "Reizt dich eine Szene, in der du die Führung übernimmst?",
        "Reizt dich eine Szene, in der du dich führen lässt?",
    ],
    "D": [
        "Möchtest du offener darüber sprechen, was du sexuell magst?",
        "Reizt dich langsames Tempo mehr als Abwechslung?",
        "Möchtest du öfter Feedback während des Sex?",
        "Reizt dich mehr Vorspiel als schneller Sex?",
        "Möchtest du neue Wünsche zuerst schriftlich teilen?",
        "Reizt dich ein klarer Rahmen mit vorheriger Absprache?",
        "Möchtest du nach dem Sex über Wünsche sprechen?",
        "Reizt dich mehr Nähe als Technik?",
        "Möchtest du, dass wir einander öfter sagen, was gefällt?",
        "Reizt dich ein gemeinsamer Wunschzettel für später?",
    ],
}


def seed_decks(apps, schema_editor):
    Deck = apps.get_model("roulette", "Deck")
    Question = apps.get_model("roulette", "Question")
    for code, title, description, intensity, requires_opt_in in DECKS:
        deck, _ = Deck.objects.get_or_create(
            code=code,
            defaults={
                "title": title,
                "description": description,
                "intensity": intensity,
                "requires_opt_in": requires_opt_in,
            },
        )
        for order, text in enumerate(QUESTIONS[code], start=1):
            Question.objects.get_or_create(
                deck=deck,
                order=order,
                defaults={
                    "text": text,
                    "answer_type": "choice",
                    "match_rule": json.loads(json.dumps(DEFAULT_RULE)),
                },
            )


def unseed_decks(apps, schema_editor):
    Deck = apps.get_model("roulette", "Deck")
    Question = apps.get_model("roulette", "Question")
    Question.objects.filter(deck__code__in=QUESTIONS.keys()).delete()
    Deck.objects.filter(code__in=QUESTIONS.keys()).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("roulette", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_decks, unseed_decks),
    ]
