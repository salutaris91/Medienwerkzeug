---
kind: plan
status: approved
approved_by: alex
approved_on: 2026-10-12
approval_quote: "ja, Briefing freigegeben, starte den Gate-A2-Lauf"
source: roadmap#71
---

# Feature Briefing: #71 (Teilmenge) — Einzelvideo-Ordner gruppierbar und wählbar + Folgen-Regex ohne Trennzeichen, plus #72 Punkt 1 (`new`-Härtung)

**Quelle präzise:** `roadmap#71` nur in der Teilmenge „Ordner mit genau einer Videodatei werden wie Einzeldateien gruppierbar und per Auswahlkästchen wählbar" (Kickoff `00-kickoff.md`, Scope-Abschnitt) **plus** `roadmap#72` Punkt 1 (`ROADMAP.md:1996`, Härtung `explicit_renames`/`explicit_subs` gegen Unterordner-Ziele). Nicht enthalten: volles Aufklapp-UI (#71 Kern), #72 Punkte 2–8, #68.

**Bindende Alex-Entscheidungen (Kickoff, wörtlich 2026-10-12: „ja zu 1) darfst du und den Rest entsprechend deinen empfehlungen" / „ja, beides wie empfohlen, starte das Kreativteam" / „F1 wie empfohlen nicht mitnehmen, starte Akt 2"):** (1) Muster (a) mit `(?!\d)`; (2) zwei additive Felder `single_video_relpath`/`single_video_query`; (3) Schlüssel/Serienname aus dem Dateinamen, Ordnername nur Ausweichweg; (4) nur Datei + Begleiter bewegen, Ordner bleibt liegen; (5) #72 Punkt 1 mit allen `files_param`-Konsumenten; (6) ein Gate-A2-Lauf + Handtest nativ arm64 + NAS-Livetest erst Staffel 11; (7) Aufträge ohne `files[]` byte-genau unverändert. F1 (Typ-Erkennung über Dateinamen) ist **abgesagt** → Abschnitt 4. Verbindlich zusätzlich durch Korrekturrunde 2b (Alex, wörtlich 2026-10-12: „Korrekturrunde 2b wie empfohlen, starte sie"): die Regex-Form aus ADR-71a-3 (P2) sowie die Reihenfolge in Abschnitt 11 „Freigabe- und Merge-Pfad" inkl. Plausibilitätsprüfung, Rückkanal-Abnahme und Handtest **vor** dem PR-Merge (P1).

## 1. Problemstellung

Der Live-Befund (Staffel-Ordner wie `ThWaDeS11E23/The.Walking.Dead.S11E23.…mkv`): solche Ordner können in der Smart Inbox weder automatisch zu Serien-Gruppen zusammengefasst noch per Auswahlkästchen an einen `files[]`-Serienauftrag übergeben werden. Zwei unabhängige Ursachen, beide im Kickoff verifiziert:

- **U1 — Regex:** `extractStrictSeasonEpisode` (`gui/static/app.js:12477–12490`) verlangt links zwingend ein Trennzeichen `(?:^|[._\s\-\[])` und rechts `(?:[._\s\-\]]|$)` (Zeile 12479). Bei `ThWaDeS11E23` steht links ein Buchstabe → `null` → kein Gruppenmitglied.
- **U2 — doppelter Ordner-Ausschluss:** `detectInboxGroups` (`app.js:12492–12515`) wirft `is_dir === true` raus (Zeile 12496); die Checkbox-Eligibility (`app.js:13126`, `isTvSingle`) verlangt `is_dir === false`. Ordner sind damit weder gruppierbar noch anhakbar.

Zusätzlich dokumentiert ROADMAP #72 Punkt 1 (`ROADMAP.md:1996`) eine Härtungslücke, die durch diese Änderung erstmals relevant wird: Bei `files[]`-Jobs akzeptieren die `new`-Prüfungen (`gui/workers/processor.py:969–978` Subs, `:988–997` Renames) relative Ziel-Pfade mit Unterordnern (`XyzS02E05/Neuer.Name.mkv` passiert alle Checks, Kickoff B7). Der legitime Client sendet `new` immer als reinen Dateinamen (`queue_api.py:568–569`, `:622–644`) — die Prüfung „kein Separator in `new`" verletzt also keinen legitimen Pfad. Da dieser Lauf Ordner massenhaft in `files[]`-Jobs bringt (173 ThWaDe-Ordner im Live-Bestand, siehe Abschnitt 2; erster Live-Batch Staffel 11 mit 23 Ordnern), wird Punkt 1 mitgenommen ([produktberater]: „Verschieben = bewusstes Akzeptieren eines Sicherheitsfensters in dem Moment, wo die Feature-Nutzung skaliert").

Server-Vorbereitung ist schon halb vorhanden: Ordner-Einträge tragen `is_dir` (`gui/api/project_api.py:1502`, aus #65 Lauf A) und die Payload-Feldliste (`:1490–1503`) ist der Ort, an dem die zwei neuen additiven Felder ergänzt werden (Kickoff B5).

## 2. Zielnutzer

Alex. Live-Bestand (lesendes NAS-Listing von Claude Code, 2026-10-12, P3): **173 Ordner** `ThWaDeS01E01` … `ThWaDeS11E23` (Staffeln 1–11; Staffel 11 = 23 Ordner), je **genau eine `.mkv`** — **keine losen Dateien** dieser Serie, **keine Untertitel/Begleiter, keine NFO, keine Samples, keine Unterordner**. Die Ordner mit genau einer Videodatei gehen künftig automatisch in eine Serien-Gruppe (bzw. sind per Kästchen manuell wählbar), und ein Klick verarbeitet die Auswahl als EINEN Serien-Job über den bewährten `files[]`-Weg aus #65 — ohne dass die Ordner selbst in der Inbox angefasst oder gelöscht werden. Die gemischte Gruppe aus loser Datei + Ordner sowie Begleiter-/Fremddatei-Behandlung sind Feature und werden ausschließlich im Handtest (Abschnitt 12) geprüft — im Live-Bestand existieren diese Fälle nicht. Kein externer Nutzer.

## 3. Akzeptanzkriterien

AK0 ist Aufgabe von Claude Code (nicht des Workers); AK1–AK10 sind ausführbare Tests, die der Worker neu schreibt oder ergänzt. Bestehende Suites bleiben grün (Ausnahme dokumentierte Verhaltensänderung AK1d).

- [ ] **AK0 — Ausgangsmessung:** **Claude Code** misst VOR dem scharfen Gate-A2-Lauf im Worker-Image (kein Testlauf auf dem Host) die volle Suite und schreibt die wörtlichen Ausgaben mit Exit-Code in `docs/sessions/2026-10-12-inbox-ordnerfolgen/ak0-ausgangsmessung.md`. Befehl wie Abschnitt 11 (`test_cmd`). Basis: `origin/main` @ `17b96d1` (#65 Lauf A `dd65244` + Lauf B `17b96d1` gemergt); der Session-Head `fc75466` ist docs-only und nicht Teil der Worker-Basis.
- [ ] **AK1 — Muster (a) in `extractStrictSeasonEpisode`** (Frontend-Test, Erweiterung `tests/frontend/inbox_group.test.js`, Muster Zeilen 646–667): Es prüft, dass
  (a) `ThWaDeS11E23` → `{season: 11, episode: 23, formatted: "S11E23"}` matcht (heute `null`, U1);
  (b) der Ziffern-Fall `ThWaDeS11E24720p` → `null` liefert (greedy `(\d{1,3})` + `(?!\d)`: `E247`→`2` folgt Ziffer, Backtracking `E24`→`7`, `E2`→`4` — alle Fail; Beleg [advocatus] KOS1);
  (c) die bestehenden Positiv-Fälle `Show.S01E01.720p.mkv` → S01E01 und `Show_S02E15_1080p.mkv` → S02E15 unverändert matchen UND die bestehenden Null-Erwartungen `Movie.1920x1080.x264.mkv`, `The Rock (1996).mkv`, `Show.1x05.mkv`, `Staffel 2 Folge 3 – Show.mkv` (`inbox_group.test.js:661–667`) weiterhin `null` liefern (Kickoff N2: alle enthalten kein `s\d+e\d+`-Muster — die Suite kippt nicht);
  (d) die dokumentierte Verhaltensänderung greift: `The.Show.S01E01PROPER.mkv` matcht künftig S01E01 (rechte Seite `(?!\d)` statt Trennzeichen/Ende — N2, global; einziger Aufrufer ist `detectInboxGroups` `app.js:12499`, dazu globalThis-Export `:13234` für Tests — keine weiteren Nutzer, per grep verifiziert);
  (e) eine Ziffer direkt links liefert `null`: `Show.1080S02E03.mkv` → `null` (Linker-Lookbehind `(?<!\d)` der verbindlichen Form: direkt vor dem `S` steht `0`; P2, Alex-Entscheidung Korrekturrunde 2b);
  (f) ein Buchstabe direkt links matcht auch kleingeschrieben: `shows01e02.mkv` → S01E02 (der Großbuchstabe-Fall ist schon (a); P2).
- [ ] **AK2 — zwei additive Server-Felder, eigene 10er-Zählung** (Backend-Test, Erweiterung `tests/test_inbox_suggestions.py`, nur ergänzen): Es prüft für `/api/inbox/analyze`-Einträge:
  (a) Ordner mit GENAU EINER Videodatei nach `GROUP_VIDEO_EXTENSIONS` (10er-Liste, `gui/core/helpers.py:798`) liefert `single_video_relpath` (Inbox-relativ, inkl. Unterordner-Pfad `Ordner/Sub/Datei.mkv` → `os.path.relpath`, vgl. `project_api.py:1333–1340` rekursiver Walk) und `single_video_query`;
  (b) Ordner mit 2 Videos nach 10er-Liste — auch `.mp4`+`.wmv` (6er-Liste zählt hier nur 1!) — liefert BEIDE Felder NICHT ([advocatus] K2: Zählung darf nicht aus `video_files`/`video_count` abgeleitet werden);
  (c) Ordner mit 0 Videos nach 6er-Liste (z. B. nur `.flv`) erscheint weiterhin gar nicht im Payload (`video_count == 0 → continue`, `project_api.py:1345–1346`, bekannte Grenze N3);
  (d) lose Einzeldateien und alle übrigen Einträge erhalten die neuen Felder nicht (additiv, nur für Ordner);
  (e) `video_count` bleibt 6er-Liste-unverändert (`:1321`), alle bestehenden Felder unverändert.
- [ ] **AK3 — `single_video_query` = Einzeldatei-Pipeline (N1)** (Backend-Test): Es prüft, dass `single_video_query` eines Einzelvideo-Ordners **byte-identisch** zum `suggested_query` ist, das die bestehende Einzeldatei-Pipeline (`tv_pattern.search` → Präfix → `strip(' ._-')` → `clean_show_name`, `project_api.py:1413–1421`, `:1438–1440`) auf denselben Dateinamen in der Inbox-Root liefert (also „The.Walking.Dead" mit Punkten, nicht mit Leerzeichen — B3-Nuance); und dass bei einem Dateinamen OHNE `SxxExx`-Treffer (`video.mkv` in `ThWaDeS11E23/`) `single_video_query` auf den Eintrags-`suggested_query` des Ordners zurückfällt (Entscheidung 3: „Ordnername nur als Ausweichweg").
- [ ] **AK4 — Gruppierung einbeziehen, Schlüssel aus dem Dateinamen** (Frontend-Test, `detectInboxGroups`): Es prüft, dass
  (a) ein tv-Ordner mit `single_video_relpath` + `single_video_query` als Gruppenmitglied teilnimmt; Gruppenschlüssel bei Ordnern `single_video_query` ist, bei losen Dateien `suggested_query`;
  (b) **gemischte Gruppe:** lose Datei `The.Walking.Dead.S11E24.mkv` und Ordner `ThWaDeS11E23/The.Walking.Dead.S11E23.mkv` (Schlüssel aus AK3 identisch) zu EINER Gruppe zusammengefasst werden (≥2-Mitglieder-Regel `app.js:12508–12513` unverändert);
  (c) die S/E-Ermittlung bei Ordnern zuerst gegen den Dateinamen aus `single_video_relpath` läuft, bei `null` gegen den Ordnernamen fällt zurück (Fall `ThWaDeS11E23/video.mkv` → S11E23 über Ausweichweg);
  (d) tv-Ordner OHNE `single_video_relpath` (≥2 Videos) weiterhin nie gruppiert werden — der bestehende Test `inbox_group.test.js:672–700` (Fake-Ordner ohne neue Felder → `{}`) bleibt grün ([advocatus] W4: Negativ-Test bleibt gültig, weil an die Feld-Anwesenheit geknüpft);
  (e) leere Schlüssel/Sentinel-Regeln unverändert gelten (`app.js:12498`, `:1094–1099` Sentinel-Test grün).
- [ ] **AK5 — Checkbox, Übergabe und Gruppenname für Ordner** (Frontend-Test, Muster `inbox_group.test.js:968–1062`): Es prüft, dass
  (a) die Eligibility (`app.js:13126`) einen tv-Ordner mit `single_video_relpath` als Kandidat zulässt (Checkbox aktiv, nicht verarbeitete Ordner), ein tv-Ordner ohne Feld sowie Doku-/Film-Ordner weiterhin KEINE Checkbox erhalten — der bestehende Test `:968–995` („Folders must not have checkboxes", Fake ohne Felder) bleibt grün; die Checkbox trägt `aria-label="Ordner mit einer Folge auswählen"` und `title="Verarbeitet wird: <single_video_relpath>"`;
  (b) **Übersetzung project→relpath an allen Übergabepfaden** ([advocatus] K1 — ohne sie liefert JEDER Ordner-Auftrag HTTP 400, weil `validate_group_files` Ordner ablehnt, `helpers.py:851–852`): Banner-Apply (`app.js:12630` `members.map(m => m.project)`), Gruppen-Knopf (`:13075`), Bulk-Weg (`:12698` `Array.from(selectedInboxProjects)`), — alle legen in `files[]` für Ordner-Mitglieder exakt `single_video_relpath` ab, für lose Dateien weiterhin `project`;
  (c) **Key-Vertrag V1 bleibt:** `mappings`-Schlüssel = identische `files[]`-Strings (auch bei relpath-Einträgen); das Auswahl-Set bleibt über `item.project` keyed (Ordnername), die Übersetzung passiert erst bei Payload-Bau; Auswahl übersteht Re-Render und Sortierwechsel wie bisher (`:997–1026` grün);
  (d) **Gruppenname aus dem Dateinamen:** Im Bulk-Weg wird der `fallbackName`-Lookup (`app.js:12706`, heute `find(s => s.project === files[0])` — schlägt bei relpath als `files[0]` fehl) über die ausgewählten ITEMS geführt und bevorzugt `single_video_query`; `detectManualGroupSeriesName` (`:12641–12661`) erhält die `files`-Strings (Separator-Strip `:12645` liefert bei relpaths automatisch den inneren Dateinamen). Testfall: nur Ordner-Mitglieder `ThWaDeS11E23/The.Walking.Dead.S11E23.mkv` + `ThWaDeS11E24/The.Walking.Dead.S11E24.mkv` → Gruppenname `The.Walking.Dead` (nicht `ThWaDeS`/`ThWaDe`, Kickoff B4/N4);
  (e) `isProcessing`-Guard unverändert (Set/Verarbeitungsschlüssel bleibt `item.project`, `app.js:13121`).
- [ ] **AK6 — Job-Realität: nur Video + Begleiter bewegen, Ordner bleibt liegen** (Backend-Test, tmp-Inbox, Muster `tests/test_inbox_group_files.py`): Es prüft mit Aufbau `XyzS01E01/Xyz.Show.S01E01.Titel.mkv` + Begleiter `Xyz.Show.S01E01.Titel.de.srt` + Fremddateien im selben Unterordner (`XyzS01E01/movie.nfo`, `XyzS01E01/sample.mkv` (zweite Videodatei → Ordner hätte dann ≥2 — für DEN Testordner daher: `sample.mkv` in einen ZWEITEN Beobachtungsordner legen oder nicht-video-Fremddatei wählen), Bild `poster.jpg`) sowie Show-Level-Dateien auf Ordner-Ebene (`tvshow.nfo`): Ein ausgeführter `files[]`-Job mit `single_video_relpath` als Eintrag bewegt NUR die Videodatei + `<stem>.*`-Begleiter (`find_group_companion_files`, `helpers.py:870–918`, sucht im Ordner der Videodatei — B2), lässt Fremd- und Show-Level-Dateien unberührt ([advocatus] W3), und der Ordner EXISTIERT NACH dem Job weiter auf der Scheibe (Entscheidung 4; leerer-Ordner-Cleanup läuft nur bei `files_param is None`, `processor.py:1084–1091`, `:1717` — strukturell schon erfüllt, hier festzuschreiben). Der Eintrag verschwindet im nächsten Listing nur, weil `video_count == 0` (`project_api.py:1345–1346`).
- [ ] **AK7 — #72 Punkt 1: `new` ohne Separator bei `files[]`-Jobs** (Backend-Test, Erweiterung `tests/test_inbox_group_files.py`): Es prüft, dass bei Aufträgen MIT `files[]` ein `explicit_renames`-/`explicit_subs`-Eintrag mit `new` = `Sub/Neuer.Name.mkv`, `Sub\\Neuer.Name.mkv` (Backslash — auf POSIX ist `os.path.basename` hier kein Schutz, [advocatus] W2), `./x.mkv` oder leerem String `""` den Job **LAUT** abbricht, bevor irgendetwas bewegt wird (Prüfblöcke `processor.py:969–978`, `:988–997` laufen vor der ersten Bewegung ab `:999`); und dass der legitime Fall unverändert bleibt: `old = "XyzS01E01/Datei.mkv"` (Unterordner = normal, Hochziehen per `os.rename(current_dir/old → current_dir/new)`, `processor.py:1058–1068`) mit reinem `new = "Neuer.Name.mkv"`.
- [ ] **AK8 — Abwärtskompatibilität byte-genau (Entscheidung 7):** Es prüft, dass alle Pfade OHNE `files[]` unverändert sind (bestehende Suite grün; `files[]`-Logik bleibt strikt in `if files_param is not None`-Zweigen, `queue_api.py:73–95`, `:815–833`, `processor.py:870–884`, `:947–997` — Kickoff, Entscheidung 7/4-Beleg); dass die Payload nur um die zwei Felder ERGÄNZT wird (lose Dateien und Mehrvideo-Ordner: Felder abwesend, kein `null`-Rauschen nötig — Implementierung: Keys nur setzen, wenn zutreffend); dass `media_type`-Erkennung unverändert bleibt (F1 abgesagt — kein Ordner wird über den Dateinamen zur Serie).
- [ ] **AK9 — Cache-Buster v100:** `app.js?v=99` → `?v=100` in `gui/static/index.html:2760` UND allen neun ES-Modul-Importen `app.js:1–9`; `tests/frontend/cache_busting.test.js` bleibt grün (erzwingt Index↔Import-Identität, `:13–47`; Version selbst ist agnostisch — der Bump ist über Abschnitt 11 + Review abgesichert, Kickoff B6).
- [ ] **AK10 — Hygiene:** `git diff --check` sauber (keine Trailing Whitespace); Tests schreiben nur in tmp-Verzeichnisse; Frontend-Tests räumen alle Timer aus `app.js` ab (stubben/clear, Erfahrungswert aus #65 Lauf B); keine Secrets; `.env` wird nie gelesen.

## 4. Bewusst verworfen (Scope-Eingrenzung)

- **F1 — Typ-Erkennung über den Dateinamen:** Alex, wörtlich 2026-10-12: „F1 wie empfohlen nicht mitnehmen, starte Akt 2". Ein Ordner ohne `SxxExx` im Ordnernamen (z. B. `CD1/The.Walking.Dead.S01E01.mkv`) bleibt `media_type: "movie"` → weder Gruppe noch Checkbox. Begründung der Absage (von Alex angenommen): die Änderung der `media_type`-Erkennung hätte auch Einzelaufträge ohne `files[]` betroffen (Entscheidung 7 verletzt). **Folgepunkt zu ROADMAP #71** — die ROADMAP-Notiz schreibt Claude Code, nicht dieser Lauf.
- **Volles Aufklapp-UI aus #71** (Videodateien eines Mehrvideo-Ordners einzeln auswählen): eigener, späterer Teil von #71; hier werden nur Ordner mit GENAU EINEM Video behandelt.
- **#72 Punkte 2–8:** nur Punkt 1 wird umgesetzt (Punkt 8 „Endungslisten bündeln" bleibt eigene Arbeit; die 6er/10er-Inkonsistenz ist als bekannte Grenze N3 dokumentiert, nicht behoben).
- **#68 Ordner-Aufräumen:** der leer zurückbleibende Ordner wird bewusst NICHT weggeräumt (Entscheidung 4 „Ordner bleibt liegen"; Cleanup-Code bleibt bei `files_param is None` abgeschaltet).
- **Neue Badge „1 Video" + Ordner-Icon + zweizeilige Mitgliederliste** ([grafiker]-Vorschläge): **verworfen** — die Meta-Zeile zeigt bereits „N Datei(en)" (`app.js:13109`), ein Icon für ALLE Ordnerzeilen und eine umbaute Mitgliederliste vergrößern Diff und Testfläche ohne Funktionsgewinn (Reviewer-Prompt-Grenze ~120 KB). Übernommen: Checkbox-Parität, `aria-label`, `title`-Tooltip. Begründung in Abschnitt 6 (Dissens 2).
- **Früh-Prüfung `new`-Separator in `queue_api.py` (Preview/Process, HTTP 400):** **verworfen** — `queue_api.py` konsumiert `explicit_renames`/`explicit_subs` heute gar nicht (per grep verifiziert: keine Treffer); die bestehenden `new`-Prüfungen (absolut/`..`/Ausbruch) sitzen ebenfalls nur im Processor. Ein dritter Validierungsstrang wäre neue Angriffsfläche ohne Schutzgewinn, da der Job vor jeder Bewegung laut abbricht. Begründung in Abschnitt 6 (Dissens 1).
- **Auswahl-Set auf `single_video_relpath` umstellen:** **verworfen** — bräche `isProcessing`-Guard (`processingSet` keyed nach `item.project`, `app.js:13121`) und drei bestehende Tests; Übersetzung project→relpath erfolgt nur beim Payload-Bau (ADR-71a-2).
- **Server-seitige Gruppierung / `media_type`-Änderung / neue Endpunkte:** alles unverändert; nur zwei additive Payload-Felder.

## 5. ADR-Blöcke

### ADR-71a-1: Server liefert zwei additive Felder mit eigener 10er-Zählung
- **Entscheidung:** `get_inbox_suggestions` (`project_api.py:1299–1508`) zählt im bestehenden `os.walk`-Durchlauf (`:1333–1340`) zusätzlich die Videodateien nach `GROUP_VIDEO_EXTENSIONS` (10er-Liste `helpers.py:798`; via `from gui.core.helpers import *` bereits im Scope von `project_api.py:4`, sonst explizit importieren). Nur Ordner mit exakt 1 Treffer der 10er-Liste erhalten `single_video_relpath = os.path.relpath(vollpfad, inbox_dir)` und `single_video_query`; alle anderen Einträge bekommen die Keys nicht. `video_count`/6er-Liste bleiben unangetastet. `single_video_query` = `tv_pattern`-Pipeline gegen den Dateinamen mit Unterordner-Ausweich auf den Eintrags-`suggested_query` (AK3).
- **Alternativen:** Ableitung aus `video_files`/`video_count` (**abgelehnt** — [advocatus] K2: `.mp4`+`.wmv` würde fälschlich als Einzelvideo deklariert, die `.wmv` bliebe stumm liegen); Felder auch für lose Dateien (**abgelehnt** — redundant, `project`/`suggested_query` leisten das bereits); separates Detail-Objekt/Endpunkt (**abgelehnt** — Over-Engineering, [produktberater] Falle „keine neue Serverlogik über die zwei Felder hinaus").
- **Begründung:** Entscheidung 2 (bindend): genau zwei additive Felder; `video_count` bleibt. Die 10er-Liste ist die Liste des Verarbeitungspfads (`validate_group_files`, `helpers.py:857–859`) — nur sie darf das Einzelvideo-Kriterium definieren.
- **Konsequenzen:** Payload wächst pro Einzelvideo-Ordner um zwei Strings; 30-s-Cache (`:1303–1305`) wirkt unverändert (dokumentiertes Restrisiko W5, Abschnitt 6).

### ADR-71a-2: Eine Übersetzungsfunktion project→files-Eintrag, Auswahl bleibt project-gekeyed
- **Entscheidung:** Eine neue Hilfsfunktion in `app.js` (Arbeitsname `inboxFilesEntryForItem(item)`: bei `is_dir === true && single_video_relpath` → `single_video_relpath`, sonst `item.project`) wird an ALLEN Übergabestellen verwendet: Banner-Apply (`:12630`), Gruppen-Knopf (`:13075`), Bulk-Weg (`:12698`, dort Map über die zu `selectedInboxProjects` gehörenden Items aus `currentSmartInboxRawSuggestions`). Das Set selbst bleibt über `item.project` keyed. `fallbackName`-Lookup (`:12706`) führt die Items (nicht die files-Strings) und bevorzugt `single_video_query` vor `suggested_query`.
- **Alternativen:** Set auf relpath umstellen (**abgelehnt**, Abschnitt 4); je Aufrufer eigene Inline-Map (**abgelehnt** — [advocatus] K1 zählt fünf Stellen, Drift-Gefahr bei der nächsten Änderung); `mappings`-Schlüssel auf Ordnernamen normieren (**abgelehnt** — verletzt Key-Vertrag V1 aus #65, `briefing-65.md` ADR-65-2).
- **Begründung:** Der Server lehnt Ordnernamen in `files[]` ab (`helpers.py:851–852`); ohne Übersetzung schlägt jeder Ordner-Auftrag fehl. Eine zentrale Funktion hält die **Übergabe-Invariante** (die drei files-Bau-Stellen `:12630`/`:12698`/`:13075` plus `fallbackName`-Lookup `:12706`; [advocatus] K1 zählte zusätzlich den `detectInboxGroups`-Member-Push, der kein Übergabepfad ist) testbar (AK5b/d) und hält den Diff klein.
- **Konsequenzen:** Theoretische Namens-Kollision „Ordner X + Datei X in derselben Inbox" bleibt (Set-Key `project` ist dann nicht unterscheidbar) — dokumentiertes Restrisiko (Abschnitt 6); in der Praxis verhindert die Inbox-Struktur den Fall ([grafiker]).

### ADR-71a-3: Muster (a) = linke Trennzeichen-Pflicht fällt, rechte Seite `(?!\d)`
- **Entscheidung:** `extractStrictSeasonEpisode` (`app.js:12479`) wird auf die **verbindliche** Form `/(?<!\d)[sS](\d{1,2})[eE](\d{1,3})(?!\d)/i` geändert. Alex hat diese Form in der Korrekturrunde 2b ausdrücklich angenommen (wörtlich 2026-10-12: „Korrekturrunde 2b wie empfohlen, starte sie") — die Schreibweise ist damit **keine Worker-Entscheidung** mehr. Verbindlich sind zusätzlich die AK1-Verhaltensfälle (a–f): match `ThWaDeS11E23` und `shows01e02`, null `ThWaDeS11E24720p` und `Show.1080S02E03`, bestehende Null-Fälle bleiben null, `…E01PROPER` matcht künftig. Wirkung global für alle Aufrufer — das ist nur `detectInboxGroups` (`:12499`) plus globalThis-Export für Tests (`:13234`), per grep verifiziert (Notiz N2).
- **Alternativen:** Linke Gruppe komplett entfernen (**abgelehnt** — `(?<!\d)` verhindert Ziffer-präfixierte False-Positives wie `…1080s2e3…` fast nichts kostend; [produktberater]-Empfehlung); Buchstaben-Alternative `[a-zA-Z]` links (**abgelehnt** — komplexer, gleiche Treffermenge für den Live-Fall).
- **Begründung:** Alex' Entscheidung 1 ist bindend. Die linke Seite war im Kickoff-Prompt **explizit benannt** — dort stand „Vor `S\d{1,2}E\d{1,3}` ist zusätzlich ein Buchstabe erlaubt"; die ursprüngliche Regel lautete „Buchstabe oder Trennzeichen". Alex hat diese Regel auf Empfehlung von Claude Code durch „alles außer einer Ziffer" (links `(?<!\d)`) ersetzt und die Form in der Korrekturrunde 2b verbindlich gemacht. Die AK1-Verhaltensfälle (a–f) bleiben als ausführbarer Vertrag daneben bestehen; `(?<!\d)` schließt ziffernpräfixierte False-Positives (z. B. `Show.1080S02E03`, AK1e) praktisch kostenlos aus. Bekannte False-Positive-Klasse (N2-Klasse, z. B. `Windows10E2` → S10E02) bleibt auf tv-klassifizierte Einträge beschränkt, weil `detectInboxGroups` vorab `media_type === "tv"` verlangt (`:12496`) — [advocatus] KOS1.
- **Konsequenzen:** Dokumentierte Verhaltensänderung (AK1d); keine Änderung an `js/parse.js`/`guessSeasonAndEpisode` (unerlaubte Datei, Präzedenz ADR-65-4).

### ADR-71a-4: Gruppierung: Ordner nur mit Feld-Set einbezogen, Schlüssel und S/E aus dem Dateinamen
- **Entscheidung:** `detectInboxGroups` (`app.js:12492–12515`) ändert die Filterlogik von „`is_dir === true` raus" auf „tv-Einträge rein, aber Ordner nur mit `single_video_relpath`"; Gruppenschlüssel = `item.is_dir === true ? item.single_video_query : item.suggested_query` (leer-Regel `:12498` unverändert); S/E = `extractStrictSeasonEpisode(basename(single_video_relpath)) || extractStrictSeasonEpisode(item.project)` (Entscheidung 3: Ordnername nur Ausweichweg). Gruppenpseudo-Eintrag, Sortierung, ≥2-Regel, Aggregation bleiben unangetastet.
- **Alternativen:** Ordnernamen als Schlüssel (**abgelehnt** — Entscheidung 3; gemischte Gruppe lose+Ordner würde nie verschmelzen, `ThWaDe` ≠ `The.Walking.Dead`); S/E nur aus dem Ordnernamen (**abgelehnt** — schlägt bei `XyzS01E01/Xyz.Show.S01E01.Titel.mkv`-Konstruktion fehl, wenn Ordnernamen und Dateiname unterschiedliche Staffeln tragen); Dateinamen-basierte `media_type`-Erkennung als Voraussetzung (**abgesagt via F1**, Abschnitt 4).
- **Begründung:** AK3 sichert die Byte-Identität der Schlüssel; damit entsteht die gemischte Gruppe (AK4b) automatisch ohne neuen Gruppierungscode.
- **Konsequenzen:** Bestehende Negativ-Tests (`:672–700`) bleiben gültig, weil Fake-Ordner ohne Felder weiterhin rausgefiltert werden ([advocatus] W4).

### ADR-71a-5: #72 Punkt 1 als reine Processor-Härtung (beide Prüfblöcke)
- **Entscheidung:** In `processor.py:969–978` (Subs) und `:988–997` (Renames), ausschließlich im `files_param is not None`-Zweig: `new` wird verworfen, wenn es `/` oder `\` enthält oder leer ist (nach bisherigem `if new_s:`-Guard zusätzlich `new_s is not None and new_s == "" → Abbruch`, [advocatus] KOS3). `old` darf weiterhin Unterordner enthalten (legitimes Hochziehen, `:1058–1068`, B7). Fehlermeldung benennt Eintrag und Grund (kein stilles Scheitern).
- **Alternativen:** Zusätzlich HTTP-400 in `queue_api.py` (**abgelehnt**, Abschnitt 4/Dissens 1); Prüfung per `os.path.basename(new) == new` (**abgelehnt** — [advocatus] W2: auf POSIX ist `\` kein Separator, der Backslash-Fall würde durchrutschen).
- **Begründung:** Die Prüfung verletzt keinen legitimen Client (`new` ist immer reiner Dateiname, `queue_api.py:568–569`, `:622–644`); der Processor ist der einzige Konsument von `explicit_*` und prüft vor jeder Bewegung.
- **Konsequenzen:** Manipulierte `files[]`-Jobs enden im Fehlerstatus statt fremdem Ordner; Aufträge ohne `files[]` bleiben byte-genau unverändert (Entscheidung 7).

### ADR-71a-6: UI = Checkbox-Parität plus Tooltip/aria, keine neuen Zeilen-Elemente
- **Entscheidung:** Einzelvideo-Ordner zeigen die Checkbox exakt wie Einzeldateien (Position links, `isProcessing`-disabled-Analogie `app.js:13133`), mit `aria-label="Ordner mit einer Folge auswählen"` und `title="Verarbeitet wird: <single_video_relpath>"` ([grafiker] übernommen). Name bleibt `item.project` (Ordnername), Meta-Zeile bleibt „N Datei(en) · Größe · Datum" (`:13109–13119`). Aufgeklappte Gruppenmitglieder zeigen Ordnernamen + SxxExx-Badge aus `_se` (Struktur `:13019–13033` unverändert). Mehrvideo-Ordner: kein Hinweis (bewusst still, #71-Vollausbau ist der Folgeschritt). Film-Ordner ohne `SxxExx`: unveränderter Ist-Zustand inkl. Film-Sperre (`:13139–13145`) — F1-Absage akzeptiert ([grafiker] Punkt 4: „stiller Zustand reicht").
- **Alternativen:** „1 Video"-Badge + Ordner-Icon + zweizeilige Mitglieder (**abgelehnt**, Abschnitt 4/Dissens 2); Zeilenklick → Checkbox togglen (**abgelehnt** — bräche das bestehende Projekt-Öffnen, `:13178–13179`).
- **Begründung:** Der Nutzer unterscheidet Ordner am Namen und am Fehlen/Auftauchen der Checkbox; Tooltip erklärt, WAS verarbeitet wird. Minimale Diff-Fläche schützt den Review-Engpass.
- **Konsequenzen:** `style.css` bleibt unerlaubt (alles über bestehende Klassen/Inline-Muster); `index.html` nur Cache-Buster.

### ADR-71a-7: Ein Gate-A2-Lauf (Server + Frontend + Processor zusammen)
- **Entscheidung:** Ein Lauf mit einer Erlaubnisliste (Abschnitt 11), nicht zwei wie bei #65.
- **Alternativen:** Server-Lauf A + UI-Lauf B (**abgelehnt** — die #65-Schnittlogik „Server zuerst, UI darauf" greift hier nicht: die UI-Änderungen sind ohne die zwei Felder nicht testbar und die Felder ohne UI folgenlos; der Gesamt-Diff bleibt klein (zwei Payload-Zeilen, vier app.js-Funktionsstellen, zwei processor.py-Blöcke, Tests) und bleibt unter der 120-KB-Reviewer-Grenze); Antigravity direkt (**abgelehnt** — Präzedenz #65: Gate-A2 mit fester Erlaubnisliste und Übergabe-Pflicht).
- **Begründung:** Alex-Entscheidung 6 ist bindend („ein Gate-A2-Lauf").
- **Konsequenzen:** Ein Review, ein Merge, eine AK0-Messung; Nahtstellen-Risiko (Backend↔Frontend-Vertrag) wird durch AK3/AK5b/c im selben Lauf gemeinsam getestet — besser als über zwei Läufe verteilt.

## 6. Dissens & Risiken

**Dissens 1 — Ort der `new`-Prüfung (entchieden gegen [advocatus]):** [advocatus] W2 forderte die Prüfung zusätzlich früh in `queue_api.py` `/process`, damit manipulierte Anfragen sofort HTTP 400 statt asyncem Job-Fehler erhalten. **Verworfen:** `queue_api.py` liest `explicit_renames`/`explicit_subs` heute nirgends (grep-verifiziert); die bestehenden `new`-Prüfungen (absolut/`..`/Ausbruch, `processor.py:970–974`, `:989–993`) sitzen ebenfalls nur dort. Ein neuer Validierungsstrang müsste das Parsing duplizieren (vierte und fünfte `files[]`-Zweigstelle) ohne zusätzlichen Schutz — der Abbruch erfolgt vor jeder Dateibewegung (`:947–997` vor `:999+`). Restrisiko bleibt: manipulierter Job wird erst im Worker laut fehlerhaft statt mit 400 abgewiesen — kein Datenrisiko, dokumentiert.

**Dissens 2 — UI-Differenzierung des Ordner-Eintrags (entchieden gegen [grafiker]):** [grafiker] schlug „1 Video"-Badge (grün), Ordner-Icon (Lucide `folder`) und zweizeilige Mitgliederliste (Ordnername + interner Dateiname muted) vor. **Verworfen:** Die Meta-Zeile zeigt bereits „1 Datei(en)" (`app.js:13109`); ein Icon für alle Ordnerzeilen und eine umgebaute Mitgliederliste vergrößern Diff, CSS-Fläche und Testfälle, ohne das Verhalten zu ändern — bei einer Reviewer-Prompt-Grenze von ~120 KB und Alex als einzigem Reviewer ist Minimalität hier Produktentscheidung. **Übernommen:** Checkbox-Parität, `aria-label`, `title`-Tooltip („Verarbeitet wird: …"). Falls der Handtest (Abschnitt 12) Verwirrung zeigt, ist das Badge ein Nachzug — kein Blocker.

**Dissens 3 — linke Regex-Seite (entchieden mit [produktberater], seit Korrekturrunde 2b verbindlich):** Die Kickoff-Entscheidung 1 nannte die rechte Seite `(?!\d)`; die linke Seite war im Kickoff-Prompt mit der Regel „Buchstabe oder Trennzeichen" benannt („Vor `S\d{1,2}E\d{1,3}` ist zusätzlich ein Buchstabe erlaubt") — die linke Trennzeichen-Pflicht ist die eigentliche U1-Ursache. [produktberater] zeigte in Akt 2 auf, dass `(?<!\d)` („alles außer einer Ziffer") robuster ist: es schließt ziffernpräfixierte False-Positives wie `Show.1080S02E03` aus, die unter der Buchstabe-oder-Trennzeichen-Regel durchrutschen würden. **Auflösung:** Alex ist dieser Empfehlung in der Korrekturrunde 2b gefolgt (wörtlich 2026-10-12: „Korrekturrunde 2b wie empfohlen, starte sie") und hat die ursprüngliche Regel „Buchstabe oder Trennzeichen" durch „alles außer einer Ziffer" ersetzt; die Form `/(?<!\d)[sS](\d{1,2})[eE](\d{1,3})(?!\d)/i` ist damit verbindlich in ADR-71a-3 festgeschrieben (nicht mehr „Empfehlung" oder „Worker-Entscheidung"). Verworfene Alternativen: linke Gruppe ganz streichen, `[a-zA-Z]`-Alternative.

**Dissens 4 — Auswahl-Key (entschieden nach [grafiker], gegen [advocatus] K1-Variantenvorschlag):** Set bleibt über `item.project` keyed; [advocatus] hatte alternativ „relpath oder Map" genannt. Begründung: `isProcessing`-Guard und drei bestehende Tests hängen am project-Key; die Übersetzung an einer zentralen Stelle (ADR-71a-2) erfüllt denselben Sicherheitszweck.

**Verbleibende Risiken (dokumentiert, nicht blockierend):**
- **N2-Verhaltensänderung global:** `…S01E01PROPER…`-artige Namen matchen künftig (AK1d); False-Positive-Klasse bleibt auf tv-Einträge beschränkt ([advocatus] KOS1). Einziger Nutzer ist `detectInboxGroups` — kein manueller Titel-Pfad betroffen.
- **N3-Bekannte Grenze:** Ordner, deren einzige Videodatei `.flv`/`.m2ts`/`.3gp`/`.wmv` ist, erscheinen nie in der Inbox (6er-Liste, `project_api.py:1321`, `:1345–1346`) — Feld kann dort nie greifen. Listen-Bündelung ist #72 Punkt 8, bewusst nicht hier.
- **W3 Show-Level-Dateien:** `tvshow.nfo`/`poster.jpg` auf Ordner-Ebene bleiben im Ordner zurück (nur `<stem>.*`-Begleiter werden bewegt, `helpers.py:902–911`). Kein Datenverlust; Ordner bleibt ohnehin liegen (Entscheidung 4).
- **W5 30-s-Cache-Fenster:** Nach dem Listing neu abgelegte zweite Videodatei → Job verarbeitet nur das deklarierte Einzelvideo, zweites bleibt liegen; gelöschte/verschobene Datei → Fehlerstatus (TOCTOU-Check `processor.py:947–951` deckt relpaths unverändert ab, `validate_group_files` prüft Existenz `helpers.py:848–849`).
- **Namens-Kollision Ordner X + Datei X:** project-keyed-Set kann sie theoretisch nicht unterscheiden ([grafiker] Risiko 2) — in der Inbox-Struktur praktisch ausgeschlossen; bewusst akzeptiert.
- **#72 Punkt 7 (Client `\d{1,3}` vs. Server `\d{1,2}`):** bleibt bestehen ([advocatus] KOS2), nicht im Scope; Episoden ≥100 werden client-seitig erkannt, Server-`tv_pattern` kürzt — kein Crash, mappings-S/E kommen aus dem Matching-UI und sind serverseitig nicht mustervalidiert.
- **Kein E2E-Test gegen echten Server:** Frontend-Tests mocken `fetch` (Präzedenz #65 Restrisiko) — Abhilfe ist der Pflicht-Handtest (Abschnitt 12), nicht optional.
- **B4 bleibt Bestehen:** ohne Provider-Auswahl nutzt der Manuell-Fallback den Gruppennamen (jetzt korrekt aus `single_video_query`); TMDB/TVDB-Auswahl überschreibt weiterhin (`app.js:3280–3283`) — unveränderte, korrekte Realität.

**Dissens-Dokumentation Rohoutputs:** Die ungekürzten Antworten von [produktberater], [advocatus] und [grafiker] archiviert Claude Code mechanisch per `opencode export` in diesen Ordner (Rollen-Dateien). Alle Rollenzitate dieses Briefings sind erst mit den archivierten Rohoutputs voll belegbar (IOU wie bei `briefing-65.md`, Abschnitt 6).

## 7. Quellen, Referenzen & Lizenzen

- Kein Third-Party-Code, keine neuen Assets/Fonts/Icons. Verwendete Lucide-Inline-SVG-Muster (ISC) sind bereits im Projekt vorhanden (`app.js:13094–13104` Badges); es werden keine neuen Icon-Sets eingeführt.
- Referenz-Apps nur als Muster, nicht kopiert: macOS Finder, Jellyfin, Synology Download Station ([grafiker], Akt-2-Konsultation).
- Interne Referenzen: `ROADMAP.md:1967–1987` (#71), `ROADMAP.md:1996` (#72 Punkt 1), `docs/sessions/2026-10-12-inbox-ordnerfolgen/00-kickoff.md` (B1–B7, Entscheidungen 1–7, N1–N4), `docs/sessions/2026-10-08-roadmap64-65-inbox/briefing-65.md` (Key-Vertrag V1, Gate-A2-Format Abschnitt 11, Erfahrungswerte), `docs/sessions/2026-10-12-inbox-ordnerfolgen/ak0-ausgangsmessung.md` (Claude Code, vor dem Lauf).

## 8. Offene Fragen

1. **Alex-Go für den scharfen Gate-A2-Lauf** (Klasse B je Kette) nach Freigabe dieses Briefings. Verbindliche Reihenfolge siehe Abschnitt 11 „Freigabe- und Merge-Pfad" (P1): Freigabe → AK0 → Gate-A2-Lauf → Plausibilitätsprüfung (Claude Code) → **Rückkanal-Abnahme durch das Planungsteam (Pflicht)** → Patch-Übernahme/Commit → **Handtest nativ arm64 vor dem PR-Merge** → Push/PR → Merge (Klasse C) → grüne Main-CI → NAS-Update (Klasse C) → Live-Test Staffel 11. AK0 liefert Claude Code vorher in `ak0-ausgangsmessung.md`.
2. **F1-Folgepunkt in ROADMAP #71:** schreibt Claude Code (nicht dieser Lauf, nicht der Worker — `ROADMAP.md` ist unerlaubt).
3. **NAS-Livetest-Termin:** erst Staffel 11 per Auswahlkästchen (Abschnitt 12); beaufsichtigt von Alex, zeitlich nach Merge + CI-Build.

Keine inhaltlichen Blocker offen; design-frage- und sicherheits-frage-Eskalationen sind mit den bindenden Entscheidungen 1–7 und F1-Absage beantwortet.

## 9. Aufwand (KI-Implementierung vs. menschlicher Engpass)

- **KI/Pipeline (schnell):** ein Gate-A2-Lauf; realistisch 1–2 Runden (Diff klein: zwei Payload-Zeilen serverseitig, vier Funktionsstellen `app.js`, zwei Prüfblöcke `processor.py`, drei Testdateien, ein Cache-Buster).
- **Menschlicher Engpass (Alex, der Takt):** AK0-Beleg zur Kenntnis; Review des Gesamt-Diffs (Server + UI + Processor in einem PR — bewusst kleiner als bei #65); **Handtest nativ arm64 VOR dem PR-Merge** (~20–30 min mit vorbereiteten Testdaten); Merge (Klasse C); danach NAS-Update (Klasse C) und NAS-Livetest Staffel 11 (~15 min, beaufsichtigt). Vor der Patch-Übernahme liegen zwei Pflicht-Schritte, die nicht Alex' Zeit kosten, aber einen Nachbesserungslauf auslösen können: Plausibilitätsprüfung durch Claude Code und Rückkanal-Abnahme durch das Planungsteam (Abschnitt 11). Grob 45–60 min Menschenzeit, nicht Laufzeit.

## 10. Git-Zustand

Geliefert von Claude Code im Kickoff (wörtlich übernommen; ich habe `bash: deny` und habe in dieser Session keinen Git-Befehl ausgeführt — und auch keine Git-Schreiboperation vorgenommen):

```
## feat/inbox-gruppe-ordnerfolgen...origin/main [ahead 1]
fc75466 docs: mark ROADMAP #64/#65 done, add native ARM64 test variant (#73), document emulation hang
17b96d1 feat(inbox): group series episodes in the smart inbox (ROADMAP #65, run B) (#150)
dd65244 feat(inbox): server-side files[] group processing (ROADMAP #65, run A) (#149)
```

Feature-Branch, kein main-Stop. Arbeitsverzeichnis: `/Users/alex/Documents/Medienwerkzeug/.worktrees/feat-inbox-gruppe-ordnerfolgen`. Diese Session schreibt ausschließlich unter `docs/sessions/2026-10-12-inbox-ordnerfolgen/` (dieses Briefing, `ALEX_ZUSAMMENFASSUNG.md`, Rohoutput-Archivierung durch Claude Code). Der Gate-A2-Lauf läuft in eigener Clone/Workspace der Kit-Pipeline (Branch-Vorschlag `feat/inbox-single-video-folder-grouping`), Patch-Übernahme/Commits/PRs bleiben bei Claude Code nach Alex-Go.

## 11. Worker-Auftrag (Gate-A2-Pipeline, ein Lauf)

**Kontext:** Briefing-Abschnitte 3–7 sind verbindlich; AKs sind Testfälle, keine Wünsche. `test_cmd` identisch zu `docs/sessions/2026-10-08-roadmap64-65-inbox/briefing-65.md` Abschnitt 11 (ohne eigenes `timeout`; Pipeline-Limit `test_timeout_s` = 600 wegen der pip-Installation):

```bash
python3 -m pip install -q --user --break-system-packages -r requirements.txt pytest && python3 -m pytest -q -p no:cacheprovider --deselect tests/test_utils.py::TestMediawerkzeugLogic::test_conversion_estimation_test_encode && npm run test:frontend
```

```text
Einzelvideo-Ordner in der Smart Inbox: gruppierbar, anhakbar, files[]-Uebergabe;
Folgen-Regex ohne Trennzeichen; new-Ziel-Haertung bei files[]-Jobs —
ROADMAP #71 Teilmenge + #72 Punkt 1 (ein Lauf, Server UND Oberflaeche).

Kontext: gui/api/project_api.py get_inbox_suggestions() (:1299-1508) liefert das
Payload-Dict (:1490-1503, traegt bereits is_dir :1502); 6er-Liste video_exts
(:1321), rekursiver os.walk (:1333-1340), video_count==0 -> skip (:1345-1346);
tv_pattern + suggested_query-Pipeline (:1413-1421, :1438-1440); 30s-Cache
(:1303-1305). gui/core/helpers.py: GROUP_VIDEO_EXTENSIONS 10er-Liste (:798),
validate_group_files (:801-867, lehnt Ordner :851-852), find_group_companion_files
(:870-918, sucht im Video-Ordner, Praefix <stem>.). gui/static/app.js:
extractStrictSeasonEpisode (:12477-12490, Muster Zeile :12479, einziger Aufrufer
detectInboxGroups :12499, globalThis-Export :13234), detectInboxGroups
(:12492-12515), buildGroupedInboxSuggestions (:12517+), Banner-Apply files-Mapping
(:12630), detectManualGroupSeriesName (:12641-12661, :12645 strippt Ordneranteil),
Bulk-Bar + fallbackName (:12663-12721, Lookup :12706), Gruppen-Knopf (:13065-13083),
Checkbox-Eligibility isTvSingle (:13126-13135), Auswahl-Set selectedInboxProjects
ueber item.project (:13192-13202), isProcessing processingSet (:13121).
gui/workers/processor.py: files[]-Zweig (:870-884), Scope-/TOCTOU-Checks
(:947-997, subs new :969-978, renames new :988-997), Rename-Ausfuehrung
(:1058-1068), Leere-Ordner-Cleanup nur ohne files (:1084-1091, :1717).
gui/api/queue_api.py konsumiert explicit_* NICHT (nur files/mappings :73-95,
:815-833). Cache-Buster: index.html :2760 app.js?v=99, neun Importe app.js:1-9.

NUR diese Aenderungen:
1. project_api.py: im bestehenden Walk-Durchlauf Videodateien ZUSAETZLICH nach
   GROUP_VIDEO_EXTENSIONS (10er-Liste) zaehlen (import aus helpers; video_count/
   6er-Liste UNVERAENDERT). Nur Ordner (is_dir) mit exakt 1 Treffer der 10er-Liste
   erhalten zwei additive Payload-Felder:
   - single_video_relpath = os.path.relpath(vollpfad, inbox_dir) (Unterordner-
     Pfade erlaubt, Posix-Separator wie os.walk/os.path.relpath liefert),
   - single_video_query = tv_pattern-Pipeline gegen den DATEINAMEN (inkl.
     Extension, identische Schritte wie :1417-1421 + :1438-1440: search,
     Praefix, strip(' ._-'), clean_show_name); bei tv_pattern-kein-Treffer am
     Dateinamen: fallback auf den Eintrags-suggested_query des Ordners.
     Lose Dateien und 0/≥2-Videos-Ordner: Keys gar nicht erst setzen.
     media_type-Erkennung UNVERAENDERT (F1 abgesagt).
2. app.js extractStrictSeasonEpisode (:12479): Muster (a) — das bestehende
   Muster ERSETZEN durch die BINDende Form
   /(?<!\d)[sS](\d{1,2})[eE](\d{1,3})(?!\d)/i (linke Trennzeichen-Pflicht
   entfaellt, ersetzt durch (?<!\d); rechte Seite (?:[._\s\-\]]|$) -> (?!\d)).
   Die Form ist verbindlich (Alex, Korrekturrunde 2b) — keine
   Worker-Entscheidung. Verbindlich zusaetzlich die AK1-Faelle (a-f).
   js/parse.js nicht anfassen.
3. app.js detectInboxGroups (:12492-12515): tv-Ordner nur mit
   single_video_relpath einbeziehen; Schluessel = single_video_query (Ordner) bzw.
   suggested_query (Datei); S/E zuerst gegen basename(single_video_relpath),
   bei null gegen item.project. Leere-Schluessel/Sentinel-Regeln bleiben.
4. app.js neue Hilfsfunktion inboxFilesEntryForItem(item):
   is_dir===true und single_video_relpath vorhanden -> single_video_relpath,
   sonst item.project. Nutzen in: Banner-Apply (:12630), Gruppen-Knopf (:13075),
   Bulk-Weg (:12698 — dort ueber die Items aus currentSmartInboxRawSuggestions
   mappen; selectedInboxProjects bleibt project-gekeyed). fallbackName-Lookup
   (:12706) ueber das Item (nicht den files-String) fuehren und
   single_video_query VOR suggested_query bevorzugen.
5. app.js Checkbox-Eligibility (:13126): isTvSingle erlauben fuer
   media_type==="tv" und (is_dir===false ODER (is_dir===true und
   single_video_relpath vorhanden)). Checkbox bei Ordnern mit
   aria-label="Ordner mit einer Folge auswählen" und
   title="Verarbeitet wird: <single_video_relpath>". Keine neuen Badges/Icons,
   keine Mitgliederlisten-Umbauten, style.css und index.html-Struktur bleiben
   unveraendert.
6. processor.py (nur files[]-Zweig :947-997): In beiden new-Pruefungen
   (subs :969-978, renames :988-997) zusaetzlich verwerfen, wenn new '/' oder
   '\' enthält oder der leere String ist (new is not None and new == "").
   old bleibt unveraendert erlaubt inkl. Unterordner (Hochziehen :1058-1068).
   LAUTer Abbruch mit Eintrag + Grund VOR jeder Bewegung. Keine Aenderung an
   queue_api.py, helpers.py, Cleanup-Logik (:1084-1091, :1717 bleibt wie
   gegeben: Ordner bleibt liegen).
7. Cache-Buster: index.html:2760 und ALLE neun app.js:1-9-Importe v99 -> v100.

Akzeptanzkriterien (Tests: tests/test_inbox_suggestions.py NUR ergaenzen
(AK2/AK3), tests/test_inbox_group_files.py NUR ergaenzen (AK6/AK7),
tests/frontend/inbox_group.test.js NUR ergaenzen (AK1/AK4/AK5); bestehende
Faelle unveraendert lassen — insbesondere :661-667, :672-700, :968-995,
:1067-1092 bleiben gruen):
- Es prüft, dass ThWaDeS11E23 -> S11E23 matcht, ThWaDeS11E24720p -> null,
  Show.1080S02E03.mkv -> null, shows01e02.mkv -> S01E02, die vier bestehenden
  Null-Faelle null bleiben, die bestehenden Positiv-Faelle matchen und
  ...S01E01PROPER... kuenftig matcht (AK1a-f).
- Es prüft, dass ein Ordner mit genau einer 10er-Videodatei
  single_video_relpath (inkl. Unterordner-Fall Ordner/Sub/Datei.mkv) und
  single_video_query liefert; ein Ordner .mp4+.wmv (2 nach 10er, 1 nach 6er)
  KEINE Felder liefert; ein Ordner mit nur .flv/.wmv weiterhin gar nicht
  erscheint; video_count und alle Bestandsfelder unveraendert bleiben
  (AK2a-e).
- Es prüft, dass single_video_query byte-identisch zum suggested_query der
  Einzeldatei-Pipeline auf denselben Dateinamen ist, und dass ein Dateiname
  ohne SxxExx auf den Ordner-suggested_query faellt (AK3).
- Es prüft, dass lose Datei The.Walking.Dead.S11E24.mkv und Ordner
  ThWaDeS11E23/The.Walking.Dead.S11E23.mkv EINE gemischte Gruppe bilden
  (Schluessel-Gleichheit), dass S/E am Ordner zuerst aus dem Dateinamen kommt
  (Ausweichweg Ordnername getestet), und dass Ordner ohne single_video_relpath
  nie gruppiert werden (AK4a-e).
- Es prüft, dass ein Einzelvideo-Ordner eine aktive Checkbox erhaelt
  (aria-label + title-Tooltip gesetzt), ein tv-Ordner ohne Feld, Doku- und
  Film-Ordner keine erhalten, und dass in ALLEN Uebergabepfaden (Bulk,
  Banner, Gruppen-Knopf) files[] fuer Ordner exakt den single_video_relpath
  enthaelt, fuer Dateien den project-Namen; mappings-Schluessel ==
  files-Strings; Auswahl-Set bleibt project-gekeyed und uebersteht Re-Render/
  Sortierung; Bulk-Gruppenname aus single_video_query/innerem Dateinamen
  entsteht (The.Walking.Dead, nicht ThWaDeS) (AK5a-e).
- Es prüft im tmp-Inbox-Aufbau XyzS01E01/Xyz.Show.S01E01.Titel.mkv +
  Begleiter .de.srt + Fremddateien (nicht-Video) + Show-Level tvshow.nfo,
  dass ein files[]-Job (Eintrag = relpath) nur Video + <stem>.*-Begleiter
  bewegt, Fremd-/Show-Level-Dateien und den Ordner selbst unangetastet
  laesst (Ordner existiert nach Job) (AK6).
- Es prüft, dass bei files[]-Jobs new mit '/', '\', './x.mkv' und new=""
  den Job laut abbrechen, bevor etwas bewegt wird, und dass old aus dem
  Unterordner mit reinem new-Dateinamen weiter funktioniert (AK7).
- Es prüft, dass alle Pfade ohne files[] unveraendert bleiben (bestehende
  Suite gruen), die Payload nur additiv waechst und media_type sich nicht
  aendert (AK8).
- cache_busting.test.js bleibt gruen (v100); git diff --check sauber; Tests
  nur in tmp-Verzeichnissen; KEINE echten Timer stehen lassen (app.js-Timer
  stubben/abräumen — Erfahrungswert #65 Lauf B); keine Secrets; .env wird
   nie gelesen.

ERLAUBTE DATEIEN (ausschliesslich):
gui/api/project_api.py (nur die additive Einzelvideo-Logik), gui/static/app.js,
gui/static/index.html (nur Cache-Buster v100), gui/workers/processor.py (nur
die zwei new-Pruefungen), API.md (zwei neue Payload-Felder + new-Regel bei
files[]), tests/test_inbox_suggestions.py (nur ergaenzen),
tests/test_inbox_group_files.py (nur ergaenzen),
tests/frontend/inbox_group.test.js (nur ergaenzen).

NICHT ANFASSEN (auch nicht "nebenbei"): gui/core/helpers.py,
gui/api/queue_api.py, gui/static/style.css, gui/static/js/** (inkl. parse.js),
ROADMAP.md, STAND.md, VERLAUF.md, docs/** (inkl. docs/sessions/**),
scripts/**, package.json, pytest.ini, uebrige gui/**, uebrige tests/**
(nur die drei erlaubten Ergaenzungen), .env (nie lesen), data/**.
Diff klein halten — Reviewer-Prompt-Grenze ca. 120 KB; Trailing Whitespace
vermeiden.
```

**Schritt 0 vor dem ersten Code-Diff:** Basis ist `origin/main` @ `17b96d1` (#65 Lauf A+B gemergt; der docs-only-Head `fc75466` des Session-Worktrees ist nicht Teil der Worker-Basis). Verifikation: Payload enthält `is_dir` (`project_api.py:1502`), `/preview_process`/`/process` akzeptieren `files` (`queue_api.py:73–95`, `:815–833`), `app.js?v=99` an `index.html:2760` und allen neun Importen. Bei Abweichung: STOPP + Rückmeldung an Claude Code/Alex — AKs werden NICHT autonom angepasst (Planänderung = Freigabepunkt).

**Pflicht: feste Liste WÖRTLICHER Rohausgaben bei der Übergabe** (keine rekonstruierten Belege; jede Ausgabe mit Exit-Code), Muster `briefing-65.md` Abschnitt 11c: `git status --short --branch`; `git log --oneline -5`; `git diff --stat <basis>..HEAD`; `git diff --check <basis>..HEAD`; volle Ausgabe + Exit des pytest-Teils von `test_cmd`; volle Ausgabe + Exit von `npm run test:frontend`; `git diff --stat` je eigenem Commit.

**Freigabe- und Merge-Pfad (verbindliche Reihenfolge, Alex-Vorgabe zu Beginn der Kette, P1):** (1) Briefing-Freigabe (Freigabepunkt 2, Alex). (2) AK0-Ausgangsmessung durch Claude Code im Worker-Image (`ak0-ausgangsmessung.md`) — kein Testlauf auf dem Host. (3) Start des scharfen Gate-A2-Laufs: Alex-Go (Klasse B je Kette). (4) **Plausibilitätsprüfung durch Claude Code:** erlaubte Dateiliste, `git diff --check`, volle Suite im Worker-Image, neue Tests gegen alten Stand rot, gezielte Gegenprobe. (5) **Rückkanal-Abnahme durch das Planungsteam (Pflicht):** `rueckkanal.md` mit `ABNAHME: JA|NEIN`; bei `NEIN` Gate-A2-Nachbesserungslauf, danach Schritte (4)–(5) erneut. (6) Patch-Übernahme/Commits durch Claude Code, nur auf Alex' separate Anweisung — nie durch den Worker. (7) **Handtest nativ arm64 in OrbStack VOR dem PR-Merge** (Image vom Branch-Stand, Abschnitt 12). (8) Push/PR durch Claude Code. (9) Merge — Klasse C, nur Alex. (10) Grüne Main-CI. (11) NAS-Update — Klasse C. (12) Live-Test Staffel 11 (Abschnitt 12). ROADMAP-Status #71/#72 erst nach Merge (und gehört nicht in diesen Worker-Lauf).

## 12. Handtest-Liste + Live-Test

**Handtest nativ arm64 in OrbStack — VOR dem PR-Merge** (Schritt 7 im Abschnitt 11 „Freigabe- und Merge-Pfad"; Image vom Branch-Stand; kein x86-Emulationshang — ROADMAP-#73-Notiz im Kickoff-Commit `fc75466`), mit künstlichen Testdaten in einer tmp-Inbox (keine echten NAS-Daten):

1. `XyzS01E01/Xyz.Show.S01E01.Titel.mkv` + Begleiter `Xyz.Show.S01E01.Titel.de.srt` + Fremddatei `XyzS01E01/info.nfo` + Bild `XyzS01E01/cover.jpg` + Show-Level `XyzS01E01/tvshow.nfo` → Ordner erscheint, hat Checkbox, Badge „Serie", Tooltip zeigt den inneren Pfad.
2. `XyzS01E02/Xyz.Show.S01E02.Titel.mkv` + `.de.srt` → zweiter Einzelvideo-Ordner.
3. `XyzS02E01/Xyz.Show.S02E01.mkv` + `XyzS02E01/sample.mkv` (ZWEI Videos) → KEINE Checkbox, nicht gruppierbar (Mehrvideo-Grenze, #71-Vollausbau bleibt offen).
4. Lose Datei `Xyz.Show.S01E03.Titel.mkv` (dieselbe Serie) → muss mit 1+2 zu EINER Gruppe zusammengefasst werden (gemischte Gruppe, AK4b); aufgeklappt: drei Mitglieder mit S01E01–E03-Badges.
5. Ziffern-Fall-Ordner `XyzS11E24720p/Xyz.Show.S11E24.mkv` → Ordnernamen-Muster null (AK1b): der kryptische Ordnername darf weder Schlüssel noch S/E liefern. Erwartetes, KORREKTES Ergebnis: der Ordner fällt über den Dateinamen (Schlüssel `Xyz.Show` mit Punkten, B3-Nuance; S/E = S11E24) in dieselbe Seriengruppe wie die S01-Folgen — Sichtprüfung: Mitglied mit Badge S11E24 in der `Xyz.Show`-Gruppe, keine Extra-Gruppe nach Ordnernamen, kein Absturz.
6. Alle Ordner + lose Datei anhaken → „Ausgewählte als Serie verarbeiten" → Titel-Feld zeigt `Xyz.Show`-Serie (nicht `XyzS…`), Modal-Mitgliederliste zeigt relpaths, `files[]`/`mappings` im Payload identische Strings (DevTools) → Job starten → prüfen: Videos + `.de.srt` wandern in `Output/Serien/…`, `info.nfo`/`cover.jpg`/`tvshow.nfo` bleiben im jeweiligen Ordner, Ordner existieren weiter (Entscheidung 4), Inbox-Listung blendet leere Ordner aus (`video_count 0`), `sample.mkv`-Ordner (3) bleibt komplett unverändert liegen.
7. Regression Sichtprüfung: ein Film-Ordner ohne `SxxExx` (z. B. `CD1/Ein.Film.2020.mkv`) verhält sich exakt wie heute (Badge „Film", keine Checkbox, Einzelverarbeitung möglich); ein Bestehender-Einzelauftrag ohne `files[]` (lose Filmdatei) läuft wie heute durch.

**Live-Test NAS (Schritte 10–12 des Abschnitts 11: nach Merge + grüner Main-CI + `docker compose pull && up -d`, Version via `app.js?v=100` bestätigt):** ZUERST NUR STAFFEL 11 (Alex-Entscheidung 6). Live-Bestand (lesendes NAS-Listing von Claude Code, 2026-10-12, P3): 173 Ordner `ThWaDeS01E01` … `ThWaDeS11E23` (Staffeln 1–11; Staffel 11 = 23 Ordner), je genau eine `.mkv` — keine losen Dateien dieser Serie, keine Untertitel/Begleiter, keine NFO, keine Samples, keine Unterordner. Daher: im NAS-Inbox-Listing **nur** die 23 Ordner `ThWaDeS11E*` per Auswahlkästchen wählen → EIN Auftrag → prüfen: 23 `.mkv` im Serienziel, Staffel 11; alle 23 Ordner `ThWaDeS11E*` liegen danach **leer** in der Inbox (es darf nichts weiter darin liegen — Begleiter existieren im Live-Bestand nicht); die Ordner Staffel S01–S10 (150 Ordner) sind unverändert (Vorher/Nachher-Listing); Job-Historie fehlerfrei. **Ziel-Erwartung (P4):** Ziel ist der auf dem NAS bereits vorhandene Serienordner „The Walking Dead (2010)" bzw. das, was `resolve_series_folder_name`/NAS-Match nach TMDB-Auswahl liefert — ein Treffer auf den vorhandenen Ordner ist **korrekt** (Namenskonflikt bekannt aus ROADMAP #46); ein neuer, abweichender Ordner (z. B. `ThWaDe` oder `The.Walking.Dead`) ist ein **Fehler**. Gemischte Gruppen und Begleiter-/Fremddateien werden im Live-Test NICHT geprüft (diese Fälle existieren im Live-Bestand nicht) — ausschließlich im Handtest oben. Erst nach diesem Erfolg: restliche Staffeln in mehreren Batches.

## Änderungen in Akt 2b (Korrekturrunde; Alex, wörtlich 2026-10-12: „Korrekturrunde 2b wie empfohlen, starte sie")

- **P1 — Ablauf:** Abschnitt 11 „Freigabe- und Merge-Pfad" nun als verbindliche 12-Schritte-Reihenfolge ausgeschrieben; Plausibilitätsprüfung durch Claude Code und Rückkanal-Abnahme durch das Planungsteam (`rueckkanal.md`, `ABNAHME: JA|NEIN`, bei NEIN Nachbesserungslauf) als Pflichtschritte ergänzt; Handtest ausdrücklich VOR den PR-Merge gezogen (Abschnitte 8, 9, 11, 12; Frontmatter-Absatz „Bindende Alex-Entscheidungen"; `ALEX_ZUSAMMENFASSUNG.md` offene Fragen 1–2).
- **P2 — Regex verbindlich:** ADR-71a-3 erklärt die Form `/(?<!\d)[sS](\d{1,2})[eE](\d{1,3})(?!\d)/i` für verbindlich (keine Worker-Entscheidung mehr); Begründungstext korrigiert (Kickoff-Prompt nannte links explizit die Regel „Buchstabe oder Trennzeichen"; Alex ersetzte sie auf Empfehlung durch „alles außer einer Ziffer"); Dissens 3 angepasst; AK1 um Fälle (e) Ziffer links → null (`Show.1080S02E03.mkv`) und (f) Kleinbuchstabe links → Treffer (`shows01e02.mkv`) ergänzt; Worker-Auftrag und AK-Zusammenfassung in Abschnitt 11 auf AK1a–f und die bindende Form aktualisiert.
- **P3 — Live-Bestand:** korrigiert auf 173 Ordner `ThWaDeS01E01`…`ThWaDeS11E23` (Staffeln 1–11, Staffel 11 = 23), je genau eine `.mkv`; keine losen Dateien, keine Begleiter/Untertitel, keine NFO, keine Samples, keine Unterordner (Abschnitte 1, 2, 12; `ALEX_ZUSAMMENFASSUNG.md`). „264 Staffel-Ordner", „verstreute lose Einzeldateien" und „`.de.srt` mitgewandert" sind gestrichen; gemischte Gruppen und Begleiter prüft ausschließlich der Handtest.
- **P4 — Live-Ziel:** Erwartung im Live-Test ist der vorhandene NAS-Ordner „The Walking Dead (2010)" bzw. das Ergebnis von `resolve_series_folder_name`/NAS-Match nach TMDB-Auswahl; Treffer auf den vorhandenen Ordner = korrekt, neuer abweichender Ordner (`ThWaDe`, `The.Walking.Dead`) = Fehler (Abschnitt 12; Stichproben-Hinweis in `ALEX_ZUSAMMENFASSUNG.md`).
- **Mikro-Korrektur (Konsistenz, keine Inhaltsänderung):** Abschnitt 3 Intro: Verweis auf die dokumentierte Verhaltensänderung „AK1c" → „AK1d" (die Verhaltensänderung ist Fall d).
- **plan-reviewer Runde 1: `VERDICT: APPROVE`** (keine Blocker, keine wichtigen Findings). Drei kosmetische Anmerkungen, Umgang dokumentiert: (1) Zähl-Diskrepanz „fünf vs. vier" Null-Erwartungen zwischen Kickoff N2 (`00-kickoff.md:90`, unveränderliche Referenz) und Briefing — bewusst kein 2b-Eingriff, die reale Zahl wird bei AK0/Plausibilitätsprüfung verifiziert und dann angeglichen; AK-Aussage und Ausführbarkeit bleiben davon unberührt. (2) `ALEX_ZUSAMMENFASSUNG.md` Frage 3 nannte die Regex-Form nur durch Akt-1-Entscheidungen abgedeckt — **behoben**: Korrekturrunde-2b-Zusage ergänzt. (3) API.md steht in der Erlaubnisliste mit klarem Zweck, aber ohne eigenen Änderungspunkt in der „NUR diese Aenderungen"-Liste — bestehend vor 2b, bewusst nicht geändert (abgefedert durch Plausibilitätsprüfung und Alex' Diff-Review); Empfehlung für künftige Worker-Aufträge: Doku-Dateien als expliziten eigenen Änderungspunkt führen.
