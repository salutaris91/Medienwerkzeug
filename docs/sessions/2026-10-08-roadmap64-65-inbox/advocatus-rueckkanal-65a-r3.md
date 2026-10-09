# Rohoutput advocatus — Rückkanal-Abnahme #65 Lauf A, Runde 3, 2026-10-09

Hinweis Claude Code (2026-10-09): Mechanisch aus `opencode export ses_edf9cdfb2ffesyL6PoyWfc2fSu` (ceo-planner, Rückkanal-Sitzung Runde 3) abgelegt, nicht vom Moderator abgeschrieben (Lehre 59). Einzige Änderung: Trailing Whitespace entfernt. Volle Daten: Kit `scripts/gate-a2/logs/2026-10-09-roadmap65-lauf-a-nachbesserung3/export-rueckkanal.json`.

---

## Advocatus: letzte Runde, nur kritisch (Subagent-Sitzung ses_edf99db46ffenSLn3ocpU63SL6, Status: completed)

<task id="ses_edf99db46ffenSLn3ocpU63SL6" state="completed">
<task_result>
# Risikoprüfung — ROADMAP #65 Lauf A, dritte & letzte Rückkanal-Runde

Prüfgegenstand: Head `f264b1f`, Nachbesserungs-Diff `cb152f0..f264b1f` (laut Auftrag: `API.md` +4, `processor.py` +68, `tests/test_inbox_group_files.py` +279). Arbeitsweise: ausschließlich statische Lektüre des aktuellen Dateizustands im Worktree. Kein Git, kein bash, nichts geschrieben — die Head-Identität `f264b1f` und der exakte Diff-Umfang sind **nicht selbst verifiziert** (kein Git-Zugriff), ich habe nur die vier Befunde gegen den Ist-Stand geprüft.

---

## 1. Befund-Status

| Befund | Geschlossen | Code (Datei:Zeile) | Test (Name:Zeile) |
|---|---|---|---|
| **N1** [kritisch] Fallback-Video-Rename | **ja** | `processor.py:1489–1492` (Existenzcheck `os.path.exists(target_filepath) and abspath(filepath) != abspath(target_filepath)` → `raise RuntimeError`) vor `os.rename` bei `:1495` | `test_n1_fallback_video_target_collision_with_foreign_file_aborts_loudly` `tests/test_inbox_group_files.py:729–766` (byte-genau `:763–764`) |
| **N2** [wichtig] explicit_renames/subs `new` | **ja** | `processor.py:960–978` (subs: absolut `:970–971`, Traversal `:972–974`, Ziel-Existenz `:977–978`); `:979–997` (renames: absolut `:989–990`, Traversal `:991–993`, Ziel-Existenz `:996–997`); Apply-Redundanz direkt vor `os.rename` `:1065` und `:1078` | `test_n2_explicit_renames_destination_validation_and_collisions` `:805–870` (byte-genau `:867–869`); `test_n2_explicit_subs_destination_validation_and_collisions` `:872–935` (byte-genau `:932–935`) |
| **N3** [wichtig] Konvertierung temp/final | **ja** | `processor.py:1604–1614` (Temp-Check `:1607–1610`, Final-Check `:1611–1614`) vor `execute_video_conversion` bei `:1638` | `test_n3_convert_temp_target_collision_aborts_loudly` `:937–969` (byte-genau `:967–969`); `test_n3_convert_final_target_collision_aborts_loudly` `:971–1003` (byte-genau `:1001–1003`) |
| **N5** [wichtig, Doku] API.md | **ja** | `API.md:263` (preview-process) und `API.md:268` (process) — beide nennen „nur für `media_type` `'tv'` … HTTP 400“ | — (Doku, kein Test nötig) |

**Zusätzlich (über die vier Befunde hinaus) abgedeckt:** Episoden-NFO-Generierung im files-Zweig (`processor.py:1560–1565`, Ziel `{clean_title}.nfo` mit Existenzcheck) + Test `test_n1_nfo_target_collision_with_foreign_file_aborts_loudly` `:768–803`. Das war in R2 noch eine offene Kollisionsfläche derselben Klasse und ist jetzt laut abgesichert.

---

## 2. Beantwortung der drei Prüffragen

**(1) Sind die neuen Checks vor jeder schreibenden Aktion wirksam?** Ja. Alle drei Zielpunkte prüfen `os.path.exists(<ziel>)` **vor** der schreibenden Operation: N1 vor `os.rename` (`:1489`→`:1495`), N2 doppelt — Scope-Phase (`:977/996`) **und** redundant unmittelbar vor `os.rename` (`:1065/:1078`), N3 vor `execute_video_conversion` (`:1607–1614` → `:1638`). Der `abspath(old) != abspath(new)`-Vergleich verhindert zudem, dass die eigene Datei (No-Op-Rename bzw. Konvertierung einer bereits `.mkv`-benannten Datei auf ihr eigenes Ziel) fälschlich als Kollision gewertet wird.

**(2) Sind alle neuen Raises/Checks an `files_param is not None` gegated (D1)?** Ja, vollständig. Die Scope-/Ziel-Validierung steht komplett im Block `if files_param is not None:` (`:947–997`); N1-Check (`:1489`), NFO-Check (`:1560`), N3-Checks (`:1606`) und die Apply-Redundanz (`:1062/:1074`, `:1065/:1078`) sind jeweils explizit mit `files_param is not None` bedingt. Alt-Pfade ohne `files` (inkl. des Untertitel-Fallback-`os.listdir`-Zweigs `:1540–1552`) bleiben unverändert.

**(3) Legitime Aufruffolge mit False-Positive oder übersehener Fremddatei-Überschreibung?** Kein [kritisch]-Befund gefunden. Der normale Preview-/Process-Client setzt `new`/`target_filename` stets auf `clean_title.ext` (flacher Name, kein Pfadteil, kein Absolutpfad); für diesen Fluss sind alle drei Zielpunkte jetzt existenzgeprüft. Keine legitime Aufruffolge überschreibt mehr still eine Fremddatei im Inbox-Root. Die in R2 entkräfteten Stellen (safe_move_recursive-Aufrufe, `move_with_fallback`, `_finalize_job:346`, NAS-Companion-Copy, movie-/tool-Zweige) sind vom neuen Diff nicht berührt und wurden daher nicht erneut geprüft.

---

## 3. Neue [kritisch]-Befunde

**Keine.** Es wurde kein stiller Datenverlust/Überschreiben einer Fremddatei und keine Aktion außerhalb der Gruppe gefunden, die ein legitimer Preview-/Process-Aufruf (ohne manipulierte Parameter) auslösen kann.

---

## 4. ROADMAP-Kandidaten (nicht blockierend)

- **N2(b)-Rest:** `new` mit Pfadteil in einen *existierenden* Unterordner innerhalb der Inbox (kein `..`, kein Absolutpfad, Ziel noch nicht vorhanden) wird nicht blockiert — erreichbar nur mit manipuliertem `new`, ohne Überschreiben; ggf. Konfinement von `new` auf flache Inbox-Root-Namen erwägen.
- **Stale-Temp:** Eine zurückgebliebene `{clean_title}_neu.mkv` aus einem abgebrochenen Convert-Lauf lässt den Retry laut abbrechen (konservativ, kein Datenverlust).
- **Halbzustand:** Bei lautem Abbruch in einer späteren Episode bleiben frühere Episoden bereits umbenannt/verschoben (vorbestehendes sequenzielles Design, kein neuer Befund).
- **Test-Hygiene:** `test_n1_nfo_…` ruft ungepatchtes `mw_metadata.fetch_tvdb` auf (echter Netzwerk-Call, nur durch `try/except` `:1161–1191` abgefangen) — potenziell langsam/flaky, aber korrekt funktionsfähig.

---

## 5. Restunsicherheiten

- Head `f264b1f` und Diff-Umfang `cb152f0..f264b1f` nicht selbst verifiziert (kein Git-Zugriff); Bewertung beruht auf dem Ist-Stand der drei Dateien.
- TOCTOU-Fenster zwischen Existenzcheck und `os.rename`/`execute_video_conversion` besteht weiterhin (AK7 prüft nur die Quell-Existenz, nicht das Ziel) — nicht über einen legitimen Client-Aufruf ausnutzbar, daher nicht kritisch.
- `generate_episode_nfo` (in `gui/mw_metadata.py`) selbst wurde nicht geprüft, da außerhalb des Diffs; ihr einziges Ziel im files-Zweig (`{clean_title}.nfo` in `current_dir`) ist durch den neuen Check `:1560–1565` abgedeckt.

**VERDICT: APPROVE** — N1/N2/N3/N5 sind geschlossen, alle neuen Checks sind D1-konform an `files_param is not None` gegated, die neuen Tests sind echte `process_worker`-Ausführungen mit byte-genauen Fremddatei-Assertionen, und es verbleibt kein [kritisch]-Befund.
</task_result>
</task>
