
---

## 📄 `PLAN.md`

```markdown
# Plan – Club Zweisam (v1.3)

## Status
- **Aktueller Meilenstein:** M2 – Séparée (Roulette) + Vitrine
- **Letzte Aktualisierung:** 2026-11-13

## Fortschritt
- [x] M0 – Setup & Grundgerüst (2026-11-13, freigegeben)
- [x] M1 – Auth & Clubraum (2026-11-13, autonom freigegeben)
- [ ] M2 – Séparée (Roulette) + Vitrine (in Arbeit)
- [ ] M3 – Concierge (Wünsche) + Playbook (Knistern)
- [ ] M4 – Lounge (Status) + Logbuch (Feed)
- [ ] M5 – Deep Talk (Gespräch/Reparatur) + Krisenmodus
- [ ] M6 – Punkte & Belohnungen
- [ ] M7 – Admin-Backend
- [ ] M8 – RTF-Seiten
- [ ] M9 – Privacy Shield (Safe Mode)
- [ ] M10 – Härtung & Abschluss

## Vorgehen
Ein Meilenstein ist abgeschlossen, wenn alle Akzeptanzkriterien erfüllt sind,
`pytest` + `playwright` grün sind, `README.md` und `PLAN.md` aktualisiert wurden
und der Nutzer die Freigabe erteilt hat.

## Meilensteine

### M0 – Setup & Grundgerüst
**Inhalt:** Repo-Skeleton, Docker-Compose (Caddy, web, db, redis, assets, mailhog),
Django-Skeleton, Vite-Pipeline, Bind Mounts, TinyMCE lokal, Feldverschlüsselungs-Setup,
Pre-Commit, Doku-Gerüst.

**Akzeptanzkriterien:**
- `docker compose up --build` startet alle sechs Services.
- `https://localhost` liefert die Django-Startseite über Caddy (TLS via Caddy internal CA).
- Static/Media werden korrekt ausgeliefert, ohne CDN.
- Mailhog erreichbar unter `:8025` (Dev).
- Bind Mounts greifen: Template-Änderung sofort sichtbar.
- `ruff` und `black` clean, pytest leer-grün (Skeleton-Test).
- `README.md`, `PLAN.md`, `INTERVIEW.md`, `docs/*` vorhanden.

### M1 – Auth & Clubraum
**Inhalt:** Registrierung, Login, Logout, Clubraum-Gründung, Rollen (Hauptmitglied,
Moderator, Berater, Mediator, Sex-Partner/Gast, Gast/Beobachter), Einladungen per E-Mail.
**Akzeptanz:** Zwei Nutzer können Clubraum gründen, einladen, annehmen. Rollen
haben korrekte Permissions. Einladungen laufen ab. Widerruf wirkt sofort.

### M2 – Séparée (Roulette) + Vitrine
**Inhalt:** Frage-Decks A–D, Antwortformate, serverseitige Match-Erkennung, Match-Matrix
(Fantasie+Fantasie, Vielleicht-Fälle), Freigabe-Schalter, Symmetrie, Grenzschutz,
Feldverschlüsselung für `SecretAnswer`, Datenminimierung nach Match.
**Akzeptanz:** Antworten sind vor Match für niemanden lesbar (außer Verfasser).
Match zeigt beide Antworten symmetrisch. Kein Match leakt nichts. Grenze erscheint
nur als „Grenze respektiert". Nach 30 Tagen werden Nicht-Matches gelöscht.

### M3 – Concierge (Wünsche) + Playbook (Knistern)
**Inhalt:** Wunschkarten (5 Typen), Antwortoptionen, beidseitige Bestätigung,
Challenge-Bibliothek, Timer, Abbruch, Tages-Deckel.
**Akzeptanz:** Wünsche können gestellt, angenommen, alternativ beantwortet, abgelehnt
werden. Keine Ketten-Wünsche. Challenges Stufe 3 nur nach Opt-in.

### M4 – Lounge (Status) + Logbuch (Feed)
**Inhalt:** Check-in (3-Tage-Barometer + opt-in Wochenrückblick), Feed mit Ereignistypen,
Filter, inhaltslose Benachrichtigungen, Safe-Mode-Flag, Server-Queue.
**Akzeptanz:** Feed zeigt keine Geheiminhalte. Safe Mode queue't Benachrichtigungen.
Bei Deaktivierung werden sie inhaltslos zugestellt.

### M5 – Deep Talk (Gespräch/Reparatur) + Krisenmodus
**Inhalt:** Leitfragen, Time-out, Versöhnungskarten, separater Krisenmodus mit
Hilfsverweis.
**Akzeptanz:** Krisenmodus ist eigenes Sub-Modul, nicht Teil von Deep Talk. Harte
Verweise auf professionelle Hilfe. Keine Gamification im Krisenmodus.

### M6 – Punkte & Belohnungen
**Inhalt:** Ledger, Verdienen-Regeln, Deckelung (10/Tag, 3 aus Challenges),
Belohnungskatalog, Einlöse-Workflow, Rückbuchung, Gast-Ledger (isoliert 1:1).
**Akzeptanz:** Kein Punktabzug für Nein. Rückbuchung nur beidseitig. Gast-Ledger
isoliert, kein Wettbewerb.

### M7 – Admin-Backend
**Inhalt:** Dashboard (aggregiert), CRUD für Fragen/Decks/Belohnungen/Challenges,
Nutzer-/Clubraum-Verwaltung, Audit-Log (append-only, hash-chain), Break-Glass-Anträge
(nur Metadaten + geteilte Einträge, Vier-Augen, 24h, Nutzer-Benachrichtigung),
Banner „Zugriff protokolliert".
**Akzeptanz:** Admin sieht keine Klartext-Geheimantworten. Break-Glass blockiert auf
E2EE-Klassen (Geheimantworten, Grenzen, ungeteilte Fantasie-Wünsche). Jeder Zugriff
erzeugt Audit-Eintrag und Nutzer-Benachrichtigung.

### M8 – RTF-Seiten
**Inhalt:** Modell `StaticPage`, TinyMCE lokal, Media-Upload, Admin-Editor für AGB,
Impressum, Datenschutz, Partner, Disclaimer.
**Akzeptanz:** Seiten sind als Einzelseiten editierbar. Bilder-Upload funktioniert.
Nur Super-Admin/Plattform-Admin darf bearbeiten.

### M9 – Privacy Shield (Safe Mode)
**Inhalt:** Clientseitig, Decoy-Screen (Notizen/RSS), Biometrie/PIN-Rückkehr,
Server-Queue für Benachrichtigungen, keine Server-Roundtrips im Aktivierungsmoment.
**Akzeptanz:** Safe Mode in <100 ms aktiv. Keine externen Requests. Kein anderer
sieht, dass Safe Mode aktiv ist.

### M10 – Härtung & Abschluss
**Inhalt:** `bandit`, `pip-audit`, DSGVO-Export/Löschung, Lasttest, Security-Review,
Doku-Abschluss, Feldverschlüsselungs-Rotation.
**Akzeptanz:** Alle Tests grün. DSGVO-Flows geprüft. Feldverschlüsselung nachweisbar.
Doku vollständig.

## Cross-Cutting (ab M0 mitdenken)
- Feldverschlüsselung (Django-Fernet) für sensible Modelle
- Audit-Log als Basisklasse in `apps/core`
- Safe-Mode-Flag im `User`-Modell
- Permissions-Design: keine Modellrechte für Geheiminhalte an Admin-Gruppen
- Benachrichtigungen: Queue-fähig, inhaltslos