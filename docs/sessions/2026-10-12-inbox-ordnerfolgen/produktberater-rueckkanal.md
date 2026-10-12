# Rohoutput produktberater — Rückkanal 2026-10-12 (Ordner-Folgen)
Hinweis Claude Code (2026-10-12): Mechanisch aus `opencode export ses_ecf9d329bffenaBDzh0B97oY3K` (ceo-planner, Rückkanal) abgelegt, nicht vom Moderator abgeschrieben (Lehre 59). Einzige Änderung: Trailing Whitespace entfernt. Volle Daten: Kit `scripts/gate-a2/logs/2026-10-12-inbox-ordnerfolgen/export-rueckkanal.json`.

---

## produktberater: Produktchancen Inbox-Ordner (Subagent-Sitzung ses_ecf90d2e4ffeSt2SIbIXyTIGfA, Status: completed)

<task id="ses_ecf90d2e4ffeSt2SIbIXyTIGfA" state="completed">
<task_result>
Ich habe ROADMAP, Briefing und Code analysiert. Hier meine Bewertung als Scope-Wächter:

---

## Analyse: Was ist bereits in ROADMAP (VERBOTEN)

**Abgedeckte Einträge:**
- **#45**: Inbox/Outbox aufräumen, Speicherbelegung
- **#64**: Sortierbare Liste (✅ erledigt)
- **#65**: Als Serie gruppieren (✅ erledigt)
- **#67**: XSS-Härtung Vorschau
- **#68**: Inbox-Aufräumen (leere Ordner)
- **#69**: Filmreihe am Stück
- **#70**: Filter nach Medientyp
- **#71**: Ordner aufklappen (Kern = volles Aufklapp-UI)
- **#72 Punkt 8**: Endungslisten bündeln
- **#73**: OrbStack native ARM64

**Bereits verworfen im Briefing (nicht aufwärmen):**
- "1 Datei"-Badge + Ordner-Icon + zweizeilige Mitgliederliste (Dissens 2)
- F1 Typ-Erkennung über Dateinamen
- Mehrvideo-Ordner kennzeichnen

---

## Kandidaten-Prüfung

### ✅ KANDIDAT 1: Staffel-Buttons im Gruppen-Header

**Name:** Pro-Staffel-Schnellauswahl in Serien-Gruppen

**Nutzen (1-2 Sätze):** Bei 173 ThWaDe-Ordnern über 11 Staffeln muss Alex aktuell 23 Ordner einzeln anhaken, um Staffel 11 zu verarbeiten. Ein Button "S11" im Gruppen-Header reduziert das auf einen Klick.

**Was technisch schon da ist:**
- `app.js:12553-12556`: Members sind bereits nach Season/Episode sortiert
- `app.js:12610`: `seasons`-Array wird bereits berechnet (für Banner)
- `app.js:13018-13032`: Gruppen-Header hat Platz für weitere Buttons
- `_se.season` ist pro Member vorhanden (`app.js:12521`)

**Aufwand:**
- KI-Implementierung: ~30 min (Dropdown oder Button-Leiste im Header, Click-Handler der über Members iteriert und `selectedInboxProjects.add(m.project)` für passende Season aufruft)
- Alex-Engpass: ~10 min Review (kleiner, lokaler Diff)

**Abgrenzung zu ROADMAP:**
- Nicht in #71 (Ordner aufklappen = internes Aufklappen des Ordners, nicht Staffelauswahl in der Gruppe)
- Nicht in #70 (Filter nach Medientyp, nicht nach Staffel)
- Nicht in #65 (Gruppenauswahl = alle oder nichts)

**Empfehlung:** **JETZT** — hoher Nutzen für den Live-Workflow (23 Klicks → 1), minimaler Aufwand, technisch naheliegend.

---

### ✅ KANDIDAT 2: "Rest der Gruppe auswählen" in Bulk-Bar

**Name:** Bulk-Bar-Erweiterung um "Rest auswählen"-Button

**Nutzen (1-2 Sätze):** Wenn Alex einige Folgen manuell ausgewählt hat (z.B. 5 von 23), könnte ein Button "Rest der Gruppe auswählen" die verbleibenden 18 Folgen derselben Serie ergänzen. Nützlich bei teilweiser Vorauswahl.

**Was technisch schon da ist:**
- `app.js:12679-12740`: Bulk-Bar hat bereits "Auswahl aufheben" und "Als Serie verarbeiten"
- `app.js:12714-12716`: `selectedItems` wird bereits aus `selectedInboxProjects` + `currentSmartInboxRawSuggestions` gebaut
- Gruppen-Mitglieder sind über `detectInboxGroups(suggestions)` zugreifbar

**Aufwand:**
- KI-Implementierung: ~20 min (Button + Handler: finde Gruppe der ausgewählten Items, füge alle Members hinzu, die nicht schon selected sind)
- Alex-Engpass: ~5 min Review

**Abgrenzung zu ROADMAP:**
- Nicht in #65 (Bulk-Auswahl existiert, aber "Rest" ist neu)
- Nicht in #71 (hat nichts mit Ordner-Aufklappen zu tun)

**Empfehlung:** **NACH LIVE-TEST** — mittelbarer Nutzen (nur relevant bei teilweiser Vorauswahl), aber minimaler Aufwand. Erst nach Live-Betrieb evaluieren, ob Alex das vermisst.

---

### ❌ VERWORFEN: Gruppen-Badge mit Staffel-Spanne

**Name:** "Staffeln 1–11" im Gruppen-Header statt nur "173 Folgen"

**Nutzen:** Zeigt die Staffelspanne an (Info, keine Aktion).

**Bewertung:** Eher kosmetisch. Die Info ist nett, aber nicht kritisch. Alex sieht die Staffeln in der aufgeklappten Mitgliederliste. **Verworfen:** geringer Nutzen, kein Funktionsgewinn.

---

### ❌ VERWORFEN: Staffel-Gruppierung innerhalb der Gruppe

**Name:** Members nach Staffeln clustern (collapsible sections pro Staffel)

**Nutzen:** Bei 173 Folgen wäre die Mitgliederliste nach Staffeln strukturiert.

**Bewertung:** Zu großes UI-Refactoring. Die Mitgliederliste (`app.js:13034-13052`) ist aktuell flach. Eine Cluster-Struktur würde neue DOM-Elemente, Collapse-Handler, CSS erfordern. **Verworfen:** Aufwand unverhältnismäßig, eher #71-Vollausbau.

---

### ❌ VERWORFEN: Tooltip mit Dateinamen für Ordner in Mitgliederliste

**Name:** `title="Verarbeitet wird: <single_video_relpath>"` an Members

**Nutzen:** Zeigt den inneren Dateinamen beim Hover über den Ordnernamen in der Mitgliederliste.

**Bewertung:** Der Tooltip ist bereits an der Checkbox (`app.js:13154`). In der Mitgliederliste (`app.js:13042-13046`) fehlt er. Aber: Alex sieht den Ordnernamen (`ThWaDeS11E23`) und die SxxExx-Badge — der innere Dateiname ist redundant. **Verworfen:** marginaler Nutzen, wird vom Briefing explizit als "bewusst verworfen" gestützt (Dissens 2: keine zusätzlichen UI-Elemente).

---

### ❌ VERWORFEN: Shift-Click Range-Select

**Name:** Shift+Click auf Checkbox wählt alle Folgen zwischen erstem und letztem Click aus

**Nutzen:** Standard-Feature in vielen UIs, würde 23 Klicks auf 2 reduzieren.

**Bewertung:** Erfordert Last-Clicked-Tracking, Range-Detection, Event-Handling. **Verworfen:** Aufwand unverhältnismäßig für Einzelnutzer-Tool; Kandidat 1 (Staffel-Buttons) löst das Problem eleganter.

---

### ❌ VERWORFEN: Bulk-Bar mit Staffeln-Info

**Name:** "23 ausgewählt (Staffel 11)" in der Bulk-Bar

**Nutzen:** Zeigt, welche Staffel ausgewählt ist.

**Bewertung:** Erfordert Zuordnung `selectedInboxProjects` → group members → `_se.season`. Die Members haben `_se`, aber die Items in `currentSmartInboxRawSuggestions` nicht. Man müsste über `detectInboxGroups` die Zuordnung herstellen. **Verworfen:** komplexer als der Nutzen rechtfertigt.

---

## Gesamtempfehlung

**Kandidatenwürdig (candidates only, KEINE ROADMAP-Schreibaktion):**

1. **Staffel-Buttons im Gruppen-Header** — **JETZT umsetzen**
   - Hoher Nutzen (23 Klicks → 1)
   - Minimaler Aufwand (~30 min KI, ~10 min Alex)
   - Technisch naheliegend (`_se.season` ist da)
   - Nicht in ROADMAP

2. **"Rest der Gruppe auswählen"** — **NACH LIVE-TEST evaluieren**
   - Mittelbarer Nutzen
   - Minimaler Aufwand (~20 min KI, ~5 min Alex)
   - Nicht in ROADMAP
   - Erst nach Live-Betrieb prüfen, ob Alex das vermisst

**Nicht kandidatenwürdig:**
- Gruppen-Badge mit Staffel-Spanne (kosmetisch)
- Staffel-Gruppierung innerhalb der Gruppe (zu groß)
- Tooltip mit Dateinamen (redundant)
- Shift-Click Range-Select (zu komplex, Kandidat 1 ist eleganter)
- Bulk-Bar mit Staffeln-Info (zu komplex für marginalen Nutzen)

**Scope-Wächter-Veto:** Keine der verworfenen Ideen hat genug Nutzen, um den Review-Engpass zu rechtfertigen. Kandidat 1 ist das klare MVP für den Live-Workflow.
</task_result>
</task>
