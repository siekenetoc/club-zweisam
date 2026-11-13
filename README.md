# Club Zweisam

Privater Kommunikations- und Spielraum für Paare. Kein Therapieersatz.
Ein Stack, Caddy als Reverse Proxy, Django serverseitig mit Feldverschlüsselung
für sensible Inhalte.

**Status:** M0 bis M3 abgeschlossen; M4 (Lounge & Logbuch) in Arbeit.

## Stack
- Python 3.12, Django 5.0, Gunicorn
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

## Setup (Dev)
```bash
cp .env.example .env
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Ausgabe als FIELD_ENCRYPTION_KEY in .env eintragen; SECRET_KEY und
# POSTGRES_PASSWORD ebenfalls ersetzen.

docker compose up --build
```

- Web: <https://localhost> (TLS über Caddys interne CA)
- Registrieren: <https://localhost/registrieren/>
- Anmelden: <https://localhost/anmelden/>
- Séparée: <https://localhost/separee/>
- Vitrine: <https://localhost/vitrine/>
- Concierge: <https://localhost/concierge/>
- Playbook: <https://localhost/playbook/>
- Mailhog (Einladungs-E-Mails): <http://localhost:8025>
- Admin: <https://localhost/admin/>

Einladungen laufen standardmäßig nach 7 Tagen ab (`INVITATION_TTL_DAYS` in `.env`).
Die Einladungs-E-Mail enthält nur den Annahme-Link, keine Geheiminhalte.
Geheimantworten werden nach 30 Tagen bzw. beim Rundenende gelöscht
(`ROULETTE_ANSWER_RETENTION_DAYS`, `manage.py roulette_purge`).
Challenges sind auf drei Läufe pro Tag und Clubraum begrenzt
(`PLAYBOOK_DAILY_LIMIT`).

Caddy verwendet in Dev ein internes Zertifikat. Der Browser warnt beim ersten
Aufruf. Root-Zertifikat zum Importieren:
```bash
docker compose exec caddy cat /data/caddy/pki/authorities/local/root.crt > caddy-root.crt
```

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
```

- `pytest` nutzt `clubzweisam.settings.test` (SQLite in-memory).
- Der Playwright-Test läuft im Profil `e2e` gegen Caddy (Registrierung + Clubraum).
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
