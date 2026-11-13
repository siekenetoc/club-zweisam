from django.db import migrations

PAGES = [
    (
        "agb",
        "Nutzungsbedingungen (AGB)",
        """
        <p><strong>Platzhalter.</strong> Diese Seite muss vor dem Produktivbetrieb
        rechtlich geprüft und an den Betreiber angepasst werden.</p>
        <h2>Zweck</h2>
        <p>Club Zweisam ist ein privater Kommunikations- und Spielraum für
        volljährige Paare. Es ist kein Therapieersatz, keine Währung für Sex und
        kein Druckmittel.</p>
        <h2>Freiwilligkeit</h2>
        <p>Alle Angebote beruhen auf Zustimmung. Ein Nein ist neutral und kostet
        keine Punkte. Grenzen werden respektiert und nicht offengelegt.</p>
        <h2>Punkte</h2>
        <p>Punkte sind eine interne Anerkennung. Sie sind nicht übertragbar,
        nicht auszahlbar und begründen keinen Anspruch.</p>
        <h2>Sicherheit</h2>
        <p>Sensible Felder werden verschlüsselt gespeichert. Ein Super-Admin mit
        Datenbank- und Schlüsselzugriff kann technisch alles lesen; Schutz ist
        organisatorisch und durch Audit, nicht kryptografisch erzwungen.</p>
        """,
    ),
    (
        "impressum",
        "Impressum",
        """
        <p><strong>Platzhalter.</strong> Betreiberangaben, Anschrift und
        Kontaktmöglichkeiten müssen vor dem Produktivbetrieb ergänzt werden.</p>
        <h2>Angaben gemäß § 5 DDG</h2>
        <p>Name und Anschrift des Betreibers: [bitte ergänzen]</p>
        <p>E-Mail: [bitte ergänzen]</p>
        <p>Verantwortlich für den Inhalt: [bitte ergänzen]</p>
        """,
    ),
    (
        "datenschutz",
        "Datenschutz",
        """
        <p><strong>Platzhalter.</strong> Diese Datenschutzhinweise müssen vor dem
        Produktivbetrieb rechtlich geprüft und ergänzt werden.</p>
        <h2>Verarbeitete Daten</h2>
        <p>Konto- und Clubraumdaten, Mitgliedschaften, Einladungen, Statuswerte,
        Wünsche, Antworten, Matches, Punkte, Logbuch-Ereignisse und
        Benachrichtigungen.</p>
        <h2>Schutz</h2>
        <p>Geheimantworten vor Match, Grenzen, private Wünsche und Antwortnotizen
        werden feldverschlüsselt gespeichert. Audit-Einträge sind append-only.</p>
        <h2>Speicherdauer</h2>
        <p>Geheimantworten werden spätestens nach 30 Tagen gelöscht. Nicht-Matches
        werden nach 30 Tagen entfernt. Gesetzliche Aufbewahrungspflichten bleiben
        unberührt.</p>
        <h2>Rechte</h2>
        <p>Auskunft, Berichtigung, Löschung, Einschränkung, Datenübertragbarkeit
        und Widerspruch nach DSGVO. Kontakt: [bitte ergänzen].</p>
        <h2>Kein Tracking</h2>
        <p>Es werden keine externen Analyse- oder Werbedienste eingebunden.
        Schriftarten und Skripte werden lokal ausgeliefert.</p>
        """,
    ),
    (
        "partner",
        "Partner und Hilfe",
        """
        <p>Club Zweisam ist kein Therapieersatz. Bei Belastung, Gewalt oder akuter
        Gefahr nutze professionelle Angebote – unabhängig von diesem Portal.</p>
        <h2>Telefonseelsorge</h2>
        <p>0800 111 0 111 · 0800 111 0 222 · online.telefonseelsorge.de</p>
        <h2>Hilfetelefon Gewalt gegen Frauen</h2>
        <p>116 016 · hilfetelefon.de</p>
        <h2>Hilfetelefon Gewalt gegen Männer</h2>
        <p>0800 123 0000 · maennerhilfetelefon.de</p>
        <h2>Akute Gefahr</h2>
        <p>Notruf 112</p>
        """,
    ),
    (
        "disclaimer",
        "Disclaimer",
        """
        <p><strong>Kein Therapieersatz.</strong> Die Inhalte ersetzen keine
        professionelle psychologische oder medizinische Beratung.</p>
        <p><strong>Keine Währung für Sex.</strong> Punkte und Belohnungen sind
        freiwillige Anerkennung, kein Anspruch und kein Druckmittel.</p>
        <p><strong>Kein heimliches Überwachen.</strong> Sichtbarkeiten werden
        durch Rollen und Freigaben begrenzt. Geheiminhalte erscheinen nicht im
        Logbuch.</p>
        <p><strong>Technische Grenze.</strong> Ein Super-Admin mit Datenbank- und
        Schlüsselzugriff kann technisch alles lesen. Der Schutz ist
        organisatorisch und durch Audit, nicht kryptografisch absolut.</p>
        """,
    ),
]


def seed_pages(apps, schema_editor):
    StaticPage = apps.get_model("pages", "StaticPage")
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name="Plattform-Admin")
    for slug, title, content_html in PAGES:
        StaticPage.objects.get_or_create(
            slug=slug,
            defaults={
                "title": title,
                "content_html": content_html,
                "is_published": True,
            },
        )


def unseed_pages(apps, schema_editor):
    StaticPage = apps.get_model("pages", "StaticPage")
    Group = apps.get_model("auth", "Group")
    StaticPage.objects.filter(slug__in=[page[0] for page in PAGES]).delete()
    Group.objects.filter(name="Plattform-Admin").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("pages", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(seed_pages, unseed_pages),
    ]
