ABNAHME: JA

# Rückkanal-Review — Medienwerkzeug ROADMAP #89 (2026-10-22)

Einordnung: Dieser Rückkanal wurde von Claude Code (Reviewer/Vermittler) beauftragt, nicht von Alex.
Geprüft: Briefing `docs/sessions/2026-10-22-roadmap89-sample-ordner/briefing.md` (status: approved, Alex-Zitat vorhanden)
gegenüber dem aktuellen Worktree-Stand der sechs geänderten Dateien (`gui/core/helpers.py`, `gui/api/queue_api.py`,
`gui/api/project_api.py`, `API.md`, `tests/test_inbox_suggestions.py`, `tests/test_inbox_group_files.py`).
Konsultiert: `produktberater` (Nutzerwert/Vollständigkeit) und `advocatus` (Risiken/Edge-Cases) — Rohoutputs werden
 Separat exportiert (Claude Code); hier nur der SYNTHETEBestand mit Rollen-Zuordnung.
Grenzen dieses Laufs: keine Git-/Shell-Befehle, kein `.env`, keine Git-Verwaltungsdateien. Was dadurch nicht prüfbar
war, ist in Abschnitt 5 offen benannt.

Kurzbegründung des JA: Kein Befund ist [kritisch]. Alle acht ausführbaren Akzeptanzkriterien sind im aktuellen Stand
am Code belegt, die Rot-Probe-Logik ist intern widerspruchsfrei nachgerechnet, und die drei [wichtig]-Befunde sind
niedrig-realistisch, nicht datenzerstörend und gegenüber `f0a29a4` allesamt eine Netto-Verbesserung. Empfehlung an
Alex: Abnahme mit den in Abschnitt 4/5 genannten Begleitschlüssen (ein Einzeiler-Logging optional noch vor dem PR).

## 1. Prüfung gegen AK1–AK10

| AK | Status | Beleg im aktuellen Stand |
|---|---|---|
| AK0 | erfüllt | `ak0-ausgangsmessung.md`: 529 passed/1 deselected, Frontend 231/231, Exit 0, wörtliche Ausgabe + SHA-256. Nachgerechnet: 529 + 8 neue Tests (AK1–AK6 in `test_inbox_suggestions.py:299–515`, AK7/AK8 in `test_inbox_group_files.py:1164–1278`) = 537 wie gemeldet; Frontend unverändert 231 (passt zu „keine Frontend-Änderungen“). |
| AK1 | erfüllt | `tests/test_inbox_suggestions.py:299–336`: exakt das Lanterns-Muster (Folge 350 MB sparse, `Sample/`-Sample 68 MB, `.nfo`/`.sfv`, Werbeordner); Assertion `single_video_relpath = "XyzS01E01/Xyz.S01E01.Rel/xyz.s01e01.rel.mkv"` (:331–334), `single_video_query = "xyz"` (:335), `video_count == 2` (:336). |
| AK2 | erfüllt | `tests/test_inbox_suggestions.py:338–369`: Sample per Name UND per Pfadsegment, jeweils > 300 MB (Kriterium 1 dominiert die Größe). |
| AK3 | erfüllt | `tests/test_inbox_suggestions.py:371–387`: 350 MB + 50 MB ohne „sample“-Marke → Einzelvideo. |
| AK4 | erfüllt | `tests/test_inbox_suggestions.py:389–417` (zwei große, zwei kleine → kein `single_video_relpath`); Bestand `MixedFolder.S01` (`:203–249`) inhaltlich unverändert und logisch gegen die neue Regel nachgeprüft: zwei 100-Byte-Videos → keine Datei > 300 MB → Kriterium 2 kann nicht zünden → beide bleiben Nicht-Samples → Erwartung grün bleibt stichhaltig. |
| AK5 | erfüllt | `tests/test_inbox_suggestions.py:419–453`: nur-Sample per Name, nur-Sample per Pfad → kein `single_video_relpath`; einzelnes kleines Normalvideo bleibt Einzelvideo-Ordner (:449–453). |
| AK6 | erfüllt | Kombinierter analyze+preview-Test `tests/test_inbox_suggestions.py:455–515` (analyze-Teil rot-fähig, wie in ADR-89-5 nach Runde 1 verlangt). Hilfsfunktion enthält die Film-Regel ausdrücklich NICHT (`helpers.py:808` Docstring; Film-Regel bleibt in `queue_api.py:205–208`). Bestand `tests/test_movie_processing_fixes.py:160–211` (`test_sample_detection_in_preview`) unangetastet gelesen; Vorschau ruft dieselbe Funktion (`queue_api.py:194`). |
| AK7 | erfüllt | `helpers.py:799` (`GROUP_EXCLUDED_COMPANION_EXTENSIONS = ('.nfo', '.sfv')`) + `helpers.py:937` (case-insensitiv via `entry_lower`); benannte Einzige Änderung am Bestandstest exakt wie vorgeschrieben: `tests/test_inbox_group_files.py:137` jetzt `assertNotIn("Show.S01E01.nfo", …)`, Restblock unverändert; neuer Test `:1164–1186` deckt Groß-/Kleinschreibung (`.NFO`/`.SFV`) und Erhalt von `.de.srt` ab. |
| AK8 | erfüllt | End-to-End `tests/test_inbox_group_files.py:1188–1278`: `files[]`-Job mit `provider`/`show_id` (Metadaten gemockt :1257–1260), Episode + erzeugte Episoden-NFO im Serienziel (:1264–1266), Sample/Release-`.nfo`/`.sfv`/Werbeordner unverändert in der Inbox (:1269–1278). Kollisionsschutz `test_n1_nfo_target_collision_with_foreign_file_aborts_loudly` (`:768–803`) unverändert vorhanden. Mechanik am unveränderten Kontext verifiziert: Vorschau plante `<Titel>.nfo` als Extra (`queue_api.py:612–614`), Processor benannte vor der Schleife um (`processor.py:1078–1089`), Guard bricht ab (`processor.py:1568–1573`) — die gemeldete Rot-Meldung „Kollision beim Generieren von NFO“ passt exakt zu dieser Stelle. |
| AK9 | erfüllt | `API.md:146` beschreibt `single_video_relpath` als „einzige Videodatei nach Abzug von Samples“ mit beiden Kriterien; `API.md:270` hält fest, dass `<stem>.nfo`/`<stem>.sfv` nicht als Begleitdateien gelten und im Quellordner verbleiben; `API.md:265` (preview-process) gelesen: enthält keine Begleitdateien-Aussage, unverändert — wie von plan-reviewer Runde 2 festgelegt. |
| AK10 | teilweise erfüllt | Erfüllbar geprüft: Tests schreiben nur in `tempfile.TemporaryDirectory` (beide Test-Setups), große Dateien ausschließlich per `f.truncate(...)` (sparse), keine Test-Weichen im Produktivcode (neue Codepfade kennen keine Test-Env). `git diff --check` in diesem Lauf NICHT prüfbar (kein Git) — gilt als von Claude Code gemeldeter, hier nicht gegenverifizierter Beleg. |

Rot-Probe-Plausibilität (Lektüre-Nachrechnung, nicht erneut ausgeführt): AK1/AK2/AK3/AK5/AK6-Analyse-Teil wären gegen
`f0a29a4` zwingend rot (dort zählte `len(group_video_files) == 1` ohne Sample-Abzug), AK7/`test_find_group_companion_files`
wegen des damaligen `assertIn` auf die `.nfo`, AK8 wegen der U2-Kette; AK4 ist erwartbar grün (Bestandsschutz) — die
gemeldete Rot-/Grün-Verteilung ist damit in sich konsistent.

## 2. Bewertung der Hinweise (a)–(d)

(a) Pfadsegment „sample“ auf Inbox-relativem Pfad — Bestätigt, real niedrig [wichtig].
`project_api.py:1516` baut den Relativpfad zur Inbox, `helpers.py:820` prüft das Segment exakt (`"sample" in
path_segments` ist Listen-Mitgliedschaft, kein Substring). Ein Top-Level-Ordner, der literal `Sample`/`sample` heißt,
macht alle seine Videos zu Samples → kein `single_video_relpath` mehr (Verhaltensänderung ggü. `f0a29a4`). „Samples“,
„MySampleShow“ etc. triggeren NICHT; nur der exakt so benannte Ordner. Im Lanterns-Muster ist `Sample` immer
Unterordner (dort korrekt). Asymmetrie zur Vorschau: dort ist der Pfad relativ zum Projektordner, der Ordnername fehlt
als Segment [advocatus]. Empfehlung: akzeptieren, ROADMAP-Eintrag (Härtung: Projektordner-Segment ausnehmen).

(b) `os.path.getsize` je Videodatei — zwei Teile.
Kosten [kosmetisch]: `project_api.py:1511–1515` statet die 10er-Liste zusätzlich zum bestehenden 6er-`os.stat`-Zyklus
`:1368–1374`; der 30-s-Cache (`:1303–1305`) deckelt die Neuberechnung — der 6-s-Neuaufbau des Frontends trifft nur den
Cache. Die marginalen Extra-Stats sind klein gegen die bestehenden bis zu 10 ffprobe-Aufrufe je Ordner (`:1351–1357`).
Akzeptieren [advocatus, eigene Prüfung bestätigt].
Schweigender Fehler [wichtig]: `except OSError: gvf_size = 0` (`:1514–1515`) klassifiziert eine nicht statbare Datei
still als Sample (Kriterium 2), ohne `log_message` — anders als der direkt benachbarte Zyklus `:1373–1374`. Verletzt
die Hausregel „Fehler sichtbar“. Realismus sehr gering (stat-Fehler der Hauptfolge UND >300-MB-Sample müssen
zusammenfallen); keine Datenzerstörung, Datei bleibt in der Inbox liegen. Empfehlung: Einzeiler-Logging noch vor dem
PR (billig) oder ROADMAP-Follow-up — kein Abnahmeblocker.

(c) `.nfo`/`.sfv`-Ausschluss auf alle `files[]`-Aufträge — kein problematischer Fall gefunden [kosmetisch].
Show-level-Dateien (`tvshow.nfo`, `movie.nfo`) waren wegen der Stem-Präfix-Regel (`helpers.py:930`, `:942`) NIE
Companions — der Ausschluss trifft exakt `<stem>.nfo`/`<stem>.sfv`, also das Szene-Release-Muster von U2. Ein
selbsterzeugtes `<stem>.nfo` mitzunehmen wäre genau der Kollisionsfall, den der Guard `processor.py:1568–1573`
schützen muss; die App erzeugt Episoden-NFOs selbst. Dokumentiert in `API.md:270`, durch Alex' Entscheidung gedeckt
(Briefing §4: Variante A2 verworfen). Bestandtest `test_ak6_single_video_folder_job_execution`
(`test_inbox_group_files.py:1044–1096`) bestätigt unverändert, dass `movie.nfo`/`tvshow.nfo`/`poster.jpg` liegen
bleiben. Akzeptieren [advocatus, eigene Prüfung bestätigt].

(d) Kleingeschriebener Gruppenschlüssel „lanterns“ — nur Anzeige, kein Funktionsverlust [kosmetisch].
`project_api.py:1528–1532` zieht den Schlüssel aus dem (szeneüblich kleingeschriebenen) Dateinamen;
`clean_show_name` (`utils.py:23–30`) lowercasing findet nicht statt, es bleibt die Dateinamen-Kleinschreibung.
Gruppierung funktioniert, weil alle acht Ordner denselben Schlüssel liefern (`app.js:12538`); Profilsuche nutzt
`suggested_query` (`project_api.py:1446`), nicht `single_video_query` — unberührt; Anbieter-Suche ist
case-insensitiv; der NAS-Zielordnername entsteht aus dem Metadaten-Titel, nicht aus dem Schlüssel. Bleibende
Auswirkung: Banner zeigt „lanterns (8 Folgen)“ — im Briefing §6 bereits bewusst als außer Scope dokumentiert
[advocatus + produktberater, eigene Prüfung bestätigt].

## 3. Befunde (nach Schwere)

- [kritisch] — keine.
- [wichtig] B1 — Exaktes Inbox-Top-Level-Segment „Sample“ entzieht dem Ordner die Gruppierbarkeit (Neuer
  Fehlermodus ggü. `f0a29a4`). Stelle: `gui/api/project_api.py:1516` + `gui/core/helpers.py:820`. Realismus sehr
  gering. Empfehlung: akzeptieren, ROADMAP (Abschnitt 5, R1). [advocatus + eigene Verifikation]
- [wichtig] B2 — Stiller `OSError`-Pfad bei `getsize` → Größe 0 → Fehlklassifikation als Sample, ohne Log;
  widerspricht „Fehler sichtbar“ (Benachbarter Zyklus loggt). Stelle: `gui/api/project_api.py:1511–1515` vs.
  `:1368–1374`. Empfehlung: `log_message` ergänzen (Einzeiler, optional schon im PR) sonst ROADMAP (R2). [advocatus]
- [wichtig] B3 — Kriterium 2 frisst echte kleine Episoden (< 300 MB) neben großen (> 300 MB): Ordner wird
  gruppierbar, verarbeitet wird nur die große Folge, die kleine bleibt ohne Hinweis liegen. Gegenüber `f0a29a4`
  trotzdem Netto-Verbesserung (dort war der ganze Ordner blockiert) und wiederherstellbar (nach dem Umzug der
  großen Folge erscheint die kleine als normales Einzelvideo). Briefing §6 dokumentiert nur Kriterium 1 als „grob“,
  nicht Kriterium 2 — Lücke im Risikodokument. Stelle: `gui/core/helpers.py:822` + `gui/api/project_api.py:1524`.
  Empfehlung: akzeptieren, ROADMAP (R3) + Handtest-Punkt 5. [advocatus, produktberater (c)2]
- [kosmetisch] B4 — Doppel-Stats 6er-/10er-Liste (Kostenfrage, durch 30-s-Cache gedeckelt; Notiz nur falls Inbox
  auf hunderte Ordner wächst). Stelle: `gui/api/project_api.py:1511–1515`. [advocatus]
- [kosmetisch] B5 — „sample“-Kriterium-1-Logik bleibt an zweiter Stelle inline (`queue_api.py:222`) — Drift-Risiko
  bei künftigen Änderungen, heute verhaltensgleich. [advocatus]
- [kosmetisch] B6 — `video_count` (6er-Liste, `project_api.py:1321/:1347`) und Sample-Erkennung (10er-Liste,
  `:1342`) nutzen unterschiedliche Extensions-Sets: latente Anzeige-Inkonsistenz z. B. bei `.flv`-Sample; für
  Lanterns (.mkv) irrelevant. [produktberater]
- [kosmetisch] B7 — Testlücke: Lanterns-Muster im Nicht-`files[]`-TV-Vorschau-Pfad ungetestet (Samples enden dort
  implizit als Junk, weil kein Mapping existiert — bestehendes Verhalten, nicht Teil dieses Fixes).
  [produktberater]
- [kosmetisch] B8 — Anzeige „lanterns (8 Folgen)“ kleingeschrieben; bewusst außer Scope (Briefing §6).

## 4. Gesamtempfehlung

Abnahme JA. Der Fix adressiert beide belegten Ursachen (U1/U2) eng begrenzt, testseitig vollständig (AK1–AK8) und
dokumentiert (AK9); die Bestandsschutz-Tests (`MixedFolder.S01`, `test_sample_detection_in_preview`,
NFO-Kollisions-Guard) sind im aktuellen Stand unangetastet und logisch tragfähig. B2 ist der einzige Punkt, den ich
noch vor dem PR nachziehen würde (Einzeiler); B1/B3 gehören als ROADMAP-Einträge festgehalten, damit sie nicht
verloren gehen. Die vom produktberater empfohlene Priorisierung von ROADMAP #81 (Inbox-Reste aufräumen) teile ich:
nach diesem Fix ist der Nutzerpfad erkennbar, aber die Reste bleiben sichtbar liegen.

## 5. Zurückgestellt / ROADMAP-Kandidaten und nicht prüfbare Punkte

ROADMAP-Kandidaten (Vorschlag an Claude Code zur Aufnahme unter #89-Follow-ups):
- R1 (B1): Segment-Check der Sample-Erkennung vom Projektordner-Namen ausnehmen (Pfad relativ zum Projektordner
  statt zur Inbox prüfen).
- R2 (B2): `log_message` bei `getsize`-OSError in `project_api.py:1511–1515` (oder Einzeiler direkt im PR).
- R3 (B3): Kriterium 2 dokumentieren/nachschärfen — Hinweis, wenn ein Nicht-Sample-Video bei der Gruppenverarbeitung
  liegen bleibt.
- R4 (B5): `queue_api.py:222` ebenfalls auf `find_sample_video_files` umstellen (eine Quelle pro Regel).
- R5 (B6): 6er-`video_exts` und 10er-`GROUP_VIDEO_EXTENSIONS` in `project_api.py` vereinheitlichen.
- R6 (B7): Test für Nicht-`files[]`-TV-Vorschau mit Sample-Unterordner.
- Bestehende #81 (Inbox-Reste) gewinnt Dringlichkeit [produktberater].

In diesem Lauf nicht verifizierbar (Restrisiko, Belege stammen von Claude Code):
- Exakter Diff-Umfang `60366d5` vs. `f0a29a4` (kein Git). Indirekte Evidenz: die neuen Symbole
  (`find_sample_video_files`, `GROUP_EXCLUDED_COMPANION_EXTENSIONS`, `SAMPLE_SIZE_THRESHOLD_BYTES`) kommen laut
  Repo-Grep nur in `helpers.py`/`queue_api.py`/`project_api.py` vor; die unverändert zitierten Kontextstellen
  (`processor.py:1078–1089`, `processor.py:1568–1573`, `app.js:12527/:12537`) stimmen wortgleich mit dem Briefing.
- Suite-Ausgaben (537/231), Rot-Probe-Ausführungen, `git diff --check`, Probe-Instanz — nur plausibilisiert
  (Zahlenrechnung, Testlogik, Rot-Erwartungen), nicht erneut ausgeführt.
- Live-NAS-Verhalten (bleibt ohnehin eigener Schritt nach Merge mit Alex-Einzel-Go, Briefing §8).

## 6. Handtest-Prüfliste für Alex (lokal, max. 6 Punkte)

Vorbereitung wie Briefing §12: Wegwerf-Instanz mit drei `XyzS01E01…03`-Ordnern im Lanterns-Muster (Folge sparse
> 300 MB, `Sample/`-Clip < 300 MB, `<stem>.nfo`/`<stem>.sfv`, Werbeordner) plus ein Ordner mit zwei echten großen
Videos.

1. Inbox öffnen: alle drei Xyz-Ordner haben ein Auswahlkästchen und erscheinen gesammelt im Gruppenbanner
   („xyz (3 Folgen)“); Tooltip „Verarbeitet wird: …“ zeigt die Folgen-Datei, nicht das Sample.
2. Der Ordner mit zwei echten Videos: weder Kästchen noch Gruppenvorschlag.
3. ~15 s warten (6-s-Neuaufbau): Vorschlag und Kästchen bleiben stabil.
4. Gruppe starten → Vorschau: Sample, `<stem>.nfo` und `<stem>.sfv` tauchen nirgends als umzubenennendes Extra auf;
   Verarbeitung durchlaufen → kein „Kollision beim Generieren von NFO“, Folge + erzeugte Episoden-NFO im Serienziel,
   Sample/`.nfo`/`.sfv`/Werbeordner unverändert in der Inbox.
5. Grenzfall B3: ein Ordner mit großer Folge (> 300 MB) plus kleinem Video ohne „sample“-Marke (< 300 MB) → nur die
   große Folge gruppierbar, kleine bleibt liegen — bewusst ansehen und entscheiden, ob R3 priorisiert wird.
6. Grenzfall B1: Inbox-Ordner, der exakt „Sample“ heißt und eine Folge enthält → nicht mehr gruppierbar — prüfen,
   ob das für den eigenen Bestand relevant ist (eher nein).

— Ende des Rückkanal-Laufs. STOPP gemäß Auftrag; keine Git-Aktionen, kein Push, keine Subagent-Rohoutputs
abgeschrieben (Verbleib: Export durch Claude Code).
