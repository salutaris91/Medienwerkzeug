# Rohoutput advocatus — Kreativteam-Session 2026-10-08 (Akt 3, #65)
Hinweis Claude Code (2026-10-08): Mechanisch aus `opencode export ses_ee533a3c8ffesW6v133rMvr61E` (ceo-planner) abgelegt, nur Aufrufe ab dem Akt-3-Auftrag, nicht vom Moderator abgeschrieben (Lehre 59). Einzige Änderung: Trailing Whitespace am Zeilenende entfernt (Pre-Commit-Hook). Volle Prompts und Antworten: Kit `scripts/gate-a2/logs/2026-10-08-roadmap64-65/export-ceo-planner-akt3.json`.

---

## advocatus zu #65 Briefing (Subagent-Sitzung ses_ee5022258ffe1EP9EVUwz3QXL1, Status: completed)

<task id="ses_ee5022258ffe1EP9EVUwz3QXL1" state="completed">
<task_result>
## Advocatus-Review — briefing-65-Entwurf (Weg 2, Regeln 1–3), Session 2026-10-08

Read-only geprüft gegen den Ist-Code (queue_api.py, processor.py, helpers.py, project_api.py, parse.js, app.js, jobs.py, ROADMAP.md). Der Rahmen ist grundsätzlich tragfähig, aber drei Scope-/Konsistenz-Lücken sind Blocker.

### [kritisch] 1. Scope-Loch: Auffangregel räumt bei `files[]` die ganze Inbox leer
`processor.py:1587-1603` → `safe_move_recursive(current_dir, dest_show_dir_outbox, prefix_filter=None, …)`. Bei `files[]` ist `current_dir == inbox_root`; `prefix_filter=None` heißt in `safe_move_recursive` (`processor.py:516-518`) **every non-video, non-junk file unter inbox_root wird in den Show-Outbox-Ordner verschoben** — fremde Untertitel, NFOs, Poster anderer Projekte. „explicit ⊆ Gruppe∪Begleitdateien sonst Abbruch" deckt nur Junk/Subs, **nicht** diese Auffangregel. Auch die per-Episode-Variante `processor.py:1498-1505` (prefix_filter=clean_title) kann fremde Dateien mit Namenspräfix einer anderen Serie fangen. → Bei `files[]` Auffangregel überspringen ODER auf die Verzeichnis-Union von `files[]` begrenzen.

### [kritisch] 2. NFO/Poster-Schreibpfade landen bei `files[]` im Inbox-Toplevel
`processor.py:1036` (`generate_tvshow_nfo(…, current_dir, …)`), `:1402` (`generate_episode_nfo(…, current_dir, …)`), `:1571-1580` (Show-Metadateien aus `current_dir`-Toplevel verschieben). Mit `current_dir == inbox_root` wird `tvshow.nfo` + heruntergeladene Poster ins Inbox-Root geschrieben — kollidiert mit anderen Serien, und die Show-Level-Verschiebung greift fremde `tvshow.nfo`. Es fehlt ein definiertes per-Show-Zielverzeichnis für den `files[]`-Fall (nicht in `current_dir` schreiben).

### [kritisch] 3. TOCTOU = stilles Scheitern trotz „kein stilles Scheitern"
`processor.py:958-963`, `:965-971` (rename/subs) und `:902-909` (junk) prüfen nur `os.path.exists` und **skippen still**. Eine von 264 Dateien, die zwischen Preview und Ausführung verschoben/gelöscht wurde, ⇒ Job meldet Erfolg, Datei unverarbeitet. Der Brief verspricht „LAUT abbrechen" nur für den Scope, nicht für fehlende Dateien. AK ergänzen: fehlender `files[]`-Eintrag zur Ausführungszeit ⇒ Abbruch/Fehlerstatus.

### [wichtig] 4. `is_path_allowed` ist unzureichend
`helpers.py:113-140` prüft gegen `get_allowed_roots` = **alle** konfigurierten Roots (Inbox, Outbox, NAS, pCloud …), nicht nur Inbox. Der Brief nennt zwar „Pfad liegt unter Inbox-Root", das muss aber als separater Check (`os.path.realpath` beider Seiten, gemeinsames Präfix) zwingend **zusätzlich** zu `is_path_allowed` erfolgen — sonst akzeptiert die Validierung einen `files[]`-Pfad im Outbox/NAS-Root. Symlink-Breakout nur über `realpath` beider Seiten abfangen.

### [wichtig] 5. Preview↔Process-Konsistenz existiert heute nicht
`queue_api.py:19-88` und `:776-831` validieren **gar nichts**; `mappings` fließt ungeprüft in `process_worker` (`processor.py:1078, 1361`). „mappings⊆files" muss serverseitig in **beiden** Endpunkten identisch erzwungen werden, sonst verarbeitet ein stray Mapping-Key trotz `files[]` weiter (stilles `continue`).

### [wichtig] 6. Manifest ≠ Cross-Job-Idempotenz
Manifest ist keyed by `filename`, gelesen via `get_job(task_id)` (`processor.py:986`). Frischer `/process` ⇒ neuer `task_id` ⇒ leeres Manifest. Resume funktioniert nur via `/queue/retry` im selben Job (`queue_api.py:876-946`). Partial-Failure + neu gestartete Vorschau ⇒ erledigte Folgen gehen verloren. Brief muss den realen Promise benennen (kein Resume über neuen Job).

### [wichtig] 7. Begleitdateien-Ermittlung undeterministisch
`is_companion_of_any_video` (`queue_api.py:378-404`) matcht Basename-Präfix **über Ordner-Grenzen** (Z.393). „Serverseitig ermittelte Begleitdateien" muss definiert werden: (a) nur same-dir-Siblings, (b) Name-Präfix innerhalb der `files[]`-Verzeichnisse, (c) globaler Inbox-Scan (O(N²) über die ganze Inbox, zieht Fremddateien). Empfehlung (b), nie globaler Scan; Algorithmus muss Preview und Process identisch sein.

### [wichtig] 8. Gruppenschlüssel-Kollision nicht auflösbar
`suggested_query = item[:match.start()]` (`project_api.py:1407-1408`): „Show - S01E01 (2020)" und „Show - S01E01 (2022)" ⇒ beide Schlüssel „Show" ⇒ zwei Serien verschmelzen. Modal-Vorschau mit Checkboxen erlaubt kein Aufteilen innerhalb der Gruppe (ROADMAP.md:1835). AK: vollständige Quellnamen anzeigen, Einzel-De-Selektion, Schlüssel editierbar.

### [wichtig] 9. Regel 1 nicht technisch erzwungen
`guessSeasonAndEpisode` bleibt importiert/aktiv (`app.js:4, 3681, 3794`) und matcht `\b(\d+)x(\d+)\b` („1920x1080") sowie lockeres staffel/folge-Muster (`parse.js:70-77`). AK: neuer Gruppencode ruft `guessSeasonAndEpisode` **nicht**; Frontend-Test mit „1920x1080.mkv" und Filmtitel ohne Gruppenbildung.

### [kosmetisch]
- **Dedup/Case:** NAS/macOS case-insensitiv ⇒ `files[]` case-insensitiv deduplizieren; Doppel-Einträge doppelt verarbeitet (Kollisionsschutz `processor.py:922-956` greift nur bei Zielkollision).
- **Payload:** 264 Einträge × (files+mappings+renames+subs+junk); Flask `MAX_CONTENT_LENGTH`-Default prüfen.
- **Video-Ext-Inkonsistenz:** Preview `video_exts` (`queue_api.py:89`) umfasst `.ts/.m2ts/.3gp`, Frontend-Gruppierung (`app.js:3664`) nur `mp4/mkv/avi/webm/mov` — Validierung und Gruppierung müssen dieselbe Liste nutzen.
- **Referenzfehler im Brief:** „Junk :902–909, Subs :965–971, Cleanup :974–980, tvshow.nfo :612–617" liegen in `processor.py`, nicht `queue_api.py`; `:612–617` ist `_extract_show_name`, nicht die tvshow.nfo-Logik.

### Fehlende Pflicht-AKs (Zusammenfassung fürs Briefing)
Abwärtskompatibilitäts-Regressionstests (movie/tv mit `project_name`, inbox-root ohne `files[]`), laut Abbruch bei fehlender Datei, `files[]`-Dedup, Begleitdateien-Definition, NFO/safe_move-Scope, Manifest-Promise, Gruppenschlüssel-Korrektur, Cache-Buster v96 (bereits enthalten).

---

**VERDICT: REVISE** — Blocker sind die drei [kritisch]-Findings (1 Auffangregel-Scope, 2 NFO-Schreibpfade, 3 stilles TOCTOU-Scheitern). Nach deren Behebung im Brief ist der Rahmen (Weg 2, Regeln 1–3) tragfähig.
</task_result>
</task>
