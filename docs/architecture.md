# Architektur – Club Zweisam (v1.3)

## Überblick
Ein einziger Docker-Compose-Stack. Caddy ist der einzige öffentlich erreichbare
Dienst (80/443). Alle anderen Dienste sind nur im internen Bridge-Netzwerk
`clubzweisam_net` erreichbar.

Internet
│
▼
┌──────┐ ┌──────┐ ┌──────┐
│Caddy │──────▶│ web │──────▶│ db │
└──────┘ │Gunic.│ └──────┘
│Django│ ┌──────┐
│ │──────▶│redis │
└──────┘ └──────┘
▲
│ (Dev: Bind Mount, Static-Build)
┌──────┐
│assets│ (Vite)
└──────┘
▲
│ (Dev only)
┌──────┐
│mail │ (Mailhog)
└──────┘
text


## Komponenten

### Caddy
- Reverse Proxy, TLS, HTTP/3.
- Automatisches TLS: Prod = Let's Encrypt, Dev = internes CA.
- Security-Header zentral (HSTS, CSP, X-Frame-Options, Referrer-Policy).
- Static/Media: werden vom Django-Container (Whitenoise) ausgeliefert,
  Caddy leitet nur durch. Optional später X-Accel / direkte Auslieferung.

### Django (web)
- WSGI via Gunicorn.
- Apps: `accounts`, `clubroom`, `roulette`, `vitrine`, `wishes`, `playbook`,
  `feed`, `lounge`, `points`, `deep_talk`, `crisis`, `admin_panel`, `pages`, `core`.
- `core` enthält: Feldverschlüsselungs-Mixin, Audit-Base, Permissions, Crypto-Helper.

### PostgreSQL (db)
- Persistente Daten. Sensible Felder feldverschlüsselt (siehe `data-model.md`).
- Backups: Dumps sind verschlüsselt, weil Felder verschlüsselt sind.

### Redis
- Cache, Session-Backend optional.
- Notification-Queue (für Safe-Mode-Queueing).

### Assets (Dev)
- Vite-Watch-Modus, schreibt nach `backend/static/dist/`.
- In Prod: einmaliger Build, Artefakte werden ins Web-Image kopiert.

### Mailhog (nur Dev)
- Lokaler SMTP-Fänger, Web-UI auf `:8025`.

## Sicherheitsschichten

### 1. Transport
- TLS überall (Caddy). Kein HTTP-Fallback in Prod.

### 2. At-Rest (Feldverschlüsselung)
- Bibliothek: `cryptography` (Fernet) via `django-fernet-fields`-ähnlichem
  eigenen Mixin in `apps/core/crypto.py`.
- Schlüssel: `FIELD_ENCRYPTION_KEY` in `.env`, **niemals** im Repo.
- Verschlüsselte Modelle:
  - `roulette.SecretAnswer` – Antworten vor Match
  - `roulette.Boundary` – gesetzte Grenzen
  - `wishes.Wish` – wenn `is_private=True`
  - `wishes.FantasyWish` – ungeteilte Fantasien
- Rotation: Schlüssel-Version im Feldnamen (z.B. `encrypted_v1`), Migration
  bei Rotation möglich.

### 3. Zugriffskontrolle
- Django-Permissions, rollenbasiert.
- Admin-Gruppen haben **kein** Standard-Modellrecht auf `SecretAnswer`,
  `Boundary`, `Wish(is_private=True)`, `FantasyWish`.
- Zugriff nur über `BreakGlassRequest`-Flow (siehe `break-glass.md`).

### 4. Audit
- Jede Lese-/Schreiboperation auf sensible Modelle wird protokolliert.
- Tabelle `core.AuditEntry`: `actor`, `action`, `target_type`, `target_id`,
  `reason`, `timestamp`, `prev_hash`, `hash`.
- Append-only. Hash-Chain: `hash = sha256(prev_hash + serialized_entry)`.
- Prüfbar über `manage.py audit_verify`.

### 5. Break-Glass
- Antrag → Vier-Augen-Bestätigung → 24-h-Fenster → Nutzer-Benachrichtigung
  → Audit-Eintrag.
- Nur Metadaten + geteilte Einträge. Geheiminhalte bleiben für Admin
  unzugänglich (Permission-Ebene).

### 6. Datenminimierung
- Matches: Antworten bleiben bis zum Rundenende sichtbar, spätestens 30 Tage;
  danach werden nur Match-Ergebnis und Freigabe-Flags behalten.
- Nicht-Matches: 30 Tage, dann werden Antworten und Match-Metadaten gelöscht.
- Abgelehnte Wünsche: 90 Tage, dann Inhalte gelöscht, nur Metadaten.

### 7. Benachrichtigungen
- Niemals Inhalte. Nur Event-Typ.
- Safe-Mode-Flag: Queue auf Server, Zustellung beim Deaktivieren.
- Privacy Shield: Decoy-Screen rein clientseitig, Aktivierung ohne Server-Roundtrip.
  Der Server-Flag wird verzögert synchronisiert; bis dahin eintreffende
  Benachrichtigungen können bereits zugestellt sein. Der PIN bleibt lokal im
  Browser und ist ein Sichtschutz, keine kryptografische Sperre.

## Was das System nicht leistet (bewusste Grenze)
- Kein kryptografischer Schutz gegen Super-Admin mit DB- und Schlüsselzugriff.
- Kein Client-E2EE.
- Schutz ist organisatorisch, durch Permissions und Audit.
- Muss in AGB und UI klar kommuniziert werden.

## Nicht-Ziele
- Kein freier Chat.
- Kein Wettbewerb zwischen Paaren.
- Keine Währung für Sex.
- Kein Therapieersatz.

## Betrieb
- Ein Stack, ein Netzwerk.
- Backups: verschlüsselte DB-Dumps, Caddy-Volumes separat.
- Logs: strukturiert (JSON), sensibel-gefiltert (Crypto-Felder maskiert).
- Healthchecks pro Service.
- DSGVO: Export, Löschung, Auskunft (M10).
