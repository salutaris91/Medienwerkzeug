# Kickoff — Kreativteam-Session 2026-10-08: ROADMAP #64 (Inbox sortierbar) + #65 („Als Serie gruppieren")

> **Phase:** Akt 1 — Scope-Prüfung (read-only) gegen den Code in diesem Worktree, dann STOPP an Freigabepunkt 1.
> **Absender des Arbeitsauftrags:** Claude Code (Rolle Reviewer/Vermittler), NICHT Alex.
> **Alex-Entscheidungen** sind im Auftrag wörtlich zitiert (2026-10-08: „Ja, ich folge deinen Empfehlungen zu a–d") und werden hier nicht neu verhandelt.
> Alle Behauptungen aus dem Auftrag wurden read-only geprüft; jede ist unten mit Datei:Zeile belegt oder korrigiert.
> Diese Datei ist der einzige Schreibbeitrag von Akt 1. Die beiden Briefings und die Zusammenfassung folgen erst nach Alex' Antworten (Akt 2).

## 1. Rahmen — von Alex gesetzt (nicht zur Disposition)

1. EINE Session, ZWEI getrennte Briefings (`briefing-64.md`, `briefing-65.md`), EINE `ALEX_ZUSAMMENFASSUNG.md` mit Abschnitt je Item.
2. #64 zuerst, Ausführung über die Gate-A2-Pipeline (autonomer Worker im Container); briefing-64 braucht Abschnitt „Worker-Auftrag" (erlaubte Dateien, Nicht-anfassen-Liste, `test_cmd`-Vorschlag ohne eigenes `timeout`).
3. #65 erst NACH Merge von #64, neuer Branch von `main`, Ausführung durch Antigravity direkt (ohne Gate-A2); briefing-65 plant auf dem Stand „#64 ist gemergt".
4. #65 ohne Drag & Drop im ersten PR (Folgepunkt, Bezug ROADMAP #20); drin: SxxExx-Erkennung + Vorschlag + Auswahlkästchen.
5. briefing-65 braucht Abschnitt „Zusammenspiel mit der Sortierung aus #64".
6. Beide Items ändern `app.js` + `index.html` → je eigener Cache-Buster-Sprung.

## 2. Capability-Check (diese Session)

- **bash: nicht verfügbar** (Session-Regel) → ich führe keine Tests, kein Git, keine Skripte selbst aus. AK0 (Ausgangsmessung) und der Git-Zustand müssen von Claude Code/Alex bzw. der Pipeline geliefert werden.
- `scripts/check_updates.py` existiert in diesem Worktree **nicht** → kein Sessionbeginn-Update-Check möglich; kein Blocker.
- `graphify-out/` existiert in diesem Worktree **nicht** → Codebase-Fragen direkt per read/grep beantwortet (optional: Graphify-Initialisierung später, bleibt Alex-Empfehlung).
- Subagenten (`produktberater`, `advocatus`, `grafiker`, `plan-reviewer`): **erforderlich für Akt 2**, bewusst in Akt 1 noch NICHT konsultiert (Akt-1-Regel des Auftrags). `scout`/`rechercheur`: nicht nötig — Scope kommt aus ROADMAP + Alex-Entscheidungen.
- Schreibrechte: nur `docs/sessions/2026-10-08-roadmap64-65-inbox/*.md` (+ STAND/VERLAUF laut Regel, hier per Auftragsgrenze **ausgeschlossen**).

## 3. Behauptungen B1–B4 — Prüfung mit Belegen

### B1 — BESTÄTIGT (mit einer Präzisierung)
Die Inbox auf der Startseite ist die „Smart Inbox":

- Rendering: `gui/static/app.js:12245–12328` befüllt `#smart-inbox-list` (Container: `gui/static/index.html:461`, Karte `#card-smart-inbox`: `index.html:427`).
- Datenquelle: `fetchSmartInboxSuggestions()` — definiert in `gui/static/js/welcome.js:16–17`, `fetch("/api/inbox/analyze")`; in `app.js:6` als ES-Modul importiert und in `app.js:12247` aufgerufen. **Präzisierung zur Behauptung:** der fetch-Aufruf liegt nicht in `app.js` selbst, sondern im Modul `js/welcome.js` — inhaltlich korrekt.
- Endpoint: `gui/api/project_api.py:1495` — `@project_api.route('/inbox/analyze', methods=['GET'])`, Antwort `{'suggestions': get_inbox_suggestions()}` (`:1498`).

### B2 — INHALTLICH BESTÄTIGT, Zeilenangabe der Behauptung ist FALSCH
Das Payload-Dict wird in `gui/api/project_api.py:1477–1487` gebaut (nicht „ca. 1366–1376" — dort steht die Doku/NFO-Erkennung). Felder exakt:

`project, media_type, confidence, profile_match, profile, suggested_query, video_count, has_inefficient_codec, reasons`

- **Kein Datum, keine Größe** — bestätigt. Damit ist die Bedingung aus ROADMAP #64 („keine Server-Änderung nötig, **sofern die Payload die Felder bereits liefert**", `ROADMAP.md:1808`) für die geforderten Sortierfelder „mindestens Name, Datum, Größe" (`ROADMAP.md:1805`) **nicht erfüllt**. → echte Scope-Frage, siehe Abschnitt 6, Q1.
- Hinweis: `profile` (vollständiges Profil-Objekt) liegt bereits im Payload; „Name" (= `project`) und „Dateianzahl" (= `video_count`) sind sortierbar, ohne den Server anzufassen.

### B3 — BESTÄTIGT
- Reihenfolge: `for item in os.listdir(inbox_dir)` — `project_api.py:1315` (Behauptung „ca. 1314": passt auf die Zeile drumherum; exakt 1315). Kein `sorted()` an irgendeiner Stelle der Schleife → Reihenfolge dateisystemabhängig.
- Cache: 30 s — `project_api.py:1303–1305` (`if now - _inbox_cache_time < 30: return _inbox_cache`), Globals `:1174–1175`, Befüllung `:1489–1490`.
- Relevanz für #64: Sortierung im Frontend wird vom Cache nicht gestört (der Sortier-Zustand wäre clientseitig, z. B. `sessionStorage` wie in `ROADMAP.md:1809` gefordert).

### B4 — BESTÄTIGT
- Einzelne Videodateien direkt im Inbox-Ordner werden zu JE WEILS EINEM Eintrag: Nicht-Verzeichnis-Pfad `project_api.py:1323–1326` (nur Video-Endungen) → `video_files.append(full_path)` `:1342` → ein Suggestion-Objekt pro Datei mit `project: item` (= Dateiname) `:1478`. Eine Serie mit 11 Staffeln als Einzeldateien erzeugt also viele Einzel-Einträge — exakt Alex' Anlass.
- Teil-Erkennung existiert bereits: `tv_pattern` `project_api.py:1400` (`s\d{1,2}e\d{1,2}` u. a.) stuft jede solche Datei bereits als `media_type: "tv"` ein — aber ohne jede Gruppierung.
- Frontend-seitig existiert `guessSeasonAndEpisode()` in `gui/static/js/parse.js:64–79` (SxxExx, 1x05, deutsche Formen) mit Tests in `tests/frontend/parse.test.js:5–28` — wiederverwendbarer Kern für die #65-Erkennung.
- Was „gruppieren" technisch bedeutet (nur Anzeige vs. Dateien in Ordner verschieben vs. Mehrfachdatei-Übergabe an den Serien-Flow), ist im Code NICHT festgelegt → echte design-frage mit Datenrisiko, siehe Q2.

## 4. Weitere scope-relevante Befunde (nicht behauptet, selbst geprüft)

- **Cache-Buster-Stand:** `app.js?v=94` in `gui/static/index.html:2752` und in allen 9 ES-Importen `app.js:1–9`. `tests/frontend/cache_busting.test.js:13–48` erzwingt Gleichheit (Index-Version == jede Import-Version). → #64 und #65 brauchen je einen eigenen Sprung (Annahme: v95 → v96; final in den Briefings).
- **Gate-A2-Testtimeout:** `scripts/gate-a2/adapters.py:41` `_TEST_TIMEOUT_S = 300`, Default des `TestCommandValidator` (`adapters.py:469`). Die Behauptung „die Pipeline begrenzt den Test jetzt selbst" stimmt für diese Worktree-Kopie (Parameter-/Konstantenname weicht leicht ab) → kein eigenes `timeout` in `test_cmd` nötig.
- **Gate-A2-Baustelle (Risiko für briefing-64, Abschnitt 6):** `scripts/gate-a2/README.md:130–133` markiert die Verdrahtung von `--test-cwd` in den Container-Workspace des echten agy-Workers als „weiterhin offen". Autoritativer Test gegen den Worker-Code ist damit nicht garantiert grün-sicher; muss ins Briefing als dokumentiertes Restrisiko (keine Neuverhandlung des Pipeline-Ziels).
- **Testkommandos:** Frontend `npm run test:frontend` = `node --test "tests/frontend/**/*.test.js"` (`package.json:6`); Backend `pytest` (`tests/`). #64-AK-Tests können auf dem bestehenden DOM-Muster aufsetzen: handgebaute Element-Mocks + `eval` von `app.js` (`tests/frontend/app_warning.test.js:95–119`) — jsdom gibt es nicht.
- **Sortier-Interaktion:** Die Smart-Inbox-Karte hat heute KEINE Kopfzeile/Spaltentabelle (`index.html:427–461`, items sind Flex-Zeilen `app.js:12281–12303`). „Per Klick sortierbar" erfordert neues UI (Kopfzeile oder Sortier-Dropdown) → Gestaltungsdetail, gehört ins Briefing (grafiker), keine Alex-Scope-Frage.
- **Bestehende Klick-Übergabe:** `handleSmartInboxClick()` `app.js:12330–12355` (selectProject + Moduswahl Film/Serie) — der natürliche Andockpunkt, den #65 für „Gruppe → Serien-Flow" verwenden würde.

## 5. Git-Zustand (von Claude Code ausgeführt, wörtlich übernommen — ich habe kein bash)

```
$ git status --short --branch
## feat/roadmap-64-inbox-sortierbar
$ git log --oneline -3
288130a fix: refresh profile dropdown after save and stop name-conflict hint loop (ROADMAP #46) (#147)
3522ef2 chore: rebuild AGENTS.md from updated global rules (B1) (#146)
b174c76 feat(metadata): retry logic for JSON metadata fetches (ROADMAP #54 Teil 1) (#145)
```

Feature-Branch, Working Tree clean (keine `??`/`M`-Zeilen). Kein main-Stop ausgelöst. Commit/PR-Aktionen bleiben bei Claude Code nach Alex-Go.

## 6. Scope-Fragen an Alex — FREIGABEPUNKT 1

### Q1 — #64: „Datum, Größe" fehlen in der Payload. Server-Änderung oder reduzierte Sortierfelder?

ROADMAP #64 fordert „mindestens Name, Datum, Größe" (`ROADMAP.md:1805`), knüpft die Server-Feldfreiheit aber an eine Bedingung, die laut B2-Befund nicht erfüllt ist.

- **Empfehlung:** Variante (a) — Payload um `date` + `size` erweitern (pro Eintrag ein `os.stat` auf Datei bzw. aggregiert über die ohnehin bereits gesammelten `video_files`, `project_api.py:1329–1342`). Die Server-Änderung ist klein; derselbe Endpoint betreibt heute schon deutlich schwerere I/O (Codec-Probe über bis zu 10 Dateien je Eintrag, `:1348–1354`).
- **Trade-off/Risiko:** (a) verwässert die „reines Frontend"-Prämisse des Worker-Auftrags (erlaubte Dateien wachsen um `gui/api/project_api.py`, `pytest` wird als Test relevant) und adds `stat`-I/O auf einem ggf. gemounteten NAS-Pfad. Variante (b) (nur Name/Medientyp/Dateianzahl sortieren) hält die Server-Freiheit, erfüllt das ROADMAP-Ziel aber nachweislich NICHT — der Zieltext müsste dann in ROADMAP #64 selbst angepasst werden.
- **Entscheidungspunkt:** (a) Server liefert Datum+Größe, #64 sortiert Name/Datum/Größe — oder (b) rein-Frontend mit reduzierten Feldern + ROADMAP-Text-Korrektur?

### Q2 — #65 (design-frage, Eskalationsregel ausgelöst): Was bewirkt „Als Serie gruppieren" technisch?

- **Empfehlung:** Für den ersten #65-PR: **Anzeige-Ebene + Übergabe** — SxxExx-Erkennung (Frontend-Kern `parse.js:64–79` vorhanden), visuelle Gruppierung der Einzel-Einträge, Vorschlagskarte „Als Serie gruppieren" mit Checkbox-Auswahl (beides von Alex gesetzt), und die Bestätigung übergibt die Auswahl an den bestehenden Serien-Flow (`app.js:12330`-Muster). **Kein Verschieben von Inbox-Dateien im ersten PR.**
- **Trade-off/Risiko:** Reicht die reine Übergabe nicht, weil der bestehende Serien-Flow eine Ordnerstruktur erwartet, wäre ein Server-Schritt nötig, der Dateien in `Inbox/Serie/StaffelX/` verschiebt — das ist das Datenrisiko dieser design-frage: Klassen-C-Territorium (Umschreiben/Nutzerdateien bewegen), im Fehlerfall nicht ohne Weiteres rückgängig. Falsche Gruppierung (gleiches Namenspräfix, zwei Serien) ist zusätzlich ein UX-Risiko, das die ROADMAP selbst nennt (`ROADMAP.md:1835`).
- **Entscheidungspunkt:** Bestätigst du „Anzeige + Vorschlag + Checkboxen, Datei-Verschieben NEIN" für PR 1 — oder soll Gruppieren die Dateien physisch in Serien-/Staffelordner legen (dann: eigener, explizit freigegebener Daten-Schritt mit Rückfrage, bevor briefing-65 das plant)? Falls unklar, ob der Serien-Flow Einzeldateien schluckt: Empfehlung „erst klären" — fehlende Info ist, wie `selectProject`/Verarbeitung mit mehreren Einzel-Top-Level-Dateien umgeht; das würde ich in Akt 2 read-only ausloten und dir das Ergebnis als zweite, engere Frage vorlegen.

### Q3 — formale Kleinigkeit zur Bestätigung (Empfehlung steht, nur zum Zur-Kenntnis-Nehmen)

Cache-Buster-Sprünge: #64 → `v=95`, #65 (auf gemergtem #64) → `v=96`. Sortier-Zustand pro Sitzung via `sessionStorage` (liest `ROADMAP.md:1809` so vor). **Empfehlung:** so annehmen, außer du widersprichst; Trade-off: keines — rein konventionell. Entscheidungspunkt: nur ggf. „widersprechen".

## 7. Was nach Alex' Antworten folgt (Akt 2 — HIER NOCH NICHT GESTARTET)

1. Subagenten-Konsultation (produktberater/advocatus/grafiker je Item; plan-reviewer am Ende), Rohoutputs bleiben bei Claude Code (opencode export), ich zitiere nur mit Rollenzuordnung.
2. `briefing-64.md` (source: roadmap#64, mit Abschnitt „Worker-Auftrag") und `briefing-65.md` (source: roadmap#65, mit „Zusammenspiel mit der Sortierung aus #64"), je 11 Abschnitte nach Vorlage.
3. `ALEX_ZUSAMMENFASSUNG.md` (beide Items, je ein Abschnitt, max. eine Bildschirmseite).
4. STOPP an Freigabepunkt 2 (finaler Planreview, plan-reviewer-VERDICT auf die Briefings VOR Vorlage der Zusammenfassung).

---

**STOPP — Freigabepunkt 1 erreicht.** Akt 2 (Subagenten, Briefings) beginnt erst nach Alex' Antworten auf Q1–Q3.
