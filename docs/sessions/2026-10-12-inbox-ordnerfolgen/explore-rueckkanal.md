# Rohoutput explore — Rückkanal 2026-10-12 (Ordner-Folgen)
Hinweis Claude Code (2026-10-12): Mechanisch aus `opencode export ses_ecf9d329bffenaBDzh0B97oY3K` (ceo-planner, Rückkanal) abgelegt, nicht vom Moderator abgeschrieben (Lehre 59). Einzige Änderung: Trailing Whitespace entfernt. Volle Daten: Kit `scripts/gate-a2/logs/2026-10-12-inbox-ordnerfolgen/export-rueckkanal.json`.

---

## explore: Konsumenten-Sweep Inbox-Felder (Subagent-Sitzung ses_ecf9148ccffelxKKGwO6PGq4fi, Status: completed)

<task id="ses_ecf9148ccffelxKKGwO6PGq4fi" state="completed">
<task_result>
Recherche abgeschlossen. Im Arbeitsbaum befindet sich der uncommittete Patch (`git diff --stat`: project_api.py, app.js, processor.py, API.md, index.html, 3 Testdateien). Ich habe den kompletten Datenfluss `Payload → Auswahl → Matrix → Preview → /process → Processor → Retry` statisch verfolgt. Befundliste:

---

## (a) Vollständige Konsumenten-Liste mit Urteil

### A. app.js — `item.project` / Auswahl-Identität (Ordnernamen-keyed)

| Stelle | Inhalt | Urteil |
|---|---|---|
| app.js:12492-12498 | `inboxFilesEntryForItem` (neu): relpath für Ordner mit `single_video_relpath`, sonst `item.project` | OK |
| app.js:12500-12531 | `detectInboxGroups`: Gate `is_dir===true && !single_video_relpath → return`; Key = `single_video_query` für Ordner; S/E via `relpath.split('/').pop()` (12511), Fallback auf `item.project` | OK |
| app.js:12533-12583 | `buildGroupedInboxSuggestions`: `groupedItemsByProject` über `m.project` (12541, 12575) — Ordnernamen bleiben eindeutig in einem Verzeichnis | OK |
| app.js:12585-12655 | Banner: `appliedInboxGroups`/`sessionStorage['smart-inbox-ignore-group-'+groupKey]` (12594, 12628) über Query-String, dateipfadunabhängig; `files = members.map(inboxFilesEntryForItem)` (12646) | OK |
| app.js:12679-12740 | Bulk-Bar: `selectedInboxProjects` (Projekt-Keys) → Rücklookup `s.project === proj` (12715) → `inboxFilesEntryForItem` (12717); `fallbackName` priorisiert `single_video_query` (12726); `detectManualGroupSeriesName` stript Verzeichnis via `replace(/^.*[\\/]/, '')` (12661) | OK |
| app.js:12995-13107 | Gruppen-Zeile: nur `data-group-key`, kein `data-project` (AK11-konform); Mitglieder-Rendering zeigt `m.project` (13045); „Auswählen" nutzt `inboxFilesEntryForItem` (13094) | OK |
| app.js:13140 | `isProcessing = processingSet.has(item.project)` — Ordner-Zeile gegen `activeProjectsProcessing` | **Bedenken → Befund 2** |
| app.js:13144-13157 | Checkbox-Eligibility `is_dir===true && Boolean(single_video_relpath)` (13145); Checkbox keyt weiter über `item.project`, Titel zeigt relpath (13154) | OK (Keying konsistent mit 13219/13151) |
| app.js:13160-13167, 13227-13234 | Movie-Unlock nur `is_dir===false` — Ordner nicht解锁bar; `unlockedMovieProjects` über `item.project` | OK |
| app.js:13172, 13207-13212 | `data-project` an Zeile; Quarantäne `deleteProject(item.project)` → `/api/delete-project` mit Ordnernamen — korrekt (Ordner, nicht relpath) | OK (aber → Befund 2) |
| app.js:12377-12424 | `sortInboxSuggestions`: `a.project` nur Anzeige-Sortierung, Gruppe mit `project=groupKey` | OK |
| app.js:12426-12452 | Sort-sessionStorage nur `{field, direction}` — keine Pfad-Keys | OK |
| app.js:2461-2508 | reaktive Verarbeitung: `data-project` → `activeProjects.has(p)` (2466), Checkbox/Delete disabled | OK für klassische Jobs; Lücke für Gruppen-Jobs → Befund 2 |
| app.js:2511-2528 + 13283-13314 | `configureSmartInboxButton` → `handleSmartInboxClick(projectName, …, btn.getAttribute("data-suggested-query"))` | **Problem → Befund 3** |
| app.js:12742-12925 | `startSeriesGroupWorkflow`: `currentProject=""` (12750), `projectFiles=[...files]` (12751); Dateitabelle `f.endsWith("/")` (12881 — relpath endet nie mit "/"), `f.split('.').pop()` (12883 — korrekt „mkv"), Suchfeld/`searchSeries` mit `groupName` (12918-12922) | OK |
| app.js:13256-13281 | globalThis-Exporte inkl. `inboxFilesEntryForItem` (13258); `selectedInboxProjects` etc. als Live-Set-Referenzen | OK |

### B. `suggested_query`-Konsumenten

| Stelle | Inhalt | Urteil |
|---|---|---|
| app.js:13197 | `data-suggested-query="${escapeHTML(item.suggested_query||"")}"` am „Auswählen"-Knopf — für Ordner **der aus dem Ordnernamen abgeleitete Wert** | **Problem → Befund 3** |
| app.js:13293 → 224 → 1820/1848 | `currentProjectSuggestedQuery = suggestionTitle` → Auto-Befüllung Serien-/Suchfeld | betroffen via Befund 3 |
| app.js:2882 | `currentProjectSuggestedQuery = data.suggested_query` aus `/api/scan-project` (project_api.py:353-368, ebenfalls ordnernamebasiert) | OK (klassischer Pfad, unverändert) |
| app.js:12506 | `detectInboxGroups`: Ordner nutzt `single_video_query`, loses File `suggested_query` — Backend reinigt beide mit `clean_show_name` (project_api.py:1441-1443 vs. 1514-1516), Form konsistent | OK |
| app.js:12726 | Bulk-`fallbackName`: `single_video_query || suggested_query || …` | OK |

### C. projectFiles/activeSeriesGroupFiles → Matrix → Workflow

| Stelle | Inhalt | Urteil |
|---|---|---|
| app.js:3560-3577, 3632-3657 | Ext-Filter (10 Extensions, Zeilen 3564/3636) lassen relpaths durch; `filenames=relpaths` an `/api/guess-season` + `/api/match-episodes` | OK |
| search_api.py:117-124, 154, 256-273 | `matches[file]`/`duplicates[file]` keyen mit **Input-String (relpath)**, Analyse mit `os.path.basename(file)` (118) → Frontend-Lookup `matches[file]` (app.js:3814) & `duplicates[file]` (3827) passt exakt | OK |
| mw_metadata.py:2435 | `guess_season` tokenisiert `get_words(f)` über den **gesamten relpath** → Ordnername liefert Zusatz-Wörter für Fuzzy-Staffelraten | Bedenken (harmlos, Ordner-/File-Stem meist identisch) |
| app.js:3699-3718 | Manual-Mode: `guessSeasonAndEpisode(file)`/`guessEpisodeNumber(file)`/`cleanFilenameForManualTitle(file)` aus parse.js auf relpath | **Bedenken → Befund 4/5** |
| app.js:3721, 3824 | `data-file=escapeHTML(file)` — relpath überlebt Attribut-Roundtrip (Zeile 3995 **ohne** escapeHTML → Befund 9) | OK / 9 |
| app.js:4346/4366/4468 → 4434 | `mappings`-Schlüssel aus `data-file` = exakt dieselben Strings wie `payload.files` (4447-4448) | OK |
| queue_api.py:85-90, 826-833 | Mapping-Schlüssel ⊆ `validated_files` (identische Strings; `validate_group_files` stripped, normt aber nicht um → keine Drift) | OK |
| helpers.py:801-867 | `validate_group_files`: `os.path.join(inbox_root, relpath)`, verweigert Ordner (851-852) und fremde Extensions (857-859) — relpaths passieren sauber | OK |
| helpers.py:870-918 | `find_group_companion_files`: nur Same-Directory-Stem-Präfix-Kandidaten | → Befund 6 |
| app.js:3840/3846 | `window.currentProjectFileNfoStatuses[file]` mit relpath gegen Map des letzten `selectProject` (2880) | Bedenken (Befund 8) |
| app.js:10235-10428 → queue_api.py:73-95, 492-649 | Preview: `mappings.get(f)` exakt (498); Rename-`old`=relpath, `new`=**nackiger Name** (569); Subs analog (622, 626, 631-633); `dirname`-Vergleiche (574, 583ff) relpath-bewusst | OK |
| app.js:10394-10401, 10615-10649 | Preview-Checkbox-Attributes `data-old/data-new` (escapeHTML) → `explicit_renames/subs/junk` alt=relpath, neu=nackig | OK |
| processor.py:865-884 | files-Job: `current_dir = inbox_root` (875); alle `os.path.join(current_dir, f)` (903, 949, 1067-1081, 1485, 1532-1533, 1569) mit relpath korrekt | OK |
| processor.py:976-1005 (neu) | Guards: Rename/Sub-Ziel ohne Pfadtrenner, nicht leer — pas到 zu Preview-Generatoren (nackige Namen) | OK |
| processor.py:1511-1547, 1688-1715 | Sub-Rename & allowed_files mit `dirname(filename)`/basename-Dualität; `safe_move_recursive` realpath-normalisiert (502-510), `path_endswith` komponentenbasiert (375-384) | OK |
| processor.py:1452, 1485-1503, 1677 | Video wird aus dem Ordner an Inbox-**Wurzel** hochgezogen („Hochgezogen"-Semantik) | OK (Design), Restordner → Befund 6 |
| processor.py:1105, 1462-1479, 1732-1739 | `manifest` mit relpath-Key, Retry-lesend (2500ff.) — konsistent, da dieselben Strings | OK |
| app.js:2616-2647 + search_api.py:286-305 | `updateSizeEstimation`: Ext-Liste nur 5 (2620); Backend `join(inbox_root, relpath)` bei `project_name ""` korrekt | Bedenken (Befund 7) |
| app.js:11929-11991, 12022-12053 | Dup-Compare: `newPath = inbox_dir + "/" + (projName ? projName+"/" : "") + newFilename` — im Gruppenmodus `currentProject=""` → `inbox_dir/ThWaDeS11E23/x.mkv` **korrekt rekonstruiert** | OK |

### D. Queue/Überschneidung/Processing-State

| Stelle | Inhalt | Urteil |
|---|---|---|
| app.js:4314-4328 | Gruppen-Zweig: `activeFilesSet` **nur aus `job.files`** — klassische Jobs (files=None) unsichtbar | **Problem → Befund 1** |
| app.js:4329-4333, 4493-4496 | Klassischer Zweig: `activeProjectsProcessing.has(currentProject)` — Gruppen-Jobs mit `project_name ""` unsichtbar | **Problem → Befund 1** |
| app.js:10860-10870 | `activeSet` ignoriert `project_name === ""` → Gruppen-Jobs deaktivieren keine Inbox-Zeilen | **→ Befund 2** |
| queue_api.py:898-911 | `/api/queue` liefert `files` (relpaths) und `project_name` mit — konsistent mit Frontend-Prüfung | OK |
| queue_api.py:803-882 | serverseitig **keine** Übersneidungsprüfung beim Einreihen (nur Validierung) | Befund 1 (verschärfend) |
| queue_api.py:930-998 | Retry: `files` reisen in `job.params` mit (833, 909-910) → Re-Validierung im Processor; teilverarbeitete relpaths → „Datei existiert nicht" | OK (Bedenken 11) |

### E. js/*.js und weitere Payload-Konsumenten

| Stelle | Inhalt | Urteil |
|---|---|---|
| welcome.js:16-19 | nur Fetch auf `/api/inbox/analyze` | OK |
| nfo_ui.js:60-74 | `prepareSeriesPayload` hängt nur `mw_data` an — keine files/mappings-Manipulation | OK |
| parse.js:11-79 | guess-Funktionen ohne basename-Stripping | Befund 4/5 |
| intelligence.js, fsk_batch.js, utils.js, format.js, theme.js | keine Konsumenten des analyze-Payloads / files[] (grep „suggested_query|inbox|analyze" trifft nur welcome.js:17; `osBasename` nur Health/FSK: app.js:13787, 18083f., 18206) | OK |
| app.js:2937/2953 (Trennen), 6304-6348 (cleanCurrentProject, `if (!currentProject) return`), 6649 (paths-clean), 17213ff. (NFO-Agent `data-file`=basename, CSS.escape 17424) | konsumieren `/api/scan-project`/`/api/scan`/eigene Server-Relpaths, **nicht** die files[] des Gruppen-Workflows | OK |
| processor.py:3354-3523 (`season_nfo_overrides`, NFO-Agent-Farm) | eigene Pfadquelle, unabhängig vom analyze-Payload | OK |
| `job.records` (Aufgabe 6) | **existiert nicht** — keine Treffer in queue_api.py/jobs.py/processor.py | nichts zu prüfen |

---

## (b) Problemfälle mit Szenario

**1. [wichtig] Überschneidungsprüfung Gruppe↔klassisch versagt in beide Richtungen** (app.js:4314-4333, 10860-10669; queue_api.py ohne Server-Gegenprüfung).
- Richtung B→A: Job B = klassischer Ordner-Job `project_name="ThWaDeS11E23"`, `files` nicht gesetzt. Nutzer startet danach Gruppen-Job A mit `files=["ThWaDeS11E23/The.Walking.Dead.S11E23.mkv"]`. Zeile 4319-4324 sammelt nur `job.files` → B liefert nichts in die Set → **keine Blockierung**. Erwartet: Block, da B denselben Ordner/Datei bewegt.
- Richtung A→B: Job A (Gruppe, `project_name ""`) läuft; `activeSet` (10864) verwirft leere Namen → `ThWaDeS11E23` nicht in `activeProjectsProcessing` → Nutzer kann dieselbe Folge klassisch über „Auswählen"→Verarbeiten starten; Zeile 4330 prüft nur `activeProjectsProcessing.has(currentProject)`, nicht die files-Sets laufender Gruppen-Jobs → **keine Blockierung**.
- Gruppe↔Gruppe mit identischen relpaths funktioniert (exakte String-Übereinstimmung) — der einzige durch die Prüfung abgedeckte Fall. Frontend-Tests bestätigen das nur für A↔A (`inbox_group.test.js:1777`). Da die Datei-Identität jetzt relpath und die Projekt-Identität Ordnernname ist, können die beiden Job-Arten einander strukturell nicht mehr erkennen; der zweite Job scheitert dann mittig im ersten mit TOCTOU-Error (processor.py:951/1491) — laut, aber nach teilweisem Datei-Move.

**2. [wichtig] Laufender Gruppen-Job deaktiviert die Ordner-Zeile nicht** (app.js:13140, 2461-2508, 10860-10869).
- Szenario: Ordner `ThWaDeS11E23` per Checkbox gruppiert, Job läuft. `processingSet.has("ThWaDeS11E23")` = false (Job hat `project_name ""`), also: Checkbox nicht disabled, **Quarantäne-Knopf klickbar** (13207-13212) → `deleteProject` verschiebt den Ordner während des Laufs → Job bricht mit „Datei nicht gefunden (TOCTOU)" ab, teilverarbeitete Gruppe bleibt halbfertig. Vor dem Patch betraf diese Lücke nur lose Root-Dateien; jetzt ist sie für kompletten Ordner (inkl. ihrer Metadaten) bedienbar.

**3. [wichtig] „Auswählen"-Knopf nutzt weiterhin `suggested_query` statt `single_video_query`** (app.js:13197 → 2524-2528 → 13293 → 1820/1848).
- Szenario: Ordner `ThWaDeS11E23` mit Datei `The.Walking.Dead.S11E23.720p.mkv`. Backend: `suggested_query="ThWaDe"` (project_api.py:1420-1424, aus dem **Ordnernamen**), `single_video_query="The Walking Dead"` (1512-1516, aus dem **Dateinamen**). Klick auf „Auswählen" (klassischer Modus) befüllt die Serien-Suche mit „ThWaDe"; Klick auf Gruppen-/Checkbox-Pfad nutzt „The Walking Dead". Dasselbe Inbox-Objekt bekommt je nach入口 einen anderen Such-/Profil-Query — Profile (`/api/profile`-Save bei Ausführung, app.js:10669 `show_name` aus selectedShow) und Suche divergieren. Kein Datenkorruptionsfehler, aber die im Kontext genannte Divergenz ist real und im Patch nicht an 13197 verdrahtet.

**4. [Bedenken] S/E-Fallback-Rateschauen auf den ersten Match im relpath — Ordneranteil gewinnt** (parse.js:28-78 via app.js:3704/3712/3817).
- Szenario: Ordner `Foo.S01E99` enthält `Real.Show.S02E05.mkv` ( umbenannter Ordner). `guessSeasonAndEpisode("Foo.S01E99/Real.Show.S02E05.mkv")` matcht zuerst `s01e99` → falsche Vorauswahl Staffel/Folge in der Matrix. Nur Fallback, wenn das Backend (`match-episodes`, nutzt korrekt `basename`, search_api.py:118) nichts liefert; Nutzer sieht die falsche Vorauswahl. Vor-Patch irrelevant (Ordner nicht gruppierbar).

**5. [kosmetisch] `cleanFilenameForManualTitle` stript kein Verzeichnis** (parse.js:13-19 via app.js:3718).
- `ThWaDeS11E23/The.Walking.Dead.S11E23.mkv` → Manual-Titel „ThWaDe /The Walking Dead" (S/E-Teile entfernt, Slash bleibt). Nur editierbarer Default-Wert.

**6. [Bedenken] Ordner-Belegte werden zurückgelassen** (helpers.py:870-918, queue_api.py:95, processor.py:1091-1099 + 1725).
- Szenario: Ordner enthält `The.Walking.Dead.S11E23.mkv` + `ThWaDeS11E23.nfo` (nach Ordner, nicht nach Video-Stem benannt) + `folder.jpg`. Companion-Erkennung akzeptiert nur `Stem.*`-Präfixe → diese Dateien sind nie in `all_files` (883-884/95), erscheinen in keiner Preview, werden nicht hochegezogen. Video+Stem-Companions gehen nach Outbox/NAS, der (nun videoleere) Ordner bleibt inkl. Resten in der Inbox; leerer Ordner wird für files-Jobs bewusst nicht aufgeräumt (1092, 1725). Die Smart-Inbox zeigt ihn nicht mehr (video_count==0, project_api.py:1348), aber er müllt die Inbox physisch.

**7. [Bedenken] Extension-Listen driften**: Gruppen-Mitglieder können `.ts/.m2ts/.flv/.3gp/.wmv` sein (GROUP_VIDEO_EXTENSIONS, helpers.py:798; Backend-Zählung project_api.py:1342), aber `updateSizeEstimation` (app.js:2620) und das Datei-Tabellen-Badge (app.js:12884) kennen nur 5 Extensions → für Ordner-Videos dieser Formate keine Prognose / Badge „TS" statt video, während die Matrix (3564/3636, 10 Ex.) sie zeigt. Vorhandene Inkonstistenz, durch Ordner-Mitglieder erstmals in Gruppen-Payloads sichtbar.

**8. [kosmetisch] `window.currentProjectFileNfoStatuses[file]`** (app.js:3840/3846; Map-Quelle 2880) — Gruppen-relpaths treffen nie in die Map der letzten `selectProject`-Scans; „NFO fertig → skip"-Default entfällt. Bestehendes Verhalten, jetzt mit anderer Key-Form.

**9. [kosmetisch/Randrisiko] `data-new-file="${file}"` unescaped** (app.js:3995; korrekt escaped nur 3828). `"` im Ordner-/Dateinamen würde das Attribut brechen (Dup-Badge-Flow 12004-12008). Vorhandenes Muster, jetzt mit längeren Strings.

**10. [ok, verifiziert] Keine Drift keys↔files**: `mappings`-Schlüssel (4346/4366), `payload.files` (4448), Preview `mappings.get(f)` (queue_api.py:498), Processor `filename` (1354/1485), `nfoOverrides.episodes` (4481 → processor.py:1577) und `manifest`-Keys (1732) verwenden durchgehend **identische relpath-Strings**; `validate_group_files` ändert sie nur um `strip()` (helpers.py:823/862). Kein basename-Truncating auf diesen Pfaden gefunden. Retry (queue_api.py:930-998) spielt `params["files"]` unverändert zurück (833, 909-910).

---

## (c) Was ich nicht prüfen konnte

- **Kein Runtime-/Browser-Test**: alles statisch; die neuen Tests (`inbox_group.test.js` AK1/AK4/AK5, `test_inbox_group_files.py` AK6/AK7, `test_inbox_suggestions.py` AK2/AK3) habe ich nur überflogen, nicht ausgeführt (Leseaufgabe).
- **Windows-Pfade**: Frontend-relpaths sind erzungen POSIX (`/`, project_api.py:1510); `is_subtitle_matching_video` vergleicht mit `os.sep` (queue_api.py:386) und `os.path.dirname/relpath` (500-501, 572ff.) ist unter Windows backslash-dominiert — ob gemischte Separatoren dort driftieren, ließ sich ohne Lauf nicht abschließend bewerten.
- **NAS-/pCloud-Transfer-Stufe** (processor.py:1741ff.) nur angelesen: Zielpfade bauen sich aus `clean_title`/`clean_show_name`, relpath-frei — im Detail nicht Zeile für Zeile verifiziert.
- **`clean_show_name`-Normalisierung** im Edge-Fall (Groß-/Kleinschreibung, Sonderzeichen), die entscheiden könnte, ob `single_video_query` und `suggested_query` verlorener Dateien im selben gemischten Group-Key landen — Annahme „beide sauber" basiert auf identischer Pipeline (project_api.py:1441-1443 vs. 1514-1516), nicht auf Test.
- **Profil-Load-Pfad** `load_show_profile(suggested_query)` für Ordner mit `single_video_query != suggested_query`: Welche Variante beim klassischen „Auswählen"最终 greift (scan-project-eigene Herleitung, project_api.py:353-368), habe ich nicht bis zum Suche-Resultat durchgerechnet.

Kurzfazit: Die relpath-Kette selbst (Payload → Matrix → mappings/files → Preview → Processor → Retry) ist konsistent und hält stichprobenartig allen String-Vergleichen stand. Die realen Schwachstellen liegen **neben** der Kette: die Queue-/Processing-Erkennung (Befunde 1-2, Projektname- vs. files-Identität) und der nicht verdrahtete `single_video_query` am „Auswählen"-Knopf (Befund 3) — genau die Klasse von Consumer, deren Übersehen im Vorlauf schon einmal Thema war.
</task_result>
</task>
