# Rohoutput plan-reviewer — Kreativteam 2026-10-08 (Akt 4, #65)
Hinweis Claude Code (2026-10-09): Mechanisch aus `opencode export ses_ee2dc847cffeefAVh2xzGtKoRQ` (ceo-planner, Akt 4b–4d im #65-Worktree) abgelegt, nicht vom Moderator abgeschrieben (Lehre 59). Einzige Änderung: Trailing Whitespace entfernt. Der in Akt 4c hängengebliebene plan-reviewer-Aufruf (Subagent-Sitzung ses_ee2c4d97bffe3qpBcSH5O8ZJ1P, Modell-Stream abgerissen, von Claude Code beendet) hat keinen Output; er erscheint unten als erster Abschnitt mit Status „running“. Volle Daten: Kit `scripts/gate-a2/logs/2026-10-08-roadmap64-65/export-akt4.json`.

---

## plan-reviewer Runde 1 briefing-65 (Subagent-Sitzung ses_ee2c4d97bffe3qpBcSH5O8ZJ1P, Status: running)

Kein Output: None

---

## plan-reviewer Runde 1 briefing-65 (Neustart) (Subagent-Sitzung ses_ee2a0c18effe4BzyfDzuqWULX3, Status: completed)

<task id="ses_ee2a0c18effe4BzyfDzuqWULX3" state="completed">
<task_result>
## Beleg-Verifikation am Code (alles selbst gelesen, gezielte Ausschnitte)

**`gui/api/project_api.py`** — alle Belege bestätigt: `is_dir` nur intern (`:1320`), Einzeldatei-Filter (`:1323–1326`), `video_files.append(full_path)` (`:1342`), `tv_pattern` (`:1413`), `suggested_query = item[:match.start()].strip(' ._-')` (`:1421`, ergibt bei Treffer an Position 0 `""`), Payload-Dict `:1490–1502` mit `modified_at`/`total_size`, ohne `is_dir`; delete-project `:942–983` (Join `:962`, Sentinel-Sperre `:954`).

**`gui/static/app.js`** — bestätigt: 9 Importe `?v=95` (`:1–9`), Sentinel (`:2314`), reaktive Schleife mit Selektor `#smart-inbox-list .smart-inbox-item` + `data-project` + deleteBtn-Verdrahtung (`:2458–2491`), `deleteProject` (`:2514–2538`), `selectProject` (`:2674–2676`), Video-Endungsliste `['mp4','mkv','avi','webm','mov']` (`:3664`) + legitimer `guessSeasonAndEpisode`-Aufruf (`:3681`), `executeSeriesWorkflow`/mappings-Bau (`:4290 ff.`), `openPreviewModal` (`:10182`), Preview-Fetch (`:10259–10264`), `btn-preview-execute`/finalPayload (`:10540–10553`), Process-Fetch (`:10612–10616`), `sortInboxSuggestions` (`:12259–12306`), sessionStorage (`:12308–12334`), Sortier-Klick → Rerender (`:12383–12392`), `renderSmartInboxList` (`:12396–12497`) mit `innerHTML=""` (`:12413`), `data-project` (`:12452`), bedingungslosem Quarantäne-Knopf (`:12466–12470`, disabled-Logik `:12468`), Verdrahtung (`:12480–12489`), `handleSmartInboxClick` (`:12499`), Lucide-Inline-SVGs (`:12419–12429`).

**`gui/static/index.html`** — bestätigt: `style.css?v=48` (`:9`), Sortier-Leiste (`:461–466`), `#smart-inbox-list` (`:467`), `app.js?v=95` (`:2758`).

**`gui/api/queue_api.py`** — bestätigt: Preview-Parameter (`:20–37`), `current_dir`-Auflösung inkl. `else: current_dir = inbox_root` (`:73–89`), `video_exts` (`:89`), `is_companion_of_any_video` mit Basename-Präfix (`:378–404`, `:393`), Dreifach-Fallback `mappings.get(rel_f) or mappings.get(f) or mappings.get(basename)` (`:474`), Process-Endpunkt ohne Validierung (`:776–831`).

**`gui/workers/processor.py`** — bestätigt: `safe_move_recursive` (`:479–543`), Auffangregel `prefix_filter=None → belongs=True` (`:516–518`), Leere-Ordner-Cleanup (`:534–543`), `build_job_pipeline` (`:563–589`), `current_dir`-Auflösung (`:846–856`), `explicit_*`-Joins mit stillen `os.path.exists`-Skips (`:896–980`, konkret `:902–909`, `:958–963`, `:965–971`, `:974–980`), tvshow.nfo in `current_dir` (`:1032`), Manifest (`:986`, `:1330–1357`), `Staffel N`-Zielstruktur (`:1334`), Per-Folge-Move (Aufruf `:1498–1505`, Briefing nennt `:1496–1504` — umfasst whitelist-Aufbau, vertretbar), Meta-Verschiebung (`:1571–1580`), Show-Level-Move (Aufruf `:1594–1601`, Briefing `:1592–1600` — vertretbar).

**`gui/core/helpers.py`** — bestätigt: `is_path_allowed` prüft gegen alle allowed_roots (`:113–140`).

**`gui/static/js/parse.js`** — bestätigt: `\b(\d+)x(\d+)\b` (`:70`, matcht „1920x1080"), lockeres drittes Muster (`:74–77`).

**`gui/main.py:294–301`** — bestätigt: waitress-serve ohne `MAX_CONTENT_LENGTH`/Buffer-Limit.

**`tests/frontend/cache_busting.test.js`** — bestätigt: prüft nur Konsistenz (index.html-Version == alle Import-Versionen, ≥8 Importe; style.css/utilities.css nicht-leer) — „Lauf A bumpt nichts" bleibt damit grün, verträglich.

**ROADMAP.md:1822–1842** — bestätigt (Problem `:1826–1827`, Ausweichwege/Checkboxen `:1835`, Bestätigbarkeits-Pflicht `:1838`).

**Session-Rohoutputs:** `rueckkanal-64.md` R6 (beide Kollisionsflächen a+b) ist vollständig in AK11 übernommen; `advocatus-akt3.md` (3×[kritisch], 6×[wichtig], kosmetisch) ist vollständig in AK6/AK7/AK5/AK6(e)/ADR-65-2(b)/ADR-65-3/ADR-65-4/AK1/AK9 eingearbeitet; `grafiker-akt3.md` (Gruppenzeile, Banner, Film-Sperre, ≥2-Folgen-Regel, flache Mitgliederliste) in ADR-65-5/AK2/AK3; `produktberater-akt3.md` (Modal-Komplexitätsfalle, kein Modal-Refactor, strenges Muster ohne `1x05`) in Dissens 4/AK4/AK1. `briefing-64.md` Abschnitt 11: Task-Format, `test_cmd` (identischer Befehl), Freigabe-/Merge-Pfad — Struktur eingehalten, um Übergabe-Pflicht (11c) erweitert.

## Prüfung Alex 1–7, Schnitt, Formalia, Widersprüche

**Alex 1–7:** Alle operationalisiert — (1) AK12 + 11b Punkt 4 + Abschnitt 0; alter AK2-Satz als gestrichen dokumentiert. (2) AK13 + AK3 „pro Eintrag". (3) 11a/11b im briefing-64-Format, `test_cmd` identisch ohne eigenes `timeout` (`test_timeout_s` 600 dokumentiert), AK0 in eigene Datei `ak0-ausgangsmessung-65.md` im Worker-Image. (4) ADR-65-6 unverändert. (5) AK2/ADR-65-5 „keine Staffel-Zwischenüberschriften". (6) AK11 inkl. Kollisionstest. (7) AK9 v96/v49. Die vier Widerspruchs-Stellen (AK2, AK3, ADR-65-4, ADR-65-5) sind restlos umgeschrieben; Dissens 6 dokumentiert den Vorgang.

**Zwei-Lauf-Schnitt:** Dicht. A ohne B grün (`files[]` optional, `is_dir` additiv ohne Aufrufer, AK8 sichert Alt-Pfade inkl. Inbox-Root-Job); B ohne A nicht testbar (Schritt 0 verifiziert `is_dir` + `files`-Endpunkt). AK-Zuordnung eindeutig (AK0/AK10 beiden, Rest eindeutig [A]/[B], konsistent zu ADR-65-7). Erlaubnislisten disjunkt, gegenseitige Nicht-anfassen-Listen decken sich (A sperrt `gui/static/**` komplett, B sperrt `gui/api|core|workers/**`). Nahtstelle testfest: Key-Vertrag V1 beidseitig (AK6(f)+11a Punkt 3 serverseitig, AK4+11b Punkt 5 clientseitig), `is_dir` (AK1b + Schritt 0 B), „nie mappings ohne files" (AK12). V1–V4 gelandet als AK1b/AK5/AK6(e)(f)/ADR-65-2; R6 als AK11; R6d (serverseitiges Verbot) als abgelehnt mit Begründung + Restrisiko (Abschnitt 4 + 6) — Dissens-Pflicht erfüllt.

**Formalia:** Frontmatter korrekt (`status: draft`, `approved_on: TBD`, `approval_quote` mit ausdrücklichem Hinweis „KEINE Plan-Freigabe"); Abschnittsstruktur komplett inkl. Pflichtabschnitt 5a; 7 ADRs mit allen vier Blöcken; AKs als „Es prüft, dass …"; Lizenzabschnitt vollständig (Lucide ISC, keine neuen Third-Party-Elemente, Referenz-Apps nur als Muster); Dissens-Pflicht erfüllt (6 Dissens-Blöcke, eingekauftes Gegenargument in ADR-65-7); Aufwand mit KI/Engpass-Trennung; Git-Zustand wörtlich, Feature-Branch, kein main-Stop; Schritt 0 + STOP-Protokoll je Lauf ohne autonome AK-Anpassung.

**Interne Widersprüche (geprüft):** AK8 ↔ Abschnitt-4-Ablehnung des Server-Verbots ↔ AK12 konsistent (clientseitige Pflicht für den NEUEN Weg, Alt-Pfad-Schutz via AK8, Restrisiko dokumentiert). „Lauf A bumpt nichts" ↔ Konsistenz-Test verträglich. v95/v48 → v96/v49 korrekt. AK13 ↔ AK2/AK3 konsistent. AK12 ↔ 11b/AK13: **inkonsistent** (siehe „Nicht dicht").

## Nicht dicht

1. **AK12 vs. 11b/AK13 — Checkbox-Kandidaten widersprüchlich definiert.** AK12 (Abschnitt 3) definiert Checkboxen „nur bei … (`media_type === "tv"` UND `is_dir === false` UND nicht `isProcessing`)"; 11b Punkt 4 und die 11b-AK-Liste schließen ausdrücklich „per ‚Trotzdem als Serie freigeben' freigegebene Film-Einträge" ein, AK13 verlangt deren Ankreuzbarkeit. Da Abschnitt 3 verbindlich ist („Abschnitte 3–7 sind verbindlich; AKs sind Testfälle"), baut ein Test nach AK12-wörtlich einen AK13-Verstoß. Ein Halbsatz in AK12 („… sowie per ‚Trotzdem als Serie freigeben' freigegebene Film-Einträge (AK13)") löst es.
2. **„Alle auswählen"-Attribution widerspricht der archivierten grafiker-Position.** Abschnitt 4 („[grafiker] und [advocatus] (K2) raten für PR1 ab") ohne Akt-4-Kennzeichnung; `grafiker-akt3.md` Abschnitt 5 + Entscheidungsvorlage empfiehlt „Alle auswählen" für PR1 (allerdings: im Modal). Dissens 5 dokumentiert die Akt-4-Zustimmung, aber (a) ist Abschnitt 4:63 so nicht als Akt-4-Position gekennzeichnet und (b) ist die Akt-3-Modal-Empfehlung („Checkbox ‚Alle auswählen' fixiert oben", grafiker-akt3.md:169–183) weder umgesetzt (AK4 sperrt Modal-Refactoring) noch als verworfene Alternative dokumentiert — Dissens-Pflicht-Lücke. Auflösung hängt an den noch nicht archivierten Akt-4-Outputs; bei Nacharchivierung verifizieren, sonst Attribution korrigieren.

## Potenziale

- `sortInboxSuggestions` (generisch field/dir) bleibt für ein späteres viertes Sortierfeld „Staffel" wiederverwendbar (bereits in 5a angelegt).
- Die strenge S/E-Muster-Funktion könnte nach Lauf B als eigenes strict-Modul nach `js/parse.js` wandern, sobald `js/**` wieder offen ist.
- `files[]`-Parameter + Companion-Helper sind die natürliche Basis für #69 („Filmreihe am Stück") und könnten langfristig die O(N²)-Kompanion-Heuristik (`queue_api.py:383`) auch im Ordner-Pfad ersetzen.
- Die AK11-Gruppenzeilen-Klasse (`smart-inbox-group-row`) kann später als Drop-Ziel für Drag & Drop (#20) dienen.
- grafiker-Akt-3-Edge-Case-Hinweise (word-break für lange Seriennamen, <600px-Layout) könnten im style.css-append-Block von Lauf B still mitreisen.

---

**Verdict-Begründung:** Beleg-Verifikation sauber (alle Zeilenangaben stimmen; nur zwei um 1 Zeile versetzte Blockreferenzen, inhaltlich korrekt), Alex 1–7 vollständig operationalisiert, Schnitt dicht, Formalia erfüllt. Zwei [wichtig]-Findings betreffen die AK-Vertragskonsistenz bzw. die Belegbarkeit gegen archivierte Subagent-Positionen und sollten vor Alex' Freigabepunkt 2 behoben sein.

VERDICT: REVISE
1. [wichtig] AK12 (briefing-65.md:53) definiert Checkbox-Kandidaten exklusiv als `media_type === "tv"` UND `is_dir === false` UND nicht `isProcessing`; 11b Punkt 4 (briefing-65.md:306–309) und AK13 (briefing-65.md:54) schließen freigegebene Film-Einträge ausdrücklich ein — ein nach AK12 wörtlich gebauter Test schlägt bei AK13-Umsetzung fehl (bzw. verbietet sie). AK12-Klammer um die AK13-Freigabe ergänzen.
2. [wichtig] Abschnitt 4 (briefing-65.md:63) schreibt [grafiker] die Ablehnung von „Alle auswählen" zu, ohne Akt-4-Kennzeichnung; die archivierte Akt-3-Quelle (grafiker-akt3.md:169–183, 213, 216) empfiehlt „Alle auswählen" für PR1 (im Modal). Die Modal-Variante ist weder umgesetzt (AK4 sperrt Modal-Refactoring) noch als verworfene Alternative dokumentiert; die Auflösung (Meinungswechsel in Akt 4, Dissens 5) ist bis zur Nacharchivierung der Akt-4-Outputs unbelegbar. Bei Nacharchivierung verifizieren und Abschnitt 4:63 als Akt-4-Position kennzeichnen bzw. die Akt-3-Empfehlung als überholt dokumentieren — sonst liegt eine Verfälschung der archivierten Subagent-Position vor.
3. [kosmetisch] Akt-4-Rohoutputs ([grafiker] Kästchen-UI, [advocatus] Schnitt/R6) noch nicht archiviert — Archiv-Hinweis (briefing-65.md:136) ist ein IOU; wie in Akt 3 Runde 2 vor Freigabepunkt 2 nacharchivieren, sonst bleiben ADR-65-5-Begründung, Dissens 5, ADR-65-7 ([advocatus]-Zitate) und R6a–R6e-Zuordnung gegen die Archivdateien unbelegt.
4. [kosmetisch] ADR-65-6 (briefing-65.md:103) zitiert „Punkt 3: ‚#68 bleibt ein eigener PR'" — nach der Abschnitt-0-Nummerierung (briefing-65.md:19) ist #68 Punkt 4; zudem ist „ein eigener" eine Paraphrase in Anführungszeichen (übermittelt: „#68 bleibt eigener PR"). Punktreferenz angleichen und Zitat wörtlich oder als Paraphrase ohne Anführungszeichen kennzeichnen.
5. [kosmetisch] AK1 (briefing-65.md:41) begründet den Verzicht auf `guessSeasonAndEpisode` u. a. mit „das lockere Dritte matcht Filmtitel (:74–77)" — für keinen der genannten Testfälle („The Rock (1996).mkv" etc.) trifft das dritte Muster (parse.js:74–77) tatsächlich zu; die Aussage ist als Kategorie vertretbar, aber unbelegt. Der harte Beleg (1920x1080 über parse.js:70) trägt die Entscheidung allein; Formulierung abschwächen oder einen konkreten Treffer-Fall nennen.
6. [kosmetisch] grafiker-Akt-3-Edge-Case-Hinweise (word-break/overflow-wrap für lange Seriennamen, <600px-Layout mit flex-wrap, grafiker-akt3.md:199–201) sind weder in ADR-65-5/AKs aufgenommen noch als verworfen dokumentiert — zwei der drei Edge-Case-Lösungen des selben Abschnitts (≥2-Folgen-Regel, gemischte Inbox) sind übernommen. Aufnehmen oder als bewusst zurückgestellt dokumentieren.
7. [kosmetisch] 11a Punkt 3 (briefing-65.md:222): Tippfehler „mappings-Konistenzpruefung" → „Konsistenzpruefung".
</task_result>
</task>

---

## plan-reviewer Runde 2 briefing-65 (Subagent-Sitzung ses_ee2926665ffexAUv6M15Jud8TH, Status: completed)

<task id="ses_ee2926665ffexAUv6M15Jud8TH" state="completed">
<task_result>
# Runde-2-Prüfung `briefing-65.md` (Akt-4-Fassung, `status: draft`)

## 1. Verifikation der Runde-1-Findings

**Finding 1 [wichtig] — AK12 ↔ AK13 ↔ 11b Punkt 4 ↔ 11b-AK-Liste: BEHOBEN.** AK12 (`briefing-65.md:53`) nennt jetzt „**zusätzlich** bei den per AK13 freigegebenen Film-Einträgen"; AK13 (`:54`) „mehrere Einträge unabhängig voneinander freigebbar"; 11b Punkt 4 (`:306–316`) „sowie fuer per ‚Trotzdem als Serie freigeben' freigegebene Film-Einträge … Ordner-Eintraege (is_dir===true) sind nie anhaktbar"; 11b-AK-Liste (`:345–347`) „(tv, Einzeldatei, nicht verarbeitend, freigegebene Filme)". Alle vier Stellen tragen dieselbe Kandidatenregel; auch ADR-65-4 (`:91`) und ADR-65-5 (`:97`, „Kandidaten nach AK12") sind konsistent angebunden. Kein neuer Widerspruch entstanden.

**Finding 2 [wichtig] — „Alle auswählen"-Attribution: BEHOBEN.** Abschnitt 4 (`:63`) kennzeichnet jetzt „[grafiker] (Akt 4) und [advocatus] (K2, Akt 4)" und dokumentiert die Akt-3-Position ausdrücklich als **anderen Ort** (Modal) mit Beleg `grafiker-akt3.md:169–183, 213` — beide verifiziert: `:169` „Checkbox ‚Alle auswählen' fixiert oben" (Modal-Kontext), `:213` Entscheidungsvorlage-Zeile. Dissens 5 (`:132`) spiegelt das widerspruchsfrei („Nachzug dokumentiert, nicht Konsensverwerfung"). Abschnitt 4 ↔ Dissens 5 ↔ Archiv-Hinweis (`:136`) greifen ineinander.

**Finding 3 [kosmetisch] — Archiv-IOU: BEHOBEN (mit neuer Teil-Lücke, siehe unten).** Der Archiv-Hinweis (`:136`) benennt jetzt konkret: [grafiker]-Positionen in ADR-65-5, Dissens 5, [advocatus]-Zitate in ADR-65-7 (Schnitt-APPROVE, V1–V4, A5/A6), R6a–R6e-Zuordnung in AK11–13. Die Akt-3-Dateien sind archiviert (Verzeichnis bestätigt `*-akt3.md`); die Akt-4-Outputs fehlen noch und sind als IOU transparent markiert.

**Finding 4 [kosmetisch] — ADR-65-6 Punktreferenz: BEHOBEN.** `:103` erklärt jetzt die Nummerierungsverschiebung explizit („sein Entscheidungspunkt 3, in Abschnitt 0 als Punkt 4 aufgeführt") und kennzeichnet die Paraphrase als „sinngemäß". ABER: Durch die Klärung ist eine neue „Punkt 4"-Kollision entstanden (siehe „Nicht dicht", Punkt 2).

**Finding 5 [kosmetisch] — AK1-Begründung: BEHOBEN.** `:41` begründet jetzt mit belegten Aussagen: `\b(\d+)x(\d+)\b` matcht „1920x1080" — **verifiziert an `parse.js:70`** (exakt dieses Muster); drittes Muster `staffel|st|s … folge|ep|e|f|episode` — **verifiziert an `parse.js:74–77`** (wortgleich) — „trifft deutsche Titel-Formen bereits an Position 0, wo der Server-Schlüssel leer wird (`project_api.py:1421`)" — **verifiziert**: `suggested_query = item[:match.start()].strip(' ._-')` ergibt bei „Staffel 2 Folge 3 – Show.mkv" (Treffer an Position 0) exakt `""`. Die unbelegte „lockere Dritte matcht Filmtitel"-Aussage ist ersetzt; „The Rock (1996).mkv" wird nur noch als Testfall der eigenen Funktion geführt (kein parse.js-Muster trifft — konsistent). `app.js:3681` bestätigt den legitimen Einsatz von `guessSeasonAndEpisode` im manuellen Serien-Modus (`isManualSeriesMode`, `:3672`).

**Finding 6 [kosmetisch] — [grafiker]-Akt-3-Kantenfälle: BEHOBEN.** ADR-65-5 (`:97`) nimmt `overflow-wrap: break-word` + `flex-wrap` unter 600 px auf mit Beleg `grafiker-akt3.md:199–201` — **verifiziert** (`:199` word-break, `:201` <600px/flex-wrap); 11b Punkt 7 (`:328–331`) nimmt beide in den style.css-append-Block auf.

**Finding 7 [kosmetisch] — Tippfehler: BEHOBEN.** `:222` „mappings-Konsistenzprüfung".

**Blockreferenzen: EXAKT KORRIGIERT.** `processor.py:1498–1505` = `safe_move_recursive(current_dir, dest_dir_outbox, prefix_filter=clean_title, …)` (Per-Folge) ✓; `:1594–1601` = `safe_move_recursive(current_dir, dest_show_dir_outbox, prefix_filter=None, …)` (Show-Level) ✓. Stimmen mit AK6 (a)/(a2), ADR-65-3 und 11a Punkt 4 überein.

**Struktur-/Konsistenz-Checks (Prüfauftrag 2):** Abschnitt 0 hat 7 Punkte; ADR-Zahl 7 mit konsistenten Querverweisen (ADR-65-7 wird referenziert); Abschnittsstruktur 0–11 mit 5a/11a–11c intakt; „Abschnitte 3–7 sind verbindlich" (`:184`) vertretbar (Abschnitt 8 ist Alex-Schritt, der Handtest ist in 6/8/9 als Pflicht verankert); Erlaubnislisten ↔ AK-Zuordnung beider Läufe disjunkt und deckend (Lauf A: AK1b/AK5–AK8/AK10 ↔ `test_inbox_suggestions.py`-Ergänzung + `test_inbox_group_files.py` neu + API.md; Lauf B: AK1–AK4/AK9/AK11–AK13/AK10 ↔ `app.js`/`index.html`/`style.css`/Frontend-Test neu); `test_cmd` ohne eigenes `timeout` mit Begründung (`:184`); Schritt 0 + STOP-Protokoll je Lauf (`:275`, `:372`); Frontmatter korrekt (`status: draft`, `approved_on: TBD`, `approval_quote`-Platzhalter mit „KEINE Plan-Freigabe"). **Lizenz-Abschnitt** (Abschnitt 7) vorhanden und gepflegt: Lucide-Inline-SVG (ISC) benannt, keine neuen Third-Party-Assets → kein Lizenz-Blocker. Subagent-Positionen bis auf eine Ausnahme (unten) alle umgesetzt, abgedeckt oder begründet abgelehnt (V1–V4, A1, A6, R6d, K2/K3, grafiker-Akt-3-Positionen, produktberater-Positionen).

## 2. Nicht dicht: neue Befunde

1. **[advocatus]-Kennung „A5" ohne Behandlungsstelle:** Der Archiv-Hinweis (`:136`) führt „A5/A6" als zitierte [advocatus]-Positionen — A6 ist zugeordnet (AK9, `:50`), A1 (ADR-65-2, `:80`) und V1–V4 (ADR-65-7, `:111`) ebenfalls, aber **A5 erscheint im gesamten Briefing nur in diesem einen Archiv-Hinweis** (grep-vollständig geprüft, auch gegen den bei der Anzeige abgeschnittenen AK6-Text) — keine Zuordnung zu einer Maßnahme, kein Ausweis als abgedeckt/verworfen. Da die Akt-4-Rohoutputs noch nicht archiviert sind, ist nicht prüfbar, ob A5 eine Bedingung war, die verloren ging. Gleiches Muster abgeschwächt bei R6a/R6b/R6c/R6e (nur Sammelbezug „R6a–R6e", aber dort ist immerhin die Behandlungsstelle AK11–13 genannt).
2. **„Alex, Punkt 4"-Doppelbelegung:** ADR-65-5 (`:97`), Abschnitt 4 (`:66`) und Dissens 3 (`:128`) zitieren „(Alex, Punkt 4)" für die Staffel-Zwischenüberschriften-Entscheidung — das ist Alex' **Akt-3-**Entscheidungspunkt 4 („1–4 ja"), in Abschnitt 0 ist Staffel aber **Punkt 5**. Seit ADR-65-6 (`:103`) Abschnitt-0-Punkt 4 explizit #68 zuordnet, stehen zwei verschiedene „Punkt 4" im Raum; die Staffel-Referenzen sind — anders als die #68-Referenz — nicht gegen Abschnitt 0 geklärt.
3. **Referenz „AK12b" (`:119`):** Abschnitt 5a verweist auf „(AK12b)" — ein solcher AK ist nicht definiert (die Liste kennt AK1b, aber kein AK12b). Gemeint ist vermutlich AK12 Testfall (b); nach dem Namensmuster „AK1b = eigener AK" irreführend.
4. **Archiv-Hinweis unvollständig bzgl. R6d:** Der Hinweis (`:136`) führt als IOU-betroffen „die R6a–R6e-Zuordnung **in AK11/AK12/AK13**" — R6d wird aber auch in **Abschnitt 4** (`:61`, Weg-1b-Absatz: „[advocatus] forderte (R6d)") zitiert; diese Stelle ist vom IOU-Verzeichnis nicht abgedeckt.
5. **`media_type: "doku"` ohne definiertes Verhalten:** AK12 (`:53`) erlaubt Checkboxen nur bei `tv` + freigegebenen **Film**-Einträgen; AK3 (`:44`) definiert Sperr-Hinweis/Freigabe-Link nur für Film-Einträge. Für Doku-Einträge (`project_api.py:1414`, `:1422–1427`) ist weder Checkbox noch Freigabe-Link noch Gruppen-Button spezifiziert — Doku-Serien ohne SxxExx (mit SxxExx wären sie tv, da `tv_pattern` bei `:1417` zuerst prüft) bleiben wie heute einzeln verarbeitbar, aber der manuelle Gruppierweg ist für sie versperrt, ohne dass das als bewusste Entscheidung dokumentiert ist. Randfall, kein Datenrisiko.
6. **Einrückungsfehler im 11b-Codeblock:** `:306` („ 4. app.js/index.html …") und `:328` („ 7. Cache-Buster …") tragen ein führendes Leerzeichen vor der Nummer (inkonsistent zu den Punkten 1–3, 5, 6). Rein optisch im Worker-Text.

## 3. Gesamteinschätzung

Alle sieben Runde-1-Findings sind nachweislich behoben, die zwei Blockreferenzen stehen exakt, und die Umbauten haben die Kernstruktur (AK-Zuordnung zu Läufen, ADR-Verweise, Erlaubnislisten, STOP-Protokolle, Frontmatter, Lizenz-Abschnitt) nicht beschädigt. Der Plan ist **inhaltlich vorlegereif** — aber vor Alex' Freigabepunkt 2 sollte zwingend die A5-Klärung erfolgen (eine Zeile Zuordnung oder Ausweis als abgedeckt/verworfen; idealerweise zusammen mit der Akt-4-Nacharchivierung, wie sie die Akt-3-Analogie vor der Vorlage etabliert hat), sonst legt das Briefing Alex eine ungeklärte Subagent-Position zur Freigabe vor. Die übrigen Punkte sind Kosmetik und können mitgenommen werden, ohne die Vorlage zu blockieren.

**Potenziale (optional, keine Auflage):**
- Die Doku-Randfrage (Befund 5) ließe sich mit einem Satz an AK12/AK13 mitentscheiden (Doku verhält sich wie Film ohne Freigabe-Link — oder erhält denselben Freigabe-Link).
- Kennungs-Zuordnung künftig direkt an der Behandlungsstelle (Muster „[advocatus] A6" in AK9) — für A5 und R6a–R6e übernehmen, dann erübrigen sich Archiv-Hinweis-Ergänzungen dieser Art.
- Der „Alle auswählen"-Nachzug (Listenebene + Modal) ist in Abschnitt 4/8 sauber als Planwechsel-Freigabepunkt verankert — gutes Muster für künftige Nachzüge.

---

VERDICT: REVISE

1. [wichtig] [advocatus]-Kennung „A5" ohne Behandlungsstelle: nur im Archiv-Hinweis zitiert (`briefing-65.md:136`), anders als A6 (AK9, `:50`), A1 (`:80`) und V1–V4 (`:111`) weder einer Maßnahme zugeordnet noch als abgedeckt/verworfen ausgewiesen; bei noch nicht archivierten Akt-4-Outputs ist ein verlorener Einwand nicht ausschließbar. Vor Freigabepunkt 2 klären (Zuordnung ergänzen oder begründet ausweisen; Akt-4-Nacharchivierung vor der Vorlage).
2. [kosmetisch] „Alex, Punkt 4"-Doppelbelegung: Staffel-Referenzen (`:66`, `:97`, `:128`) meinen Alex' Akt-3-Punkt 4, kollidieren aber mit Abschnitt-0-Punkt 4 (#68), den ADR-65-6 (`:103`) jetzt explizit macht — analog zu ADR-65-6 klären (z. B. „Alex' Akt-3-Punkt 4, in Abschnitt 0 als Punkt 5 geführt").
3. [kosmetisch] Referenz „AK12b" (`:119`) auf einen nicht definierten AK; gemeint vermutlich AK12 Testfall (b) — an das Namensmuster AK1b angeglichen irreführend.
4. [kosmetisch] Archiv-Hinweis (`:136`) deckt die R6d-Nennung in Abschnitt 4 (`:61`) nicht ab (führt R6a–R6e nur „in AK11/AK12/AK13").
5. [kosmetisch] `media_type: "doku"` in der Kandidatenregel (AK12 `:53`, AK3 `:44`) ohne definiertes Verhalten — Doku-Einträge ohne SxxExx weder auto- noch manuell gruppierbar, nicht als bewusste Entscheidung dokumentiert (kein Datenrisiko).
6. [kosmetisch] Einrückungsfehler im 11b-Codeblock (`:306`, `:328`: führendes Leerzeichen vor der Punktnummer).
</task_result>
</task>

---

## plan-reviewer Runde 3 briefing-65 (Subagent-Sitzung ses_ee284d420ffeWSSnsxHJoXEgbR, Status: completed)

<task id="ses_ee284d420ffeWSSnsxHJoXEgbR" state="completed">
<task_result>
## Runde 3 (Finalrunde) — Verifikation `briefing-65.md` (Akt-4-Fassung, 389 Zeilen)

### Runde-2-Findings: Status je Zeile

1. **[wichtig] A5-Kennung — behoben.** ADR-65-7 Konsequenzen (briefing-65.md:113) ordnet A5 jetzt mit tragfähiger Begründung zu (`files[]` strenger validiert als der `project_name`-Pfad — Inbox-Konfinement zusätzlich zu `is_path_allowed`, nur Video-Endungen; LAN-Endpoint erreicht heute bereits jede Inbox-Datei). Beleg `helpers.py:113–140` stimmt: `is_path_allowed` prüft gegen alle erlaubten Roots, nicht nur Inbox.
2. **[kosmetisch] „Alex, Punkt 4" — behoben.** Abschnitt 4 (:66), ADR-65-5 (:98) und Dissens 3 (:129) sagen einheitlich „Akt-3-Entscheidungspunkt 4, in Abschnitt 0 als Punkt 5 geführt"; ADR-65-6 (:104) sagt „Entscheidungspunkt 3, in Abschnitt 0 als Punkt 4". Beide Mappings stimmen mit Abschnitt 0 überein (Punkt 5 = Staffel, Punkt 4 = #68).
3. **[kosmetisch] AK12b — behoben.** Keine „AK12b"-Referenz mehr im gesamten Session-Ordner; Abschnitt 5a (:120) sagt „AK12, Testfall (b)".
4. **[kosmetisch] Archiv-Hinweis R6d — behoben.** :137 deckt R6d jetzt ausdrücklich in Abschnitt 4 ab.
5. **[kosmetisch] `media_type: "doku"` — behoben.** AK12 (:53), Abschnitt 4 (:67 mit Begründung „Alex' Regel 2 nannte nur Film-Einträge" — verifizierbar: produktberater-akt3.md:15–16 formuliert Regel 2 ausschließlich als Film-Sperre + Ausnahme) und 11b Punkt 4 (:311–312) regeln den Ausschluss konsistent. Server-Beleg real: `project_api.py:1414` (`doku_pattern`) und `:1422–1427` (Zweig setzt `media_type: "doku"`).
6. **[kosmetisch] Einrückung 11b — behoben mit Rest.** Die Fortsetzungszeilen unter Punkten 4 (:307–319) und 7 (:331–334) fluchten jetzt mit dem Eintragspräfix; Rest siehe „Nicht dicht" Nr. 5.

### Zusatzprüfung Finalrunde

- **AK12 ↔ AK13 ↔ 11b Punkt 4:** Auf Regel-Ebene konsistent (Doku weder Auto-Kandidat noch anhaktbar, kein Freigabe-Link). ABER die 11b-Testfall-Liste (:348–350) nennt Doku nicht unter den nicht-wählbaren Fällen → „Nicht dicht" Nr. 1.
- **Abschnitt 4 ↔ Dissens 5 ↔ Archiv-Hinweis:** Konsistent — Listenebene-„Alle auswählen" verworfen, Modal-Variante aus Akt 3 als Nachzug dokumentiert; `grafiker-akt3.md:169–183` **und** `:213` verifiziert (Empfehlung existiert genau dort, im Modal).
- **ADR-65-7 ↔ AK9:** Konsistent — AK9 trägt [B], „Lauf A bumpt nichts — [advocatus] A6" (:50), 11a sagt „KEIN Cache-Buster-Bump in diesem Lauf" (:262).
- **Formales:** 7 ADRs ✓, Abschnitte 0–11 mit 5a/11a–11c vollständig ✓, Frontmatter `status: draft` / `approved_on: TBD` / Platzhalter mit „KEINE Plan-Freigabe" ✓. Lizenzabschnitt (Abschnitt 7) vorhanden und vollständig: Lucide-Inline-SVG (ISC) bereits im Projekt, keine neuen Assets/Icons, Referenz-Apps nur als Muster — keine unklare Third-Party-Lizenz, kein blockierendes Finding.
- **Beleg-Stichproben (alle neu eingefügten, alle verifiziert):** `helpers.py:113–140` ✓ · `queue_api.py:89` (video_exts, maßgebliche Liste) ✓ · `project_api.py:1414/:1422–1427` (doku_pattern-Zweig) ✓ · `grafiker-akt3.md:169–183` (Modal-„Alle auswählen") ✓. Daneben quer verifiziert: `queue_api.py:474` (Dreifach-Fallback `mappings.get(rel_f) or mappings.get(f) or mappings.get(basename)`) ✓, `app.js:12259` (`sortInboxSuggestions`) ✓, Payload-Dict `project_api.py:1490–1502` (mit `modified_at`/`total_size`, ohne `is_dir`) ✓, `index.html:9`/`:2758` + `app.js:1–9` (v95/v48, neun Importe) ✓, `index.html:461–466`/`:467` ✓, AK11-Belege `app.js:2314/:2458/:2514` ✓, `parse.js:70/:74–77` ✓, produktberater.md:115–117 („primäre Falle: DOM-Performance") ✓.
- **AK6-Schwanz (Zeile 47 > 2000 Zeichen, Anzeige abgeschnitten):** Per grep bestätigt — (f) schließt mit dem `queue_api.py:474`-Zitat, es gibt keine (g)-Klausel; Klauselstruktur (a), (a2), (b)–(f) vollständig und deckungsgleich mit ADR-65-2/3 und 11a.
- **Akt-3-Subagent-Positionen (archiviert, geprüft):** Keine wesentliche verloren — grafiker-Edge-Cases (`:199–201`) in ADR-65-5 übernommen, „Gruppe mit 1 Folge" → AK2 (≥2), Server-Dedup abgelehnt + Dissens 2, Modal-„Alle auswählen" als Nachzug dokumentiert; produktberater-akt3 (MVP-Schnitt, #68-Veto, kein Modal-Refactor, keine doppelte Sortierlogik, v95→v96) vollständig eingearbeitet. Ein Rendering-Detail geht undokumentiert auseinander → „Nicht dicht" Nr. 3.
- **Vorlegereife:** **Ja, unter der dokumentierten IOU-Bedingung.** Das IOU ist im Briefing selbst verankert (:137), das Frontmatter behält die Plan-Freigabe bewusst offen, und die Akt-4-Entscheidung ist ehrlich als „übermittelt von Claude Code" gekennzeichnet — korrekte Behandlung nach der Herkunfts-Grundregel.

### Nicht dicht (neue Befunde, alle kosmetisch)

1. 11b-Testfall-Liste (:348–350) nennt Doku-Einträge nicht unter den nicht-wählbaren Fällen (nur „Ordner- und Verarbeitungslauf-Einträge"), obwohl AK12 (:53, verbindlich) und 11b Punkt 4 sie ausschließen — ein Worker, der nur der 11b-Liste folgt, lässt den Doku-Testfall weg.
2. AK12 ordnet „nicht isProcessing" nur der tv-Klausel zu; die Film-Freigabe-Klausel (AK13) trägt keinen isProcessing-Guard. ADR-65-5 („disabled analog zum Quarantäne-Knopf bei isProcessing") und die 11b-Liste („Verarbeitungslauf-Einträge nicht wählbar") lesen es generisch — Absicht gedeckt, AK12-Formulierung ambivalent.
3. Auflösung der konkurrierenden Film-Sperre-Renderings ist nicht als Dissens dokumentiert: grafiker-akt3:142 empfiehlt „deaktivierter Button + Tooltip", produktberater-akt3:16 „klare Warnung + Sekundär-Button"; AK3 (:44) entscheidet still zugunsten der Warnung-Variante.
4. Die IOU-Aufzählung im Archiv-Hinweis (:137) ist nicht vollständig — nicht genannt: [advocatus] A1 (ADR-65-2), K1/K4 (ADR-65-5 Begründung), K3 (Dissens 2), V3 (AK5), V4 (AK6), A6 (Zitatstelle ist AK9, nicht ADR-65-7), [advocatus] K2 (Abschnitt 4 „Alle auswählen"), [grafiker] sessionStorage-Vorschlag (Verbleibende Risiken :145). Ein Review nach Nacharchivierung, der der Liste folgt, prüft diese Zitierstellen nicht.
5. Einrückungs-Rest im 11b-Block: Die Nummern „ 4."/:307 und „ 7."/:331 tragen weiterhin ein Leerzeichen gegenüber Punkten 1–3/5/6, und Punkt 3 nutzt 4-Space-Fortsetzung bei 3-Zeichen-Präfix — rein optisch im fenced text-Block, ohne Funktionsauswirkung auf den Worker-Auftrag.

**VERDICT: APPROVE**

1. [kosmetisch] 11b-Testfall-Liste (briefing-65.md:348–350): Doku-Einträge unter den nicht-wählbaren Fällen ergänzen (Spiegel zu AK12 :53 und 11b Punkt 4 :311–312).
2. [kosmetisch] AK12 (briefing-65.md:53): isProcessing-Guard explizit auch für freigegebene Film-Einträge formulieren (Deckung aktuell nur über ADR-65-5 :98 und 11b-Testliste :350).
3. [kosmetisch] Film-Sperre-Rendering (AK3, briefing-65.md:44): Abweichung von grafiker-akt3:142 (deaktivierter Button + Tooltip) zugunsten der produktberater-Variante (produktberater-akt3.md:16) als Dissens-/Verwurf-Zeile dokumentieren.
4. [kosmetisch] Archiv-Hinweis (briefing-65.md:137): IOU-Aufzählung um die weiteren Akt-4-Zitierstellen ergänzen (A1, K1–K4, V3/V4, A6-in-AK9, K2-in-Abschnitt-4, grafiker-sessionStorage) oder als „u. a." kennzeichnen.
5. [kosmetisch] 11b-Block (briefing-65.md:307, :331): führende Leerzeichen vor „4."/"7." angleichen (Nummern auf Spalte 0 wie Punkte 1–3/5/6).

Alle sechs Runde-2-Findings sind behoben; keine neuen inhaltlichen Widersprüche zwischen AKs, ADRs, Abschnitt 4, Dissensen und Worker-Aufträgen; alle neu eingefügten Belege stimmen am Code. Die fünf Restpunkte sind kosmetisch und können vor der Vorlage an Alex in einer Mini-Nachbesserung mitlaufen oder bewusst mitgenommen werden — keiner berührt die Plan-Substanz. Vorlegereif für Freigabepunkt 2: **ja**, unter der dokumentierten Bedingung, dass Claude Code die Akt-4-Rohoutputs vor der Vorlage nacharchiviert.

**Potenziale-Block:**
- Der Zwei-Lauf-Schnitt mit dateiebenen disjunkten Erlaubnislisten + je-Lauf-AK0-Messung (ADR-65-7) ist ein wiederverwendbares Muster für künftige Server-/Oberflächen-Features — ebenso der explizite Nahtstellen-Vertrag (Key-Vertrag V1 + `is_dir`-Semantik) als Test-fest formulierte Annahme zwischen getrennten Läufen.
- Der ehrliche Umgang mit der Akt-4-Entscheidung („übermittelt von Claude Code … KEINE Plan-Freigabe" im Frontmatter) ist ein vorbildliches Muster für die Herkunfts-Grundregel und lohnt sich als Kit-Regel-Kandidat.
- Der „bewusste Scope-Enge mit Nachzug, nicht still vorausgesetzt"-Eintrag (Doku, Abschnitt 4 :67) ist ein gutes Template für künftige Auschluss-Entscheidungen.
</task_result>
</task>
