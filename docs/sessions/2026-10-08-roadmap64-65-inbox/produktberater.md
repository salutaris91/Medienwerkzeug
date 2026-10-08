# Rohoutput produktberater — Kreativteam-Session 2026-10-08 (Akt 2)
Hinweis Claude Code (2026-10-08): Mechanisch aus `opencode export ses_ee533a3c8ffesW6v133rMvr61E` (ceo-planner) abgelegt, nicht vom Moderator abgeschrieben (Lehre 59). Je Abschnitt: Auftragsbeschreibung, Subagent-Sitzung, dann die wörtliche Subagent-Antwort. Einzige Änderung: Trailing Whitespace am Zeilenende entfernt (Pre-Commit-Hook); sonst unverändert. Volle Prompts und Antworten: Kit `scripts/gate-a2/logs/2026-10-08-roadmap64-65/export-ceo-planner.json`.

---

## produktberater zu #64 Scope (Subagent-Sitzung ses_ee5270538ffe9zhlaCuKqMYgIP, Status: completed)

<task id="ses_ee5270538ffe9zhlaCuKqMYgIP" state="completed">
<task_result>
## 1. Echter Nutzer-Nutzen

Das Problem (ROADMAP:1802) ist **Priorisierung**, nicht Auffindbarkeit.

- **Kern-Felder:** `Datum` (welches Projekt ist frisch / liegt am längsten?) und `Größe` (wo steckt der meiste Platz / Impact?). Beide beantworten „was zuerst?".
- **Beiwerk:** `Name` (alphabetisch) hilft beim *Wiederfinden*, nicht beim *Priorisieren*. Trotzdem von Alex entschieden → mitnehmen, aber nicht aufwerten.
- **Implizit wertvoll, aber nicht bestellt:** `confidence`/`profile_match` sind bereits als Reasons-Badges sichtbar — eine Sortierung danach wäre ein nächster Schritt, gehört aber nicht in PR1.

**Empfehlung:** Datum + Größe sind die Wert-Treiber. Name ist Komfort.

---

## 2. MVP-Check

**MUSS in PR1:**
- Server: Payload um `modified_at` (Unix-Timestamp, Sekunden) und `total_size` (Bytes, rekursiv aufsummiert) erweitern — `gui/api/project_api.py:1477–1487`.
- Frontend: Drei Sort-Buttons (Name/Datum/Größe), Klick toggelt asc↔desc, aktiver Zustand visuell gekennzeichnet.
- Frontend: Sort-Zustand in `sessionStorage` (ein Key, z.B. `inbox-sort:{field}:{dir}`).
- Cache-Buster v94→v95 (index.html + app.js-Importe synchron).

**DARF NICHT:**
- Server-seitige Sortierung (alle Daten kommen ohnehin komplett zum Client → Sortierung dort trivial und ohne Roundtrip).
- Drag&Drop, Filter, Multi-Column-Sort, localStorage (über Sitzung hinaus), Auto-Sort-Heuristiken.
- Änderung der Cache-Logik (30s-Cache `project_api.py:1303–1305` bleibt unverändert).

---

## 3. Standard-Sortierung

**Empfehlung: Datum absteigend („neueste zuerst") als Default.**

Begründung: Die heutige „Server-Reihenfolge" ist `os.listdir` (`project_api.py:1315`) — das ist **filesystem-arbiträr**, keine sinnvolle Reihenfolge. Diese beizubehalten hieße, dem Nutzer absichtlich eine nicht-deterministische Reihenfolge zu zeigen. „Neueste zuerst" ist die etablierte Inbox-Erwartung (E-Mail, Finder, Dateimanager) und ersetzt sinnfrei durch vorhersagbar.

Trade-off: Es *ist* eine Verhaltensänderung — aber nur visuell, nicht funktional. Kein Datenverlust, kein API-Bruch.

---

## 4. Akzeptanzkriterien

1. **Payload vollständig:** Es prüft, dass `GET /api/inbox/analyze` für jeden Eintrag die Felder `modified_at` (int, Unix-Sekunden) und `total_size` (int, Bytes) liefert.
2. **Sortierung Name:** Es prüft, dass nach Klick auf den „Name"-Header die Einträge alphabetisch aufsteigend nach `project` sortiert erscheinen; erneuter Klick kehrt die Reihenfolge um.
3. **Sortierung Datum:** Es prüft, dass nach Klick auf „Datum" die Einträge nach `modified_at` absteigend sortiert sind (neueste zuerst); erneuter Klick kehrt um.
4. **Sortierung Größe:** Es prüft, dass nach Klick auf „Größe" die Einträge nach `total_size` absteigend sortiert sind; erneuter Klick kehrt um.
5. **Session-Persistenz:** Es prüft, dass nach Setzen einer Sortierung und simuliertem Seiten-Reload (gleiche Session) die Sortierung automatisch wiederhergestellt wird.
6. **Default ohne gespeicherten Zustand:** Es prüft, dass ohne vorhandenen `sessionStorage`-Eintrag die Sortierung `modified_at` desc (neueste zuerst) ist.

---

## 5. Komplexitäts-Widerstand — wo ich Veto einlege

| Versuchung | Warum streichen |
|---|---|
| **Server-seitiger Sort-Parameter** (`?sort=name&dir=asc`) | Alle Daten sind client-seitig vorhanden. Server-Sort = zusätzlicher Endpoint-Parameter, Cache-Key-Komplexität, Testfläche — ohne Nutzen. |
| **„modified_at" als newest-video-mtime statt folder-mtime** | Ordner-mtime ist ein `os.stat`-Aufruf (`project_api.py`-Pfad existiert bereits). Rekursiv über alle Videos nach max-mtime zu suchen = zusätzlicher I/O pro Eintrag, für marginalen Genauigkeitsgewinn. **Empfehlung: `os.stat(full_path).st_mtime` für Ordner, `os.stat(full_path).st_mtime` für Einzeldateien.** |
| **`total_size` via `os.walk` + `os.stat` pro Datei** | Hier ist der rekursive Walk unvermeidbar (korrekte Größe). Aber: nicht `ffprobe`/Media-Größe nehmen — reines `os.path.getsize` reicht. |
| **Sort-UI als Dropdown/Combobox** | Drei Buttons (Header-Clicks) sind das Minimum. Dropdown = mehr DOM, mehr Accessibility-Fläche, mehr Code. |
| **Animierter Sort-Transition** | Nice-to-have, lenkt den Worker ab. Statische Re-Render reichen. |

**Kritischste Gefahr:** Der Worker fasst die `get_inbox_suggestions()`-Struktur an (Refactoring, Cache-Invalidation ändert) statt nur zwei Felder ans Dict anzuhängen. **Scope = additive Felder, keine Umsortierung der Funktion.**
</task_result>
</task>

---

## produktberater zu #65 Übergabe (Subagent-Sitzung ses_ee51705dbffe9XXJETGM7GQ1mb, Status: completed)

<task id="ses_ee51705dbffe9XXJETGM7GQ1mb" state="completed">
<task_result>
## Produktbewertung ROADMAP #65 — Serien-Gruppierung

### 1. Weg-Empfehlung: **1b** (1 Job, mappings-basiert)

- **1a** (N Jobs): 264 Jobs in der Queue = unübersichtlich, kein "Gruppengefühl", widerspricht Alex' Vorstellung "virtueller Ordner".
- **1b** (1 Job): Nutzt bestehenden Flow (project_name="" + mappings), 1 Job-Karte, 1 Bestätigung. Server unverändert. Liefert Alex' UX exakt.
- **2** (files[] Backend): Sauberer Vertrag, aber Backend-Änderung = mehr Scope für null Zusatznutzen.

**Empfehlung: 1b.** Scope minimal, Nutzen maximal.

### 2. MVP-Schnitt PR1

**Muss rein:**
- SxxExx-Erkennung (Frontend, clientseitig)
- Gruppierung in Inbox-Liste (visuell: einklappbarer Ordner "Serie X (264 Folgen)")
- Vorschlagskarte mit Checkboxen (alle Folgen vorausgewählt)
- Übergabe in bestehendes Vorschau-Modal (project_name="" + mappings)

**Darf NICHT rein:**
- Drag&Drop (Alex hat explizit ausgeschlossen)
- Staffel-Zwischengruppierung im Modal (nice-to-have, später)
- Automatische Verarbeitung ohne Bestätigung

### 3. UX-Fragen

- **Warteschlange:** 1 Job "Serie X (264 Folgen)" — klarer als 264 Einzeljobs. Job-Karte zeigt "264 Dateien, 128 GB".
- **Vorschau-Modal mit 264 Renames:** DOM-Performance kritisch. **Empfehlung:** Virtualisierung (z.B. nur sichtbare 50 Zeilen rendern) oder "Zeige erste 50, Rest einklappen". Staffel-Zwischengruppierung im Modal: für MVP verzichtbar (alle Folgen in einer Liste, sortiert nach SxxExx).
- **Fehlerbehandlung:** Wenn 1 Folge fehlschlägt → Job-Status "263/264 erfolgreich, 1 fehlgeschlagen" mit Detail-Log.

### 4. Akzeptanzkriterien (ausführbar, nutzerseitig)

1. **AC1:** Nutzer sieht in der Inbox alle Folgen einer Serie gruppiert (einklappbarer Ordner "Serie X (264 Folgen)").
2. **AC2:** Nutzer wählt die Gruppe aus, klickt "Verarbeiten", und es öffnet sich das Vorschau-Modal mit allen 264 Folgen + Checkboxen (alle vorausgewählt).
3. **AC3:** Nach Bestätigung erscheint in der Warteschlange 1 Job "Serie X (264 Folgen)" statt 264 Einzeljobs.
4. **AC4:** Alle 264 Folgen werden korrekt verarbeitet (Renames, Subs, Junk) gemäß Vorschau.
5. **AC5:** SxxExx-Erkennung funktioniert für gängige Formate (S01E01, s1e1, Staffel 1 Folge 1) und zeigt Vorschlag "Serie X" an.

### 5. Komplexitätsfalle

**Primäre Falle:** Vorschau-Modal bei 264 Dateien → DOM-Performance. Wenn das Modal 264 Zeilen ohne Virtualisierung rendert, wird es träge. **Lösung:** Virtualisierung oder Pagination.

**Sekundäre Falle:** SxxExx-Parsing-Edge-Cases (falsche Erkennung, mehrdeutige Dateinamen). **Lösung:** Nutzer muss Korrekturmöglichkeit haben (Checkboxen abwählen, manuell umbenennen).

**Tertiäre Falle:** Teilfehler (1 Folge fehlschlägt). **Lösung:** Job-Status muss klar kommunizieren (263/264 erfolgreich) mit Detail-Log.

---

**Scope-Wächter-Veto:** Keine Backend-Änderungen (Weg 2), keine Drag&Drop, keine Staffel-Zwischengruppierung im Modal. Alles andere ist nice-to-have für PR2+.
</task_result>
</task>
