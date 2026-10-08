# Zusammenfassung für Alex: #64 Inbox sortierbar + #65 „Als Serie gruppieren"

## #64 — Sortierbare Inbox-Liste (Briefing fertig, Planprüfer: APPROVE)

**Was wird gemacht?** Die Vorschlagsliste auf der Startseite bekommt drei Klick-Felder „Name | Datum | Größe"; die Reihenfolge bleibt für den Browser-Tab erhalten. Der Server lernt zwei neue Infos pro Listeneintrag dazu: letztes Änderungsdatum und Gesamtgröße der Videodateien.

**Warum?** Bisher ist die Reihenfolge Zufall (Dateisystem); mit vielen Kandidaten siehst du nicht, was frisch oder groß ist — genau das brauchst du zum Priorisieren.

**Was du noch kippen kannst (eine Feinentscheidung):** Standard-Reihenfolge ohne gespeicherte Wahl = „neueste zuerst" (Datum absteigend). Die Gegenoption war „alphabetisch" — die Runde war gespalten: Produktberater wollte „neueste zuerst" (Inbox-Erwartung), Designer „alphabetisch". Wir haben „neueste zuerst" gewählt, weil die Roadmap-Begründung Priorisierung heißt.

**Risiken in Klartext:**
- Nach dem ersten Deploy kann der erste Listen-Aufruf spürbar langsamer sein, weil der Server jetzt jede Videodatei einer Mappe „wiegt" (NAS-Leselast). Absicherung: der 30-Sekunden-Vorschau-Zugriff bleibt unverändert; Beobachtungspunkt nach Deploy, kein Blocker.
- Wenn Dateien auf dem NAS nicht lesbar sind, zeigt der Eintrag weiterhin statt zu verschwinden: Datum/Größe fehlen dann einfach in der Zeile (so festgelegt und als Test abgesichert).
- Ausführung durch den Gate-A2-Worker in der Container-Pipeline; enger Erlaubnis-Rahmen (6 Dateien + 2 neue Testdateien) und Verbotsliste sind im Briefing festgezurrt. **Vor dem Lauf fehlt noch die Ausgangsmessung (AK0): bitte `pytest` + `npm run test:frontend` laufen lassen und die Ausgabe ins Briefing eintragen — das kann ich als Agent nicht selbst.**
- Stichproben-pflichtige Themen (Geld, Außenwirkung, Recht/Registrierung, Kaufentscheidungen): keine betroffen.

## #65 — „Als Serie gruppieren": nur die Weg-Frage ist offen

**Was wird gemacht?** Folgen mit SxxExx-Namen in der Inbox werden automatisch zu einer Serie gruppiert (nur Ansicht, es wird keine Datei verschoben), mit Vorschlagskarte und Ankreuzfeldern; per Bestätigung geht die Gruppe in den bekannten Serien-Ablauf.

**Warum?** Deine 11-Staffel-Serie liegt als Hunderte Einzeldateien in der Inbox; heute müsstest du jede Datei einzeln verarbeiten.

**Die eine offene Frage — wie die Gruppe übergeben wird:**
- **Weg 1 („Auftrag pro Folge"):** sicher, kein Eingriff in die Server-Logik — aber ~264 einzelne Aufträge, 264 Metadaten-Abfragen bei den Serienanbietern, unübersichtliche Warteschlange. Widerspricht deinem „ein Ordner"-Bild.
- **Weg 2 (empfohlen):** Das Programm sagt dem Server in einem Auftrag: „diese Dateiliste gehört zusammen" — genau dein Ordner-Bild: eine Bestätigung, ein Auftrag. Preis: Der Verarbeitungskern (der meistgetestete Teil des Projekts) braucht eine kleine, klar abgegrenzte Erweiterung plus Begleittests; du reviewst den Server-Teil einzeln.
- Ein möglicher Abkürzungsweg (ein Auftrag, Server unverändert) wurde **verworfen und belegt**: Er hätte Dateien anderer Inbox-Projekte in die Quarantäne rücken können (Nachweise im Optionen-Dokument, `65-uebergabe-optionen.md`). Die Runde war hier geteilt: Produktberater für die Abkürzung, Risikoprüfer dagegen — meine eigene Nachprüfung gab dem Risikoprüfer recht.
- **Randfund (bestehend, nicht neu):** schon heute räumt jeder Inbox-Einzel-Auftrag leere Ordner in der Inbox weg; gehört als Notiz in die Roadmap.

**Deine Entscheidung**
- [ ] **#64 freigeben** (Plan-Freigabe): dann AK0-Ausgangsmessung durch Claude Code, danach Gate-A2-Lauf. (Widerspruch nur gegen „neueste zuerst" als Standard möglich.)
- [ ] **#65: Weg 1 oder Weg 2?** (Empfehlung: Weg 2.)
- [ ] Rückfragen — Session geht in eine weitere Runde.

*Technische Details: `briefing-64.md` (Planprüfer-APPROVE, 2. Runde) und `65-uebergabe-optionen.md` in diesem Ordner; Subagenten-Rohoutputs archiviert Claude Code per `opencode export` hierher.*
