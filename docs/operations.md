# Betrieb – Club Zweisam

## Voraussetzungen

- Docker + Docker Compose, Domain mit TLS (Prod), ausgehende Mailzustellung
  oder SMTP-Relay.
- `.env` aus `.env.example`; `SECRET_KEY`, `FIELD_ENCRYPTION_KEY`,
  `POSTGRES_PASSWORD`, `DOMAIN` und `ACME_EMAIL` zwingend ersetzen.
- `FIELD_ENCRYPTION_KEY` erzeugen:
  `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

## Dev

```bash
cp .env.example .env
docker compose up --build
docker compose exec web python manage.py createsuperuser
```

- Web: https://club-zweisam.localhost (Caddy internal CA; https://localhost bleibt gültig)
- Mailhog: http://localhost:8025
- Tests: `docker compose exec web pytest`
- E2E: `docker compose --profile e2e run --rm playwright`

## Dev-TLS ohne Zertifikatswarnung

`club-zweisam.localhost` und `localhost` zeigen auf die Dev-Instanz. Caddy nutzt
eine interne CA. Einmalig exportieren und vertrauen:

```bash
scripts/setup-dev-tls.sh            # exportiert caddy-root.crt, zeigt Befehle
scripts/setup-dev-tls.sh --all      # libnss3-tools + systemweit + Browser-NSS (sudo)
```

- System/curl/wget: `sudo update-ca-certificates` nach Kopie in
  `/usr/local/share/ca-certificates/`.
- Firefox: eigene Zertifikatsverwaltung; Import per UI oder `certutil` im
  jeweiligen Profil (`~/.mozilla/firefox/*` bzw. Snap-Profil).
- Chrome/Chromium: `certutil -d sql:$HOME/.pki/nssdb` oder Einstellungen →
  Zertifikate verwalten; Chrome danach neu starten.
- Hostname: `*.localhost` wird hier auf Loopback aufgelöst. Falls nicht:
  `127.0.0.1 club-zweisam.localhost` in `/etc/hosts` ergänzen.
- Ohne Systeminstallation: `curl --cacert caddy-root.crt ...`.

## Prod

```bash
cp .env.example .env
# DEBUG=False, starke Secrets, echte Domain
docker compose -f docker-compose.yml up -d --build
docker compose exec web python manage.py createsuperuser
```

Der Entrypoint führt `migrate` und `collectstatic` aus; Gunicorn startet danach.
Das Prod-Image enthält keine Dev-Werkzeuge.

## E-Mail und Aktivierung

- Neue Konten sind erst nach Klick auf den Aktivierungslink nutzbar.
- Dev: Mailhog `http://localhost:8025`; Produktion: SMTP in `.env` konfigurieren.
- Django Sites (`SITE_ID=1`) auf die echte Domain setzen:
  `docker compose exec web python manage.py shell` →
  `Site.objects.filter(pk=1).update(domain="example.org", name="Club Zweisam")`.
- Passwort-Reset: `/accounts/password/reset/`.

## Admin-Zugang

- Django-Admin: `/admin/` (Staff/Superuser)
- Aggregierte Verwaltung: `/management/` (Staff)
- Break-Glass: `/management/break-glass/` (Superuser, Vier-Augen)
- Seiten bearbeiten: Superuser oder Gruppe „Plattform-Admin" (wird per Migration
  angelegt), Mitglieder der Gruppe zusätzlich `is_staff=True` setzen.

## Backups und Restore

- DB: `docker compose exec db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > backup.sql`
- Medien: Volume `media_data` bzw. Dev `backend/media`
- Caddy: Volumes `caddy_data` und `caddy_config`
- Schlüssel: `FIELD_ENCRYPTION_KEY` getrennt und sicher aufbewahren. Ohne Schlüssel
  sind DB-Backups für sensible Felder unlesbar.
- Restore: Stack stoppen, DB leeren, Dump einspielen, Volumes wiederherstellen,
  gleiche Schlüsselversion setzen, `migrate`, `collectstatic`.

## Aufbewahrung

```bash
docker compose exec web python manage.py roulette_purge      # 30 Tage
docker compose exec web python manage.py wishes_purge        # 90 Tage
docker compose exec web python manage.py audit_verify        # Hash-Chain
```

Per Cron/systemd täglich einplanen. `AuditEntry` wird nie gelöscht.

## Schlüsselrotation

1. Neuen Schlüssel erzeugen.
2. In `.env`: `FIELD_ENCRYPTION_KEY=<neu>` und `FIELD_ENCRYPTION_KEY_OLD=<alt>`.
3. `docker compose up -d web` (Neustart, damit die Einstellungen geladen werden).
4. `docker compose exec web python manage.py encrypt_rotate`
5. `FIELD_ENCRYPTION_KEY_OLD` entfernen, erneut neu starten.
6. `audit_verify` prüfen und ein Backup mit neuem Schlüssel erstellen.

## DSGVO

```bash
docker compose exec web python manage.py gdpr_export --user <username|id> --output export.json
docker compose exec web python manage.py gdpr_delete --user <username|id> --confirm
```

Self-Service: `/konto/export/` und `/konto/loeschen/` (Passwort + Bestätigung).
Löschung anonymisiert das Konto; Audit-Einträge bleiben pseudonym erhalten.

## Sicherheit und Updates

```bash
docker compose exec web bandit -r apps -q
docker compose exec web pip-audit -r requirements.txt
docker compose exec -e DJANGO_SETTINGS_MODULE=clubzweisam.settings.prod web python manage.py check --deploy
```

Bei Updates: Requirements anheben, Image neu bauen, Tests + E2E + `check --deploy`
ausführen. Security-Review: `docs/security-review.md`.

## Lasttest

```bash
python scripts/loadtest.py --url https://localhost/healthz --requests 300 --concurrency 20
```

## Logs

- Strukturierte JSON-Logs mit Sensitive-Filter (Crypto-/Secret-Felder maskiert).
- Keine Geheiminhalte in Logs; Einladungs-Token kann in Access-Logs der URL stehen.
- Audit-Log über Admin oder `manage.py audit_verify` prüfen.
