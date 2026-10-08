---
kind: plan
status: approved
approved_by: alex
approved_on: 2026-10-08
approval_quote: "1–4 ja, Regeln 1–3 ja"
source: roadmap#64
---

# Feature Briefing: #64 — Smart Inbox: sortierbare Liste (Name/Datum/Größe)

## 1. Problemstellung

Die „Smart Inbox"-Vorschlagsliste auf der Startseite wird in dateisystemarbiträrer Reihenfolge angezeigt: `get_inbox_suggestions()` iteriert unsortiert über `os.listdir(inbox_dir)` (`gui/api/project_api.py:1315`, verifiziert im Kickoff, B3). Bei vielen Kandidaten ist nicht schnell erkennbar, welche Projekte zuerst anstehen (ROADMAP.md:1802). ROADMAP #64 fordert Klick-Sortierung „mindestens Name, Datum, Größe" (`ROADMAP.md:1805`) mit Erhalt des Sortier-Zustands pro Sitzung (`:1809`).

Die Bedingung der ROADMAP „keine Server-Änderung nötig, sofern die Payload die Felder bereits liefert" (`ROADMAP.md:1808`) ist NICHT erfüllt: Das Payload-Dict (`project_api.py:1477–1487`) enthält nur `project, media_type, confidence, profile_match, profile, suggested_query, video_count, has_inefficient_codec, reasons` — kein Datum, keine Größe (verifiziert, Kickoff B2). Alex hat auf Freigabepunkt 1 Q1 mit Variante (a) entschieden: **der Server liefert Datum + Größe nach** („Alex: ‚Ja, ich folge deinen Empfehlungen zu Q1–Q3.'", 2026-10-08).

## 2. Zielnutzer

Alex als Einzelnutzer des Medienwerkzeugs: Er sieht auf der Startseite, welche Inbox-Projekte frisch (Datum) oder groß (Größe) sind, und priorisiert daraus, was zuerst verarbeitet wird. Sortieren nach Name hilft beim Wiederfinden. Kein externer Nutzer, keine Außenwirkung.

## 3. Akzeptanzkriterien

- [ ] **AK0 — Ausgangsmessung:** Vor dem Worker-Lauf führt Claude Code die volle Testsuite im Pipeline-Image aus (Befehl wie in Abschnitt 11 `test_cmd`). Die wörtliche Ausgabe steht in `docs/sessions/2026-10-08-roadmap64-65-inbox/ak0-ausgangsmessung.md` (eigene Datei, damit der freigegebene Plan danach nicht mehr geändert wird). *(Korrektur Claude Code nach Freigabepunkt 2, Alex-Go „1–4 ja“: ursprünglich Platzhalter in diesem Briefing.)*
- [ ] **AK1 — Payload-Felder (Backend-Test, neu `tests/test_inbox_suggestions.py`):** Es prüft, dass `GET /api/inbox/analyze` je Eintrag `modified_at` (int, Unix-Sekunden oder `null`) und `total_size` (int, Bytes) liefert; dass für einen Ordner `modified_at` = größte `st_mtime` aller Videodateien und `total_size` = Summe ihrer `st_size` ist (tmp-Verzeichnis, `os.utime`-gesteuerte Mtimes, `load_settings` gepatcht, Cache-Globals `_inbox_cache`/`_inbox_cache_time` zwischen Tests zurückgesetzt); dass für eine einzelne Videodatei beide Werte exakt dieser Datei entsprechen.
- [ ] **AK2 — NAS-/stat-Fehlerfall:** Es prüft, dass ein `os.stat`-Fehler pro Datei (Mock: `OSError`) den Eintrag NICHT verschwinden lässt: die fehlerhafte Datei zählt für `total_size` als 0 und fällt bei `modified_at` heraus; sind alle Dateien unlesbar, ist `modified_at = null` und `total_size = 0`. Es prüft, dass der Fehler sichtbar geloggt wird (kein stilles Scheitern).
- [ ] **AK3 — Sortier-Funktion (Frontend-Test, neu `tests/frontend/inbox_sort.test.js`):** Es prüft, dass die reine Funktion `sortInboxSuggestions(items, field, dir)` — in `app.js` als normale Funktionsdeklaration OHNE `export`-Keyword, storage-frei; im Test via `globalThis.sortInboxSuggestions = sortInboxSuggestions;` vor dem `eval` exponiert (Muster `app_warning.test.js:103–117`) — nach `name` via `localeCompare(..., "de", { numeric: true, sensitivity: "base" })`, nach `date` via `modified_at`, nach `size` via `total_size` sortiert; dass `asc`/`desc` spiegeln; dass Einträge mit `modified_at = null` bei BEIDEN Richtungen ans Ende sortieren; dass bei Gleichstand deterministisch nach `project` (gleiche Locale-Regel) nachsortiert wird; dass Umlaute („Ä" wie „A") und Ziffernfolgen („S01E2" vor „S01E10") richtig einsortieren.
- [ ] **AK4 — Sortier-Leiste (UI):** Es prüft (DOM-Test nach Muster `app_warning.test.js:95–119`, eigene Mocks inkl. `globalThis.sessionStorage`, keine echten Timer), dass über der Liste drei `<button>`-Elemente „Name | Datum | Größe" existieren (`#smart-inbox-sort-bar`), Klick auf ein inaktives Feld dieses aktiviert (Richtung asc), Klick auf das aktive Feld asc↔desc toggelt, das aktive Feld `aria-pressed="true"` und ▲/▼-Indikator trägt, und die Leiste bei leerer Liste NICHT gerendert wird.
- [ ] **AK5 — Persistenz + Rerender:** Es prüft, dass die Wahl unter `sessionStorage`-Key `smart-inbox-sort` als JSON `{field, direction}` gespeichert und beim Rendern wieder angewendet wird; dass der Zugriff defensiv in try/catch liegt; dass die Sortierung VOR der Render-Schleife auf das Array angewendet wird und damit einen erneuten fetch/Rerender übersteht.
- [ ] **AK6 — Metazeile je Eintrag:** Es prüft, dass jeder Eintrag zusätzlich „N Datei(en)" die Segmente Größe (bestehendes `formatBytes`, `gui/static/js/format.js:11–18`) und Datum (`de-DE`, TT.MM.JJJJ) mit „ · "-Trennung anzeigt; dass bei `null`/fehlendem Wert das Segment komplett entfällt (kein leeres „· ·"); dass neue Felder nur als Zahlen in HTML-Fluss gehen (Escape-Muster wie bisher) — kein neuer XSS-Vektor.
- [ ] **AK7 — Default ohne gespeicherten Zustand:** Es prüft, dass ohne `sessionStorage`-Eintrag die Reihenfolge `date`/`desc` (neueste zuerst) ist (ADR-64-4).
- [ ] **AK8 — Cache-Buster:** `app.js?v=95` in index.html:2752 UND allen 9 Importen app.js:1–9; `style.css?v=48` in index.html:9. Der bestehende `tests/frontend/cache_busting.test.js` prüft nur die KONSISTENZ (index.html ↔ Importe), nicht den Bump selbst — der Bump ist ausschließlich über Task-Punkt 3 (Worker-Auftrag) und die Reviewer-Diff-Prüfung abgesichert. `npm run test:frontend` muss mit den neuen Versionen grün bleiben.
- [ ] **AK9 — Hygiene:** `git diff --check` ist sauber (kein Trailing Whitespace — Finding aus dem #46-Lauf); Tests schreiben nur in tmp-Verzeichnisse; keine neuen echten Timer ohne Abräumen im Testpfad.

## 4. Bewusst verworfen (Scope-Eingrenzung)

- **Server-seitige Sortierung / Query-Parameter** (`?sort=…`): alle Daten liegen bereits beim Client; Roundtrip und Cache-Key-Komplexität ohne Nutzen (produktberater).
- **Kappung der stat-Aufrufe auf 10 Dateien** (Codec-Probe-Muster `project_api.py:1350`): würde „Größe" systematisch unterschätzen und die Sortierung falsch machen (advocatus K2); stat-Kosten sind durch den ohnehin nötigen Size-Pass + 30-s-Cache amortisiert.
- **Datum = Ordner-mtime statt max(mtime der Videodateien):** auf NAS/rclone-Mounts unzuverlässig (Ordner-mtime ändert nicht bei Datei-Rewrites); die Datei-mtimes fallen beim Size-Pass ohnehin kostenlos an (siehe ADR-64-1, Dissens dokumentiert in Abschnitt 6).
- **Drag & Drop / Mehrfachsortierung / Sort-Animationen / localStorage-Persistenz über die Sitzung hinaus:** nicht bestellt; Drag&Drop ist ROADMAP #65-Folgepunkt bzw. #20.
- **Sortierung nach `confidence`/`profile_match`:** wäre denkbar, ist aber nicht Teil des Alex-Scopes (produktberater: „Beiwerk").
- **Refactoring von `get_inbox_suggestions()`** (Cache-Logik, Globals, Typ-Inkonsistenz `_inbox_cache = {}` vs. Liste, advocatus C3): nur additive Felder an das bestehende Dict.

## 5. ADR-Blöcke

### ADR-64-1: Server liefert `modified_at` + `total_size` aus einem stat-Pass über `video_files`
- **Entscheidung:** In `get_inbox_suggestions()` wird die bereits bestehende Liste `video_files` (`project_api.py:1332–1342`) in EINEM Durchlauf mit `os.stat` ausgewertet: `total_size = sum(st_size)`, `modified_at = max(st_mtime)`; Einzeldatei = dieselbe Logik mit einem Element. Pro Datei try/except: Fehler → Datei zählt 0/entfällt, `log_message`-Eintrag; alle fehlgeschlagen → `modified_at=None`, `total_size=0`, Eintrag bleibt sichtbar. Felder heißen exakt `modified_at` (int-Sekunden oder None) und `total_size` (int).
- **Alternativen:** (a) Ordner-mtime + `os.path.getsize` nur für Top-Level — abgelehnt, s. Abschnitt 4; (b) Kappung auf 10 Dateien — abgelehnt (advocatus K2: falsche Zahlen sind schlimmer als keine); (c) Eintrag bei stat-Fehler verwerfen — abgelehnt (advocatus K1: Projekt würde still aus der Anzeige verschwinden).
- **Begründung:** Alex-Entscheidung Q1(a); Semantik „jüngste Änderung / reale Gesamtgröße" erfüllt das Priorisierungs-Ziel aus ROADMAP.md:1802; ein einziger, vorhersagbarer I/O-Pass.
- **Konsequenzen:** Endpoint antwortet beim ersten Call nach Cache-Ablauf langsamer auf großen NAS-Ordern (30-s-Cache `:1303–1305` amortisiert); API.md:122 ff. muss die neuen Felder dokumentieren (Drift-Gefahr, advocatus W3).

### ADR-64-2: Sortierung vollständig im Frontend, reine Funktion + Sortieren VOR Render
- **Entscheidung:** `sortInboxSuggestions(items, field, dir)` als **normale Funktionsdeklaration OHNE `export`-Keyword** in `gui/static/app.js` (das eval-Testmuster `app_warning.test.js:100` stript nur `import`-Zeilen; ein `export function` würde dort und im neuen Test beim `eval` einen SyntaxError werfen und den bestehenden app_warning-Test brechen, den der Worker nicht ändern darf). Der neue Test exponiert sie nach Muster `app_warning.test.js:103–117` via angehängtem `globalThis.sortInboxSuggestions = sortInboxSuggestions;` vor dem `eval`. Die Render-Sektion (`app.js:12245–12328`) sortiert das `suggestions`-Array VOR der `forEach`-Schleife. Comparator: `name` → `localeCompare("de", {numeric:true, sensitivity:"base"})`; `date`/`size` numerisch mit `null`-Regel „immer ans Ende"; Tie-Break immer `project`.
- **Alternativen:** Server-Sort (verworfen, Abschnitt 4); DOM-Nachträgliches Umsortieren (verworfen: Rerender nach 30-s-Cache würde die Reihenfolge verlieren, advocatus W2).
- **Begründung:** Daten sind vollständig beim Client; reine Funktion ist ohne DOM-/Timer-Mocks testbar (advocatus W5 — der letzte Gate-A2-Lauf hing an echten Timern im eval-Pfad).
- **Konsequenzen:** `data-project`-Sync (`app.js:2457–2479`) bleibt reihenfolge-agnostisch, keine Änderung nötig (advocatus W2, grafiker Abschnitt 4).

### ADR-64-3: Sortier-Leiste aus drei Buttons statt Kopfzeile/Dropdown
- **Entscheidung:** Statischer `<div id="smart-inbox-sort-bar" role="toolbar">` mit drei `<button>` („Name | Datum | Größe") in `index.html` zwischen Kartenkopf und `#smart-inbox-list` (`:461`); aktiver Button: ▲/▼-Unicode (aria-hidden), `aria-pressed`, `font-weight:600`; Hover/Fokus als ~10-Zeilen-Block in `style.css` (Klickfläche ≥28px Höhe). Leere Liste → Leiste wird per JS ausgeblendet.
- **Alternativen:** Dropdown `<select>` (grafiker Variante B — abgelehnt: versteckt Zustand, bricht Dark-UI); Chips (Variante C — abgelehnt: konkurriert visuell mit den Typ-Badges); echte Tabellenkopfzeile (abgelehnt: Einträge sind Flex-Zeilen ohne Spaltraster).
- **Begründung:** Alle drei Felder sofort sichtbar (Affordanz für ein sekundäres Feature), minimaler Footprint; Muster folgt grafikers Variante A.
- **Konsequenzen:** `style.css` rutscht in die erlaubte Dateiliste (advocatus W6 warnte vor Scope-Creep — durch „nur append-Block + Versionsbump" gefasst); A11y-Korrektur gegenüber grafiker-Vorschlag: `aria-pressed` statt `aria-sort` (aria-sort ist nur für Tabellen-Sortierköpfe definiert).

### ADR-64-4: Default ohne gespeicherten Zustand = `date` desc („neueste zuerst")
- **Entscheidung:** Fehlt der `sessionStorage`-Eintrag, wird `modified_at` absteigend sortiert.
- **Alternativen:** Server-Reihenfolge beibehalten (abgelehnt: die ist `os.listdir`-arbiträr, kein sinnvoller Default); `name` asc (grafikers Vorschlag — abgelehnt, Begründung siehe Dissens in Abschnitt 6).
- **Begründung:** Das Problem laut ROADMAP.md:1802 ist PRIORISIERUNG („welche Projekte zuerst anstehen"); „neueste zuerst" ist die etablierte Inbox-Erwartung (produktberater).
- **Konsequenzen:** Sichtbare Reihenfolge ändert sich beim ersten Laden nach Deploy (nur visuell, keine Datenwirkung). Alex kann diesen Default bei Freigabepunkt 2 übersteuern.

### ADR-64-5: Persistenz via `sessionStorage`-Key `smart-inbox-sort`, defensiv gekapselt
- **Entscheidung:** Speichern von `{field, direction}` als JSON unter `sessionStorage["smart-inbox-sort"]` bei Klick; Lesen beim Render; beide Zugriffe in try/catch. Die reine Sortierfunktion (ADR-64-2) berührt den Storage nicht.
- **Alternativen:** localStorage (über die Sitzung hinaus — nicht bestellt); keine Persistenz (widerspricht ROADMAP.md:1809).
- **Begründung:** „pro Sitzung erhalten" ist exakt sessionStorage-Semantik; advocatus K3: `sessionStorage` existiert in der eval-Testumgebung nicht und wirft sonst `ReferenceError` — Kapselung + Mock im Test lösen das.
- **Konsequenzen:** Tests müssen `globalThis.sessionStorage` mocken; Privatmodus/iframe-Würfe sind abgefangen.

### ADR-64-6: Metazeile „N Datei(en) · Größe · Datum", existierende Formatter
- **Entscheidung:** Pro Eintrag wird die Meta-Zeile zu `video_count · formatBytes(total_size) · formatDateDe(modified_at)` erweitert; `formatBytes` aus `js/format.js` (bereits importiert, `app.js:3`); `formatDateDe` als kleine Helper in `app.js` (`toLocaleDateString("de-DE", …)`); fehlende/`null`-Werte lassen das Segment komplett entfallen.
- **Alternativen:** Eigene Größen-Formatter-Funktion (grafiker-Entwurf — verworfen: Duplikat zu `formatBytes`); ISO-Datum (abgelehnt: deutsche Kurzform erwartet).
- **Begründung:** Reihenfolge Größe vor Datum nach Relevanz (grafiker Abschnitt 2); Server liefert nur Zahlen, Formatierung im Client — kein XSS-Vektor (advocatus W7).
- **Konsequenzen:** Zeile wird länger; `flex-wrap` der bestehenden Struktur trägt das, lange Namen bekommen `overflow-wrap` (grafiker Abschnitt 4).

### ADR-64-7: Cache-Buster app.js v94→v95 und style.css v47→v48
- **Entscheidung:** `index.html:2752` `app.js?v=95`, alle 9 Modul-Importe `app.js:1–9` auf `?v=95`; `index.html:9` `style.css?v=48` (da style.css geändert wird).
- **Alternativen:** Nur app.js bumpen — verworfen, weil die geänderten style.css-Regeln sonst im Browser-Cache festhängen würden.
- **Begründung:** Hausregel aus ROADMAP #137 (Versionsbump-Pflicht bei geänderten Dateien); `cache_busting.test.js:13–48` erzwingt die app.js-Konsistenz ohnehin.
- **Konsequenzen:** Alle Clients ziehen nach Deploy frische Assets; keine Kompatibilitätsprobleme, da KEIN externer Konsument existiert (fetch in `js/welcome.js:16–17`, Rendering in `app.js:12245–12328` — beide werden gleichzeitig auf v95 gestellt).

## 6. Dissens & Risiken

**Dissens 1 — Default-Sortierung (offen, Alex entscheidet mit Freigabepunkt 2):** [produktberater] empfiehlt `date` desc, weil die heutige Server-Reihenfolge `os.listdir`-arbiträr sei und „neueste zuerst" die Inbox-Erwartung bediene; [grafiker] empfiehlt `name` asc als „mental erwartete Reihenfolge einer Projektliste". Entscheidung im Briefing: date desc (ADR-64-4), Begründung Priorisierungs-Problemstellung ROADMAP.md:1802. Trade-off: date desc ist eine sichtbare Verhaltensänderung beim ersten Laden; name asc wäre näher am heutigen „alphabetisch gefühlt". **Alex kann bei der Freigabe widersprechen — dann nur ADR-64-4 + AK7 anpassen, kein Scope-Wechsel.**

**Dissens 2 — Datum-Semantik (entchieden):** [produktberater] wollte nur die Ordner-mtime (1 stat-Aufruf, billiger); [advocatus] verlangte die Festnagelung `max(st_mtime)` über die Videodateien (C2), weil Ordner-mtime auf NAS-Mounts bei Datei-Rewrites nicht zieht und der AK sonst nicht deterministisch testbar ist. Entscheidung ADR-64-1: max-mtime, weil der stat-Pass für `total_size` ohnehin läuft und mtime dort kostenlos abfällt. Verworfen als Alternative dokumentiert.

**Dissens 3 — style.css (entchieden):** [advocatus] (W6) warnte, die Sortier-Controls rein inline zu halten und style.css auf die Nicht-anfassen-Liste zu setzen; [grafiker] brauchte ~10 Zeilen für Hover/Fokus-Pseudoklassen (JS-Listener seien fehleranfälliger). Entschieden: style.css FREIGEGEBEN, aber streng begrenzt auf den append-Sortierblock + Versionsbump (ADR-64-3, ADR-64-7).

**Behobener Einwand (Transparenz):** [advocatus] schloss als „Restrisiko" die laut `scripts/gate-a2/README.md:130–133` offene `--test-cwd`-Verdrahtung ein. Diese Sorge beruht auf der veralteten Gate-A2-Kopie in diesem Worktree (Stand PR #128). Korrektur durch Claude Code (2026-10-08, wörtlich im Akt-2-Auftrag): Die Pipeline läuft aus dem AI-Coding-Starter-Kit mit `in_container_test: true` und `test_timeout_s` (Default 300); im letzten Lauf (#46, Lauf 2) liefen pytest + `npm run test:frontend` im Container mit Exit 0. Das Risiko ist damit gegenstandslos und wird NICHT als Briefing-Risiko geführt.

**Verbleibende Risiken:**
- **I/O bei großen NAS-Ordnern:** Der stat-Pass über alle Videodateien kann den ersten Endpoint-Call nach Cache-Ablauf spürbar bremsen (bewusst in Kauf genommen, ADR-64-1; 30-s-Cache dämpft). Beobachtungspunkt nach Deploy, kein Blocker.
- **Worker-Scope-Creep:** Die kritischste Gefahr benennt [produktberater]: Der Worker könnte `get_inbox_suggestions()` umstrukturieren statt nur zwei Felder anzuhängen, oder die Cache-Logik anfassen. Abgesichert durch Abschnitt 11 (Nicht-anfassen-Liste) und Reviewer-Task-Text.
- **Test-Hänger:** eval-Pfad über `app.js` mit echten Timern hat im #46-Lauf schon gehangen — durch reine Funktion + isolierten Test (ADR-64-2, AK3/AK4) und AK9 entschärft, Restrisiko bleibt bei der Pipeline-Diagnose.
- **AK0-Lücke:** Die Ausgangsmessung kann ich nicht selbst liefern (kein bash) — sie ist als Pflicht-Placeholder in AK0 verankert und muss VOR dem Worker-Lauf von Claude Code eingetragen werden.

## 7. Quellen, Referenzen & Lizenzen

- Kein Third-Party-Code, keine neuen Assets, Fonts oder Icons. ▲/▼ sind Unicode-Zeichen (U+25B2/U+25BC, gemeinfrei).
- Die im Eintrag-Rendering bereits vorhandenen Lucide-Inline-SVGs (`app.js:12259–12268`, ISC-Lizenz) bleiben unverändert; es kommen keine hinzu.
- Referenz-Muster nur als Inspiration (nicht kopiert): Sortier-Leisten von macOS Finder / GitHub-PR-Liste / Spotify-Playlists (grafiker, Abschnitt 1); Umsetzung folgt den bestehenden Inline-Style-/Button-Mustern des Projekts.
- Interne Referenzen: ROADMAP.md:1797–1815 (#64), Briefing-Vorlage und Struktur des letzten Briefings `docs/sessions/2026-10-06-roadmap46-namenskonflikt/briefing.md`.

## 8. Offene Fragen

Keine blockierenden offenen Fragen. Q1–Q3 sind von Alex beantwortet („Alex: ‚Ja, ich folge deinen Empfehlungen zu Q1–Q3.'", 2026-10-08). Einzige mitzustimmende Feinentscheidung: Default-Sortierung (Dissens 1 / ADR-64-4) — Widerspruch bei Freigabepunkt 2 möglich, ohne Scope-Folge.

## 9. Aufwand (KI-Implementierung vs. menschlicher Engpass)

- **KI/Pipeline (schnell):** Backend-Felder + Frontend-Sortierung + 2 neue Testdateien + Doku — realistisch 1–3 Gate-A2-Runden, Minuten bis wenige Stunden Laufzeit.
- **Menschlicher Engpass (Alex):** AK0-Ausgangsmessung bereitstellen (~10 min), Freigabepunkt 2 (~10 min), nach APPROVE: Review des Diffs, Merge-Entscheidung, NAS-Deploy-Verifikation (~20–30 min). Roadmap-Status-Pflichtupdate erst nach Merge (Klasse A, durch Claude Code).

## 10. Git-Zustand (geliefert von Claude Code, wörtlich; ich habe kein bash)

```
$ git status --short --branch
## feat/roadmap-64-inbox-sortierbar
$ git log --oneline -3
288130a fix: refresh profile dropdown after save and stop name-conflict hint loop (ROADMAP #46) (#147)
3522ef2 chore: rebuild AGENTS.md from updated global rules (B1) (#146)
b174c76 feat(metadata): retry logic for JSON metadata fetches (ROADMAP #54 Teil 1) (#145)
```

Feature-Branch, clean. Kein main-Stop. Ausführung #64: Gate-A2-Pipeline aus dem Kit; Ergebnis-Übernahme/Commits/PR ausschließlich durch Claude Code nach Alex-Go.

## 11. Worker-Auftrag (für `gate_run_task`, Kit-Pipeline)

**Task-Text (Copy-Paste-Basis, AKs gemäß Konvention `scripts/gate-a2/README.md` mit in den --task):**

```text
Smart Inbox (Startseite) sortierbar machen — ROADMAP #64.

Kontext: gui/api/project_api.py, get_inbox_suggestions() (:1299-1492) liefert
Vorschlaege; gui/static/app.js rendert sie (:12245-12328).

NUR diese Aenderungen:
1. Backend: Payload-Dict (:1477-1487) ergaenzen um modified_at (int Unix-Sekunden
   oder None) und total_size (int Bytes). Ein os.stat-Durchlauf ueber die bereits
   gesammelten video_files: total_size = Summe st_size, modified_at = max st_mtime.
   Pro Datei try/except OSError: fehlerhafte Datei zaehlt 0/entfaellt, Fehler
   sichtbar loggen; alle fehlgeschlagen -> modified_at=None, total_size=0.
   Der Eintrag bleibt in jedem Fall sichtbar. NICHTS anderes an der Funktion
   aendern (kein Refactoring, Cache-Logik :1303-1305 bleibt, video_files bleibt).
2. Frontend app.js: reine Funktion sortInboxSuggestions(items, field, dir) als
   NORMALE Funktionsdeklaration OHNE export-Keyword (ein `export function` würde
   den bestehenden app_warning-Test brechen, dessen Strip nur import-Zeilen
   entfernt; im neuen Test via globalThis-Zuweisung vor eval exponieren — Muster
   app_warning.test.js:103-117). Comparator:
   (name: localeCompare de numeric/base; date/size numerisch, null IMMER ans Ende;
   Tie-Break project). Sortierung VOR der Render-forEach anwenden. Sortier-Leiste
   mit drei Buttons Name|Datum|Größe (index.html, id smart-inbox-sort-bar), Klick
   aktiviert (asc), erneut klickt toggelt (asc/desc), aktiver Button aria-pressed
   + Pfeil-Indikator; Leiste bei leerer Liste ausblenden. sessionStorage-Key
   "smart-inbox-sort" ({field,direction}), Lesen+Schreiben in try/catch; Default
   ohne Speicher: date desc. Metazeile je Eintrag: "N Datei(en) · Groesse · Datum"
   (formatBytes aus js/format.js nutzen; Datum de-DE TT.MM.JJJJ; null-Segment
   entfaellt komplett; neue Felder nur als Zahlen, Escape-Muster beibehalten).
3. Cache-Buster: app.js?v=94 -> ?v=95 (index.html:2752 UND alle 9 Importe
   app.js:1-9); index.html style.css?v=47 -> ?v=48; style.css nur um den
   Sortierleisten-Block (Hover/Fokus) ERGAENZEN.
4. API.md: Abschnitt GET /api/inbox/analyze um modified_at/total_size ergaenzen.
5. Tests NEU: tests/test_inbox_suggestions.py (Payload + stat-Fehlerfall,
   tmp_path + os.utime, load_settings patchen, _inbox_cache/_inbox_cache_time
   zuruecksetzen) und tests/frontend/inbox_sort.test.js (node:test; Sortier-
   funktion + Leiste + Persistenz mit gemocktem globalThis.sessionStorage;
   KEINE echten Timer stehen lassen; keine bestehenden Tests aendern).

Akzeptanzkriterien:
- Es prüft, dass jeder Eintrag modified_at/total_size nach obiger Semantik liefert
  (Ordner: max mtime / Summe size der Videodateien; Einzeldatei: ihre Werte).
- Es prüft, dass ein stat-Fehler die Datei ueberspringt, loggt und den Eintrag
  erhaelt (nie Projekt verschwinden lassen).
- Es prüft, dass die drei Sortierfelder asc/desc umschaltbar sind, null-Datum ans
  Ende sortiert, Gleichstand stabil nach project geht, Umlaute/01E10-Muster
  localeCorrect sortieren.
- Es prüft, dass die Sortierung sessionStorage überlebt und nach erneutem fetch
  korrekt gerendert wird (Sortierung vor Render).
- Es prüft, dass Metazeile Groesse/Datum anzeigt und null-Segmente entfallen.
- Es prüft, dass Default ohne Speicher date desc ist.
- cache_busting.test.js bleibt grün (v95/v48); git diff --check sauber;
  keine Secrets, kein .env-Zugriff, keine Pfad-Hardcodierung.

ERLAUBTE DATEIEN (ausschliesslich):
gui/api/project_api.py, gui/static/app.js, gui/static/index.html,
gui/static/style.css (nur append-Sortierblock), API.md,
tests/test_inbox_suggestions.py (neu), tests/frontend/inbox_sort.test.js (neu).

NICHT ANFASSEN (auch nicht "nebenbei"): ROADMAP.md, STAND.md, VERLAUF.md,
docs/**, scripts/**, package.json, gui/core/**, gui/workers/**, gui/api/uebrige,
gui/static/js/** (alle Module inkl. welcome.js/format.js — unveraendert nutzen),
uebrige tests/**, .env (nie lesen), data/**.
```

**`test_cmd`-Vorschlag (ohne eigenes `timeout`; Pipeline-Limit ist `test_timeout_s`, Default 300):**

```bash
python3 -m pip install -q --user --break-system-packages -r requirements.txt pytest && python3 -m pytest -q -p no:cacheprovider --deselect tests/test_utils.py::TestMediawerkzeugLogic::test_conversion_estimation_test_encode && npm run test:frontend
```

*(Korrektur Claude Code nach Freigabepunkt 2, Alex-Go „1–4 ja“: Das Worker-Image bringt die Python-Abhängigkeiten nicht mit; ohne Installation scheitert die Validierung sofort (Erfahrungswert #46, Lauf 2). Wegen der Installation setzt die Laufkonfiguration `test_timeout_s` auf 600.)*

Begründung: Der deselectete Test erzeugt per `subprocess` eine ffmpeg-Testvideo-Datei (`tests/test_utils.py:321–335`) und scheitert im Container umgebungsbedingt (Erfahrungswert aus #46, Lauf 2). `in_container_test: true` wie in #46.

**Freigabe- und Merge-Pfad:** Start des scharfen Laufs braucht Alex-Go (Klasse B: eine Kette). Nach `APPROVED`: Patch-Übernahme nur auf Alex' separate Anweisung; PR-Erstellung/Commits durch Claude Code, nie durch den Worker (Container hat keinen Remote; `gate_apply_result`-Regeln des Kits gelten).
