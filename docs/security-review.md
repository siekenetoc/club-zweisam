# Security-Review – Club Zweisam (M10)

Stand: 2026-11-13. Grundlage: `docs/architecture.md`, `docs/data-model.md`,
`docs/break-glass.md`, `PLAN.md`.

## Automatisierte Prüfungen

| Prüfung | Ergebnis |
|---|---|
| `pytest` | 150 Tests grün |
| Playwright E2E | 2 Tests grün (Registrierung, Clubraum, Séparée, Concierge, Playbook, Lounge, Logbuch, Deep Talk, Krisenmodus, Punkte, Privacy Shield, Admin-Banner, Seiten) |
| `ruff check .` | clean |
| `black --check .` | clean |
| `bandit -r apps -q` | keine Befunde |
| `pip-audit -r requirements.txt` | keine bekannten Schwachstellen |
| `pip-audit -r requirements-dev.txt` | keine bekannten Schwachstellen |
| `manage.py check --deploy` (prod) | keine Befunde |
| `manage.py audit_verify` | Hash-Chain unversehrt |

Abhängigkeiten wurden in M10 aktualisiert: Django 5.2.17 LTS, cryptography 50.0.0,
Pillow 13.0.0. Produktions-Images enthalten keine Dev-Werkzeuge (pytest, black,
ruff, bandit, playwright, pip-audit).

## Feldverschlüsselung

- `EncryptedTextField` verschlüsselt at-rest mit Fernet; Präfix `enc:v1:`.
- Tests weisen nach: `SecretAnswer`, `Clubroom.safe_word`, `Wish.body` und
  `WishResponse.note` liegen in der Datenbank als Ciphertext vor; Klartext ist
  nicht enthalten.
- Rotation: `FIELD_ENCRYPTION_KEY_OLD` erlaubt Lesen mit altem Schlüssel;
  `manage.py encrypt_rotate` re-verschlüsselt alle sensiblen Felder mit dem
  aktuellen Schlüssel. Der Test prüft Ciphertext-Wechsel und Lesbarkeit nach
  Entfernen des alten Schlüssels.
- Grenze: Ein Super-Admin mit DB- und Schlüsselzugriff kann technisch lesen.
  Schutz ist organisatorisch + Audit, nicht kryptografisch erzwungen.

## Zugriff und Geheimnisschutz

- Admin-Registry enthält keine `SecretAnswer`, `Match`, `Wish`, `FeedEvent`
  oder andere Geheiminhalte. Sensible Admin-Routen existieren nicht.
- Clubraum-Admin blendet `safe_word` aus; Anlegen/Sperren erfolgt über die App.
- Break-Glass nur für Metadaten und freigegebene Matches; Geheimantworten,
  Grenzen und Wünsche werden auf Service-Ebene blockiert.
- Vier-Augen-Prinzip, 24-Stunden-Fenster, Pflichtbegründung, Audit-Eintrag und
  inhaltslose Nutzer-Benachrichtigung sind getestet.
- Logbuch-Metadaten werden über eine Sperrliste bereinigt; Tests prüfen, dass
  Titel, Inhalte, Notizen, Antworten und Safeword nicht im Feed erscheinen.
- Safe Mode erzeugt keinen Feed-Eintrag und keine Benachrichtigung; das Flag ist
  in der Admin-Nutzeransicht ausgeblendet.

## Transport und Header

- Caddy setzt CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy;
  in Produktion zusätzlich HSTS und Permissions-Policy.
- CSP: `default-src 'self'`, `script-src 'self' 'unsafe-eval'`,
  `style-src 'self' 'unsafe-inline'`, `img-src 'self' data:`,
  `connect-src 'self'`, `frame-ancestors 'none'`.
- `unsafe-eval` ist für Alpine.js erforderlich; `unsafe-inline` für Styles von
  Admin/TinyMCE. TinyMCE wurde unter CSP im Browser geprüft: Editor lädt,
  keine CSP-Verstöße.
- Doppelte Header (Django + Caddy) sind funktional unkritisch.

## DSGVO und Aufbewahrung

- Export: `/konto/export/` (JSON-Download) und `manage.py gdpr_export --user`.
  Export enthält eigene Wünsche, eigene Antwort-Notizen, Check-ins, Punkte,
  Benachrichtigungen und Audit-Einträge; keine Geheiminhalte Dritter, kein Safeword.
- Löschung: `/konto/loeschen/` (Passwort + Bestätigung) und
  `manage.py gdpr_delete --user --confirm`. Konto wird anonymisiert,
  Mitgliedschaften widerrufen, eigene Check-ins/Benachrichtigungen/Ledger
  gelöscht, eigene Wunschinhalte und Antwort-Notizen geleert.
- Audit-Einträge bleiben append-only und pseudonym erhalten (Sicherheitsinteresse).
- Retention: `manage.py roulette_purge` (30 Tage), `manage.py wishes_purge`
  (90 Tage für abgelehnte/Grenz-Wünsche).
- Grenze: Bei Löschung eines alleinigen Hauptmitglieds bleibt der Clubraum ohne
  aktives Hauptmitglied zurück. Das ist eine bewusste, dokumentierte Folge.

## Lasttest (Dev-Baseline)

`python scripts/loadtest.py` gegen den Dev-Stack (Django-Dev-Server, nicht
Gunicorn/Prod):

- `/healthz`, 300 Requests, Concurrency 20: 38,6 req/s, 0 Fehler, p95 89 ms,
  p99 194 ms.
- `/`, 200 Requests, Concurrency 20: 38,9 req/s, 0 Fehler, p95 66 ms,
  p99 214 ms.

Die Werte sind eine Funktions-/Stabilitätsbaseline, kein Produktions-Benchmark.

## Externe Messenger

WhatsApp, Telegram, Signal, Element und Gotify sind ausschließlich als
**inhaltslose Push-Kanäle** angebunden: Der Text ist immer
„Club Zweisam: Neues Ereignis im Portal. <PORTAL_BASE_URL>/lounge/“.
Es werden keine Titel, Wünsche, Antworten, Matches, Ereignistypen oder Namen
übertragen. Jeder Nutzer muss den Kanal in der Lounge ausdrücklich abonnieren;
Safe Mode puffert die Zustellung. Kanal-Secrets und Ziele sind feldverschlüsselt.

Grenzen: Externe Anbieter sehen Metadaten und den generischen Text. Telegram-Bots
sind nicht E2EE; Element benötigt einen unverschlüsselten Hinweisraum oder einen
E2EE-fähigen Client; Signal nutzt die inoffizielle signal-cli-REST-API; WhatsApp
benötigt Meta-Templates. Ein Inhalts-Spiegel oder automatische externe Gruppen
werden bewusst nicht angeboten.

## Restrisiken und bewusste Grenzen

- Super-Admin mit DB- und Schlüsselzugriff kann alles lesen.
- Lokaler Privacy-Shield-PIN ist ein Sichtschutz, keine kryptografische Sperre;
  ein Reload oder DevTools kann die Ablenkung umgehen.
- Safe-Mode-Server-Flag wird verzögert synchronisiert; Benachrichtigungen im
  kurzen Fenster davor können bereits zugestellt sein.
- Einladungs-Token steht in der URL und kann in Access-Logs erscheinen; der
  Token ist gehasht gespeichert und läuft ab.
- Registrierung mit E-Mail-Aktivierung, Login per Benutzername/E-Mail und
  Passwort-Reset über django-allauth sind umgesetzt; 2FA und Rate-Limit bleiben offen.
- Externe Push-Kanäle sind inhaltslos und opt-in; Fehlzustellungen werden nur
  geloggt und nicht automatisch wiederholt.
- Die Signup-Form kann bei doppelter E-Mail die Existenz offenlegen (Enumeration).
- Kein automatischer Scheduler im Stack; Retention-Befehle müssen per Cron/
  systemd ausgeführt werden.
- Audit-Einträge werden nicht automatisch gelöscht.
