---
kind: plan
status: approved
approved_by: alex
approved_on: 2026-10-22
approval_quote: "Briefing #89 freigegeben, miss AK0 und starte den Gate-A2-Lauf."
source: roadmap#89
---

# Feature Briefing: #89 — Einzelvideo-Ordner mit Sample werden gruppierbar; Release-`.nfo`/`.sfv` wandern nicht mit

Verfasst von Claude Code (Reviewer/Vermittler) als schlanke Kette ohne Kreativteam-Akte. Alex' Entscheidungen sind wörtlich zitiert.

**Freigaben bisher (Alex, wörtlich):**
- 2026-10-22: „Ja, Variante A: ROADMAP-Punkt anlegen und eine kleine Kette planen (Plan zuerst, keine Token-Läufe ohne mein Go).“
- 2026-10-22: „Plan-Go: schlanke Kette, ADR 1–5, Streitpunkt 2 neu (.nfo/.sfv aus find_group_companion_files ausschließen), Streitpunkt 3 wie empfohlen. Schreib das Briefing und lass den plan-reviewer prüfen.“

## 1. Problemstellung

Live-Bestand auf dem NAS (lesend geprüft, 2026-10-22): acht Ordner `LtnsvS01E01` … `LtnsvS01E08` („Lanterns“). Jeder enthält:
- `Lanterns.S01E0x.German.DL.1080p.WEB.h264-WvF/` mit der Folge `lanterns.s01e0x….mkv` (ca. 2,7 GB), `Sample/lanterns.s01e0x…-sample.mkv` (ca. 68 MB), `lanterns.s01e0x….nfo` (Release-Info) und `….sfv`;
- `!!!WENN IHR MICH UNTERSTÜTZEN WOLLT!!!/` mit `.txt`- und `.URL`-Dateien.

Die Ordner erscheinen einzeln als „Serie erkannt“, aber ohne Gruppenvorschlag und ohne Auswahlkästchen. Zwei Ursachen, beide am Code belegt:

- **U1 (Erkennung):** Die Einzelvideo-Erkennung aus #71 verlangt genau eine Videodatei (`gui/api/project_api.py:1508`, `if is_dir and len(group_video_files) == 1`; Sammlung `:1331–1343` per `os.walk` über die 10er-Liste `GROUP_VIDEO_EXTENSIONS`, `gui/core/helpers.py:798`). Das Sample zählt mit → 2 Videos → kein `single_video_relpath`/`single_video_query` → das Frontend schließt den Ordner von Gruppierung und Kästchen aus (`gui/static/app.js:12527`, `:12537`).
- **U2 (Verarbeitung, würde nach U1 sofort zuschlagen):** `find_group_companion_files` (`helpers.py:870–918`) nimmt jede Nicht-Video-Datei im Ordner der Folge mit, die mit `<stem>.` beginnt — also auch die Release-`.nfo` und `.sfv`. Die Vorschau plant die `.nfo` als Extra mit Ziel `<Titel>.nfo` ein (`gui/api/queue_api.py:598–627`), das Kästchen ist vorab angehakt (`app.js:10433`), der Auftrag benennt sie vor der Folgenschleife nach `current_dir` um (`gui/workers/processor.py:1078–1089`), und die Episoden-NFO-Erzeugung bricht dann ab: `RuntimeError: Kollision beim Generieren von NFO` (`processor.py:1568–1572`; der Schutz selbst ist gewollt, Test `tests/test_inbox_group_files.py:768ff.`). `find_group_companion_files` wird nur in `files[]`-Pfaden verwendet (`queue_api.py:94`, `processor.py:883`, `helpers.py:927`).

## 2. Zielnutzer

Alex, Einzelnutzer der NAS-Instanz. Szene-Releases mit Sample-Unterordner und Release-NFO sind ein häufiges Muster; die Gruppierung soll für sie genauso funktionieren wie für die #71-Ordner (Walking Dead).

## 3. Akzeptanzkriterien

AK0 ist Aufgabe von Claude Code. AK1–AK8 sind ausführbare Tests (pytest), es prüft jeweils, dass …; AK9 (Doku) und AK10 (Hygiene) prüft der Reviewer am Diff.

- [ ] **AK0 — Ausgangsmessung:** Claude Code misst vor dem Gate-A2-Lauf im Worker-Image die volle Suite mit `test_cmd` (Abschnitt 11) und schreibt die wörtliche Ausgabe mit Exit-Code nach `docs/sessions/2026-10-22-roadmap89-sample-ordner/ak0-ausgangsmessung.md`.
- [ ] **AK1 — Lanterns-Muster:** … ein Ordner `XyzS01E01/` mit `Xyz.S01E01.Rel/xyz.s01e01.rel.mkv` (> 300 MB, per `os.truncate`/Sparse-Datei, nicht real beschrieben), `Xyz.S01E01.Rel/Sample/xyz.s01e01.rel-sample.mkv` (< 300 MB), `….nfo`, `….sfv` und einem Fremdordner mit `.txt`/`.URL` in `/api/inbox/analyze` `single_video_relpath = "XyzS01E01/Xyz.S01E01.Rel/xyz.s01e01.rel.mkv"` und `single_video_query` aus dem Dateinamen der Folge liefert; `video_count` bleibt die bisherige Zählung (hier 2).
- [ ] **AK2 — Sample nur per Name/Pfad:** … ein Ordner mit großer Folge und einer Datei `…sample…` bzw. in einem Pfadsegment `Sample` (auch wenn diese ebenfalls > 300 MB ist) als Einzelvideo-Ordner gilt (Kriterium 1).
- [ ] **AK3 — Sample nur per Größe:** … ein Ordner mit einer Datei > 300 MB und einer zweiten < 300 MB ohne „sample“ im Namen/Pfad als Einzelvideo-Ordner gilt (Kriterium 2).
- [ ] **AK4 — zwei echte Videos bleiben zwei:** … ein Ordner mit zwei Videos > 300 MB ohne „sample“ KEIN `single_video_relpath` erhält; ebenso zwei kleine Videos < 300 MB (keine Datei > 300 MB → Kriterium 2 greift nicht) — der bestehende Fall `MixedFolder.S01` (`tests/test_inbox_suggestions.py:217–248`) bleibt unverändert grün.
- [ ] **AK5 — nur Sample:** … ein Ordner, dessen einzige Videodatei per Kriterium 1 ein Sample ist (z. B. `xyz-sample.mkv` oder im Pfadsegment `Sample/`), KEIN `single_video_relpath` erhält (kein Nicht-Sample-Video). Eine einzelne kleine Datei ohne „sample“-Marke ist dagegen weiterhin ein Einzelvideo-Ordner (Kriterium 2 braucht eine zweite Datei > 300 MB).
- [ ] **AK6 — gemeinsame Sample-Regel:** … die neue Hilfsfunktion in `helpers.py` und die Vorschau in `queue_api.py` dieselben Dateien als Sample werten; der bestehende Vorschau-Test `tests/test_movie_processing_fixes.py:160ff.` (`test_sample_detection_in_preview`) bleibt unverändert grün. Die Film-Regel der Vorschau („alle Videos außer dem Hauptfilm gelten als Sample“, `queue_api.py:217–220`) bleibt in `queue_api.py` und wird NICHT in die Hilfsfunktion übernommen (sonst würde AK4 brechen).
- [ ] **AK7 — Release-Begleitdateien bleiben liegen:** … `find_group_companion_files` für `Show.S01E01.mkv` weder `Show.S01E01.nfo` noch `Show.S01E01.sfv` liefert (Groß-/Kleinschreibung der Endung egal), Untertitel (`Show.S01E01.de.srt`) aber weiterhin. Benannte Anpassung des Bestandstests `tests/test_inbox_group_files.py:125–139` (`test_find_group_companion_files`): die Assertion `assertIn("Show.S01E01.nfo", companions)` wird durch `assertNotIn("Show.S01E01.nfo", companions)` ersetzt (von Alex' Entscheidung gedeckt, Zitat oben) — sonst keine Änderung am Testblock.
- [ ] **AK8 — kein NFO-Abbruch mehr (End-to-End im `files[]`-Pfad):** … ein Gruppenauftrag (`files[]`) für das AK1-Muster mit gesetztem `show_id`/`provider` (Metadaten-Aufrufe gemockt, wie in den bestehenden `files[]`-Tests) ohne `RuntimeError` durchläuft; die Folge landet umbenannt im Serienziel, die Episoden-NFO wird erzeugt; Sample, Release-`.nfo`, `.sfv` und Fremdordner liegen danach unverändert im Inbox-Ordner. Der Kollisionsschutz `test_n1_nfo_target_collision_with_foreign_file_aborts_loudly` bleibt unverändert grün.
- [ ] **AK9 — Doku:** `API.md` beschreibt `single_video_relpath` als „einzige Videodatei nach Abzug von Samples“ (Kriterien kurz benannt) und im `files`-Abschnitt (:270), dass `<stem>.nfo`/`<stem>.sfv` nicht als Begleitdateien gelten. Die `/api/preview-process`-Beschreibung (:265) bleibt unberührt (enthält keine Aussage zu Begleitdateien).
- [ ] **AK10 — Hygiene / Review-Kriterien (kein eigener Test):** keine Test-Weichen im Produktivcode; Tests nur in `tmp`-Verzeichnissen; große Dateien nur als Sparse-Dateien; `git diff --check` sauber.

## 4. Bewusst verworfen

- **Release-`.nfo` als Episoden-NFO übernehmen:** verworfen — Szene-NFOs sind Release-Infos (ASCII-Art), kein gültiges `<episodedetails>`-XML; die Episoden-NFO erzeugt Medienwerkzeug selbst.
- **`.nfo` nur bei gesetztem Metadatendienst ausschließen (Variante A2):** verworfen (Alex' Entscheidung oben) zugunsten der einfacheren Regel in `find_group_companion_files`.
- **Sample, Werbe-Ordner, Release-Dateien aufräumen/löschen:** nicht in dieser Kette (Reste in der Inbox = ROADMAP #81).
- **Anzeige „2 Datei(en)“ ändern:** nein, `video_count` bleibt unverändert.
- **Frontend-Änderungen:** keine nötig (das Frontend reagiert bereits auf `single_video_relpath`); kein Cache-Buster.
- **Kreativteam-Akte 1/2:** bewusst weggelassen (schlanke Kette, Alex' Plan-Go).

## 5. ADR-Blöcke

### ADR-89-1: Schlanke Kette
- **Entscheidung:** Briefing durch Claude Code → plan-reviewer → Briefing-Freigabe Alex → AK0 → ein Gate-A2-Lauf → Plausibilität Claude Code (inkl. Probe mit nachgebautem Lanterns-Ordner in einer Wegwerf-Instanz) → Rückkanal (`ceo-planner` + produktberater + advocatus) → Handtest Alex lokal → Push/PR (§8) → Merge Alex → NAS-Update (Einzel-Go) → Live-Blick.
- **Alternativen:** volles Kreativteam; Feature-Kette mit #81.
- **Begründung:** Ursache und Lösung sind belegt; der Mehrwert liegt in plan-reviewer, Rückkanal und Handtest. #81 hat eine ungeklärte Ursache.
- **Konsequenzen:** weniger Freigabepunkte; Nebenfragen fallen ggf. erst im Rückkanal auf.

### ADR-89-2: Eine gemeinsame Sample-Erkennung in `helpers.py`
- **Entscheidung:** Neue Hilfsfunktion in `gui/core/helpers.py`, die für eine Liste von Videopfaden (mit Größen) die Samples nach den heutigen Vorschau-Kriterien bestimmt: (1) „sample“ im Dateinamen oder als Pfadsegment (Groß-/Kleinschreibung egal); (2) Datei < 300 MB, während es eine Datei > 300 MB gibt. `queue_api.py` nutzt sie (Verhalten identisch, AK6); die anschließende Film-Regel „alles außer Hauptfilm ist Sample“ bleibt in `queue_api.py`. `project_api.py` nutzt sie für die Einzelvideo-Erkennung.
- **Alternativen:** Kriterien in `project_api.py` kopieren (zwei Stellen, die auseinanderlaufen können).
- **Begründung:** eine Quelle für dieselbe fachliche Regel.
- **Konsequenzen:** `queue_api.py` wird angefasst; abgesichert durch AK6 und den Bestandstest.

### ADR-89-3: Einzelvideo-Ordner = genau ein Nicht-Sample-Video
- **Entscheidung:** In `project_api.py` zählt für `single_video_relpath`/`single_video_query` die Liste `group_video_files` ohne Samples; genau ein Eintrag → Einzelvideo-Ordner. `video_count` und `suggested_query` bleiben unverändert.
- **Alternativen:** `video_count` mit anpassen (verworfen, Anzeige-/Verhaltensänderung außerhalb des Scopes).
- **Konsequenzen:** AK1–AK5.

### ADR-89-4: `.nfo` und `.sfv` sind keine Gruppen-Begleitdateien
- **Entscheidung:** `find_group_companion_files` überspringt Dateien mit Endung `.nfo` oder `.sfv`. Sie bleiben im Quellordner liegen; die Episoden-NFO erzeugt Medienwerkzeug selbst.
- **Alternativen:** Variante A2 (nur bei Metadatendienst), verworfen von Alex.
- **Begründung:** behebt U2 an der Wurzel; wirkt nur auf `files[]`-Aufträge.
- **Konsequenzen:** Gruppenaufträge ohne Metadatendienst nehmen eine vorhandene `<stem>.nfo` nicht mehr mit (dokumentiert in `API.md`); benannte Anpassung des Bestandstests (AK7).

### ADR-89-5: Prüfstrategie
- **Entscheidung:** AK1–AK8 als pytest (AK9/AK10 am Diff); Rot-Probe der neuen Tests gegen `f0a29a4` ohne neue Symbole (neue Hilfsfunktion nicht direkt importieren, sondern über `/api/inbox/analyze`, `find_group_companion_files` und den `files[]`-Pfad prüfen). Die Rot-Probe gilt für AK1, AK2, AK3, AK5, AK7 und AK8. AK4 und der Vorschau-Teil von AK6 sind Bestandsschutz und gegen `f0a29a4` erwartbar grün; AK6 wird als kombinierter analyze+preview-Test gebaut, sodass sein analyze-Teil (gleiche Sample-Wertung führt in `/api/inbox/analyze` zu `single_video_relpath`) rot-fähig ist; volle Suite im Worker-Image; Probe im Container mit nachgebautem Lanterns-Ordner (Gruppenvorschlag + Kästchen sichtbar, Gruppenauftrag ohne Abbruch); Handtest über den 6-s-Neuaufbau hinweg.

## 6. Dissens & Risiken

- **Eingefügtes Fremd-Review (von Alex weitergereicht, 2026-10-22):** fand U2 vor dem Briefing; Claude Code hat jede Stelle am Code nachgeprüft (Abschnitt 1). Übernommen: Ausschluss in `find_group_companion_files` (Alex' Entscheidung) und die Trennung der Film-Regel aus der Hilfsfunktion (AK6).
- **Sample-Kriterium 1 ist grob:** „sample“ als Teil eines echten Serien-/Dateinamens würde als Sample gelten. Heute schon so in der Vorschau; kein neues Risiko, aber dokumentiert.
- **Gruppenschlüssel kleingeschrieben:** Bei Lanterns ist der Dateiname klein (`lanterns.s01e01…`), Schlüssel und Suchbegriff werden „lanterns“. Funktioniert für die Suche; Anzeige kosmetisch, nicht im Scope.
- **Reste in der Inbox:** Sample, Release-Dateien und Werbe-Ordner bleiben liegen (ROADMAP #81).

## 7. Quellen, Referenzen & Lizenzen

Kein Third-Party-Code, keine neuen Abhängigkeiten oder Assets. Interne Referenzen: `ROADMAP.md` #89, #71, #72, #81; `docs/sessions/2026-10-12-inbox-ordnerfolgen/briefing.md` (#71-Teilmenge, `test_cmd`).

## 8. Offene Fragen

Keine für Alex vor der Briefing-Freigabe. Nach dem Merge: NAS-Update (Klasse C, Einzel-Go); Live-Blick nur auf Gruppenvorschlag und Kästchen für Lanterns, Verarbeitung entscheidet Alex.

## 9. Aufwand

KI/Pipeline: ein Gate-A2-Lauf (Backend + Tests + `API.md`), geschätzt 10–25 min. Alex: Briefing-Freigabe, Handtest (~10 min), Merge, NAS-Go.

## 10. Git-Zustand

```text
$ git status --short --branch
## fix/roadmap-89-sample-ordner
$ git log --oneline -2
b57c38f docs(roadmap): add #89 single-video folders with sample video are not grouped
f0a29a4 feat(inbox): season quick-select, visible start errors and search deadline (ROADMAP #74, #80, #83) (#156)
```

## 11. Worker-Auftrag (Gate-A2-Pipeline, ein Lauf)

`test_cmd` identisch zu `docs/sessions/2026-10-12-inbox-ordnerfolgen/briefing.md` Abschnitt 11 (ohne eigenes `timeout`, `test_timeout_s` 600):

```bash
python3 -m pip install -q --user --break-system-packages -r requirements.txt pytest && python3 -m pytest -q -p no:cacheprovider --deselect tests/test_utils.py::TestMediawerkzeugLogic::test_conversion_estimation_test_encode && npm run test:frontend
```

```text
Medienwerkzeug ROADMAP #89: Einzelvideo-Ordner mit Sample-Video gruppierbar machen und
Release-.nfo/.sfv nicht als Gruppen-Begleitdateien behandeln (nur Backend + Tests + API.md).

NUR diese Aenderungen:
1. gui/core/helpers.py: neue Hilfsfunktion fuer die Sample-Erkennung nach ADR-89-2
   (Kriterium 1: "sample" im Dateinamen oder als Pfadsegment, case-insensitiv;
   Kriterium 2: Datei < 300 MB, waehrend eine Videodatei > 300 MB existiert).
   Keine Film-Regel "alles ausser Hauptfilm" in der Hilfsfunktion.
2. gui/core/helpers.py: find_group_companion_files ueberspringt Dateien mit Endung
   .nfo und .sfv (case-insensitiv); Docstring anpassen.
3. gui/api/queue_api.py: Sample-Bestimmung der Vorschau (:187-215) ueber die neue
   Hilfsfunktion; Film-Regel (:217-220) bleibt dort; Verhalten identisch.
4. gui/api/project_api.py: Einzelvideo-Erkennung (:1508ff.) zaehlt group_video_files
   ohne Samples; genau 1 -> single_video_relpath/single_video_query wie bisher aus
   diesem einen Video. video_count und suggested_query unveraendert.
5. API.md: single_video_relpath (:146) und files-Abschnitt (:270) laut AK9.
6. Tests: AK1-AK5 in tests/test_inbox_suggestions.py ergaenzen; AK6 ergaenzen (Datei
   frei: test_inbox_suggestions.py oder test_inbox_group_files.py); AK7 + AK8 in
   tests/test_inbox_group_files.py ergaenzen, dort NUR die benannte Assertion in
   test_find_group_companion_files (:137) von assertIn auf assertNotIn umstellen.
   Grosse Dateien nur sparse (os.truncate), alles in tmp-Verzeichnissen.

ERLAUBTE DATEIEN (ausschliesslich): gui/core/helpers.py, gui/api/queue_api.py,
gui/api/project_api.py, API.md, tests/test_inbox_suggestions.py,
tests/test_inbox_group_files.py.

NICHT ANFASSEN: gui/static/**, gui/workers/**, uebrige gui/**, uebrige tests/**
(insbesondere tests/test_movie_processing_fixes.py), ROADMAP.md, STAND.md, VERLAUF.md,
docs/**, scripts/**, package.json, pytest.ini, README.md, data/**; .env nie lesen.
Keine Test-Weichen im Produktivcode. git diff --check sauber.
```

**Schritt 0 vor dem ersten Code-Diff:** Basis `f0a29a4` (der Branch-Commit `b57c38f` ist docs-only). Verifikation: `project_api.py:1508` `len(group_video_files) == 1`; `helpers.py:870` `find_group_companion_files`; `queue_api.py:187–220` Sample-Logik; `tests/test_inbox_group_files.py:137` `assertIn("Show.S01E01.nfo", companions)`. Bei Abweichung STOPP und Rückmeldung.

**Pflicht: wörtliche Rohausgaben bei der Übergabe** (mit Exit-Code): `git status --short --branch`; `git diff --stat`; `git diff --check`; volle Ausgabe pytest-Teil und `npm run test:frontend` aus `test_cmd`.

## 12. Handtest-Liste (lokal, vor Push/PR)

Vorbereitung durch Claude Code: lokale Testinstanz mit nachgebautem Lanterns-Bestand (3 Ordner `XyzS01E01…03` im Lanterns-Muster, Folgen als Sparse-Dateien > 300 MB, Samples < 300 MB, Release-`.nfo`/`.sfv`, Werbe-Ordner) plus ein Ordner mit zwei echten großen Videos.

1. Inbox öffnen: Für die drei Xyz-Ordner erscheint ein Gruppenvorschlag im Banner, jeder hat ein Auswahlkästchen.
2. Der Ordner mit zwei echten Videos hat weder Kästchen noch Gruppenvorschlag.
3. Ca. 15 s warten (6-s-Neuaufbau): Vorschlag und Kästchen bleiben.
4. Gruppe starten → Vorschau: weder Sample noch Release-`.nfo`/`.sfv` sind als umzubenennende Extras eingeplant.
5. Verarbeitung durchlaufen lassen (Metadaten in der Testinstanz wie verfügbar): kein Abbruch „Kollision beim Generieren von NFO“; Folgen im Serienziel; Sample, `.nfo`, `.sfv`, Werbe-Ordner liegen weiter in den Inbox-Ordnern.

Nach dem Merge (NAS, eigenes Go): nur prüfen, dass „Lanterns“ als Gruppe vorgeschlagen wird und die Kästchen erscheinen; Verarbeitung entscheidet Alex.

## Änderungen nach plan-reviewer Runde 1 (2026-10-22)

- [wichtig] Rot-Probe präzisiert (ADR-89-5): gilt für AK1–AK3, AK5, AK7, AK8; AK4 und Vorschau-Teil von AK6 sind Bestandsschutz (erwartbar grün); AK6 als kombinierter analyze+preview-Test.
- [kosmetisch] AK5 präzisiert (Sample per Kriterium 1).
- Potenzial übernommen: AK9 legt `API.md:265` als unberührt fest.
- plan-reviewer Runde 2: `VERDICT: APPROVE`; [kosmetisch] AK9-Einordnung korrigiert (AK1–AK8 pytest, AK9/AK10 Review-Kriterien).
