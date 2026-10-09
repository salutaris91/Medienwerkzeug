# Rückkanal-Abnahme ROADMAP #65, Lauf A (Server) — ZWEITE Runde (Nachbesserung auf R1–R4, D1, D3)

**Datum:** 2026-10-09 · **Auftraggeber:** Claude Code (Rolle Reviewer/Vermittler), NICHT Alex.
**Alex-Bezug (wörtlich, 2026-10-09):** „Ja, wie von dir empfohlen, aber das zeigt mir vor allen Dingen auch, wie wertvoll auch der Rückkanal sein kann.“ → zweiter Gate-A2-Nachbesserungslauf für R1–R4, D1-Rückbau (Alt-Pfade ohne `files` wieder byte-genau wie `6152839`; #68 bleibt eigener PR), D3-Test; P1 ist jetzt ROADMAP #71.
**Geprüfter Stand:** Worktree `feat-roadmap-65-als-serie-gruppieren`, Head `481d7f0` (laut geliefertem `git log`; kein bash — Head-Identität nicht selbst verifiziert). Code gelesen auf diesem Stand.
**Referenzen:** `rueckkanal-65a.md` (erste Runde, ABNAHME: NEIN), `briefing-65.md` (approved), ROADMAP #71 (`ROADMAP.md:1962`, Voraussetzung R1-Fix dort `:1978` — erfüllt, s. u.).
**Rollen im Text:** [ich] = Vermittlungsagent; [advocatus] = Risikoprüfer, Beitrag ungekürzt in Anhang A (Auftragsregel: nur diese eine Datei schreiben, daher Einbettung statt Einzeldatei; `opencode export` durch Claude Code bleibt unberührt).
**Vor-Review-Kontext:** Gate-A2 APPROVED nach 2 Runden (`481d7f0`); Claude Code meldet nur `queue_api.py`, `processor.py`, `tests/test_inbox_group_files.py` geändert, 502 passed/1 deselected + Frontend 150/150, 6 neue/angepasste Tests gegen `3a0af1b` rot.

---

## ABNAHME: NEIN

**Begründung in einem Satz:** Alle sechs nachbesserungspflichtigen Befunde (R1, R2, R3, R4, D1, D3) sind nachweislich geschlossen und mit echten End-to-End-Tests gesichert — aber die AK6-Kernzusage („ein `files[]`-Job berührt AUSSCHLIESSLICH Gruppe ∪ Begleitdateien") bleibt an einer neuen Stelle derselben Klasse durchbrochen: [advocatus] und [ich] unabhängig voneinander bestätigt, dass ein `files`-Job eine **Fremddatei im Inbox-Root mit exakt dem Zielnamen stillschweigend überschreibt** (`processor.py:1459`, ohne jedes manipulierte Parameter, allein durch Namensgleichheit — N1 [kritisch]); dazu zwei weitere Zielnamens-Lücken [wichtig] (N2, N3). Nach dem Maßstab der ersten Runde (gleiche Klasse, datengefährlich, Weg-2-Kernzusage) kann nicht abgenommen werden; der Fix ist erneut klein (Existenz-/Scope-Checks an drei Zielpunkten, analog dem bereits bewährten R3-Muster `:1489–1492`).

Das ist kein Qualitätsurteil über die behobenen Befunde — R1–R4/D1/D3 sind korrekt und getestet geschlossen. Es ist derselbe Review-Fortschritt wie von F1/F2 → R1–R4: Die Runde hat die **Quell**-Seite (old/Entry) hart abgesichert; die **Ziel**-Seite (new/Target) ist die symmetrisch offene Flanke.

---

## 1. Befund-Tabelle: Schließungsprüfung (Code-Prüfung [ich], bestätigt durch [advocatus])

| Befund | Geschlossen? | Beleg Code | Beleg Test |
|---|---|---|---|
| **R1** `files[]` nur mit `media_type=="tv"` | **ja** (dreifach) | Preview `queue_api.py:76–78` (400, vor jeder Validierung; `media_type` fehlt/None → ebenfalls 400); Process `queue_api.py:817–819` (400; Default „unknown" `:814` → 400); Processor-Sicherungsnetz `processor.py:870–872` (RuntimeError VOR jeder Verzweigung — damit sind movie/youtube/tool-Zweige für `files` auch bei direktem `process_worker`-Aufruf und beim Retry unerreichbar; Claude Codes „unveränderter" Movie-Root-Scan `:1867`/:2029ff. und `safe_move_recursive` `:2128` sind für `files`-Jobs nicht mehr reichbar) | `test_r1_files_param_with_non_tv_media_type_rejected` (`tests/test_inbox_group_files.py:478–514`): beide Endpunkte 400 + Worker-RuntimeError + Datei bleibt |
| **R2** Basename-Fallback im `explicit_*`-Scope-Check | **ja** | `processor.py:953–969`: nur noch exakte `normpath(entry)`-Memberschaft in `scope_files` (`:956/:962/:968`), kein `os.path.basename`-Zweig; Abbruch bleibt VOR jeder Bewegung (`:972` ff.); Anwendung der Einträge unverändert (`:976`, `:1031–1048`) | `test_r2_explicit_junk_same_basename_in_other_folder_aborts_loudly` (`:516–546`, exakt der R2-Repro „Fremdordner/Folge 1.srt") + `test_explicit_subs_and_renames_outside_scope_aborts_loudly` (`:691–724`) |
| **R3** Fallback-Untertitel-Rename ohne Scope-Begrenzung | **ja** | `processor.py:1465–1497`: `files`-Zweig iteriert nur `companion_files` mit Verzeichnisgleichheit (`:1474`) und Wortgrenze `vstem+"."` (`:1468/:1475`); Kollisionsraise bei doppeltem Ziel (`:1481–1484`) und bei existierendem Ziel (`:1489–1492`); der unbegrenzte `os.listdir(current_dir)`-Pfad läuft nur noch im `else`-Zweig `files_param is None` (`:1498–1510`, byte-getreu Alt-Verhalten) | `test_r3_fallback_subtitle_rename_boundary_and_foreign_file_untouched` (`:548–586`, fremde „Folge 10.srt" bleibt) + `test_fallback_subtitle_rename_multiple_languages_preserved` (`:651–689`, schließt den R3-Zusatzbefund Mehrsprach-Kollision ein) |
| **R4** Unterordner-Gruppen verlieren Begleitdateien | **ja** | `processor.py:1467` `vstem` jetzt aus `basename(filename)`; `:1626–1641` `episode_allowed_files` mit `comp`/`comp_name`/`clean_title`-Zielvarianten, Verzeichnisvergleich normpath (`:1633`); Preview↔Process kohärent (`queue_api.py:571`) | `test_r4_subfolder_group_with_companion_file_moved_to_outbox` (`:588–619`): Unterordner-Video + Unterordner-Untertitel beide in Outbox, beide aus Inbox weg |
| **D1** Cleanup-Rückbau auf Alt-Stand | **ja** (verhaltensseitig; Byte-Identität s. Restunsicherheiten) | `processor.py:1052` `if files_param is None:` (der `current_dir != inbox_root`-Zusatz ist entfernt) und `:1657` `cleanup_empty_dirs=(files_param is None)` → Alt-Jobs inkl. Wurzel-/Einzeldatei-Jobs räumen leere Unterordner wieder wie vor #65; die einzige verbleibende `current_dir != inbox_root`-Stelle ist `:346` (`_finalize_job`, vorbestehend, von [advocatus] und in Runde 1 bereits entkräftet) | `test_d3_regression_tv_single_file_job_without_files_cleans_empty_dirs` (`:621–649`) assertiert die Wiederherstellung positiv (Leerordner WIRD beim Root-Einzeldatei-Job bereinigt); `test_backwards_compatibility_paths_without_files_param` (`:432–473`) + `test_files_job_scope_enforcement_and_untouched_foreign_files` (`:273–352`, fremder Leere-Ordner bleibt bei `files`-Job) sichern beide Seiten |
| **D3** tv-Einzeldatei-Regressionstest | **ja** | — (Testbefund) | `:621–649` wie D1-Zeile; deckt genau den durch D1 berührten Pfad (`current_dir == inbox_root`, tv, ohne `files`) |

**Nicht beauftragt, unverändert offen (nur der Vollständigkeit halber, keine neuen Blocker):** D2 (Endungsliste doppelt: `helpers.py:798` ≡ `queue_api.py:113`, inhaltlich identisch) und D4 (toter Code `get_group_scope_files`, `helpers.py:921–929` — Reposuche bestätigt: nur Definition) — beide [kosmetisch], gehörten nicht zum Nachbesserungsauftrag.

**AK-Überblick:** AK5/AK6/AK7-Tests grün wie oben; AK8-Alt-Pfade wieder verhaltensgleich (D1 geschlossen); AK10-Hygiene unverändert erfüllt (Tests nur in tmp, `:16–31`). Diff-Umfang der Nachbesserung laut Claude Code auf `queue_api.py`/`processor.py`/Testdatei beschränkt — plausibel, mit dem Gelesenen konsistent.

---

## 2. Neue Risiken derselben Klasse (nur Neues gegenüber `rueckkanal-65a.md`)

Klasse = „ein ausgeführter `files[]`-Job berührt Daten außerhalb Gruppe ∪ Begleitdateien". Systematisch: Die Runde hat alle **Quellen** (Dateien, die der Job liest/bewegt) scope-geprüft; die **Ziele** (Pfade, die der Job beschreibt/überschreibt) sind an drei Stellen ungeprüft.

### Blockierend für die Abnahme

- **N1 [kritisch] — Fallback-Video-Rename überschreibt Fremddatei im Inbox-Root ([advocatus] H1/N1, von [ich] unabhängig bestätigt):** `processor.py:1459` `os.rename(filepath, target_filepath)` ohne `os.path.exists(target_filepath)`-Check; bei `files`-Jobs ist `target_filepath` in der Inbox-Root (`:1412`). **Repro ohne jedes manipulierte Parameter:** `POST /api/process` `{"media_type":"tv","files":["Show.S01E01.mkv"],"mappings":{"Show.S01E01.mkv":{"season":1,"episode":1,"title":"Pilot"}}}` (ohne `explicit_renames` — genau der Pfad des AK6-Haupttests), wenn im Root eine Fremddatei `MyShow - S01E01 - Pilot.mkv` liegt → POSIX-Rename ersetzt sie kommentarlos. Der AK6-Haupttest (`test:304`) verfehlt den Fall nur um eine Endung (`…Pilot.adversarial.txt`). Realistischster Auslöser: ein halbabgebrochener Vorjob (z. B. N4 unten) oder zwei Gruppen mit identischem Episoden-Titel. **Der R3-Fix hat genau diesen Existenzcheck für Untertitelziele eingebaut (`:1489–1492`) — für das Videoziel fehlt er.** Verletzt AK6 („AUSSCHLIESSLICH") und die ADR-65-2-Grundregel (Preview kann die Kollision nicht zeigen, weil sie Fremddateien nicht sieht).
- **N2 [wichtig] — `explicit_renames`/`explicit_subs`: Ziel `new` durch keine Prüfung ([advocatus] N2, von [ich] verschärft):** `processor.py:1030–1038` und `:1040–1049` prüfen nur `old` (R2-Check); `new_path = os.path.join(current_dir, r["new"])` (`:1032/:1043`) ist unvalidiert. Drei Wirkungen: (a) Ziel existiert (Fremddatei) → stille Überschreibung wie N1; (b) `new` mit Pfadteil → Gruppe wandert in fremden Ordner; (c) von [ich] ergänzter Mechanismus: `new` **absolut** → `os.path.join` verwirft die Root, `os.rename` schreibt **außerhalb der Inbox** (Konfinement nur auf der Quellseite). Erfordert einen Client, der `new` manipuliert/verirrt — der Lauf-B-Client wird Preview-Namen senden, aber die API steht offen.
- **N3 [wichtig] — Konvertierung schreibt temp/final in den Root ohne Check ([advocatus] N3/H3 bestätigt):** `processor.py:1554` (`{clean_title}_neu.mkv`) und `:1581` (`{clean_title}.mkv`) liegen bei `files`-Jobs in der Inbox-Root; `convert=True` + namengleiche Fremddatei → Überschreibung; zusätzliche Kollisionsfläche gegenüber N1 (zwei weitere Zielnamen).

### Nicht blockierend, aber dokumentierpflichtig

- **N4 [klein] — Halb umbenannter Zustand bei Mittel-Abbruch:** Die neuen R3-Kollisionsraises (`:1482/:1490`) feuern NACH dem Video-Rename (`:1459`) desselben Episoden-Durchlaufs; der Job bricht laut ab, aber das Video bleibt umbenannt im Root, und ein Retry läuft in die TOCTOU-Sperre (`:1450–1451`). Kein Datenverlust, aber Handarbeit nötig. Gehört thematisch zur Retry-/Wiederaufnahme-Story (#68-Nachbarschaft) — dokumentieren.
- **N5 [wichtig, Doku] — API.md dokumentiert den neuen 400er nicht:** `API.md:263/:267–268` beschreiben `files`, aber nicht die R1-Einschränkung „nur `media_type=tv`" — Verhaltensänderung an öffentlichen Endpunkten; Hausregel „Code und Doku dürfen nicht auseinanderlaufen". Ein Zeilennachtrag im nächsten Lauf.
- **N6 [kosmetisch] — Normalisierungsasymmetrie ([advocatus] H4, als Sicherheitslücke widerlegt):** `validate_group_files` liefert Rohstrings (`helpers.py:862`), `scope_files` mischt Roh-+normalisierte Einträge (`processor.py:884`), der R2-Check vergleicht `normpath` — erzeugt nur **konservative Fehl-Abschreibungen** (z. B. Client schickt `Sub//Ep.mkv`), keine falsche Zulassung. Notiz: Rohstrings konsequent `normpath`en.

### Geprüft und entkräftet ([advocatus] H2 + [ich], keine Findings)

- **Retry-Pfad** (`queue_api.py:927–996`): re-queued nur persistierte Params; `process_worker` revalidiert vollständig (`:871` media_type, `:879` validate, `:948–951` TOCTOU) — kein Umgehungsweg (H2 widerlegt).
- **Alle `safe_move_recursive`-Aufrufe:** `:1649` (files-Zweig, `allowed_files` gesetzt → Realpath-Gate `:502–521` bleibt, F2-Klasse weiter gedeckt), `:1748` (nur `files_param is None`), `:2128` (movie, für `files` via R1 unerreichbar).
- **`move_with_fallback` `:386–479`:** Ziel-Existenzbehandlung vorhanden (`:469–474`), operiert nur im job-eigenen Outbox-Ordner; sein breites `path_endswith`/Basename-Match (`:404`) kann bei `files`-Jobs nur noch Dateien treffen, die das `allowed_files`-Gate vorgelassen hat.
- **Alle `os.rename`/`shutil.move`-Stellen außerhalb der tv-Datei-Verarbeitung** (`:2593` ff. youtube/tool): durch `processor.py:870–872` für `files`-Eingaben unerreichbar.
- **`_finalize_job` `:346`** und **NAS-Companion-Copy**: wie in Runde 1 entkräftet, unverändert.

---

## 3. Chancen und weitere Features

**Keine neuen** gegenüber `rueckkanal-65a.md` (P1–P4 dort; P1 ist inzwischen als ROADMAP #71 eingetragen — `ROADMAP.md:1962`; die dort als Voraussetzung notierte R1-Schließung (`:1978`) ist mit dieser Runde erfüllt; N1–N3 betreffen #71 nicht als Blocker, wohl aber als „vor Lauf B sauber machen"-Anlass, da #71 auf demselben `files[]`-Zielpfad aufsetzt).

---

## 4. Empfehlung an Alex

1. **ABNAHME: NEIN → dritter, sehr kleiner Nachbesserungsschlag, dann mergebereit.** Muster der letzten beiden Runden hat sich bewährt; die Fixes sind symmetrisch zu R3 und winzig: (a) **N1:** vor `os.rename` `:1459` eine `files_param is not None`-gegatele Existenzprüfung mit RuntimeError analog `:1489–1492` (Alt-Pfade bleiben byte-getreu — D1-Prinzip wahren); (b) **N2:** `new`-Werte von `explicit_renames`/`explicit_subs` in den R2-Check einbeziehen (normpath, Konfinement unter `current_dir`, Ablehnung absoluter Pfade) + Ziel-Existenzcheck; (c) **N3:** Konvertierungsziele `_neu.mkv`/final in den Scope-Check einbeziehen oder die temp-Ziele in einen job-eigenen Unterordner legen; (d) die drei fehlenden Tests (Fremddatei mit exaktem Zielnamen; `new` absolut/fremd; convert-Kollision) + **N5**-API.md-Zeile. **Trade-off:** dritte Runde — KI-seitig erneut schnell; dein Engpass ist wieder nur die Review-Read des kleinen Diffs. Die Alternative „N1 als Restrisiko akzeptieren" verwerte ich ausdrücklich nicht, weil sie genau die Kernzusage bricht, wegen der Weg 2 gewählt wurde, und N1 ohne jeden Missbrauchsverdacht zuschlägt (Halb-Abbruch-Szenario N4 erzeugt die Kollisionsdatei selbst).
2. **Reihenfolge unverändert:** dieser Schlag in Lauf A, dann Merge, dann Lauf B; #71 bleibt wie eingetragen.
3. **N4/#68-Hinweis:** bei #68 (Retry-/Wiederaufnahme-Bug) den halb-umbenannten-Zustand als Anwendungsfall mitbedenken — nicht jetzt lösen.

**Stichproben-pflichtige Themen (Geld/Aussenwirkung/Recht/Kauf):** keine — reine Server-Integritätsrunde, keine Assets/Lizenzen/Registrierungen berührt.

---

## 5. Dissens-Pflicht

- **Schwere N1:** [ich] initially [wichtig] (erfordert Namenszusammenfall, kein aktiver Missbrauch); [advocatus] [kritisch] (stiller Datenverlust an Fremddatei ohne manipulierte Parameter, Realisierung bereits durch eigenes Abbruch-Muster N4 möglich). [ich] übernimmt die strengere Bewertung — die mildere Lesart ist hier als verworfene Alternative dokumentiert.
- **H4:** [ich] hielt die Normalisierungsasymmetrie zunächst für potenzielle Zulassungslücke; [advocatus] widerlegt (nur konservative Abschreibungen) — Übernahme der Entkräftung, Findings-Downgrade auf [kosmetisch] (N6).
- **H2:** [ichs] Verdacht auf Retry-Umgehung von [advocatus] widerlegt — keine Findings-Aufnahme.
- Kein Rollenwiderspruch zu R1–R4/D1/D3-Schließungen; [ich] und [advocatus] kamen unabhängig auf dieselbe offene Flanke (Zielseite).

## 6. Restunsicherheiten (nicht selbst ausführbar)

Kein bash/git: Head-Identität (`481d7f0`), die **byte-genau**-Behauptung von D1 gegen `6152839` (ich habe Verhaltensgleichheit aus dem Code abgeleitet — `:1052`/`:1657` gating, `:346` vorbestehend — nicht den Wortlaut-Diff), die Testresultate (502 grün; 6 Tests gegen `3a0af1b` rot) und `git diff --check` sind Claude-Code-Berichte. Der Retry-Pfad ist statisch geprüft, aber ungetestet (Notiz, kein Blocker).

---

*Ende des Rückkanal-Laufs r2. Gemäß Auftrag: danach STOPP — kein Git, kein Push, kein repo-operator, keine weiteren Dateien. Diese Datei war die einzige Schreibaktion; der [advocatus]-Rohoutput ist wegen der Ein-Datei-Grenze als Anhang A ungekürzt eingebettet (Claude Codes `opencode export`-Archivierung bleibt davon unberührt).*

---

## Anhang A — [advocatus], ungekürzter Beitrag (zweite Runde)

# Rückkanal-Bericht — ROADMAP #65 Lauf A, ZWEITE Runde (Risikoprüfer/advocatus)

Prüfgegenstand: Nachbesserungslauf (Head laut Kontext `481d7f0`), der R1–R4, D1, D3 schließen soll. Arbeitsweise: ausschließlich statische Code-Lektüre im exklusiven Worktree, keine Git-Verifikation (kein bash), kein Schreiben. Referenz: `rueckkanal-65a.md` (gelesen zuerst).

---

## 1. ABNAHME-Einschätzung je Befund

| Befund | Urteil | Beleg (Datei:Zeile) |
|---|---|---|
| **R1** (files[] an `media_type=="tv"` binden) | **geschlossen** | `queue_api.py:75–78` (preview: `if files_param is not None: if media_type != "tv": return 400`), `queue_api.py:816–819` (process: identischer 400), `processor.py:870–872` (process_worker: `raise RuntimeError(f"files[] wird nur für media_type 'tv' unterstützt, erhalten: '{media_type}'.")`). Alle drei Konsumpunkte (preview, process, worker) sind abgesichert; die Worker-Prüfung ist die Sicherungsnetz-Ebene für direkte `process_worker`-Aufrufe. |
| **R2** (explicit_*-Scope-Check ohne Basename-Fallback) | **geschlossen** | `processor.py:953–969`: `explicit_junk` (`norm_j = os.path.normpath(j); if norm_j not in scope_files: raise`), `explicit_subs` (`:958–963`), `explicit_renames` (`:964–969`). Ausschließlich `normpath(entry) in scope_files`-Memberschaft; kein `os.path.basename`-Fallback mehr. Die Anwendung (Trash/Rename) liegt strikt danach (`:972` ff.), d. h. LAUTer Abbruch VOR jeder Bewegung bleibt erhalten. |
| **R3** (Fallback-Untertitel-Rename im files-Zweig) | **geschlossen** | `processor.py:1465–1497`: Wortgrenze `vprefix = vstem + "."` (`:1468`), Iteration nur über `companion_files` mit `comp_dir == filename_dir` (`:1470–1475`), Kollisions-`raise` für doppelte Zielnamen (`:1481–1485`) und für bereits existierendes Ziel (`:1488–1492`), erst dann `os.rename` (`:1495`). Der unbegrenzte `os.listdir(current_dir)`-Pfad existiert nur noch im `else`-Zweig (`:1498–1510`), also bei `files_param is None`. |
| **R4** (Unterordner-Gruppen verlieren Begleitdateien nicht) | **geschlossen** | `processor.py:1467` (`vstem = os.path.splitext(os.path.basename(filename))[0]` — Basename statt vollem Relativ-Schlüssel), `:1474` (`normpath(comp_dir) == normpath(filename_dir)`), und die allowed_files-Konstruktion `:1619–1641` (fügt `comp`, `comp_name` sowie `clean_title`-Varianten für Unterordner-Companions hinzu). Preview (`queue_api.py:571` `base_old = os.path.splitext(basename)[0]`) und Process sind jetzt kohärent. |
| **D1** (Cleanup-Gating nur an `files_param is None`) | **geschlossen** | `processor.py:1052` (`if files_param is None:`) und `:1657` (`cleanup_empty_dirs=(files_param is None)`). Der `current_dir != inbox_root`-Zusatz ist an beiden Stellen entfernt; die einzige verbliebene `current_dir != inbox_root`-Stelle ist `:346` in `_finalize_job` (vorbestehend, kein files-Bezug). Alt-Pfade ohne `files` (inkl. Wurzel-/Einzel-Jobs) verhalten sich damit wieder wie vor #65. |
| **D3** (fehlender tv-Einzeldatei-Regressionstest) | **geschlossen** | `tests/test_inbox_group_files.py:621–649` (`test_d3_regression_tv_single_file_job_without_files_cleans_empty_dirs`) — echter `process_worker`-Lauf mit tv-Einzeldatei in Root + leerem Fremd-Unterordner, prüft Ausgabe UND Bereinigung des leeren Ordners. |

**Zwischenfazit:** Alle sechs nachzubessernden Befunde sind auf dem geprüften Stand korrekt und mit ausführbaren Tests geschlossen. Die Nachbesserung ist inhaltlich sauber umgesetzt.

---

## 2. Neue Findings (nur Neues gegenüber rueckkanal-65a.md)

### N1 [kritisch] — Zielnamens-Kollision beim Fallback-Video-Rename überschreibt Fremddatei stillschweigend

**Stelle:** `processor.py:1443–1459` (Fallback-Zweig `explicit_renames is None`), konkret `:1459 os.rename(filepath, target_filepath)` ohne `os.path.exists(target_filepath)`-Check.

**Mechanismus:** Bei einem `files`-Job ist `current_dir == inbox_root`. `target_filepath = os.path.join(current_dir, target_filename)` (`:1412`), `target_filename = f"{clean_title}{ext}"`. Existiert im Inbox-Root eine **Fremddatei** mit exakt dem Namen `clean_title.ext` (z. B. eine früher verarbeitete Folge oder eine manuell abgelegte Datei gleichen Namens), überschreibt `os.rename` sie auf POSIX stillschweigend — **Datenverlust ohne Warnung**.

**Repro-Pfad:** `POST /api/process` mit `{"media_type":"tv","show_name":"MyShow","season":1,"files":["Show.S01E01.mkv"],"mappings":{"Show.S01E01.mkv":{"season":1,"episode":1,"title":"Pilot"}}}` — **ohne** `explicit_renames`. Liegt im Inbox-Root zusätzlich eine Datei `MyShow - S01E01 - Pilot.mkv` (nicht in `files`, nicht Begleitdatei), wird sie bei `:1459` überschrieben. Der bestehende AK6-Haupttest (`:273–352`) fährt genau diesen Pfad, setzt seine Kollisionsdatei aber als `MyShow - S01E01 - Pilot.adversarial.txt` (andere Endung), sodass der exakte Zielnamens-Clash nicht ausgelöst wird.

**Bewertung:** Dies ist die AK6-Kernzusage-Verletzung derselben Klasse wie R1–R4 — ein `files[]`-Job berührt eine Datei außerhalb Gruppe ∪ Begleitdateien — und zwar **ohne** bösartige Parameter, allein durch Namensgleichheit. Der R3-Fix hat den Ziel-Existenzcheck nur für **Untertitelziele** (`:1489–1492 raise`) eingeführt, nicht für das Video-Ziel. Daher [kritisch].

### N2 [wichtig] — `explicit_renames`/`explicit_subs`: Ziel (`new`) weder Scope- noch Existenz-geprüft

**Stellen:** `processor.py:1030–1038` (`explicit_renames`: `os.rename(old_path, new_path)` bei `:1037`), `:1040–1049` (`explicit_subs`: `os.rename` bei `:1048`).

**Mechanismus:** Der R2-Scope-Check (`:964–969` bzw. `:958–963`) prüft ausschließlich die **Quelle** (`old`). Der Zielname `new` ist vollständig ungeprüft: kein `normpath`-Konfinement, keine Memberschaft in `scope_files`, kein `os.path.exists(new_path)` vor dem Rename. `new_path = os.path.join(current_dir, r["new"])` mit `current_dir == inbox_root` (`:1032`).

**Repro-Pfad:** `POST /api/process` mit `{"media_type":"tv","files":["Show.S01E01.mkv"],"mappings":{"Show.S01E01.mkv":1},"explicit_renames":[{"old":"Show.S01E01.mkv","new":"Fremdordner/Fremddatei.txt"}]}`. Der `old`-Eintrag liegt in `scope_files` → Check passiert. Existiert `Fremdordner/Fremddatei.txt`, wird sie bei `:1037` überschrieben. Ein legitimer Preview-Fluss setzt `new` zwar auf `clean_title.ext`, aber die offene API erlaubt beliebige `new`-Werte inkl. Unterordner-Ziele. Der Kollisions-Check `:985–1028` erkennt nur Mehrfach-`old`→gleiches-`new` **innerhalb der Liste**, nicht Kollisionen mit dem Dateisystem.

**Bewertung:** Scope-Durchgriff derselben Klasse (Ziel liegt außerhalb der Gruppe), erfordert allerdings manipulierte/irrtümliche `new`-Werte. Daher eine Stufe unter N1 → [wichtig].

### N3 [wichtig] — Konvertierungs-Pfad schreibt temp/final in den Inbox-Root ohne Existenzcheck (Hypothese H3)

**Stellen:** `processor.py:1554` (`temp_output = os.path.join(current_dir, f"{clean_title}_neu.mkv")`) und `:1581` (`final_filepath=os.path.join(current_dir, f"{clean_title}.mkv")`) — bei `files`-Job ist `current_dir == inbox_root`.

**Mechanismus:** Bei `convert=True` schreibt `execute_video_conversion` den Temp-/Final-Output in den Inbox-Root. Existiert dort eine Fremddatei mit exakt `{clean_title}_neu.mkv` oder `{clean_title}.mkv`, wird sie von ffmpeg (bzw. über `delete_original`/Post-Schritte) überschrieben. Zusätzlich: das Video wurde bereits bei `:1459` auf `clean_title.ext` umbenannt, und `final_filepath` `clean_title.mkv` kollidiert potenziell mit einer **anderen** Fremddatei als das `:1459`-Ziel, sofern die Quelldatei-Endung von `.mkv` abweicht.

**Bewertung:** Dieselbe Kollisionsklasse wie N1, zusätzlich erweitert um die Suffixe `_neu.mkv` und das konvertierte `.mkv`. `convert` ist ein Opt-in-Parameter; Schwere [wichtig].

---

## 3. Hypothesen-Bewertung

- **H1 (Zielnamens-Kollision ohne Existenzcheck) — bestätigt, [kritisch].** Drei ungeschützte `os.rename`-Ziele: `:1459` (Fallback-Video, **ohne** `explicit_renames`), `:1037` (explicit_renames, **mit**), `:1048` (explicit_subs, **mit**). Der R3-Fix schützt nur Untertitelziele im Fallback-Zweig (`:1489–1492`), nicht die drei oben genannten Stellen. Erreichbar über `/process` in beiden Varianten (mit und ohne `explicit_renames`).

- **H2 (`/queue/retry` umgeht Gates) — widerlegt.** `queue_api.py:927–996` re-queued nur bereits persistierte Job-Params. `job_queue_worker` (`processor.py:3690–3706`) ruft `process_worker(params)` auf, der bei `files_param is not None` **vollständig revalidiert**: `media_type`-Check (`:871`), `validate_group_files` (`:879`), TOCTOU-Existenzprüfung (`:948–951`). Ein `files`+Nicht-tv-Job kann gar nicht erst entstehen (`/process` lehnt mit 400 ab), und selbst ein Altbestands-Job würde beim Retry im Worker mit `RuntimeError` abgewiesen. Kein Umgehungsweg.

- **H3 (Konvertierungs-Pfad) — bestätigt, [wichtig].** Siehe N3. temp/final im Inbox-Root ohne Existenzcheck; zusätzliche Kollisionsfläche über `_neu.mkv`/konvertiertes `.mkv`.

- **H4 (Normalisierungsasymmetrie als Sicherheitslücke) — widerlegt als Sicherheitslücke.** `validate_group_files` liefert Rohstrings (`f_clean`, `helpers.py:862`), `companion_files` liefert `relpath`-normalisierte Pfade (`helpers.py:912`); der R2-Check vergleicht `normpath(entry)` gegen dieses gemischte Set. Die Asymmetrie erzeugt **nur konservative falsche Abweisungen** (unnormalisierte Client-Pfade wie `Sub//File.mkv` oder Case-Varianten auf case-insensitivem APFS werden nicht als Mitglied erkannt → `RuntimeError`). Eine **falsche Zulassung** ist nicht konstruierbar: `normpath(j) in scope_files` erzwingt case-sensitiv exakte Übereinstimmung, und `os.path.join(current_dir, j)` zeigt dann case-insensitiv garantiert auf dieselbe Datei. Kein Datenrisiko; lediglich ein Robustheits-/Konsistenz-Hinweis (Rohstrings konsequent `normpath`en).

- **H5 (weitere Lücken derselben Klasse):** Keine zusätzlichen über N1–N3 hinaus gefunden. Die geprüften übrigen Konsumenten (`safe_move_recursive`-Aufrufe `:1649–1658` mit `allowed_files`, `:1748–1755` nur bei `files_param is None`, `:2128–2135` movie — durch R1 nicht mehr files-erreichbar; `move_with_fallback` `:386–479` operiert nur im job-eigenen Outbox-Ziel mit Existenzprüfung `:469–474`; `tool_pull_files`/`tool_batch_convert` `:3200–3269` sind Nicht-tv-Zweige und durch R1 für `files` unerreichbar) zeigen keinen Durchgriff auf Inbox-Fremddaten.

---

## 4. Testabdeckung / Testlücken

**Jede Schließung hat einen echten End-to-End-Fall (process_worker-Ausführung):**
- R1: `test_r1_files_param_with_non_tv_media_type_rejected` (`:478–514`) — echte `test_client.post`-Aufrufe für beide Endpunkte + direkter `process_worker`-Lauf.
- R2: `test_r2_explicit_junk_same_basename_in_other_folder_aborts_loudly` (`:516–546`) und `test_explicit_subs_and_renames_outside_scope_aborts_loudly` (`:691–724`).
- R3: `test_r3_fallback_subtitle_rename_boundary_and_foreign_file_untouched` (`:548–586`) und `test_fallback_subtitle_rename_multiple_languages_preserved` (`:651–689`).
- R4: `test_r4_subfolder_group_with_companion_file_moved_to_outbox` (`:588–619`).
- D1/D3: `test_d3_regression_tv_single_file_job_without_files_cleans_empty_dirs` (`:621–649`) und `test_backwards_compatibility_paths_without_files_param` (`:432–473`).

Die AK5-Helper-Tests (`:73–168`) sind Unit-Tests, aber die **Schließungsfälle** R1–R4/D1/D3 sind echte Ausführungen, nicht nur Helper-Aufrufe.

**Nicht durch Tests gefangen:**
- **N1/H1:** kein Test legt eine Fremddatei mit **exakt** dem Video-Zielnamen (`clean_title.ext`) an. Der AK6-Haupttest (`:304`) verwendet `…adversarial.txt` und prüft damit nur den `safe_move_recursive`-`prefix_filter`-Durchgriff, nicht den `os.rename`-Ziel-Clash bei `:1459`.
- **N2:** kein Test für `explicit_renames`/`explicit_subs` mit `new` außerhalb Scope bzw. auf existierende Fremddatei.
- **N3/H3:** kein Test mit `convert=True` + `files`-Job + Kollisionsdatei (`_neu.mkv`/final `.mkv`).
- **H2:** kein `retry`-Test mit `files` — akzeptabel, da H2 widerlegt ist, aber die Revalidierung im Retry-Pfad ist ungetestet (Restrisiko-Notiz).

---

## 5. Entkräftete Punkte (geprüft, kein Finding)

- **H2** (retry-Umgehung): widerlegt, vollständige Revalidierung im Worker.
- **H4** (Normalisierungsasymmetrie als Sicherheitslücke): nur konservative falsche Abweisungen, keine falsche Zulassung.
- `safe_move_recursive`-allowed_files-Realpath-Set (`:502–510` + `:518–521`) schließt Fremdzugriff beim Verschieben in den Outbox weiterhin aus; die F2-Klasse bleibt gedeckt.
- `_finalize_job` `:346` (`current_dir != inbox_root`) greift bei `files`-Jobs nicht (dort `current_dir == inbox_root`) — vorbestehend, kein files-Bezug.
- `tvshow.nfo`/Artwork-Ziel (`:1101–1103`) bleibt bei `files`-Jobs im Outbox-Show-Ordner, nicht im Inbox-Root.
- `move_with_fallback` (`:386–479`): Ziel-Existenzprüfung vorhanden (`:469–474`), operiert nur im job-eigenen Outbox-Ziel; NAS-Companion-Copy (`:137–139`) nur im Outbox-Ordner (bereits in rueckkanal-65a entkräftet).
- `tool_pull_files`/`tool_batch_convert`: Nicht-tv-Zweige, durch R1 für `files`-Eingaben unerreichbar.

---

## Gesamteinschätzung

Die sechs beauftragten Schließungen (R1–R4, D1, D3) sind vollständig und korrekt umgesetzt und getestet. Die AK6-Kernzusage ist jedoch weiterhin **nicht lückenlos**: Es verbleibt eine neue Lücke derselben Klasse — die **Zielnamens-Kollision** beim Rename in den Inbox-Root (N1 [kritisch], N2/N3 [wichtig]). Diese ist klein behebbar (Existenzcheck am Ziel analog `:1489–1492` vor den `os.rename`-Stellen).
