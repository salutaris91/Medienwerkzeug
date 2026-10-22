<!-- Mechanisch aus `opencode export ses_e9b684467ffevjFjh8AAUBEHzA` extrahiert (Claude Code, 2026-10-22, Rückkanal): alle Assistant-Textteile in Reihenfolge, ungekürzt, unverändert (nur Trailing Whitespace entfernt). Rohdatei: Kit scripts/gate-a2/logs/2026-10-22-roadmap89-sample-ordner/rueckkanal/export-advocatus-e9b684467ffe.json -->

Ich habe das Briefing, alle sechs geänderten Dateien sowie die unveränderten Kontextstellen (processor.py:1070–1100/1560–1580, app.js:12500–12560/10420–10440) gelesen und die vier vorgegebenen Hinweise plus die Zusatzpunkte am Code nachvollzogen. Kein Befund ist [kritisch]. Im Folgenden sortiert nach Schweregrad.

---

## Befunde

### [wichtig] 1 — Hinweis (a): Top-Level-Ordner exakt „Sample“ macht alle seine Videos zu Samples
**Ort:** `gui/core/helpers.py:819–820` (Segment-Check) i. V. m. `gui/api/project_api.py:1516` (`rel_gvf = os.path.relpath(gvf, inbox_dir)`), `:1518`.

**Risiko:** Der Pfadsegment-Check läuft auf dem Pfad *relativ zur Inbox*, also **inklusive** des Projektordner-Namens als erstem Segment. Ein Inbox-Projektordner, der exakt `Sample`/`sample` heißt, erzeugt für jede darin liegende Videodatei das erste Segment `sample` → `"sample" in path_segments` schlägt an → alle Videos gelten als Samples → kein `single_video_relpath`, Ordner verschwindet still aus Gruppierung/Kästchen. Das ist eine echte Verhaltensänderung gegenüber `f0a29a4` (dort gab es in `project_api` gar keine Sample-Erkennung).

Wichtig zur Präzisierung: Der Segment-Check ist **Exakt-Gleichheit** (`"sample" in path_segments`, Listen-Membership), *nicht* Substring. Ein Ordner „Samples 2024“ oder „MySampleShow“ löst **nicht** aus (Segment `"samples 2024"` ≠ `"sample"`). Nur der literal `Sample`/`sample` benannte Ordner ist betroffen. Der Substring-Check gilt nur für den **Dateinamen** (`basename_lower`), nicht für Pfadsegmente.

**Realismus:** Sehr gering. Ein Top-Level-Ordner, der exakt „Sample“ heißt und eine ganze Show enthält, ist untypisch — im Lanterns-Muster ist `Sample` immer ein *Unter*ordner (dort korrekt). Die Asymmetrie ist bemerkenswert: In `queue_api.py` ist `f` relativ zu `current_dir` (Projektordner), dort taucht der Projektordnername also **nicht** als Segment auf — der Fehlgriff existiert nur im neuen `project_api`-Pfad.

**Empfehlung:** Akzeptieren für den Merge; **ROADMAP-Eintrag** (triviale Härtung: erstes Segment / Projektordnername vom Segment-Check ausnehmen, oder Pfad relativ zum Projektordner statt zur Inbox).

---

### [wichtig] 2 — Hinweis (b), Teil 2: `os.path.getsize`-Fehler wird still zu „Größe 0“ → Fehlklassifikation als Sample
**Ort:** `gui/api/project_api.py:1511–1515`.

**Risiko:** `except OSError: gvf_size = 0` schluckt Fehler still. Bei Größe 0 greift Kriterium 2 (`file_size < 300 MB` bei `largest > 300 MB`) → die Datei wird als Sample gewertet. Konkret fehlklassifiziert wird eine Hauptfolge nur im Sonderfall „Hauptfolgen-stat schlägt fehl **und** ein >300-MB-Sample existiert“ (bei einem <300-MB-Sample wird `largest` ≤ 300 MB und Kriterium 2 zündet nicht). Zusätzlich betrifft der stille Pfad exakt die 10er-Extensions-Dateien (`.m2ts/.flv/.3gp/.wmv`), die der bestehende `os.stat`-Zyklus `:1368–1374` **nicht** erfasst — dort wäre der Ausfall vollkommen stumm (kein `log_message`).

**Realismus:** Sehr gering (zwei kumulierte Bedingungen), aber es verletzt die Hausregel „Fehler sichtbar, kein stilles Scheitern“ und weicht vom direkt darüberliegenden, protokollierenden Zyklus ab.

**Empfehlung:** `log_message` analog `:1374` ergänzen; alternativ bei Stat-Fehler den Eintrag als „unbekannt“ behandeln statt als Sample. Kleiner Fix, low Dringlichkeit — optional vor Merge, sonst ROADMAP.

---

### [wichtig] 3 — Eigenständig: Kriterium 2 frisst echte kleine Episoden neben großen
**Ort:** `gui/core/helpers.py:822` (Kriterium 2) i. V. m. `gui/api/project_api.py:1524`.

**Risiko:** 250-MB-Episode neben 2,7-GB-Episode (kein „sample“ im Namen/Pfad): die kleine gilt als Sample → `non_sample_group_videos = [große]` → `single_video_relpath` = große Episode, die kleine bleibt **still im Inbox-Ordner** liegen und ist aus der Gruppierung ausgeschlossen. Regression gegenüber `f0a29a4`? Nein, streng genommen eine **Verbesserung mit neuem Fehlermodus**: In `f0a29a4` war der Ordner mit 2 Videos *komplett* blockiert (gar kein `single_video_relpath` → weder Gruppierung noch Kästchen). Jetzt ist er gruppierbar, aber nur die große Folge wird verarbeitet; die kleine echte Episode fällt still unter den Tisch.

Mildernd: Die kleine Episode wird **nicht gelöscht** (nur verarbeitete Dateien werden bewegt). Nach dem Verarbeiten der großen Folge wird der Restordner erneut analysiert und die kleine Episode erscheint dann als normales Einzelvideo (Kriterium 2 zündet nicht mehr, da keine Datei >300 MB übrig). Der Fall ist also wiederherstellbar, aber der Nutzer sieht beim ersten Durchlauf keinen Hinweis, dass eine Episode übrig bleibt — und `video_count` zeigt weiterhin 2, während der Ordner jetzt als „1 Video“ gruppiert wird (leichte Anzeige-Inkonsistenz, im Briefing als bewusste Entscheidung festgehalten).

**Realismus:** Mittel. Gemischte Qualitäten in einem Ordner kommen vor; die 300-MB-Schwelle ist grob. Dokumentiert ist im Briefing §6 nur Kriterium 1 als „grob“, **nicht** Kriterium 2.

**Empfehlung:** **ROADMAP-Eintrag** (Heuristikgrenze dokumentieren, ggf. künftig: kleine Nicht-Sample-Episoden ≠ Sample, oder Warnhinweis „Nicht-Sample-Video bleibt liegen“). Für den Merge akzeptieren — gegenüber `f0a29a4` ist es eine Netto-Verbesserung.

---

### [kosmetisch] 4 — Hinweis (b), Teil 1: Zusätzliche `stat`-Aufrufe (Performance)
**Ort:** `gui/api/project_api.py:1511–1515` vs. bestehendem Zyklus `:1368–1374`.

**Risiko:** Je Videodatei der 10er-Liste ein zusätzlicher `os.path.getsize` (= `stat`). Für Ordner, deren Videos alle in der 6er-Liste liegen, verdoppelt das die `stat`-Last; für `.wmv`/`.m2ts`-Ordner kommt sie neu hinzu. Auf einem Netz-Mount sind `stat`s Roundtrips.

**Realismus:** Gering/unkritisch. Der 30-s-Server-Cache (`:1303–1305`) deckelt die Neuberechnung: Der Frontend-6-s-Neuaufbau trifft nur den gecachten Pfad, die `getsize`-Schleife läuft höchstens einmal je 30 s. Single-User-App, einstellige Videodateien je Ordner üblich.

**Empfehlung:** Akzeptieren. Kein Handlungsbedarf; ggf. Notiz in ROADMAP, falls die Inbox je auf viele Hundert Ordner wächst.

---

### [kosmetisch] 5 — Hinweis (c): `.nfo`/`.sfv`-Ausschluss — kein realistischer Fall, in dem `<stem>.nfo` mitwandern sollte; show-level `tvshow.nfo` unberührt
**Ort:** `gui/core/helpers.py:937` (und Konstante `:799`).

**Risiko-Analyse:** `find_group_companion_files` arbeitet über die Stem-Präfix-Regel (`prefix = vstem + "."`, `:930` + `:942`). Ein show-level `tvshow.nfo`/`movie.nfo` beginnt **nicht** mit dem Videostem (`Show.S01E01.`) und war daher *nie* ein Companion — unabhängig vom neuen Ausschluss. Bestätigt durch den unveränderten Test `test_ak6_single_video_folder_job_execution` (`movie.nfo`, `tvshow.nfo`, `poster.jpg` bleiben unberührt). Der Ausschluss trifft also exakt das `<stem>.nfo`/`<stem>.sfv`-Muster der Release-Info, das den Kollisions-Abbruch auslöste.

Ein `<stem>.nfo`, das der Nutzer *mitnehmen möchte* (selbst erzeugte Episoden-NFO), ist genau der Kollisionsfall U2: Die App erzeugt die Episoden-NFO selbst (`generate_episode_nfo`, `processor.py:1568–1582`), eine vorhandene `<stem>.nfo` würde kollidieren. Verhalten ist in `API.md:270` dokumentiert und von Alex per Entscheidung (Ausschluss statt Variante A2) gedeckt. `.sfv` ist ein Prüfsummen-Artefakt ohne Migrationswert.

**Realismus des „Sollte-mitwandern“-Falls:** Keiner identifiziert.

**Empfehlung:** Akzeptieren, kein Befund. (Rest-Notiz: Der Ausschluss wirkt, wie beabsichtigt, auf *alle* `files[]`-Aufträge — das ist Teil der Entscheidung, nicht ein unbeabsichtigter Seiteneffekt.)

---

### [kosmetisch] 6 — Hinweis (d): Gruppenschlüssel/Suchbegriff kleingeschrieben — nur Anzeige, kein funktionaler Impact
**Ort:** `gui/api/project_api.py:1528–1532` (`raw_q` aus kleingeschriebenem Dateinamen; `clean_show_name` `gui/core/utils.py:23–30` lowercased **nicht**, entfernt nur Sonderzeichen) i. V. m. `gui/static/app.js:12538` (Gruppenschlüssel aus `single_video_query`).

**Risiko-Analyse:**
- **Profilsuche (`load_show_profile`):** nutzt `suggested_query` (`project_api.py:1446`), nicht `single_video_query` — unberührt.
- **NAS-Zielordnername:** entsteht in der Verarbeitung aus dem kanonischen Serientitel des gewählten Eintrags (Metadatenanbieter), nicht aus dem Gruppenschlüssel — kein Kleinschreibungs-Ordner.
- **Suche beim Anbieter:** Metadaten-APIs sind case-insensitiv; „lanterns“ findet „Lanterns“.
- **Anzeige:** Banner zeigt „lanterns (3 Folgen)“ statt „Lanterns“ — rein kosmetisch, im Briefing §6 bereits dokumentiert.

**Empfehlung:** Akzeptieren (bereits bewusst in den Scope-Entscheidungen verankert).

---

### [kosmetisch] 7 — Eigenständig: „sample“-Logik ist weiterhin an zwei Stellen implementiert (Drift-Risiko)
**Ort:** `gui/api/queue_api.py:222` (`"sample" in basename.lower() or "sample" in f.lower().split(os.sep)`) vs. neuer `find_sample_video_files` (`helpers.py:817–820`).

**Risiko:** Die Vereinheitlichung in ADR-89-2 betrifft nur die *Sample-Set-Bestimmung* (`:194`). Der `belongs_to_sample`-Fallback `:222` wiederholt Kriterium 1 weiterhin inline. Beide Stellen implementieren „sample“ im Namen/Pfad unabhängig — künftige Änderung an einer Stelle driftet. Heute verhaltensgleich auf Linux (dort ist `os.sep == "/"`; die Hilfsfunktion normalisiert zusätzlich `\`). Kein aktueller Bug.

**Empfehlung:** Akzeptieren; optional ROADMAP-Notiz (zweite Stelle ebenfalls auf die Hilfsfunktion umstellen).

---

## Verifizierte Punkte ohne Befund (Bestand)

- **Sparse-Dateien / `os.truncate`:** `f.truncate(n)` erzeugt die logische Größe als Metadaten-`st_size`; `os.path.getsize` liefert sie korrekt (kein Block-Read). Alle neuen Tests schreiben in `TemporaryDirectory` (AK10 erfüllt). Kein Befund.
- **Film-Vorschau identisch zu `f0a29a4`:** Die neue `find_sample_video_files`-Semantik (Substring im Basename, Exakt-Segment im Pfad, Kriterium 2) entspricht der alten Vorschau-Logik; `main_video = non_samples[0]` ist wegen vorherigem `sort(..., reverse=True)` die „größte Nicht-Sample-Datei“ wie zuvor; die Film-Regel „alles außer Hauptfilm = Sample“ (`:205–208`) bleibt in `queue_api`. AK6 deckt dies ab; der Bestandstest `test_sample_detection_in_preview` bleibt unverändert. (Nicht ausgeführt — siehe unten.)
- **`zip`-Konsistenz `project_api.py:1519–1522`:** `group_videos_with_sizes` und `group_video_files` entstehen in identischer Reihenfolge aus demselben `os.walk`; `sample_relpaths` enthält dieselben normalisierten Rel-Pfade wie `rel_gvf` — der Vergleich ist exakt-konsistent (Groß-/Kleinschreibung identisch, da die Hilfsfunktion das *Original* zurückgibt und nur intern lowercase prüft). Kein Bug.
- **Cache-Globalen `_inbox_cache`/`_inbox_cache_time`:** in Tests korrekt zurückgesetzt (`setUp`/`tearDown`); Neuberechnung nur bei Cache-Verfall. Kein Befund.
- **AK8-End-to-End** (`test_ak8_lanterns_group_job_no_nfo_collision_end_to_end`): vorhanden und plausibel; prüft genau, dass Sample/`.nfo`/`.sfv`/Fremdordner liegen bleiben und keine NFO-Kollision auftritt. Der Kollisionsschutz-Test `test_n1_nfo_target_collision_with_foreign_file_aborts_loudly` ist unverändert vorhanden (`test_inbox_group_files.py:768–803`). Bestandsschutz gegeben.

---

## Nicht prüfbar (offen benannt)

1. **Scope-Verletzung (nur die 6 erlaubten Dateien geändert):** Ich kann ohne `git` nicht verifizieren, ob `gui/static/app.js`, `gui/workers/processor.py` oder andere Dateien unangetastet blieben. Indirekter Hinweis: Die neuen Symbole (`find_sample_video_files`, `GROUP_EXCLUDED_COMPANION_EXTENSIONS`, `SAMPLE_SIZE_THRESHOLD_BYTES`) erscheinen nur in `helpers.py`, `queue_api.py`, `project_api.py`. Ein echter Diff-Scope-Nachweis ist mir nicht möglich.
2. **Behauptete Belege (Suite 537 passed/1 deselected, Frontend 231/231, Rot-Probe AK1/AK2/AK3/AK5/AK6/AK7/AK8 gegen `f0a29a4`, AK8-rot „Kollision beim Generieren von NFO“, Probe-Instanz):** nicht ausführbar, daher unverifiziert. Ich habe nur per Lektüre bestätigt, dass die zugehörigen Tests im aktuellen Stand vorhanden und logisch konsistent sind (AK1–AK8, `assertNotIn("Show.S01E01.nfo", …)` in `test_find_group_companion_files:137`).
3. **`git diff --check` / exakter Diff `60366d5` vs. `f0a29a4`:** nicht prüfbar (keine Git-/Shell-Befehle erlaubt, `.git` liegt außerhalb).

---

## Gesamtempfehlung

**VERDICT: APPROVE (JA zur Abnahme).**

Kein [kritisch], kein harter Regression-Blocker. Die drei [wichtig]-Befunde sind sämtlich niedrig-realistisch und durch den 30-s-Cache bzw. Wiederherstellbarkeit entschärft. Zwei davon (Befund 1 „Sample-Ordnername“, Befund 3 „Kriterium 2 frisst kleine Episode“) gehören als ROADMAP-Eintrag festgehalten; Befund 2 ist ein Einzeiler (Logging ergänzen), der auch nach dem Merge nachgezogen werden kann. Der eigentliche Fix (U1/U2) ist eng begrenzt, testabgedeckt und konsistent zu den ADR-Entscheidungen umgesetzt.
