# Interview / Anforderungsdialog – Rohmaterial

Dieses Dokument hält den Entstehungsdialog fest. Es ist **Rohmaterial** und
nicht die finale Spezifikation. Bei Widerspruch gewinnen `PLAN.md` und
`docs/architecture.md`.

## Ausgangsidee
Paarberater-Portal im Internet: Status, geheime erotische Fragen mit
Übereinstimmungs-Score, gegenseitige Bewertungen, Knistern-Funktionen,
Wünsche mit Punkten für Erfüllende. Kommunikationstool für einen privaten
Club zu zwei, um der Beziehung auf die Sprünge zu helfen.

## Iterative Entscheidungen

### Runde 1 – Grundfunktionen
- Clubraum zu zweit, Status, geheime Fragen, Match-Score, gegenseitige Bewertungen,
  Knistern, Wünsche mit Punkten für Erfüllende.
- Prinzipien: Consent vor Spiel, Nein ist neutral, Geheimnis schützt, Anerkennung
  statt Wettkampf, Reparatur ist Teil des Spiels.

### Runde 2 – Priorisierung
- Erst Fragen/Match, dann Punkte.
- Punkte einlösbar.
- Inhalte von romantisch bis erotisch, inkl. sexuelle Vorlieben.
- Safe Mode (Panic-Button mit Decoy-Screen) gewünscht.
- **Alles auf einmal** – kein MVP-Denken.

### Runde 3 – Rollen und Roulette
- Weitere Personen per E-Mail einladbar: Moderator, Berater, Mediator, Sex-Partner.
- Roulette-Fragen mit vorgegebenen Antworten, thematisch: Reden, Kuscheln,
  Rollenspiel, sexuelle Vorlieben.

### Runde 4 – Voller Fragenkatalog
- 40 Karten über 4 Decks (A: Reden, B: Kuscheln, C: Rollenspiel, D: Sexuelle
  Vorlieben, Opt-in).
- Match-Regeln pro Frage.

### Runde 5 – Rollen- und Rechte-Matrix
- Moderator sieht keine Geheimantworten, nur Status.
- Berater und Mediator sind getrennt (auch wenn Gemini sie zusammenfassen wollte).
- Sex-Partner mit eigener Consent-Matrix.

### Runde 6 – Punkte und Belohnungen
- Verdienen-Liste, Deckelung, Rückbuchung, Katalog (romantisch, neckisch, erotisch,
  Alltag, Erlebnisse), Gast-Konten.

### Runde 7 – Wünsche und Challenges
- Wunschkarten-Logik (5 Typen, 7 Antwortoptionen, Status-Workflow).
- Knistern-Bibliothek (8 Kategorien).

### Runde 8 – UI & Sicherheit
- Screens, Datenschutz, Lösch- und Exportrechte.

### Runde 9 – Feed und One-Pager
- Feed als Chronik ohne Geheiminhalte.
- One-Pager-Zusammenfassung.

### Runde 10 – Präzisierungen
- Status enthalten.
- **Gemeinsame Vorlieben beiden sichtbar** (Symmetrie, neuer Screen „Gemeinsamkeiten").
- **Admin-Backend** mit CRUD und Dashboard.

## Wortmarke
**Club Zweisam** – Exklusivität, Freiwilligkeit, geschützter Raum.
Tonalität: gehoben, privat, nicht klinisch, nicht sexualisiert.
Modulnamen:
- Lounge (Dashboard)
- Séparée (Roulette)
- Vitrine (Gemeinsamkeiten) – final statt „Tresor"
- Concierge (Wünsche)
- Playbook (Knistern/Challenges)
- Deep Talk (Gespräch + Reparatur)
- Logbuch (Feed)
- Privacy Shield (Safe Mode)

## Festgefahrene Entscheidungen
- **Kein freier Chat.** Kommunikation über Wünsche und Deep Talk.
- **Gäste**: isolierter 1:1-Punkte-Ledger, kein Wettbewerb mit Dyade.
- **Krisenmodus** ist eigenes Sub-Modul unter Deep Talk, kein Gamification.
- **E2EE verworfen** zugunsten Feldverschlüsselung at-rest + Audit + Break-Glass.
  Grund: Django bleibt serverseitig (Nutzerentscheidung).

## Was das System ausdrücklich nicht ist
- Kein Therapieersatz
- Keine Währung für Sex
- Kein Druckmittel
- Keine Leistungsbewertung
- Kein Wettbewerb zwischen Paaren
- Kein heimliches Überwachen