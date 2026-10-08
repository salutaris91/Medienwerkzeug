# Rohoutput advocatus — Kreativteam-Session 2026-10-08 (Akt 2)
Hinweis Claude Code (2026-10-08): Mechanisch aus `opencode export ses_ee533a3c8ffesW6v133rMvr61E` (ceo-planner) abgelegt, nicht vom Moderator abgeschrieben (Lehre 59). Je Abschnitt: Auftragsbeschreibung, Subagent-Sitzung, dann die wörtliche Subagent-Antwort. Einzige Änderung: Trailing Whitespace am Zeilenende entfernt (Pre-Commit-Hook); sonst unverändert. Volle Prompts und Antworten: Kit `scripts/gate-a2/logs/2026-10-08-roadmap64-65/export-ceo-planner.json`.

---

## advocatus zu #64 Risiken (Subagent-Sitzung ses_ee526ba0effelA2UL4Glod38yb, Status: completed)

<task id="ses_ee526ba0effelA2UL4Glod38yb" state="completed">
<task_result>
Advocatus-Review ROADMAP #64 (read-only) — Findings nach Schwere, je Befund mit Empfehlung.

## [kritisch]

**K1 — stat-Fehlerpfad-Semantik ist ungeklärt und entscheidet über Folgefehler.** Der neue Code sitzt in der `for item in os.listdir`-Schleife (`project_api.py:1315` ff.). Drei Varianten, drei verschiedene Schadensbilder:
- *Eintrag verwerfen (`continue`)*: Projekt verschwindet still aus der Inbox-Anzeige → Nutzer glaubt, Inbox ist leer. Inakzeptabel.
- *Feld weglassen*: `item.date`/`item.size` = `undefined` → Frontend-Comparator bekommt `undefined`/`NaN`, Sortierung instabil; bei naivem `a.date - b.date` ergibt `NaN` → `Array.sort` bricht Reihenfolge.
- *Feld auf Fallback setzen*: einzig sichere Variante.
**Empfehlung:** Pro Datei `os.stat` in try/except (NAS-Aussetzer ist der reale Fall); bei Fehler Datei überspringen (nicht Eintrag!), danach Feld IMMER setzen: `size = sum()` (fehlerhafte Dateien zählen 0), `date = max(mtime)` — wenn keine Datei lesbar: `size=0`, `date=None`. Eintrag bleibt sichtbar. Comparator null-sicher formulieren (s. K5). Diese Semantik wörtlich ins AK schreiben.

**K2 — Kappung der stat-Aufrufe macht „Größe" falsch.** Das bestehende Codec-Muster kappt auf `video_files[:10]` (`:1350`). Wird dieselbe Kappung für die Größen-Summe übernommen, unterschätzt die Anzeige große Serien systematisch — und „größte zuerst" sortiert dann falsch (ROADMAP-Ziel `:1805` wird verfehlt).
**Empfehlung:** Für `size`/`date` KEINE Kappung — `os.walk` liefert die Pfade bereits (`:1333–1340`), der `stat` je Datei ist der einzige Zusatz und durch den 30-s-Cache amortisiert. Die Codec-Probe (`:1348–1354`) bleibt ohnehin der teurere I/O. Falls doch gekappt werden soll (riesige Ordner), dann Feld als `size` weglassen statt halbrichtig anzeigen — eine nachweislich falsche Zahl ist schlimmer als keine. Alex-Entscheidung nötig, falls Kappung gewünscht.

**K3 — `sessionStorage` existiert in der eval-Testumgebung nicht.** `sessionStorage` wird im Code heute nirgends benutzt (grep: nur ROADMAP/Doku-Treffer). Node stellt es nicht global bereit; die bestehenden eval-Mocks (`tests/frontend/app_warning.test.js:69–93`) bauen `document`/`window`/`fetch`/`escapeHTML`, aber KEIN `sessionStorage`. Ein Sortier-Code, der beim eval von `app.js` direkt `sessionStorage.getItem(...)` ruft, wirft `ReferenceError` → Test rot oder hängt (vgl. letzter Gate-A2-Timer-Hänger).
**Empfehlung:** (a) Sortierlogik als exportierbare, reine Funktion halten (`sortInbox(items, key, dir)`), die `sessionStorage` NICHT berührt — Persistenz nur in der dünnen Aufruf-Schicht; (b) im Test `globalThis.sessionStorage = { getItem:()=>null, setItem:()=>{}, removeItem:()=>{} }` mocken; (c) im Produktivcode `sessionStorage`-Zugriff defensiv in try/catch (Privatmodus/iframe werfen ebenfalls).

## [wichtig]

**W1 — Comparator-Robustheit (null/undefined, Tie-Break, Locale).** Bei `date=None` oder fehlendem `size` muss der Comparator Defaults nutzen (`?? -Infinity`/`?? 0`), sonst `NaN`-Vergleich. Namens-/Datums-Sortierung braucht `localeCompare(..., 'de', {numeric:true, sensitivity:'base'})` — Standardvergleich sortiert Umlaute und `S01E02` vs `S01E10` falsch. Tie-Break: deterministischer Sekundärschlüssel (`project`) zwingend, sonst springt die Reihenfolge bei jedem Render.
**Empfehlung:** AK explizit: „es prüft, dass gleiche Werte nach `project` stabil geordnet werden; dass `null`-Datum ans Ende sortiert; dass `Ä` wie `A` und `S01E10` nach `S01E2` einsortiert wird."

**W2 — Sortierung muss den RERENDER überleben.** Jeder erneute fetch (30-s-Cache) leert die Liste (`app.js:12255 innerHTML=""`) und baut neu. Die reaktive Sync `app.js:2457–2479` ist reihenfolge-agnostisch (findet Items per `data-project`), also unkritisch — aber nur, wenn die Sortierung *beim Rendern* angewendet wird, nicht als nachträglicher DOM-Umbau.
**Empfehlung:** `suggestions` VOR der `forEach`-Schleife sortieren (Array.sort nach gespeichertem Zustand), dann rendern — dann ist RERENDER automatisch korrekt. AK: „es prüft, dass die Sortierung nach einem erneuten fetch erhalten bleibt."

**W3 — API.md-Drift.** `API.md:122–138` dokumentiert die Payload-Feldliste explizit; neue Felder `date`/`size` müssen dort ergänzt werden (Pflicht-Doku, sonst Code↔Doku-Drift). `profile`-Vollobjekt ist schon drin, aber die neuen Felder fehlen in Beispiel-JSON `:127–137`.

**W4 — Backend-Test fehlt komplett + Test-Hindernisse.** Kein Test für `get_inbox_suggestions`. Der neue Test muss drei Dinge beherrschen: (a) `load_settings` patchen (sonst liest er echte Settings → echter NAS-Pfad), (b) die Globals `_inbox_cache`/`_inbox_cache_time` (`:1174–1175`) zwischen Tests zurücksetzen (30-s-Cache polluiert sonst), (c) deterministische mtimes via `os.utime` im `tmp_path`-Fixture. Test-Artefakte nur in `tmp_path` (Regel).
**Empfehlung:** Fixture, das Settings-Mock + Global-Reset bündelt; AK formuliert mit tmp-Verzeichnis + `os.utime`.

**W5 — Timer im eval-Test.** `app.js` enthält echte `setTimeout` (z. B. `:12333` in `handleSmartInboxClick`); der letzte Gate-A2-Lauf hing deshalb. Ein Sortier-Test darf nicht den vollen fetch+Render-Flow (ab `:12246`) evaluieren, sondern nur die isolierte Sortierfunktion. Existierende Muster (`app_warning.test.js:100`) strippen zwar Imports per Regex, aber echte Timer bleiben.
**Empfehlung:** Sortierfunktion separat exportieren + testen; kein Test des async Render-Blocks; ggf. `node:test` mit `--test-timeout` und Timer-Abräumen im `finally`.

**W6 — Worker-Scope / Nicht-anfassen-Liste.** Erlaubte Dateien eng fassen; ausdrücklich NICHT anfassen:
- `gui/static/style.css` — Sortier-UI heute rein Inline-Styles (`app.js:12281–12303`); neue Sortier-Controls ebenfalls inline halten ODER style.css explizit freigeben (Grafiker-Klärung, sonst Scope-Creep).
- `gui/api/*.py` außer `project_api.py`, `gui/core/`, `gui/workers/`.
- Andere Tests: `tests/frontend/profile_dropdown_refresh.test.js:141` mockt `fetchSmartInboxSuggestions=()=>{}` (unkritisch), aber `tests/frontend/welcome.test.js:97–125` baut die Response — nur anfassen, wenn Payload-Beispiele erweitert werden.
- `ROADMAP.md`, `VERLAUF.md`, `STAND.md` erst nach Merge (Pflicht-Updates), nicht im PR mischen.
**Empfehlung:** Exakte Dateiliste ins Worker-Briefing: `gui/api/project_api.py`, `gui/static/app.js`, `gui/static/index.html` (nur `?v=94→95`), `tests/frontend/<neu>`, `tests/<backend-neu>`, `API.md`; plus `git diff --check` als expliziter Pflichtschritt (Trailing Whitespace war letzter Lauf-Finding).

**W7 — XSS über neue Felder.** `item.project` wird escaped (`:12285`), `item.video_count` nicht (`:12287`) — Zahl, ok. Neue Felder `size`/`date` daher als **Zahlen/None** vom Server liefern (kein vorformatiertes HTML/string), Formatierung („3,2 GB", „12.10.2026") im Frontend mit `escapeHTML` bzw. `textContent` — kein neuer XSS-Vektor, solange der Server keine formatierten Strings schickt.

## [kosmetisch]

**C1 — Cache nach Deploy ist KEIN reales Problem.** Flask läuft single-process (kein gunicorn-Multi-Worker-Indiz); Container-Neustart resettet die Globals (`:1174–1175`) → kein Stale-Cache mit halben Feldern. Neue Felder nach Deploy: alte v94-Clients ignorieren unbekannte JSON-Felder kompatibel. Kein Handlungsbedarf, nur dokumentieren.

**C2 — Datum-Semantik im AK festnageln.** „Datum" ist bei Ordnern mehrdeutig. AK muss deterministisch definieren: `date = max(st_mtime)` über alle `video_files` (jüngste Änderung), `size = sum(st_size)`; bei Einzeldatei = `mtime`/`size` der Datei. Sonst kann der AK-Test nicht grün-stabil formuliert werden.

**C3 — `_inbox_cache = {}` Default (`:1174`) vs `suggestions`-Liste (`:1489`).** Typ-Inkonsistenz (dict-Initialwert, Liste-Befüllung) — vorbestehend, nicht anfassen, nur Notiz, falls der Worker die Globals berührt.

**Restrisiko (nicht selbst verifizierbar, read-only):** Die Gate-A2-`--test-cwd`-Verdrahtung ist laut `scripts/gate-a2/README.md:130–133` als „offen" markiert — der autoritative Testlauf gegen den Worker-Code ist damit nicht garantiert grün-sicher; als dokumentiertes Restrisiko ins Briefing (kein Blocker für den Plan selbst).

VERDICT: REVISE — nicht wegen des Feature-Beschlusses, sondern weil K1/K2/K3 vor Worker-Start semantisch festgelegt und in die AKs gegossen werden müssen, sonst baut der autonome Worker drei plausible, aber falsche Varianten.
</task_result>
</task>

---

## advocatus zu #65 Übergabewegen (Subagent-Sitzung ses_ee517355dffep13AZM7li1gnTs, Status: completed)

<task id="ses_ee517355dffep13AZM7li1gnTs" state="completed">
<task_result>
## Risikoprüfung Übergabeweg ROADMAP #65 — Advocatus-Review

**Code-Fakten verifiziert** (Abweichungen kursiv): Alle Fakten stimmen. Ergänzung: `find_files_recursively` ist `os.walk` über die komplette Inbox (processor.py:700–709); Quarantäne = `send_to_trash` mit allowed-root-Check, aber **kein** „nur gemappte Dateien"-Schutz (trash.py:84–95). `/preview_process` TV-Zweig iteriert zweimal O(N²) über `all_files` (Kompanion-Heuristik queue_api.py:383, :552).

---

**1. Weg 1b (Ein-Job-Virtual-Folder) — Datenrisiken**

- **[kritisch] (a) Fremd-Junk in Quarantäne — bestätigt, kein Einzelfall.** `preview["junk"]` entsteht bei `project_name=""` über die **gesamte** Inbox: Junk-Heuristik queue_api.py:609–619 (verwaiste Untertitel, fremde `.nfo/.jpg/.txt`), `is_companion_of_any_video` :383 prüft gegen alle Inbox-Dateien. `explicit_junk` wird in processor.py:902–909 **ungefiltert** nach `inbox_root` gejoint und gelöscht. Clientseitiges Filtern ist ein **Fass ohne Boden**: Die Junk-Liste trägt keine Provenienz; der Client müsste `is_companion_of_any_video` + Junk-Heuristik duplizieren, um „gehört zur Gruppe" zu entscheiden. Ein „Alle-Junk"-Häkchen der JUI → Fremdlöschung.
- **[kritisch] (e) Widerlegt:** Quarantäne/`explicit_renames`-Pfad **berührt sehr wohl unmapped Dateien** — genau über `explicit_junk`/`explicit_subs` (processor.py:902–909, :965–971), nicht nur gemappte. Zusätzlich räumt „Cleanup empty subdirectories" :974–980 **ganz `inbox_root`** leer — kann einen leeren Ordner eines anderen Inbox-Projekts entfernen.
- **[wichtig] (b) Performance:** `find_files_recursively` + doppelte O(N²)-Kompanion-Schleife über die ganze Inbox (queue_api.py:88, :383, :552). Bei voller NAS-Inbox spürbar; kein Cache im Preview-Pfad.
- **[wichtig] (c) Neue Dateien während des Jobs:** Verarbeitung nutzt nur `mapping_items`/`explicit_*` (eingefroren), daher werden neue Videos nicht angefasst — **aber** `:974–980` läuft live über `inbox_root` und kann ein frisch angelegtes, noch leeres Verzeichnis löschen. 30-s-Cache (project_api:1304) ist irrelevant, betrifft nur Vorschläge.
- **[kosmetisch] (d) show_name_mismatch/Kollision:** `show_name_mismatch` (:749–770) und Staffel-Nummerierungs-Warnung (:745–748) laufen **einmal** pro Preview, nicht pro Folge — keine 11×-Vervielfachung. Aber: Show-Level-Metadaten `tvshow.nfo/poster.jpg` werden über die **ganze Inbox** als `subs` behalten (:612–617) → Fremd-Rauschen für JUI.

**2. Weg 1a (N Jobs pro Folge) — Risiken**

- **[wichtig] N× Provider-Fetch:** je Job `fetch_tvdb/tmdb/…` (queue_api.py:429–457 **und** processor.py:1045–1072) → Rate-Limits, #54-Retry-Kaskade bei 264 Folgen.
- **[wichtig] N× tvshow.nfo-Rewrite:** processor.py:1021–1039 schreibt je Job `tvshow.nfo` in `current_dir` (bei Einzeldatei = Datei-Ordner, oft `inbox_root`) — redundante Überschreibungen, `should_overwrite_nfo`-Fragen je Job.
- **[wichtig] Partieller Fehlschlag:** Job 37/264 scheitert → halbfertige Serie, kein transaktionaler Gesamtzustand; Queue-Überblick (queue_api:835–859) listet 264 Einzeljobs.
- **Daten-Sicherheit maximal:** pro Job `all_files=[eine Datei]`, Scope inhärent begrenzt — kein Fremd-Junk möglich.

**3. Weg 2 (files[]-Parameter) — Risiken**

- **[wichtig] Umfang/Regression:** queue_api (Param-Annahme :23–37), processor (Pfad-Auflösung :846–856), `build_job_pipeline`, Jobgröße (:866–872) — Änderung im meistgetesteten TV-Pfad.
- **[wichtig] Sicherheit:** `is_path_allowed`/Traversal-Validierung je Listenelement neu nötig; `send_to_trash`-Boundary reicht nicht als Eingabevalidierung.

**4. Backend- vs. Frontend-Tests**

- Weg 1a: **kein** neuer Backend-Test nötig (bestehender Einzeldatei-TV-Pfad); ggf. Frontend-Test „N POSTs".
- Weg 1b: Server unverändert, aber **ein** harter Regressions-Test dringend empfohlen: „`project_name=''`+mappings berührt exakt `mapping_keys ∪ explicit_*`, sonst nichts" (sichert den impliziten Vertrag).
- Weg 2: **zwingend** Backend-Tests (Pfadvalidierung, files[]-Konsistenz Vorschau↔Prozess, Regression).

**5. Empfehlung**

**Empfehlung: Weg 1a** für #65 (Alex' eigener Rahmung „Sammelauftrag pro Folge", deckungsgleich mit dem bestehenden Einzeldatei-Flow). Zero Backend-Change, keine Datenverlust-Fläche; Kosten (Rate-Limit, nfo-Rewrite, Queue) sind lästig, aber nicht destruktiv. Weg 1b scheidet aus: Fremd-Junk/Quarantäne + `inbox_root`-Cleanup sind nicht clientseitig abfederbar. Weg 2 ist der „richtige" Langfrist-Weg, aber überdimensioniert für die Oberflächen-Gruppierung des ersten PR.

**Harte AKs für Weg 1a:**
- AK1: Gruppen-Auswahl sendet **niemals** `project_name=""` — je selektierte Folge ein Einzeldatei-Job; Regressionstest: kein Preview/Process mit leerem `project_name` aus der Gruppen-UI erreichbar.
- AK2 (falls je Batching): Regressionstest „`project_name=''` + mappings berührt nur `mapping_keys ∪ explicit_*`; assert kein Fremd-Rename/-Quarantäne".
- AK3: `explicit_junk ⊆ Gruppen-Dateien` serverseitig prüfen, bevor :902–909 erreicht wird.
</task_result>
</task>
