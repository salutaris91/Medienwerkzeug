# Rohoutput advocatus — Rückkanal-Abnahme #65 Lauf A, 2026-10-09

Hinweis Claude Code (2026-10-09): Mechanisch aus `opencode export ses_ee06a9523ffewYvmhGiv6JaAr9` (ceo-planner, Rückkanal-Sitzung) abgelegt, nicht vom Moderator abgeschrieben (Lehre 59). Einzige Änderung: Trailing Whitespace entfernt. Volle Daten: Kit `scripts/gate-a2/logs/2026-10-09-roadmap65-lauf-a-nachbesserung/export-rueckkanal.json`.

---

## Advocatus: Risiken Lauf A (Subagent-Sitzung ses_ee0625539ffe7jfvEly8Pxxjyf, Status: completed)

<task id="ses_ee0625539ffe7jfvEly8Pxxjyf" state="completed">
<task_result>
Verifikation abgeschlossen. Alle Aussagen unten sind **eigene Code-Prüfung** gegen den genannten Stand (Head `2a5eec5`), gelesen ausschließlich im Worktree-Pfad. Ich habe keine Shell-/Git-Befehle ausgeführt.

---

## 1. Zu V-A bis V-D

### V-A — „files + media_type != tv“ — **BESTÄTIGT, [kritisch]**

**Eigene Verifikation der Kette:**

1. `/process` validiert `files[]` **ohne** `media_type`-Bindung. In `queue_api.py:811-826` wird `files_param` validiert und `params["files"] = validated_files` gesetzt, **bevor** `media_type` überhaupt gelesen wird (`queue_api.py:830`). Es gibt keine Abweisung von `files` bei `media_type=="movie"` (oder `youtube`, `tool_*`).

2. `processor.py:863-880` berechnet `scope_files`/`validated_files` für **jeden** files-Job — aber der `movie`-Zweig nutzt sie nirgends. Ich habe den gesamten `elif media_type == "movie":`-Block (`processor.py:1787` ff.) geprüft: `scope_files`, `validated_files`, `companion_files` kommen dort nicht vor.

3. Der filmische Videoselektor greift auf die **gesamte** Inbox-Root: `processor.py:1814-1820`
   ```python
   if explicit_renames is not None:
       video_files = [r["new"] for r in explicit_renames]
   else:
       if is_single_file:
           video_files = [project_name]
       else:
           video_files = [f for f in os.listdir(current_dir) if ...]
   ```
   Für einen files-Job ist `current_dir == inbox_root` (`:871`), `is_single_file == False` (`:872`), `explicit_renames == None` (kein Client-Pfad setzt es) → `video_files` = **alle** Videos in der Inbox-Root. Jede wird in `processor.py:1979-1985` per `os.rename(filepath, target_filepath)` auf `clean_movie_name` umbenannt — bei mehreren Videos kollidieren sie auf denselben Zielnamen (POSIX-`os.rename` überschreibt → **Datenverlust** der übrigen Filme).

4. Der Begleit-Move räumt **alles** rekursiv: `processor.py:2081-2088`
   ```python
   safe_move_recursive(current_dir, dest_movie_dir_outbox,
       prefix_filter=None, fallback_basename=clean_movie_name,
       whitelist=whitelist_movie, junk_list=explicit_junk)   # allowed_files=None
   ```
   In `safe_move_recursive` gilt dann: `allowed_set is None` (`:501-508` → kein Filter), und `prefix_filter is None` → `belongs = True` (`:533-534`). Ergebnis: **jede** Nicht-Video-Datei unter `inbox_root` (rekursiv, inkl. fremder `.srt`, `.nfo`, `.jpg`, `.txt`) wandert in den Film-Outbox-Ordner.

5. **Divergenz Preview↔Process bestätigt.** `/preview_process` Movie-Zweig iteriert `all_files` (`queue_api.py:172-182`), und `all_files` ist bei files-Jobs `validated + companion` (`queue_api.py:89-92`). Die Vorschau zeigt also nur die Gruppe; die Ausführung räumt die ganze Inbox. Das verletzt exakt das ADR-65-2-Prinzip „Preview zeigt exakt, was der Job ausführt“ (`briefing-65.md:84`).

6. **`youtube`/`tool_nfo_agent`:** `youtube` (`:2322` ff.) und `tool_nfo_agent` (`:3223` ff.) ignorieren `files` vollständig und räumen den Inbox-Root nicht querschnittlich (kein `safe_move_recursive`/`os.walk(current_dir)` dort — per Grep verifiziert: die Sweep-Stellen über `current_dir` sind nur `:350`, `:925`, `:1462`, `:1602`, `:1701`, `:1820`, `:2081`, `:3156`, `:3187`). Hier also **kein** Fremd-Datei-Sweep, sondern nur „files wird still ignoriert“ — harmlos, aber inkonsistent.

**Schwere:** [kritisch] — ein einziger POST `{"media_type":"movie","files":[...]}` räumt die komplette Inbox (Nicht-Videos rekursiv) und kollabiert mehrere Videos auf einen Namen.

---

### V-B — Fallback-Untertitel-Rename ohne Scope — **BESTÄTIGT, [wichtig]**

**Eigene Verifikation:** `processor.py:1439` (`if explicit_renames is None:` — der „Old backwards compatible fallback“) → `:1460-1472`:
```python
base_old = os.path.splitext(filename)[0]
for f in os.listdir(current_dir):
    if f.startswith(base_old) and f != filename:
        sub_ext = os.path.splitext(f)[1].lower()
        if sub_ext in ['.srt', ...]:
            ...
            os.rename(sub_old_path, sub_new_path)
```
Für einen files-Job ist `current_dir == inbox_root` (`:871`). Das ist exakt die F1-Klasse (`startswith(stem)` ohne Punkt/Wortgrenze) an einer **nicht** behobenen Stelle: `allowed_files`/dot-prefix greifen hier nicht, weil es ein **direktes `os.rename`** über `os.listdir(current_dir)` ist, keine `safe_move_recursive`-Route.

Konkret: Gruppe `Folge 1.mkv` (`base_old="Folge 1"`) + fremde `Folge 10.srt` in der Root → `"Folge 10.srt".startswith("Folge 1") == True` → wird auf `clean_title.srt` umbenannt.

**Erreichbarkeit bestätigt:** `files`+`mappings` **ohne** `explicit_renames` führt in den Fallback. Der `/process`-Handler verlangt `explicit_renames` nicht (nur `mappings`-Schlüssel-Konsistenz, `queue_api.py:819-825`). Der konforme Lauf-B-Client würde zwar `explicit_renames` senden, aber die API weist den Aufruf ohne nicht ab — und der bestehende AK6-Test ruft `process_worker` selbst ohne `explicit_renames` auf, fährt also genau diesen Pfad.

**Zusatzbefund im selben Block (Verstärkung, nicht separat gezählt):** mehrere Treffer derselben Gruppe (z. B. `Folge 1.de.srt` + `Folge 1.en.srt`) werden **beide** auf `clean_title + ".srt"` umbenannt — die Suffix-Auflösung (`parse_subtitle_suffix`) fehlt hier im Gegensatz zur Preview (`queue_api.py:608`). Kollision + Überschreiben. Das ist Alt-Verhalten, aber über den files-Pfad jetzt erstmals in scope-relevanter Form erreichbar.

**Schwere:** [wichtig] — fremde Datei wird umbenannt (Datenintegrität), kein Löschen, benötigt Namenskollision der Form „Stem ohne Wortgrenze“.

---

### V-C — explicit_*-Scope-Check mit basename-Fallback — **BESTÄTIGT, [wichtig]**

**Eigene Verifikation:** `processor.py:949-965` prüft für `explicit_junk` (`:952`), `explicit_subs` (`:958`) und `explicit_renames` (`:964`) jeweils:
```python
if norm_j not in scope_files and os.path.basename(j) not in scope_files and j not in scope_files:
    raise RuntimeError(...)
```
Ein fremder Eintrag `"Fremdordner/Folge 1.srt"` passiert, sobald `"Folge 1.srt"` (die Begleitdatei in der Root) in `scope_files` steht — `basename(j)` matcht, `norm_j` nicht. Danach:
- `explicit_junk`: `:972-975` → `os.path.join(current_dir, j)` → `trash.send_to_trash` (Quarantäne einer fremden Datei).
- `explicit_subs`: `:1036-1045` → `os.rename` einer fremden Datei.
- `explicit_renames`: `:1026-1034` → `os.rename` einer fremden Datei.

Das verletzt AK6(d) „außerhalb der Scope-Menge → LAUT abbrechen“ (`briefing-65.md:49`) für die Eingabeklasse „Pfad mit kollidierendem Basename“.

**Analoge basename-/Suffix-Fallbacks (geprüft, sekundär):**
- `move_with_fallback:404`: `path_endswith(src_path, item["old"]) or os.path.basename(src_path) == item["new"]` — breiter Basename-Match auf den **neuen** Namen.
- `safe_move_recursive:540`: `path_endswith(f_path, item["old"]) or os.path.basename(f_path) == item["new"]`.

Beide sind in `safe_move_recursive` wirksam, aber dort (a) bei files-tv-Jobs vorgeschaltet durch das `allowed_files`-Realpath-Set (`:516-519`) und (b) bei movie durch den `prefix_filter=None`/`allowed_files=None`-Sweep ohnehin irrelevant (V-A dominiert). Der **primäre** und eigenständig ausnutzbare Fall ist der Scope-Check `:949-965` selbst.

**Schwere:** [wichtig] — Quarantäne/Umbenennung fremder Dateien, benötigt `explicit_*` mit kollidierendem Basename (Attacker-/Bug-Input). Kein permanentes Löschen (`send_to_trash` ist reversibel), aber klare Scope-Verletzung.

---

### V-D — `current_dir != inbox_root` an Alt-Pfaden — **BESTÄTIGT als Verhaltensänderung, [kosmetisch]**

**Eigene Verifikation der Mechanik:**
- `processor.py:1048`: `if files_param is None and current_dir != inbox_root:` (Root-Leerordner-Cleanup).
- `processor.py:1610`: `cleanup_empty_dirs=(files_param is None and current_dir != inbox_root)`.

Für `project_name=""` ohne files und für Einzeldatei-Jobs **in der Root** (`is_single_file=True`, `current_dir == inbox_root`, `:889-890`) entfällt damit der Leere-Ordner-Cleanup. Für Ordner-Projekte (`current_dir == inbox_root/<Ordner> != inbox_root`) läuft er weiter.

**Bewertung der Konsequenz:** Der weggelassene Cleanup räumt nur **leere Unterordner** der Inbox-Root weg. Ihn zu unterlassen ist **kein Datenrisiko**, sondern ein **Sicherheitsgewinn** — es ist exakt die `#68`-Klasse (überbreiter Cleanup, der fremde leere Ordner der Inbox-Root quarentänt). Die ADR-65-3-Absicht („Root-Leerordner-Cleanup überspringen“, `briefing-65.md:88`) wird dadurch auch für den Alt-Root-Pfad erfüllt.

**Plan-Wortlaut-Spannung:** AK8 verlangt „byte-genau“ für Pfade **ohne** files (`briefing-65.md:51`), ADR-65-6 sagt, `#68` werde **nicht** mitgelöst (`briefing-65.md:105-109`). Die `current_dir != inbox_root`-Klausel verändert den Alt-Root-Pfad faktisch (leere Unterordner bleiben stehen) und ist damit streng genommen eine De-facto-Minimal-Mitigation von `#68` — eine Abweichung von der wörtlichen AK8/ADR-65-6-Linie, aber in die **sichere** Richtung und gedeckt durch AK6(a2) „bei `src_dir == inbox_root`“ (`briefing-65.md:49`). Ob die Klausel „NEU“ ist, kann ich ohne `git diff` nicht abschließend belegen (siehe Abschnitt 4).

**Schwere:** [kosmetisch] — kein Datenrisiko, nur eine (sichere) Verhaltensabweichung an Alt-Pfaden mit Plan-Wortlaut-Spannung; sollte in der Review/VERLAUF explizit als bewusste Abweichung dokumentiert werden.

---

## 2. Neue Befunde (keine F1/F2-Wiederholung)

### N1 — `files` ist nicht an `media_type=="tv"` gebunden; Scope-Härtung existiert nur im tv-Zweig — **[kritisch]**

**Eigene Verifikation:** `queue_api.py:811-826` (+ `:73-92` für Preview) validiert `files` medien-typenneutral; `media_type` wird erst `:830` gelesen und nie gegen `files` geprüft. Der Processor berechnet den Scope generisch (`:863-880`), aber **nur** der tv-Zweig konsumiert ihn. Alle anderen Zweige, die `current_dir` (= `inbox_root` bei files) querschnittlich scannen, sind ungeschützt:
- `movie`: `:1820` listdir + `:2081` `safe_move_recursive(prefix_filter=None, allowed_files=None)` → voller Sweep (das ist V-A).
- `tool_pull_files`: `:3156-3168` `os.walk(current_dir)` zieht **jede** Datei aus jedem Unterordner in die Root.
- `tool_batch_convert`: `:3187` listdir + Konvertierung mit `delete_original=True` (`:3213`) über alle Root-Videos.

Das ist die **Wurzelursache** von V-A und zeigt: der Lauf-A-Schutz ist strukturell tv-only. Empfehlung (zwei Optionen, Entscheidung bei Alex): (a) `files` bei `media_type != "tv"` mit HTTP 400 abweisen, oder (b) den Movie-/Tool-Zweig ebenfalls auf `scope_files` begrenzen. Ich empfehle (a) als kleinste, risikoärmste Absicherung, da der files-Weg laut Plan ausschließlich für die Serien-Gruppierung gebaut wurde.

### N2 — Subdirectory-Gruppen: `base_old` nutzt den vollen Relativpfad → Begleitdateien werden verfehlt; Preview↔Process-Divergenz — **[wichtig]**

**Eigene Verifikation:** `processor.py:1587` setzt `base_old = os.path.splitext(filename)[0]` mit `filename` = **voller relativer Mapping-Schlüssel**. Für eine Gruppe in einem Unterordner (`"Sub/Show.S01E01.mkv"`) ist `base_old == "Sub/Show.S01E01"`, während `comp_base = os.path.basename(comp)` = `"Show.S01E01.de.srt"` ist. Damit schlägt `comp_base.startswith(base_old)` (`:1591`) **fehl** → die Begleitdatei wird **nicht** in `episode_allowed_files` aufgenommen → `safe_move_recursive` (`:1602`, mit `allowed_files`) lässt die Untertitel im Unterordner zurück.

Die **Preview** rechnet hier korrekt mit dem Basename: `queue_api.py:568` `base_old = os.path.splitext(basename)[0]` (mit `basename = os.path.basename(f)`, `:490`) und zeigt die Begleitdatei als `subs`-Rename an. Ergebnis: Preview sagt „wird umbenannt/verschoben“, Prozess lässt sie liegen — **Divergenz**, die gegen das ADR-65-2-Prinzip verstößt. (Gleiche Wurzel erklärt, warum der V-B-Fallback bei Subdir-Gruppen ins Leere läuft: `:1461` `f.startswith("Sub/Show.S01E01")` matcht nie einen Root-Namen.)

Kein „berührt fremde Dateien“ (eher ein Unter-Touch), aber ein echter Funktions-/Konsistenzbefund desselben `base_old`-Konstrukts.

---

## 3. Testdeckungs-Lücken in `tests/test_inbox_group_files.py`

Geprüft gegen die 477 Zeilen der Datei:

| Befund | Wird er von einem bestehenden Test gefangen? | Fehlender Testfall, der ihn finge |
|---|---|---|
| **V-A** (files+movie Sweep) | **Nein.** Es gibt keinen `files`+`movie`-Test. `test_backwards_compatibility_paths_without_files_param` deckt nur movie **ohne** files ab (`:461-473`); der AK6-Test ist tv+files. | Ein Test, der `process_worker` mit `{"media_type":"movie","files":["A.mkv"]}` + fremden Root-Videos/Nicht-Videos aufruft und prüft, dass **nur** `A` verschoben wird / fremde Dateien bleiben. |
| **V-B** (Fallback-Rename Wortgrenze) | **Nein.** Der AK6-Test fährt den Fallback (kein `explicit_renames`), aber mit Stem `Show.S01E01`, zu dem keine kollidierende Fremddatei existiert; die adversarische Datei (`MyShow - S01E01 - Pilot.adversarial.txt`) kollidiert mit `clean_title`, nicht mit dem Video-Stem. | Test „Folge 1.mkv“ + fremde „Folge 10.srt“ + `explicit_renames` weggelassen → prüfen, dass „Folge 10.srt“ **nicht** umbenannt wird. |
| **V-C** (basename-Fallback) | **Nein.** `test_explicit_junk_outside_scope_aborts_loudly` (`:354-377`) nutzt `"Foreign.mkv"` (Basename **nicht** in Scope) → bricht korrekt ab. Es gibt keinen Fall, wo der Basename mit einem Scope-Eintrag kollidiert. | Test „Fremdordner/Show.S01E01.de.srt“ als `explicit_junk` bei Gruppe, deren Begleitdatei `Show.S01E01.de.srt` ist → muss LAUT abbrechen, darf nicht quarantänen. |
| **V-D** (Empty-Dir-Gating) | **Nein.** `test_backwards_compatibility_paths_without_files_param` prüft nur Outbox-Ergebnis, nicht das Leere-Ordner-Verhalten des Root-/Einzeldatei-Jobs. | Test: leerer Unterordner in der Inbox-Root + Root-Einzeldatei-Job ohne files → dokumentierte Erwartung (bleibt stehen). |
| **N1** (fehlende media_type-Bindung) | **Nein.** Kein Test POSTet `files` mit `media_type != "tv"` und erwartet Ablehnung. | Endpunkt-Test: `{"media_type":"movie","files":[...]}` → HTTP 400. |
| **N2** (Subdir-Begleitdatei) | **Nein.** `test_key_contract_v1_exact_mapping_match` (`:379-394`) nutzt `SubFolder/Show.S01E01.mkv`, aber **nur** die Preview, nie die Ausführung. | Ausführungstest mit Subdir-Gruppe + Begleitdatei → Begleitdatei muss in den Outbox-Serienordner wandern. |

---

## 4. Restunsicherheiten (ohne Bash/Git nicht prüfbar)

1. **V-D „NEU?“:** Ob die Klausel `current_dir != inbox_root` in `:1048`/`:1610` gegenüber dem Vorzustand (vor #65) hinzugefügt wurde, kann ich ohne `git diff`/`git show` gegen `main` nicht belegen. Meine Schwere-Einschätzung [kosmetisch] gilt unter der Annahme „Klausel ist neu“; die Datenrisiko-Bewertung (kein Risiko, Sicherheitsgewinn) ist davon unabhängig.
2. **Realer Client sendet `explicit_renames`:** Ob der Lauf-B-Client bei `files` immer `explicit_renames` mitliefert (was V-B faktisch verschlösse), ist ohne den gemergten Lauf B nicht prüfbar. Die Lücke bleibt serverseitig offen und ist via direkter API erreichbar.
3. **`os.rename`-Überschreibsemantik:** V-A-Datenverlust (mehrere Videos → ein Zielname) beruht auf POSIX-`os.rename`-Overwrite. Auf dem Deploy-Target (Linux/NAS) bestätigt sich das; ich habe es nicht ausgeführt, sondern nur aus dem Code abgeleitet.
4. **Testgrün des AK6-Tests:** Ich habe den AK6-Test (`test_files_job_scope_enforcement_and_untouched_foreign_files`) nicht ausgeführt, sondern nur statisch nachvollzogen, dass er den Fallback-Pfad fährt und die V-B-Kollision nicht abdeckt. Ein tatsächlicher `pytest`-Lauf steht aus.
5. **`tool_*`-Zweige (N1):** Ob `media_type` wie `tool_pull_files`/`tool_batch_convert` über den öffentlichen `/process`-Endpunkt tatsächlich aufrufbar sind oder nur intern, habe ich nicht über die Aufruferkette verifiziert — die `media_type`-Dispatchung in `process_worker` akzeptiert sie aber generisch.

---

**Zusammenfassung der Urteile:** V-A [kritisch], N1 [kritisch] (Wurzelursache, deckt V-A mit ab), V-B [wichtig], V-C [wichtig], N2 [wichtig], V-D [kosmetisch]. Keine der Lücken wird durch die bestehende Testdatei gefangen (Abschnitt 3).
</task_result>
</task>
