# Club Zweisam

Privater Kommunikations- und Spielraum für Paare. Kein Therapieersatz.
Ein Stack, Caddy als Reverse Proxy, Django serverseitig mit Feldverschlüsselung
für sensible Inhalte.

**Status:** M0 freigegeben; M1 (Auth & Clubraum) in Arbeit.

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

## Setup (Dev)
```bash
cp .env.example .env
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Ausgabe als FIELD_ENCRYPTION_KEY in .env eintragen; SECRET_KEY und
# POSTGRES_PASSWORD ebenfalls ersetzen.

docker compose up --build
```

- Web: <https://localhost> (TLS über Caddys interne CA)
- Mailhog: <http://localhost:8025>
- Admin: <https://localhost/admin/>

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
- Der Playwright-Smoke-Test läuft im Profil `e2e` gegen Caddy.
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
