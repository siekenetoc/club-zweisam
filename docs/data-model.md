# Datenmodell – Club Zweisam (v1.3)

## Konventionen
- Primärschlüssel: `BigAutoField` (Django-Standard).
- Zeitstempel: `created_at`, `updated_at` auf allen Modellen.
- Sensible Felder: feldverschlüsselt via `apps.core.crypto.EncryptedTextField`.
- Audit: Basisklasse `apps.core.audit.AuditedModel` für sensible Modelle.
- Soft-Delete: `deleted_at` auf `Clubroom`, `Wish`, `FeedEvent`.

## Apps und Modelle

### accounts
- `User` (AbstractUser)
  - `is_safe_mode_active: bool`
  - `notification_queue_id: UUID` (Redis-Queue-Referenz)
  - `age_verified: bool`
  - `tos_accepted_at: datetime`

### clubroom
- `Clubroom`
  - `name`, `slug`, `created_by` (FK User)
  - `safe_word: EncryptedTextField`
  - `rules: TextField` (Klartext, nicht sensibel)
- `Membership`
  - `clubroom` (FK), `user` (FK), `role` (Choice)
  - `module_permissions: JSONField` (pro Modul: bool)
  - `invited_by` (FK User), `invited_at`, `accepted_at`, `revoked_at`
- `Invitation`
  - `clubroom`, `email`, `role`, `token` (UUID, gehasht)
  - `expires_at`, `accepted_at`, `revoked_at`

### roulette
- `Deck`
  - `code` (A/B/C/D), `title`, `intensity`, `requires_opt_in`
- `Question`
  - `deck` (FK), `order`, `text`, `answer_type` (Choice)
  - `match_rule: JSONField` (Regeln pro Antwortkombination)
- `Round`
  - `clubroom`, `deck`, `started_by`, `started_at`, `ended_at`
- `SecretAnswer` (AuditedModel)
  - `round`, `question`, `user`
  - `answer: EncryptedTextField`
  - `is_boundary: bool`
  - `deleted_at` (nach Match/Datenminimierung)
- `Match`
  - `round`, `question`, `user_a`, `user_b`
  - `result` (full/partial/none)
  - `boundary_a: bool`, `boundary_b: bool` (Grenze gesetzt, Inhalt nie sichtbar)
  - `released_by_a: bool`, `released_by_b: bool`
  - `released_at` – erst nach beidseitiger Freigabe sichtbar
- `DeckOptIn`
  - `clubroom`, `deck`, `user` (nur für `requires_opt_in`-Decks, z. B. Deck D)

### vitrine
- `Commonality`
  - `clubroom`, `source_type` (match/wish/challenge/reward)
  - `source_id`, `category`, `created_at`
  - nur aus **beidseitig freigegebenen** Quellen erzeugt

### wishes
- `Wish` (AuditedModel)
  - `clubroom`, `created_by`, `type` (offen/konkret/fantasie/test/grenz)
  - `category`, `intensity`, `timeframe`
  - `title` (Klartext), `body: EncryptedTextField`
  - `is_private: bool`
  - `status` (draft/placed/replied/agreed/fulfilled/pending/confirmed/
              rejected/boundary/postponed/expired)
  - `responded_at`, `agreed_at`, `fulfilled_at`, `confirmed_at`
- `WishResponse`
  - `wish`, `responded_by`
  - `action` (accept/partial/alternative/postpone/reject/boundary/talk)
  - `note: EncryptedTextField`
  - eindeutig pro `wish` + `responded_by` – keine Ketten-Wünsche

### playbook
- `Challenge`
  - `category`, `title`, `duration_min`, `intensity`, `consent_stage`, `points`
- `ChallengeRun`
  - `challenge`, `clubroom`, `started_by`, `started_at`, `completed_at`
  - `user_a`, `user_b` (Hauptmitglieder zum Start, kanonisch sortiert)
  - `confirmed_by_a: bool`, `confirmed_by_b: bool`
  - `aborted_at`, `aborted_by` (Abbruch durch eine Person, sofort wirksam)
- `PlaybookOptIn`
  - `clubroom`, `user` (Opt-in für Stufe 3, beidseitig erforderlich)

### feed
- `FeedEvent`
  - `clubroom`, `event_type`, `actor` (nullable), `target_type`, `target_id`
  - `metadata: JSONField` (nur nicht-sensible Felder, sensible Schlüssel werden verworfen)
  - `deleted_at` (auf Nutzerwunsch, dann Platzhalter „Eintrag entfernt", Metadaten geleert)
- `Notification`
  - `user`, `clubroom`, `event_type` (kein Inhalt), `queued_during_safe_mode`
  - `delivered_at` (null = im Safe Mode gepuffert)

### points
- `Ledger`
  - `clubroom`, `owner` (FK User), `balance`
- `Entry`
  - `ledger`, `delta`, `reason`, `actor`, `confirmed_by_other: bool`
- `Reward`
  - `category`, `title`, `cost`, `consent_stage`
- `Redemption`
  - `reward`, `requested_by`, `status`, `accepted_by`, `completed_at`

### deep_talk
- `TalkSession`
  - `clubroom`, `mode` (talk/repair/crisis), je Modus höchstens eine aktive Sitzung
  - `started_by`, `started_at`, `ended_at`
  - `timeout_at`, `timeout_by` (Time-out ohne Begründung)
- `TalkPrompt`
  - `session`, `text`, `answered: bool`

### admin_panel
- `BreakGlassRequest`
  - `requested_by`, `approved_by`, `target_type`, `target_id`
  - `reason: TextField`
  - `approved_at`, `expires_at`, `used_at`
  - `users_notified: bool`
- `AuditEntry`
  - `actor`, `action`, `target_type`, `target_id`, `reason`
  - `created_at`, `prev_hash`, `hash`

### pages
- `StaticPage`
  - `slug`, `title`, `content_html`, `media` (FK zu `PageMedia` optional)
  - `is_published`, `updated_at`, `updated_by`
- `PageMedia`
  - `page`, `file`, `alt_text`, `uploaded_at`

### lounge
- `CheckIn`
  - `clubroom`, `user`, `date`, `mood`, `energy`, `closeness` (je 1–5)
  - eindeutig pro Nutzer, Clubraum und Tag
- `WeeklyReviewOptIn`
  - `clubroom`, `user` (Opt-in für persönlichen Wochenrückblick)

### core
- `EncryptedTextField` – Feld-Mixin
- `AuditedModel` – abstrakte Basisklasse
- `SafeModeMixin` – Flag + Queue-Logik

## Lösch- und Aufbewahrungsregeln
- `SecretAnswer`: Inhalt gelöscht beim Rundenende, spätestens nach 30 Tagen.
  `Match` bleibt mit Ergebnis und Freigabe-Flags erhalten.
- `Match(result=none)`: nach 30 Tagen gelöscht (`roulette_purge`).
- `Match`: bleibt (Ergebnis), Antworten weg.
- `Wish(rejected)`: nach 90 Tagen Inhalte gelöscht, Metadaten bleiben.
- `FeedEvent`: auf Nutzerwunsch → `deleted_at`, Anzeige „Eintrag entfernt".
- `AuditEntry`: **nie löschen** (append-only).

## Indizes
- `SecretAnswer (round_id, question_id, user_id)`
- `Match (round_id, question_id)`
- `Wish (clubroom_id, status)`
- `FeedEvent (clubroom_id, created_at DESC)`
- `AuditEntry (created_at DESC)`, `AuditEntry (target_type, target_id)`