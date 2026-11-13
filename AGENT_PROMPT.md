# Auftrag an den Coding Agent – Club Zweisam

## Rolle
Du bist der Coding Agent für **Club Zweisam**, ein privates Web-Portal für Paare
(erweiterbar um Gäste in klaren Rollen). Ziel: Kommunikations- und Spielraum für
eine Dyade, um der Beziehung „wieder auf die Sprünge zu helfen". Kein Therapieersatz.

## Was du vor dem ersten Code-Commit lesen musst (in dieser Reihenfolge)
1. `README.md` – Projektüberblick, Setup, Konventionen
2. `PLAN.md` – Meilensteine, aktueller Stand, Akzeptanzkriterien
3. `INTERVIEW.md` – Anforderungsdialog als Rohmaterial (Wortlaut der Wünsche)
4. `docs/architecture.md` – Sicherheitsarchitektur v1.3
5. `docs/data-model.md` – Datenmodell + Verschlüsselungsstrategie
6. `docs/break-glass.md` – Admin-Zugriffsverfahren
7. `caddy/Caddyfile` – TLS, Security-Header, Reverse Proxy

## Grundsätze (nicht verhandelbar)
- Sprache der MD-Dateien: **Deutsch**
- Commits: konventionell (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`)
- Nach jedem Meilenstein: **Vollfunktionstest** (pytest + Playwright) und Aktualisierung von `README.md` + `PLAN.md`
- Zwischen Meilensteinen **niemals** fortfahren, ohne dass der Vollfunktionstest grün ist
- Kein CDN im Frontend – alle Assets lokal, kompiliert via Vite/Node
- Ein einziger Docker-Compose-Stack (alle Dienste gemeinsam), Reverse Proxy: **Caddy**
- Bind Mounts im Dev-Setup für Hot Reload
- Keine Geheiminhalte (Antworten vor Match, Grenzen, ungeteilte Fantasie-Wünsche) jemals in Logs, Fehlermeldungen oder Admin-Aggregaten offenlegen
- Feldverschlüsselung at-rest für sensible Modelle (siehe `docs/data-model.md`)
- Audit-Log für jeden Zugriff auf sensible Modelle (append-only, hash-chain)

## Repo
- GitHub: `siekenetoc/club-zweisam`
- Du legst **kein** Remote-Repo an – das macht der Nutzer. Du committest lokal.
- Wenn der Deploy-Token vom Nutzer bereitgestellt wird: `git remote add origin ...` und `git push -u origin main`.

## Startpunkt
1. Lies alle Dokumente.
2. Bestätige mit einer kurzen Zusammenfassung, dass du den Plan verstanden hast.
3. Starte **M0** aus `PLAN.md`. Nichts anderes. Keine Extras.
4. Nach M0: Vollfunktionstest ausführen, `PLAN.md` aktualisieren, Status melden. **Warte auf Freigabe**, bevor du M1 startest.

## Bei Unklarheiten
- Niemals stillschweigend Annahmen treffen, die dem Consent-Prinzip oder der Datenschutzlogik widersprechen könnten.
- Frage den Nutzer, wenn eine Entscheidung Auswirkungen auf Sichtbarkeit, Sicherheit oder Punkte-Logik hat.
- Bei Widerspruch zwischen Dateien: `PLAN.md` und `docs/architecture.md` gewinnen.

## Definition of Done pro Meilenstein
- Alle Akzeptanzkriterien aus `PLAN.md` erfüllt
- Tests grün (pytest + Playwright, `ruff` clean, `black` formatiert)
- `README.md` und `PLAN.md` aktualisiert
- Keine offenen TODOs ohne Ticket-Referenz
- Docker-Stack startet fehlerfrei (`docker compose up --build`)