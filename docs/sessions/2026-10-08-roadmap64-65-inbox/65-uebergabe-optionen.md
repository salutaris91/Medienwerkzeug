# #65 — Übergabe der Gruppe an den Serien-Ablauf: Weg 1 vs. Weg 2 (read-only geklärt, Akt 2)

> **Status:** Entscheidungsvorlage für Alex. `briefing-65.md` wird ERST nach dieser Entscheidung geschrieben (Auftrag Akt 2, Punkt 2).
> **Alex-Bindung (wörtlich, 2026-10-08):** „Also ich hätte gedacht, dass es rein auf der Oberfläche dann gruppiert wird, sozusagen als Ordner, wo dann die ganzen, ähm, die ganzen Dateien dann reinkommen, beispielsweise zu einer Staffel, die ganzen Folgen." → Gruppierung nur oberflächen-seitig, KEIN Verschieben von Inbox-Dateien; Erkennung + Vorschlag + Auswahlkästchen sind gesetzt, Drag & Drop raus (Folgepunkt #20).
> Alle Code-Belege habe ich selbst read-only nachgeprüft; Subagenten-Aussagen sind mit Rolle gekennzeichnet.

## Die drei denkbaren Wege

### Weg 1a — „Sammelauftrag pro Folge" (Alex' Rahmung; N Jobs, Server unverändert)
Jede markierte Einzeldatei wird als eigener tv-Job mit identischem Serien-/Profil-Kontext eingereiht (der heutige Pfad: `selectProject(datei)` → Vorschau → `/api/process`, `app.js:10540–10616`; Einzeldatei-Handling `queue_api.py:73–78, 84–86`).

- **Datenrisiko:** minimal. Die Preview eines Einzeldatei-Jobs kennt NUR diese Datei (`all_files=[basename]`, `queue_api.py:84–86`) — Fremd-Junk/-Subs sind strukturell ausgeschlossen.
- **Kosten:** Bei 11 Staffeln × ~24 Folgen = ~264 Jobs: 264 Provider-Fetches je Lauf (`queue_api.py:429–457` UND `processor.py:1045–1072`) → Rate-Limit-/Retry-Kaskadengefahr (bezieht sich auf #54); 264 Warteschlangen-Karten; Teilfehler (Job 37/264) ohne Gesamtzustand; 264× `tvshow.nfo`-Schreibvorgänge. [advocatus] hat das als „[wichtig], aber nicht destruktiv" bewertet.
- **UX:** widerspricht Alex' „virtueller Ordner"-Vorstellung (produziert 264 Einzeljobs statt einer Gruppe).

### Weg 1b — „Ein-Job-Virtual-Folder" (von mir im Code gefunden; 1 Job, Server unverändert) — **nicht empfohlen**
Der Server kann bereits heute einen Mehrdatei-TV-Job: `project_name=""` setzt den Arbeitsordner auf die Inbox-Root (`queue_api.py:78–79`, `processor.py:855–856`), und der TV-Zweig verarbeitet exakt die in `mappings` genannten Dateien (`processor.py:1078–1082`; pro Datei season/episode, `:1235–1288`). Frontend bräuchte also nur: Gruppe bauen → `mappings` aus SxxExx → bestehendes Vorschau-Modal öffnen.

**Aber (selbst verifiziert, bestätigt durch [advocatus], Findings [kritisch]):** die Preview mit `project_name=""` scannt die GESAMTE Inbox (`find_files_recursively`, `queue_api.py:88`), und ihre Junk-/Subs-Listen enthalten damit Dateien ANDERER Projekte (`:609–619`). Zur Ausführungszeit joinnt der Processor `explicit_junk` ungeprüft auf den Arbeitsordner und schickt es in die Quarantäne (`processor.py:902–909`), benennt `explicit_subs` ungeprüft um (`:965–971`), und räumt leere Unterordner der GANZEN Inbox weg (`:974–980`). Clientseitiges Filtern ist ein Fass ohne Boden: Begleitdateien (Untertitel zu Folge X) tragen keine Gruppen-Membership — man müsste die Server-Heuristik `is_companion_of_any_video` (`queue_api.py:378–404`) im Client duplizieren oder verlustvoll wegfiltern. **[produktberater] empfahl 1b primär aus UX-/Scope-Sicht; [advocatus] widersprach mit den Datenrisiken; meine Nachprüfung gibt advocatus recht — 1b ist damit als verworfene Alternative dokumentiert (Dissens-Pflicht).**

### Weg 2 — Dateiliste an den Server (Alex' Rahmung; 1 Job, kleine Backend-Ergänzung)
`/preview_process` und `/process` erhalten einen optionalen Parameter `files: [relative Pfade]`; der Server setzt die Arbeitsbasis exakt auf diese Liste (+ ihre Begleitdateien, Heuristik bleibt serverseitig), Junk-/Subs-/Cleanup-Scopes werden serverseitig auf die Gruppe begrenzt. Frontend: Gruppierungs-UI + ein Klick in das BESTEHENDE Vorschau-Modal (Auswahlkästchen existieren schon, `app.js:10540–10546`).

- **Nutzen:** exakt Alex' „virtueller Ordner": EINE Bestätigung, EINE Warteschlangen-Karte „Serie X (264 Folgen)", transaktionaler Gesamtjob.
- **Kosten/Risiko:** Änderung im meistgetesteten Pipeline-Pfad (`queue_api.py` Projektauflösung `:73–88`, `processor.py` Scope-Logik `:846–980`); nötig: Pfadvalidierung der Listenelemente (innerhalb Inbox-Root, keine Traversals), Regressionstests „Job mit files[] berührt exakt Gruppe ∪ Companions, sonst nichts". Ausführung durch Antigravity direkt mit Alex-Review, nicht durch den Gate-Worker.
- **Nebenbefund (unabhängig von #65, bestehend):** der Leere-Ordner-Cleanup `processor.py:974–980` läuft heute schon bei JEDEM Job, dessen Arbeitsordner die Inbox-Root ist (auch Einzeldatei-Jobs) — fremde leere Inbox-Ordner können bereits heute in die Quarantäne wandern. Nicht von #65 eingeführt; gehört als Notiz in die ROADMAP (Entscheidung bei #65-Umsetzung mittragbar).

## Empfehlung

**Empfehlung: Weg 2.** Begründung: Er ist der einzige Weg, der Alex' „virtueller Ordner"-Vorstellung (1 Gruppe → 1 Bestätigung → 1 Job) ERFÜLLT, ohne die bestätigte Datenrisiko-Lücke von 1b; das Backend-Stück ist klein und eng gefasst (Parameter + Scope-Filter + Tests), weil Vorschau-Modal, mappings-Verarbeitung und Umbenennungs-Logik bereits existieren und erprobt sind.
**Trade-off:** Es wird der am häufigsten getestete Verarbeitungspfad angefasst — darum Pflicht: Regressionstests + Alex-Einzelreview des Server-Diffs; und #65 wird dadurch kein reines Frontend-Feature.
**Fallback:** Wenn Alex den Pipeline-Pfad jetzt NICHT angefasst haben will: Weg 1a (sicher, null Backend), mit dem bewussten UX-Mangel „264 Einzeljobs, 264 Provider-Fetches".

## Entscheidungspunkt für Alex

1. **Weg 2** (empfohlen): `files[]`-Parameter im Server + Gruppen-UI im Frontend, 1 Job pro Serie.
2. **Weg 1a**: nur Frontend, N Jobs — sicher, aber UX-widersprüchlich zum eigenen „Ordner"-Bild.
3. (Weg 1b ist mit Belegen verworfen; Widerspruch gegen die Verifikation wäre möglich, bräuchte aber eine Server-seitige Scope-Absicherung — das wäre dann faktisch Weg 2.)

Nach der Entscheidung schreibe ich `briefing-65.md` (inkl. Abschnitt „Zusammenspiel mit der Sortierung aus #64": Gruppenzeilen nehmen am Sortieren teil — Gruppenschlüssel = Seriennamen-/Datumswerte der Gruppe; Einträge innerhalb der Gruppe nach Staffel/Folge, unabhängig von der Listen-Sortierung; Details im Briefing).

## Quellen
- [advocatus] (Runde #65): Findings [kritisch] zu 1b (Fremd-Junk, Subs-Join, Inbox-Cleanup), [wichtig] zu 1a (N× Fetch/nfo/Queue, Teilfehler), Empfehlung 1a.
- [produktberater] (Runde #65): Empfehlung 1b aus UX-/Scope-Sicht, MVP-Schnitt (Erkennung, Gruppe, Vorschlagskarte, Modal-Übergabe; kein Drag&Drop, keine Staffel-Zwischengruppierung im Modal, keine Auto-Verarbeitung), Modal-Performance-Falle bei 264 Zeilen.
- Eigene Code-Verifikation: `queue_api.py:19–88, 353–631, 776–831`; `processor.py:768–778, 846–980, 1021–1082, 1229–1288`; `app.js:10540–10616, 12330–12355, 2674`; `project_api.py:1323–1342, 1400, 1477–1487`; `js/parse.js:64–79`.
