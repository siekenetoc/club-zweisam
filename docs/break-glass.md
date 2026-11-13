# Break-Glass-Verfahren – Club Zweisam

## Zweck
Administrativer Zugriff auf sensible Inhalte **nur im Ausnahmefall** (Missbrauchs-
verdacht, rechtliche Anforderung). Kein stiller Zugriff. Jeder Zugriff wird
protokolliert und den betroffenen Nutzern gemeldet.

## Was Break-Glass darf und was nicht

| Datenklasse | Break-Glass erlaubt? |
|---|---|
| Metadaten (Rollen, Einladungen, Punkte-Aggregat, Feed-Aggregat) | Ja, mit Audit |
| Geteilte Feed-Einträge (nach beidseitiger Freigabe) | Ja, mit Audit + Vier-Augen |
| Freigegebene Matches | Ja, mit Audit + Vier-Augen |
| Geheimantworten vor Match | **Nein** (Permission blockiert) |
| Grenzen | **Nein** (Permission blockiert) |
| Ungeteilte Fantasie-Wünsche (`Wish(is_private=True)`, `FantasyWish`) | **Nein** (Permission blockiert) |

## Ablauf

1. **Antrag** durch Super-Admin: Ziel, Begründung, Zeitfenster (max. 24 h).
2. **Vier-Augen-Prinzip**: zweiter Super-Admin bestätigt.
3. **Benachrichtigung** an betroffene Nutzer: „Ein Admin hat aus [Grund] auf
   Ihre Daten zugegriffen." (ohne Inhalte, ohne Ziel-Details).
4. **Zeitfenster** beginnt. Zugriff läuft nach 24 h automatisch ab.
5. **Audit-Eintrag** bei Antrag, Bestätigung, Zugriff und Ablauf.
6. **Kein stiller Zugriff**. Bei Ausbleiben der Bestätigung: Antrag verfällt.

## Technische Umsetzung
- Umsetzung im Admin-Backend unter `/management/break-glass/` (nur Super-Admins).
- Erlaubt sind nur Metadaten und beidseitig freigegebene Einträge; Geheimantworten,
  Grenzen und Wünsche sind technisch gesperrt.
- Benachrichtigung an betroffene Clubraum-Mitglieder erfolgt inhaltslos.
- `BreakGlassRequest`-Modell mit Status-Machine (pending/approved/used/expired).
- Django-Permission-Check: Lesezugriff auf geschützte Modelle nur, wenn ein
  gültiger `BreakGlassRequest` für `target_type` und `target_id` vorliegt UND
  der Anfragende im selben Antrag als `requested_by` oder `approved_by` steht.
- Middleware `BreakGlassMiddleware` prüft das pro Request.
- Sensible Modelle (siehe `data-model.md`) sind in `admin_panel` **nicht** als
  ModelAdmin registriert. Zugriff nur über dedizierte Break-Glass-Views.

## Audit
- Jeder Zugriff erzeugt `AuditEntry` mit `prev_hash`-Verkettung.
- Prüfbar über `manage.py audit_verify`.
- Nutzer können ihre eigenen Audit-Einträge einsehen (Transparenz).

## Verweigerung
- Ohne Vier-Augen-Bestätigung: kein Zugriff.
- Ohne gültiges Zeitfenster: kein Zugriff.
- Auf geschützte Klassen: **immer** verweigert, unabhängig vom Antrag.

## Was das Verfahren nicht kann
- Es ist **kein** kryptografischer Schutz. Ein Super-Admin mit DB- und
  Schlüsselzugriff kann technisch alles lesen. Break-Glass macht Zugriffe
  sichtbar und rechenschaftspflichtig – nicht unmöglich.
- Muss in AGB und UI klar kommuniziert werden.