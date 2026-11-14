# Club Zweisam – Bedienungsanleitung

Stand: 2026-11-14

Diese Anleitung beschreibt das Portal, die Verwaltung und die Einrichtung von
Push-Benachrichtigungen. Sie ersetzt keine rechtliche, therapeutische oder
medizinische Beratung.

---

## 1. Allgemeine Funktionsbeschreibung

Club Zweisam ist ein privater Kommunikations- und Spielraum für eine Dyade –
also zwei Hauptmitglieder, die ihre Beziehung bewusst gestalten. Das Portal
bündelt Gespräch, Wünsche, Spiele, Alltag und Anerkennung in einem geschützten
Rahmen.

Grundprinzipien:

- **Freiwilligkeit:** Alles ist ein Angebot. Ein Nein ist neutral und kostet
  keine Punkte.
- **Consent:** Grenzen werden vorher besprochen, jederzeit respektiert und
  nicht offengelegt.
- **Diskretion:** Sensible Felder werden verschlüsselt gespeichert; das Logbuch
  enthält keine Geheiminhalte.
- **Keine Gamification von Krisen:** Der Krisenmodus ist ein eigener Bereich
  ohne Punkte, Challenges oder Bewertung.
- **Kein Therapieersatz:** Bei Belastung oder Gefahr verweisen wir auf
  professionelle Hilfe.

Zentrale Module:

| Modul | Zweck |
|---|---|
| Lounge | Täglicher Check-in, 3-Tage-Barometer, Wochenrückblick (Opt-in), Push-Einstellungen |
| Séparée | Geheime Antworten auf Karten, Match erst nach beidseitiger Freigabe |
| Vitrine | Gemeinsamkeiten aus freigegebenen Matches und bestätigten Wünschen |
| Concierge | Wünsche stellen, beantworten, bestätigen |
| Playbook | Challenges mit Timer, Abbruch und Tages-Deckel |
| Logbuch | Ereignis-Chronik ohne Inhalte |
| Deep Talk | Leitfragen, Reparaturkarten, Time-out |
| Krisenmodus | Separater Hilfebereich, keine Gamification |
| Punkte | Anerkennung, Belohnungen, beidseitige Rückbuchung |
| Privacy Shield | Schneller Decoy-Screen und lokaler PIN |
| Konto & Daten | Export und Löschung nach DSGVO |

---

## 2. Anleitung für Superadmins

### 2.1 Zugang

Superadmins nutzen:

- Django-Admin: `https://<domain>/admin/`
- Aggregierte Verwaltung: `https://<domain>/management/`

Superuser anlegen:

```bash
docker compose exec web python manage.py createsuperuser
```

### 2.2 Aufgaben

- Audit-Log im Admin ansehen; es ist append-only und nicht editierbar.
- Break-Glass nur für Metadaten und freigegebene Matches beantragen.
- Vier-Augen-Prinzip: Bestätigung durch eine zweite Superadmin-Person.
- 24-Stunden-Fenster; jeder Zugriff erzeugt Audit-Eintrag und inhaltslose
  Nutzerbenachrichtigung.
- DSGVO-Export/-Löschung durchführen.
- Schlüsselrotation und Backups verantworten.
- Sicherheitsupdates einspielen.

### 2.3 Break-Glass

Erlaubt sind derzeit:

- Clubraum-Metadaten
- Mitgliedschafts-Metadaten
- geteilte Logbuch-Einträge
- freigegebene Matches

Technisch gesperrt sind Geheimantworten, Grenzen und Wünsche. Das ist gewollt;
ein Superadmin mit Datenbank- und Schlüsselzugriff kann technisch trotzdem
alles lesen. Der Schutz ist organisatorisch und durch Audit.

### 2.4 DSGVO und Aufbewahrung

```bash
docker compose exec web python manage.py gdpr_export --user <name|id> --output export.json
docker compose exec web python manage.py gdpr_delete --user <name|id> --confirm
docker compose exec web python manage.py roulette_purge
docker compose exec web python manage.py wishes_purge
```

Self-Service für Nutzer: `/konto/export/` und `/konto/loeschen/`.
Löschung anonymisiert das Konto; Audit-Einträge bleiben pseudonym erhalten.

### 2.5 Schlüsselrotation

1. Neuen Fernet-Schlüssel erzeugen.
2. `FIELD_ENCRYPTION_KEY=<neu>` und `FIELD_ENCRYPTION_KEY_OLD=<alt>` setzen.
3. Web neu starten.
4. `docker compose exec web python manage.py encrypt_rotate`
5. Alten Schlüssel entfernen, neu starten, `audit_verify` prüfen.

### 2.6 Sicherheitscheck

```bash
docker compose exec web bandit -r apps -q
docker compose exec web pip-audit -r requirements.txt
docker compose exec web python manage.py audit_verify
```

---

## 3. Anleitung für Portal-Admins

Portal-Admins sind Mitglieder der Gruppe **Plattform-Admin** und haben
`is_staff=True`. Sie dürfen Seiten, Inhalte und Push-Kanäle verwalten.

### 3.1 Nutzer zur Gruppe hinzufügen

Django-Admin → Benutzer → gewünschten Nutzer → Gruppen → „Plattform-Admin“ →
speichern. Zusätzlich `is_staff` aktivieren.

### 3.2 Statische Seiten

Admin → „Statische Seiten“. AGB, Impressum, Datenschutz, Partner und Disclaimer
sind vorbefüllt. TinyMCE lädt lokal; Bilder können als Inline-Medien mit
Alt-Text hochgeladen werden. Vor Produktivbetrieb rechtlich prüfen.

### 3.3 Systemkonfiguration

- Domain: Django Sites (`SITE_ID=1`) auf die echte Domain setzen.
- E-Mail: SMTP in `.env`; in Dev Mailhog `http://localhost:8025`.
- `PORTAL_BASE_URL` setzen, damit Push-Links auf die richtige Domain zeigen.
- TLS: in Produktion ACME/Domain; in Dev Caddy-intern (siehe README).

### 3.4 Push-Kanäle anlegen

Admin → „Benachrichtigungskanäle“ → „Hinzufügen“:

- Clubraum wählen
- Provider wählen
- Label vergeben (z. B. „Paar-Telegram“)
- Konfiguration als JSON eintragen
- aktivieren und speichern

Danach sieht jedes Clubraum-Mitglied den Kanal in der Lounge unter
„Push-Benachrichtigungen“ und kann ihn selbst aktivieren. Ohne Abonnement wird
nichts gesendet.

Inhalte der Push-Nachricht sind immer gleich und inhaltslos:

```text
Club Zweisam: Neues Ereignis im Portal. https://<portal>/lounge/
```

Kein Ereignistyp, kein Name, kein Wunschtext, keine Antwort, kein Match.

Test:

```bash
docker compose exec web python manage.py push_test --channel <ID>
```

### 3.5 Kanalkonfigurationen (JSON)

**Telegram**

```json
{"bot_token": "123456:ABC...", "default_target": "-1001234567890"}
```

**Gotify**

```json
{"server_url": "https://gotify.example.org", "app_token": "A.xxxxx"}
```

**Signal (signal-cli REST API)**

```json
{"api_url": "http://signal-cli:8080", "sender_number": "+4915112345678", "default_target": "+4915198765432"}
```

**Element/Matrix (unverschlüsselter Hinweisraum)**

```json
{"homeserver_url": "https://matrix.example.org", "access_token": "syt_...", "default_target": "!raumId:example.org"}
```

**WhatsApp Cloud API**

```json
{"access_token": "EAAG...", "phone_number_id": "1234567890", "template_name": "club_zweisam_ping", "template_language": "de", "default_target": "+4915112345678", "api_version": "v22.0"}
```

`default_target` ist optional; Nutzer können in der Lounge ein eigenes Ziel
hinterlegen. `insecure_tls: true` ist nur für selbst gehostete Testsysteme mit
selbstsigniertem Zertifikat gedacht. Secrets liegen verschlüsselt in der
Datenbank. Die Konfiguration ist nur für Plattform-Admins sichtbar.

---

## 4. Anleitung für die Dyade

### 4.1 Was ist eine Dyade?

Eine **Dyade** ist hier die Beziehungseinheit aus genau **zwei
Hauptmitgliedern** in einem Clubraum. Sie ist der kleinste gemeinsame Kontext:
ein Safeword, ein Logbuch, ein Punkte-Ledger, gemeinsame Sichtbarkeiten. Weitere
Personen können als Moderator, Berater, Mediator, Sex-Partner oder Gast
eingeladen werden, bilden aber keine zweite Dyade.

### 4.2 Clubraum einrichten

1. Eine Person registriert sich und bestätigt die E-Mail.
2. Clubraum gründen: Name, Safeword, Hausregeln.
3. Zweite Person als **Hauptmitglied** einladen.
4. Einladung annehmen; beide sind Hauptmitglieder.
5. Rollen für weitere Personen nur bewusst und einzeln vergeben.

### 4.3 Was ihr gemeinsam tun könnt

- **Lounge:** täglicher Check-in (Stimmung, Energie, Nähe), 3-Tage-Barometer.
- **Séparée:** Karten beantworten; Antworten bleiben verborgen, bis beide
  freigeben. Grenzen erscheinen nur als „Grenze respektiert“.
- **Concierge:** Wünsche stellen, annehmen, Alternative vorschlagen,
  verschieben, ablehnen, Grenze setzen. Keine Ketten-Wünsche.
- **Playbook:** Challenges in 8 Kategorien, Timer, Abbruch, Tages-Deckel.
  Stufe 3 nur mit beidseitigem Opt-in.
- **Deep Talk:** Leitfragen oder Versöhnungskarten; Time-out jederzeit.
- **Krisenmodus:** eigener Hilfebereich, keine Punkte, keine Challenges.
- **Punkte:** Anerkennung, Belohnungen, beidseitige Rückbuchung.
- **Logbuch:** Ereignisse ohne Geheiminhalte; Einträge können entfernt werden.
- **Vitrine:** gemeinsame Themen aus freigegebenen Matches und bestätigten
  Wünschen.

### 4.4 Regeln, die das System trägt

- Safeword gilt; niemand muss eine Begründung für einen Abbruch geben.
- Grenzen und Geheimantworten werden nicht offengelegt.
- Punkte sind Anerkennung, keine Währung und kein Druckmittel.
- Krisenmodus ist kein Spiel und erzeugt keine Punkte.
- Einladungen laufen ab; Widerruf wirkt sofort.

---

## 5. Anleitung für einzelne Haupt-User

Als Hauptmitglied kannst du das Portal nutzen, um deine Beziehung bewusster zu
gestalten – ohne Leistungsdruck.

### 5.1 Täglich

- Lounge öffnen und Check-in machen (Stimmung, Energie, Nähe).
- 3-Tage-Barometer ansehen, ohne es als Note zu behandeln.
- Optional Wochenrückblick aktivieren; er zeigt nur deine eigenen Werte.

### 5.2 Wünsche und Gespräche

- Im Concierge einen Wunsch stellen und konkret, offen oder als Fantasie
  formulieren.
- Bei Ablehnung oder Grenze: kein Punktabzug, kein Nachfragen.
- Deep Talk für ein Gespräch mit Leitfragen; bei Überforderung Time-out.
- Bei akuter Belastung den Krisenmodus öffnen und professionelle Hilfe nutzen.

### 5.3 Spiele und Nähe

- Séparée: eigene Antworten abgeben; erst nach beidseitiger Freigabe seht ihr
  beide Antworten.
- Playbook: Challenge mit klarer Dauer wählen; jederzeit abbrechen.
- Punkte: Anerkennung sammeln und Belohnungen gemeinsam einlösen.

### 5.4 Privatsphäre

- **Privacy Shield:** Esc zweimal oder Footer-Button öffnet sofort einen
  Notizen-Decoy. PIN lokal im Browser setzen (Lounge → Privacy Shield).
  Der Server wird erst verzögert informiert; im Aktivierungsmoment gibt es
  keine Netzwerkanfrage.
- **Safe Mode:** puffert Benachrichtigungen; beim Deaktivieren werden sie ohne
  Inhalt zugestellt.
- **Konto & Daten:** Export und Löschung in der Lounge.
- **Push:** nur inhaltslose Links; selbst aktivieren/deaktivieren.

### 5.5 Beziehung verbessern – konkret

- Ein Check-in pro Tag, kein Bewertungsgespräch.
- Ein Wunsch pro Woche, bewusst formuliert.
- Nach einem Konflikt: Repair-Karten statt Rechtfertigung.
- Challenges als Angebot, nicht als Pflicht.
- Anerkennung aussprechen, statt Punkte zu optimieren.

---

## 6. Weitere Benutzer: Rollen und Sinn

| Rolle | Sinn | Sichtbarkeit |
|---|---|---|
| Hauptmitglied | Trägt die Dyade, volle Module | Alle Module, Safeword, Punkte |
| Moderator | Unterstützt Struktur/Logbuch | Lounge, Logbuch; keine Geheiminhalte |
| Berater | Begleitet Gespräche | Lounge, Deep Talk; keine Geheiminhalte |
| Mediator | Unterstützt Reparatur | Lounge, Deep Talk |
| Sex-Partner | Eigener Consent-Kontext | Lounge, Playbook; keine Dyaden-Geheimnisse |
| Gast/Beobachter | Lesender Zugang | Lounge; kein Check-in, kein Schreiben |

Weitere Benutzer:

- dürfen keine Geheimantworten, Grenzen oder privaten Wünsche sehen.
- können jederzeit entfernt werden; Entfernung wirkt sofort.
- Hauptmitglieder können nicht gegenseitig entfernt werden.
- Gäste haben ein isoliertes Punkte-Ledger ohne Wettbewerb.
- Rollen sind kein Ersatz für professionelle Hilfe.

---

## 7. Hand-on: Push-Kanäle autorisieren und einrichten

### 7.0 Assistent im Backend

Portal-Admins (Gruppe „Plattform-Admin“, `is_staff=True`) öffnen:

```text
https://<domain>/management/messenger/
```

Dort gibt es pro Messenger ein Formular mit den nötigen Feldern; JSON-Kenntnisse
sind nicht erforderlich. Nach dem Speichern kann direkt eine inhaltslose
Testnachricht gesendet werden. Die Rohkonfiguration bleibt optional im
Django-Admin unter „Benachrichtigungskanäle“ editierbar.

**Was geht allein aus dem Backend?**

| Messenger | Backend-Assistent | Extern noch nötig |
|---|---|---|
| Telegram | Ja: Token + Chat-ID | Bot bei @BotFather, Gruppe, Bot einladen |
| Gotify | Ja: URL + App-Token | Gotify-Server selbst betreiben |
| Signal | Ja: API-URL + Nummer | signal-cli-REST betreiben, Nummer registrieren/verknüpfen |
| Element | Ja: Homeserver + Token + Raum | Matrix-Konto, Raum, Token |
| WhatsApp | Ja: Phone-ID + Token + Vorlage | Meta-Business-App, Nummer, Token, Vorlagenfreigabe |

**WhatsApp-Web-QR ist kein unterstützter Weg.** Die offizielle WhatsApp Cloud
API ist eine Business-Schnittstelle; sie kennt kein Koppeln wie
`web.whatsapp.com`. Inoffizielle Bibliotheken, die ein persönliches
WhatsApp-Web-Gerät per QR simulieren, verstoßen gegen die WhatsApp-Bedingungen
und riskieren eine Sperre. Club Zweisam implementiert das bewusst nicht.
Für persönliche WhatsApp-Nutzung bleibt nur der offizielle Cloud-API-Weg; wer
das nicht möchte, nutzt In-App-Benachrichtigungen, Telegram oder Gotify.

### 7.1 Gemeinsamer Ablauf

1. Portal-Admin öffnet `/management/messenger/`.
2. Messenger wählen, Clubraum und Bezeichnung eintragen.
3. Standardziel eintragen (Telefonnummer, Chat-ID oder Raum-ID) oder leer
   lassen, wenn jeder Nutzer sein eigenes Ziel in der Lounge setzt.
4. Zugangsdaten eintragen, „Kanal aktiv“ setzen.
5. Optional „Nach dem Speichern Testnachricht senden“ aktivieren.
6. Speichern; bei Fehlern Logs prüfen.
7. Nutzer öffnet Lounge → Push-Benachrichtigungen, aktiviert den Kanal und
   trägt ggf. sein Ziel ein.
8. Test mit `push_test` oder einem echten Ereignis (z. B. Check-in).
9. Bei Safe Mode: keine Zustellung, bis deaktiviert.

### 7.2 WhatsApp Cloud API – Schritt für Schritt

1. Meta-Business-Konto und Entwickler-App anlegen.
2. WhatsApp-Produkt hinzufügen; Test- oder Produktionsnummer verbinden.
3. `phone_number_id` notieren (nicht die Telefonnummer selbst).
4. System-User mit `whatsapp_business_messaging` anlegen und ein dauerhaftes
   Access Token erzeugen.
5. Empfänger als Testnummer hinzufügen (bei Testnummern nötig).
6. Nachrichtenvorlage (Template) mit einem Textparameter anlegen, z. B. Body
   „Neues Ereignis im Club Zweisam: {{1}}“, Sprache `de`, Kategorie Utility.
   Vorlage freigeben lassen.
7. In Club Zweisam: `/management/messenger/` → WhatsApp → Clubraum, Bezeichnung,
   Phone Number ID, Access Token, Template-Name, Sprache und Graph-API-Version
   eintragen.
8. Standardziel als internationale Nummer (`+49...`) eintragen oder Nutzer
   ihr Ziel selbst in der Lounge setzen lassen.
9. „Kanal aktiv“ setzen, speichern, Testnachricht senden.
10. Nutzer abonnieren den Kanal in der Lounge.
11. Ohne Template sendet das System eine Textnachricht; diese ist nur innerhalb
    des 24-Stunden-Kundenfensters zuverlässig. Das Template ist der stabile Weg.
12. Datenschutz: Meta sieht Metadaten und den generischen Text; niemals
    Clubraum-Inhalte in die Vorlage schreiben. Ein QR-Login wie bei
    `web.whatsapp.com` ist offiziell nicht verfügbar und wird nicht unterstützt.

### 7.3 Telegram Bot

1. Bei `@BotFather` einen Bot anlegen, Token kopieren.
2. Bot in die gewünschte Gruppe einladen.
3. Gruppe manuell in Telegram anlegen (Bots können keine Gruppen erstellen),
   Bot `@<BotName>` als Mitglied hinzufügen und dort eine Nachricht senden oder
   den Bot erwähnen. Bei aktivierter Privacy-Mode in BotFather `/setprivacy` →
   `Disable` setzen und den Bot neu hinzufügen.
   Für einen schnellen Test reicht der Privatchat: Bot öffnen, „Start“ drücken,
   Nachricht senden; die Chat-ID ist dann positiv.
4. `/management/messenger/` → Telegram → Token eintragen → **Chat-ID
   ermitteln** → gefundene Gruppe übernehmen (ID ist negativ, z. B.
   `-1001234567890`). Alternativ die numerische ID manuell eintragen.
5. Speichern und Testnachricht senden; Nutzer abonnieren.
6. Telegram-Bots sind nicht Ende-zu-Ende-verschlüsselt; nur inhaltslose Pings.

### 7.4 Signal

1. `signal-cli-rest-api` selbst betreiben und eine Nummer registrieren oder
   ein bestehendes Gerät verknüpfen (das Koppeln passiert in signal-cli, nicht
   im Club-Zweisam-Backend).
2. API-URL und Absendernummer notieren.
3. Empfängernummer als Ziel eintragen.
4. `/management/messenger/` → Signal → API-URL, Absendernummer und optional
   Authorization-Header eintragen.
5. Speichern und Testnachricht senden.
6. Signal hat keine offizielle Bot-API; der Betrieb ist selbst zu verantworten.
7. Nur generische Pings senden; keine Clubraum-Inhalte.

### 7.5 Element/Matrix

1. Dedizierten, **unverschlüsselten** Hinweisraum anlegen.
2. Matrix-Bot/Service-User mit Zugriffstoken erzeugen.
3. Raum-ID (beginnt mit `!`) kopieren.
4. `/management/messenger/` → Element → Homeserver-URL, Access Token und
   Raum-ID eintragen.
5. Speichern, Testnachricht senden; Nutzer in den Raum einladen und abonnieren.
6. Verschlüsselte Räume werden vom einfachen HTTP-Adapter nicht unterstützt;
   dafür wäre ein Matrix-Client mit E2EE nötig. Der Raum darf keine Geheiminhalte
   enthalten, nur den Portal-Link.

### 7.6 Gotify

1. Gotify selbst hosten (Docker).
2. Anwendung anlegen und App-Token kopieren.
3. `/management/messenger/` → Gotify → Server-URL und App-Token eintragen.
4. Speichern, Testnachricht senden; Nutzer abonnieren; kein Ziel nötig.
5. Selbst gehostet, aber Push läuft über den Gotify-Server; nur generische Pings.

### 7.7 Ziel pro Nutzer

`default_target` im Kanal gilt für alle Abonnenten. Ein Nutzer kann in der
Lounge ein eigenes Ziel eintragen (Telefonnummer, Chat-ID, Raum-ID). Dieses Ziel
wird verschlüsselt gespeichert und ist im DSGVO-Export enthalten.

---

## 8. Troubleshooting

- **Keine Aktivierungs-Mail:** Mailhog/SMTP prüfen; Spam; Adresse korrekt.
- **Login verweigert:** E-Mail noch nicht bestätigt; Link erneut anfordern.
- **Kein Push:** Kanal aktiv? Abonnement aktiv? Ziel vorhanden? `push_test`
  ausführen; Logs auf „Push-Zustellung fehlgeschlagen“ prüfen.
- **WhatsApp:** Vorlage genehmigt? Token gültig? Empfänger im Testmodus?
  24-Stunden-Fenster beachten.
- **Telegram „chat not found“:** Als Ziel wurde ein Gruppenname statt der
  numerischen Chat-ID verwendet. Bot in die Gruppe einladen, Nachricht senden,
  „Chat-ID ermitteln“ nutzen; Gruppen-IDs sind negativ.
- **Signal:** API erreichbar? Nummer registriert? `insecure_tls` nur bei
  selbstsigniertem Zertifikat.
- **Element:** Raum unverschlüsselt? Bot im Raum? Token gültig?
- **Safe Mode:** Push wird bewusst gepuffert; erst nach Deaktivierung.
- **Zertifikatswarnung:** Caddy-CA im System/Browser importieren
  (`scripts/setup-dev-tls.sh --all`).

---

## 9. Sicherheit und Grenzen

- Kein Bridging von Inhalten; externe Nachrichten enthalten nur den Portal-Link.
- Externe Anbieter sehen Metadaten und den generischen Text. Wer das nicht
  möchte, nutzt nur In-App-Benachrichtigungen oder selbst gehostetes Gotify.
- Ein Superadmin mit Datenbank- und Schlüsselzugriff kann technisch alles lesen.
- Der lokale Privacy-Shield-PIN ist ein Sichtschutz, keine Verschlüsselung.
- Club Zweisam ist kein Therapieersatz; bei Gefahr: Notruf 112,
  Telefonseelsorge 0800 111 0 111, Hilfetelefon 116 016.
