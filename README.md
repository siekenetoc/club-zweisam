# Club Zweisam

Privater Kommunikations- und Spielraum für Paare. Kein Therapieersatz.
Ein Stack, Caddy als Reverse Proxy, Django serverseitig mit Feldverschlüsselung
für sensible Inhalte.

**Status:** M0 bis M10 abgeschlossen – Freigabe durch den Nutzer ausstehend.

## Stack
- Python 3.12, Django 5.2 LTS, Gunicorn
- PostgreSQL 16, Redis 7
- Caddy 2 (Reverse Proxy, TLS, Security-Header)
- Node 20, Vite, Tailwind CSS, Alpine.js, HTMX
- TinyMCE (lokal, self-hosted, keine CDN-Einbindung)
- pytest, pytest-django, factory_boy, Playwright, ruff, black, bandit, pip-audit

## Struktur
```text
backend/    Django-Projekt, Apps, Templates, Static
frontend/   Vite, Tailwind, Alpine, HTMX, TinyMCE, Fonts
caddy/      Caddyfile (Prod), Caddyfile.dev (Dev)
docs/       Architektur, Datenmodell, Break-Glass
tests/      unit, integration, e2e
```

Umgesetzt in M0:
- `apps.core`: Feldverschlüsselung (`EncryptedTextField`), Audit-Log
  (append-only, Hash-Chain, `manage.py audit_verify`), Log-Filter
- `apps.accounts`: eigenes `User`-Modell inkl. Safe-Mode-Flag
- Startseite über Caddy, `/healthz`, Admin, Static/Media ohne CDN
- Docker-Compose mit sechs Diensten: `caddy`, `web`, `db`, `redis`, `assets`, `mailhog`
- Dev-Bind-Mounts für Backend, Templates, Tests und Medien

Umgesetzt in M1:
- Registrierung mit Volljährigkeits- und AGB-Bestätigung, Login/Logout
- Clubraum-Gründung mit verschlüsseltem Safeword und Hausregeln
- Rollen: Hauptmitglied, Moderator, Berater, Mediator, Sex-Partner, Gast/Beobachter
- Rollen-Matrix für Module; Gast ist lesend, Admin-/Beraterrollen ohne Geheiminhalte
- E-Mail-Einladungen mit gehashtem Token, Bindung an E-Mail-Adresse, Ablauf (7 Tage),
  Widerruf mit sofortiger Wirkung und Audit-Einträgen
- Höchstens zwei Hauptmitglieder und eine aktive Mitgliedschaft pro Nutzer
- Mitglieder-Entfernung durch Hauptmitglieder (nicht für Hauptmitglieder selbst)

Umgesetzt in M2:
- Séparée mit vier Decks (A Reden, B Kuscheln, C Rollenspiel, D Sexuelle Vorlieben) und 40 Karten
- Vorgegebene Antworten (Ja/Vielleicht/Nein), serverseitiger Match mit Voll-/Teilmatch-Regeln
- Beidseitiger Freigabe-Schalter: Antworten erscheinen erst nach Freigabe beider Seiten
- Grenzschutz: Grenzen erscheinen nur als „Grenze respektiert", nie als Inhalt
- Feldverschlüsselte `SecretAnswer`, Löschung bei Rundenende und nach 30 Tagen
- Nicht-Matches werden nach 30 Tagen entfernt (`manage.py roulette_purge`)
- Opt-in beider Hauptmitglieder für Deck D
- Vitrine mit Gemeinsamkeiten ausschließlich aus beidseitig freigegebenen Matches

Umgesetzt in M3:
- Concierge mit fünf Wunschtypen, sieben Antwortoptionen und beidseitiger Bestätigung
- Private Wünsche (Entwurf), Teilen erst auf ausdrücklichen Wunsch
- Keine Ketten-Wünsche: pro Wunsch genau eine Antwort, keine Gegenwünsche
- Feldverschlüsselte Wunsch-Inhalte und Antwort-Notizen
- Grenz-Antworten zeigen nur „Grenze respektiert", nie die Begründung
- Playbook mit 16 Challenges in 8 Kategorien, Timer, Abbruch und Tages-Deckel
- Stufe-3-Challenges nur mit Opt-in beider Hauptmitglieder
- Bestätigte Wünsche fließen als Gemeinsamkeit in die Vitrine (nicht privat)

Umgesetzt in M4:
- Lounge mit täglichem Check-in (Stimmung, Energie, Nähe) und 3-Tage-Barometer
- Wochenrückblick nur nach persönlichem Opt-in, ausschließlich eigene Daten
- Logbuch mit Ereignistypen, Filter, Soft-Delete und Platzhalter „Eintrag entfernt"
- Feed-Metadaten werden bereinigt; keine Titel, Inhalte, Antworten oder Grenzen
- Inhaltslose Benachrichtigungen mit Server-Queue
- Safe Mode puffert Benachrichtigungen und stellt sie beim Deaktivieren ohne Inhalt zu
- Safe-Mode-Aktivierung erzeugt weder Feed-Eintrag noch Benachrichtigung

Umgesetzt in M5:
- Deep Talk mit Leitfragen und Reparaturmodus mit Versöhnungskarten
- Time-out ohne Begründung, jederzeit und von jeder beteiligten Rolle
- Kein freier Chat, keine Punkte, keine Feed- oder Benachrichtigungsseitenwirkungen
- Krisenmodus als eigenes Sub-Modul mit eigener URL, eigenen Templates und ohne Gamification
- Harte Verweise auf Notruf 112, Telefonseelsorge, Hilfetelefon Frauen und Männer
- Krisenraum ohne Leitfragen und ohne Punkte; Hilfsangebote bleiben nach dem Schließen sichtbar

Umgesetzt in M6:
- Punkte-Ledger je Hauptmitglied, isolierte Gast-Ledger ohne Wettbewerb
- Tages-Deckel 10 Punkte, davon höchstens 3 aus Challenges
- Verdienen über abgeschlossene Challenges und bestätigte Wünsche; kein Abzug für Nein
- Belohnungskatalog mit fünf Kategorien und Einlöse-Workflow
- Annahme durch die andere Person, Abschluss, Ablehnung, Rückzug
- Rückbuchung nur mit Anfrage und Bestätigung durch die zweite Person
- Anerkennung für Gäste, ohne Vermischung mit der Dyade
- Keine Punkte-Ereignisse im Logbuch (Schutz vor Preisgabe von Belohnungstiteln)

Umgesetzt in M7:
- Admin-Dashboard unter `/management/` mit Aggregaten und Banner „Zugriff protokolliert"
- CRUD über Django-Admin für Decks, Fragen, Belohnungen und Challenges
- Nutzer-, Clubraum- und Mitgliedschaftsverwaltung ohne Safeword-Anzeige
- Audit-Log im Admin read-only, append-only mit Hash-Chain
- Break-Glass mit Vier-Augen-Prinzip, 24-Stunden-Fenster und Pflichtbegründung
- Break-Glass ist für Geheimantworten, Grenzen und Wünsche technisch gesperrt
- Jeder Break-Glass-Zugriff erzeugt Audit-Eintrag und inhaltslose Nutzer-Benachrichtigung

Umgesetzt in M8:
- Statische Seiten (AGB, Impressum, Datenschutz, Partner, Disclaimer) unter `/seite/<slug>/`
- TinyMCE lokal im Admin-Editor, keine CDN-Einbindung
- Bild-Upload mit Alt-Text je Seite
- Bearbeitung nur für Super-Admins und die Gruppe „Plattform-Admin"
- Footer-Links zu allen Pflichtseiten
- Platzhalterhinweis für rechtliche Prüfung vor Produktivbetrieb

Umgesetzt in M9:
- Privacy Shield mit sofortigem Decoy-Screen „Notizen" (Esc zweimal oder Footer-Button)
- Aktivierung rein clientseitig, keine Netzwerkanfrage im Aktivierungsmoment (<100 ms)
- Lokaler PIN (SHA-256 mit Salt in localStorage) zum Entsperren; kein Server-PIN
- Decoy-Inhalte vollständig lokal, keine externen Requests
- Server-Sync des Safe-Mode-Flags verzögert; Benachrichtigungen werden gepuffert
- Deaktivierung stellt gepufferte Benachrichtigungen inhaltslos zu
- Andere sehen keinen Safe-Mode-Hinweis; Admin-Ansicht zeigt das Flag nicht
- Hinweis: Der lokale PIN ist ein Sichtschutz, keine kryptografische Sperre

Umgesetzt in M10:
- Abhängigkeiten gehärtet: Django 5.2 LTS, cryptography 50, Pillow 13; Prod-Image ohne Dev-Tools
- `pip-audit` (Prod/Dev) und `bandit` ohne Befunde, `check --deploy` clean
- CSP und Security-Header über Caddy; TinyMCE unter CSP geprüft
- DSGVO-Export und -Löschung als Self-Service und Management-Commands
- Aufbewahrungs-Commands für Séparée (30 Tage) und Wünsche (90 Tage)
- Feldverschlüsselungs-Rotation mit altem Schlüssel und `encrypt_rotate`
- Lasttest-Skript und Security-Review (`docs/security-review.md`)
- Betriebsdoku (`docs/operations.md`) mit Backup, Restore, Rotation und DSGVO

## Setup (Dev)
```bash
cp .env.example .env
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Ausgabe als FIELD_ENCRYPTION_KEY in .env eintragen; SECRET_KEY und
# POSTGRES_PASSWORD ebenfalls ersetzen.

docker compose up --build
docker compose exec web python manage.py createsuperuser  # Verwaltung
```

- Web: <https://club-zweisam.localhost> (TLS über Caddys interne CA)
- Registrieren: <https://club-zweisam.localhost/registrieren/>
- Anmelden: <https://club-zweisam.localhost/anmelden/>
- Séparée: <https://club-zweisam.localhost/separee/>
- Vitrine: <https://club-zweisam.localhost/vitrine/>
- Concierge: <https://club-zweisam.localhost/concierge/>
- Playbook: <https://club-zweisam.localhost/playbook/>
- Lounge: <https://club-zweisam.localhost/lounge/>
- Logbuch: <https://club-zweisam.localhost/logbuch/>
- Deep Talk: <https://club-zweisam.localhost/deep-talk/>
- Krisenmodus: <https://club-zweisam.localhost/krisenmodus/>
- Punkte: <https://club-zweisam.localhost/punkte/>
- Verwaltung: <https://club-zweisam.localhost/management/> (Staff) und <https://club-zweisam.localhost/admin/>
- Seiten: <https://club-zweisam.localhost/seite/agb/>, `/impressum/`, `/datenschutz/`, `/partner/`, `/disclaimer/`
- Mailhog (Einladungs-E-Mails): <http://localhost:8025>
- Admin: <https://localhost/admin/>

Einladungen laufen standardmäßig nach 7 Tagen ab (`INVITATION_TTL_DAYS` in `.env`).
Die Einladungs-E-Mail enthält nur den Annahme-Link, keine Geheiminhalte.
Geheimantworten werden nach 30 Tagen bzw. beim Rundenende gelöscht
(`ROULETTE_ANSWER_RETENTION_DAYS`, `manage.py roulette_purge`).
Challenges sind auf drei Läufe pro Tag und Clubraum begrenzt
(`PLAYBOOK_DAILY_LIMIT`). Punkte sind auf 10 pro Tag gedeckelt, davon höchstens
3 aus Challenges (`POINTS_DAILY_CAP`, `POINTS_CHALLENGE_DAILY_CAP`).

Caddy verwendet in Dev eine interne CA. `https://club-zweisam.localhost` und
`https://localhost` funktionieren beide. Damit Firefox, Chrome/Chromium, curl und
wget ohne Warnung zugreifen, muss die Caddy-Root-CA einmalig importiert werden:

```bash
docker compose exec caddy cat /data/caddy/pki/authorities/local/root.crt > caddy-root.crt
```

- Systemweit (curl/wget): `sudo install -m 0644 caddy-root.crt /usr/local/share/ca-certificates/club-zweisam-caddy.crt && sudo update-ca-certificates`
- Firefox: Einstellungen → Datenschutz & Sicherheit → Zertifikate → Zertifikate
  anzeigen → Zertifizierungsstellen → Importieren → `caddy-root.crt` →
  „Diese CA zur Identifizierung von Websites vertrauen".
- Chrome/Chromium: Einstellungen → Datenschutz und Sicherheit → Sicherheit →
  Zertifikate verwalten → Zertifizierungsstellen → Importieren.

Der Hostname `club-zweisam.localhost` wird von Browsern und gängigen
Resolver-Konfigurationen auf Loopback aufgelöst. Falls curl/wget ihn nicht
auflösen, einmalig `127.0.0.1 club-zweisam.localhost` in `/etc/hosts` eintragen.
Ohne Systeminstallation funktionieren curl/wget auch mit
`--cacert caddy-root.crt` bzw. `--ca-certificate=caddy-root.crt`.
Ein Helfer exportiert die CA und importiert sie bei vorhandenem `certutil` in
Chrome/Chromium und alle Firefox-Profile:

```bash
scripts/setup-dev-tls.sh --system
```

`--system` installiert die CA systemweit (sudo-Passwort wird abgefragt).
Details und CLI-Alternativen: `docs/operations.md`.

## Setup (Prod)
```bash
cp .env.example .env
# .env anpassen: DOMAIN, ACME_EMAIL, SECRET_KEY, FIELD_ENCRYPTION_KEY,
# POSTGRES_PASSWORD, DATABASE_URL, DEBUG=False
docker compose -f docker-compose.yml up -d --build
```

In Produktion überschreibt `DJANGO_SETTINGS_MODULE=clubzweisam.settings.prod` die
Dev-Einstellungen. Der Container führt beim Start `migrate` und `collectstatic`
aus und startet Gunicorn; Static liefert Whitenoise.

## Tests und Qualität
```bash
docker compose exec web pytest
docker compose --profile e2e run --rm playwright
docker compose exec web ruff check .
docker compose exec web black --check .
docker compose exec web python manage.py check
docker compose exec web python manage.py audit_verify
docker compose exec web pip-audit -r requirements.txt
docker compose exec web bandit -r apps -q
```

- `pytest` nutzt `clubzweisam.settings.test` (SQLite in-memory); aktuell 132 Tests.
- Der Playwright-Test läuft im Profil `e2e` gegen Caddy (vollständiger UI-Durchlauf,
  2 Tests, inkl. Privacy-Shield-Aktivierung unter 100 ms ohne Netzwerkanfrage).
- Sicherheits-Selbstaudit: `docker compose exec web bandit -r apps -q` und
  `docker compose exec -e DJANGO_SETTINGS_MODULE=clubzweisam.settings.prod web python manage.py check --deploy`.
- Vor dem ersten Commit: `docker compose exec web pre-commit install`.

## Konventionen
- MD-Dateien: Deutsch
- Commits: Conventional Commits
- Kein CDN. Alle Assets lokal.
- Feldverschlüsselung für: `SecretAnswer`, `Boundary`, `Wish(is_private=true)`,
  `FantasyWish`.
- Audit-Log ist append-only; jede sensible Operation wird protokolliert.

## Sicherheitsversprechen (Klartext, gehört auch in die AGB)
- Geheimantworten vor Match, Grenzen und ungeteilte Fantasie-Wünsche werden
  verschlüsselt gespeichert.
- Admin-Zugriffe auf sensible Inhalte sind technisch protokolliert und werden
  den betroffenen Nutzern gemeldet.
- Ein Super-Admin mit DB- und Schlüsselzugriff kann technisch alles lesen.
  Schutz ist organisatorisch + Audit, nicht kryptografisch erzwungen.
- Wer mehr braucht, ist auf diesem Portal falsch – bewusste Design-Entscheidung.

## Was das System nicht ist
Kein Therapieersatz, keine Währung für Sex, kein Druckmittel, kein Wettbewerb
zwischen Paaren, kein heimliches Überwachen.

## Doku
- `PLAN.md` – Meilensteine und Status
- `INTERVIEW.md` – Anforderungsdialog
- `AGENT_PROMPT.md` – Auftrag und Arbeitsregeln
- `docs/architecture.md` – Sicherheitsarchitektur
- `docs/data-model.md` – Datenmodell
- `docs/break-glass.md` – Admin-Zugriffsverfahren
- `docs/security-review.md` – Härtung, Audits, Restrisiken
- `docs/operations.md` – Betrieb, Backup, Rotation, DSGVO
