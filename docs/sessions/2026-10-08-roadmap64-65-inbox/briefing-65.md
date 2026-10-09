---
kind: plan
status: approved
approved_by: alex
approved_on: 2026-10-09
approval_quote: "1–2 wie empfohlen, starte Lauf A"
source: roadmap#65
---

# Feature Briefing: #65 — „Als Serie gruppieren": SxxExx-Erkennung + manuelle Auswahlkästchen mit Übergabe als Serien-Job (Weg 2), umgesetzt in zwei Gate-A2-Läufen

## 0. Änderungsstand Akt 4 (nach Freigabepunkt 2-Runde 1)

Alex entschied am 2026-10-08 (wörtlich: „ist gemergt; 1–3 wie empfohlen", übermittelt von Claude Code):

1. **Manuelle Auswahlkästchen kommen in PR1** (bisher verworfen): Checkboxen bei Serien-Einzeldateien (`media_type: "tv"`, `is_dir: false`) plus Knopf „Ausgewählte als Serie gruppieren" über denselben `files[]`-Weg. Grundlage: Alex' frühere Festlegung „Erkennung + Vorschlag + Auswahlkästchen" und ROADMAP.md:1835 („auch ohne automatische Erkennung bedienbar"). Der frühere AK2-Satz „ein neuer Mehrfach-Auswahlweg wird in PR1 NICHT eingeführt" ist gestrichen.
2. **Regel 2 präzisiert:** Film-Einträge bleiben gesperrt; „Trotzdem als Serie freigeben" gilt **pro Eintrag** (der Eintrag wird ankreuzbar) statt „genau ein Eintrag insgesamt".
3. **Umsetzung über Gate-A2** (nicht Antigravity direkt), **geschnitten in zwei aufeinander aufbauende Läufe** (A = Server, B = Oberfläche), je mit eigener Erlaubnisliste, jeweils für sich grün.
4. **#68 bleibt eigener PR** (ADR-65-6 unverändert).
5. **Keine Staffel-Zwischenüberschriften** in PR1.
6. **R6 aus `rueckkanal-64.md`** (Gruppen-Pseudo-Eintrag vs. `deleteProject`/`data-project`) wird als AK11 aufgenommen.
7. Cache-Buster-Ausgang nach gemergtem #64: `app.js?v=95` (`index.html:2758`, alle neun Importe `app.js:1–9`), `style.css?v=48` (`index.html:9`) → #65: v96 / v49 (falls `style.css` geändert).

**Prüfstand:** plan-reviewer Runde 1 REVISE (2 wichtig, 5 kosmetisch — alle eingearbeitet), Runde 2 REVISE (1 wichtig: [advocatus]-Kennung A5 ohne Behandlungsstelle, 5 kosmetisch — alle eingearbeitet), **Runde 3 APPROVE** (5 kosmetische Restpunkte, in derselben Fassung nachgeführt: Doku-Fall in der 11b-Testliste, `isProcessing`-Guard für freigegebene Filme in AK12/AK13, Dissens 7 zur Film-Sperren-Darstellung, IOU-Vollständigkeit im Archiv-Hinweis, Einrückung im 11b-Block). Keine inhaltliche Substanzänderung nach dem APPROVE.

## 1. Problemstellung

Mehrere Einzeldateien mit SxxExx-Namen in der Inbox gehören oft zu einer Serie; bisher muss jede Datei einzeln verarbeitet werden (`ROADMAP.md:1826–1827`). Verifizierter Ist-Zustand auf dem gemergten #64-Stand: einzelne Videodateien direkt im Inbox-Ordner werden zu JE WEILS EINEM Smart-Inbox-Eintrag (`gui/api/project_api.py:1323–1326, :1342`); der Server klassifiziert sie per `tv_pattern` (`:1413`) bereits als `media_type: "tv"` und setzt `suggested_query` auf den Namensanteil VOR dem Treffer (`:1421`) — ein brauchbarer Gruppenschlüssel ohne neue Serverlogik. Das Payload-Dict (`:1490–1502`) enthält seit #64 `modified_at`/`total_size`, aber **kein** `is_dir` (der Ordner-/Datei-Diskriminator existiert nur serverintern, `:1320`).

Alex hat Weg 2 gewählt („Alex: ‚1–4 ja, Regeln 1–3 ja'", 2026-10-08): **Dateiliste `files[]` an den Server**, Vorschau/Prozess behandeln die Liste wie einen Ordner; Gruppierung geschieht oberflächlich als „virtueller Ordner", **ohne** Datei-Verschieben in der Inbox. Der Abkürzungsweg `project_name=""` ohne `files` wurde read-only verworfen (Belege in `65-uebergabe-optionen.md`). Mit Akt 4 kommt die **manuelle Auswahl** hinzu, weil die automatische Erkennung Fälle wie `1x05` oder „Staffel 2 Folge 3 – Show.mkv" (leerer `suggested_query`, `:1421` ergibt bei Treffer an Position 0 `""`) bewusst nicht erfasst.

Grundlage dieses Briefings ist der **gemergte #64-Stand** (PR #148, Merge `6152839`): Sortier-Leiste `index.html:461–466`, `sortInboxSuggestions` `app.js:12259–12306`, `sessionStorage`-Zustand `app.js:12308–12334`, Payload mit `modified_at`/`total_size`, Cache-Buster v95/v48.

## 2. Zielnutzer

Alex: Er sieht 264 Einzeldateien einer Serie als EINE Gruppe (automatisch vorgeschlagen oder manuell angehakt), bestätigt einmal, und die Serie läuft als EIN Auftrag durch den bewährten Serien-Flow (Staffel-Struktur entsteht wie heute erst im Ziel durch `Staffel N`-Ordnung, `processor.py:1334`). Kein externer Nutzer.

## 3. Akzeptanzkriterien

Jedes AK trägt den Lauf, in dem es fällt: **[A]** = Lauf A (Server), **[B]** = Lauf B (Oberfläche).

- [ ] **AK0 — Ausgangsmessung [A und B]:** **Claude Code** misst VOR jedem Gate-A2-Lauf im Worker-Image (kein Testlauf auf dem Host) und schreibt die wörtlichen Ausgaben mit Exit-Code in die eigene Datei `ak0-ausgangsmessung-65.md` (zwei Abschnitte: Basis für Lauf A = `main` nach #64-Merge `6152839`; Basis für Lauf B = `main` nach Merge von Lauf A). Befehl wie Abschnitt 11 (`test_cmd`). Der Worker selbst führt nur die im Lauf gesetzten Tests aus.
- [ ] **AK1 — strenges Erkennungsmuster für die AUTOMATISCHE Gruppierung (Regel 1) [B]** (Frontend-Test `tests/frontend/inbox_group.test.js`): Es prüft, dass die neue, EIGENE Extraktionsfunktion in `app.js` (KEIN Aufruf von `guessSeasonAndEpisode` aus `js/parse.js` — deren `\b(\d+)x(\d+)\b` matcht „1920x1080" (`parse.js:70`), und deren drittes Muster `staffel|st|s … folge|ep|e|f|episode` (`:74–77`) deutsche Titel-Formen bereits an Position 0 trifft, wo der Server-Schlüssel leer wird (`project_api.py:1421`) — als Automatik-Grundlage also unzuverlässig. Der harte Beleg gegen `parse.js` für die Automatik ist `:70`; die Funktion bleibt im bestehenden manuellen Modus weiterhin legitim im Einsatz (`app.js:3681`)) genau diese Fälle trifft: `Show.S01E01.720p.mkv` → S01E01; und NICHT automatisch gruppiert werden: `Movie.1920x1080.x264.mkv`, `The Rock (1996).mkv`, `Show.1x05.mkv`, `Staffel 2 Folge 3 – Show.mkv`. Die zuletzt genannten Fälle sind ausdrücklich die Zielgruppe des manuellen Wegs (AK12/AK13), nicht der Automatik.
- [ ] **AK1b — Payload-Feld `is_dir` [A]:** Es prüft in `tests/test_inbox_suggestions.py` (nur ergänzt, bestehende Fälle unverändert), dass jeder Eintrag von `/api/inbox/analyze` zusätzlich `is_dir` (bool) liefert, und zwar **am Diskriminator selbst festgemacht**: ein Ordner mit **genau einer** Videodatei liefert `is_dir: true` (nicht `false`, nur weil `video_count === 1`), eine einzelne Videodatei `false`; die bestehenden Felder bleiben unverändert (additiv, wie in #64). Begründung der Verschärfung: [advocatus] fand, eine Implementierung als `video_count > 1` wäre bei „Feld existiert"-Prüfung grün durchgerutscht und hätte 1-Video-Ordner fälschlich gruppierbar gemacht.
- [ ] **AK2 — automatische Gruppierung in der sortierten Liste [B]:** Es prüft, dass Auto-Vorschlag/Gruppe NUR Einträge mit `media_type === "tv"` UND `is_dir === false` betrifft, erst ab ≥2 Treffern mit gleichem, NICHT-LEEREM Gruppenschlüssel `suggested_query`; dass leere `suggested_query` nie automatisch gruppiert werden (Testfall „Staffel 2 Folge 3 – Show.mkv"); dass Ordner-Einträge (`is_dir === true`) nie gruppiert werden (Testfall: Ordner mit genau 1 Video); dass die Gruppe als PSEUDO-EINTRAG mit `project` = Gruppenname, `modified_at` = Maximum der Mitglieder, `total_size` = Summe der Mitglieder durch dieselbe `sortInboxSuggestions` (`app.js:12259`) sortiert teilnimmt; dass Mitglieder innerhalb der Gruppe unabhängig von der Listen-Sortierung nach (Staffel, Folge) numerisch geordnet sind. Einträge mit leerem Schlüssel bleiben zusätzlich manuell gruppierbar (AK12) — der frühere Ausschluss eines Mehrfach-Auswahlwegs ist gestrichen.
- [ ] **AK3 — Vorschlag + Bestätigung (kein Auto-Verarbeiten) [B]:** Es prüft, dass der Info-Banner „Als Serie gruppieren" (Serienname, N Folgen, erkannte Staffeln) über der Sortier-Leiste erscheint und die Gruppierung erst nach Klick anwendet; „Ignorieren" blendet den Banner für die Browser-Sitzung aus (`sessionStorage`); Film-Einträge zeigen keinen Gruppen-Button, sondern den Sperr-Hinweis und dezent den Ausweich-Link „Trotzdem als Serie freigeben" — **pro Eintrag** (AK13).
- [ ] **AK4 — Übergabe ans bestehende Vorschau-Modal [B]:** Es prüft, dass „Als Serie gruppieren" (Banner) wie der Sammelknopf (AK12) in den Serien-Modus wechselt, die Suche mit dem Gruppennamen vorfüllt und die Mitgliederliste (Dateinamen + per AK1 bzw. Nutzereingabe ermittelte S/E-Werte) als `files` + `mappings` in die `basePayload` eingehen (Muster `app.js:10259–10264` Preview-Fetch, `app.js:10612–10616` Process-Fetch); dass `mappings`-Schlüssel **exakt** die `files`-Strings sind (Vertrag V1, ADR-65-2); dass das Modal selbst NICHT refaktoriert wird (keine Virtualisierung, keine Staffel-Abschnitte); dass die Vorschau exakt die Gruppen-Dateien (+ Begleitdateien) zeigt.
- [ ] **AK5 — Server-Validierung `files[]` [A]** (Backend-Test `tests/test_inbox_group_files.py`): Es prüft, dass `/preview_process` und `/process` mit optionalem `files`-Parameter dieselbe geteilte Helper-Funktion (neu in `gui/core/helpers.py`) nutzen und jeder Eintrag abgelehnt wird, der absolut ist, `..` enthält, dessen `os.path.realpath` nicht unterhalb `realpath(inbox_root)` liegt (Inbox-Konfinement ZUSÄTZLICH zu `is_path_allowed`, da dieses nur gegen ALLE erlaubten Roots prüft, `helpers.py:113–140`), nicht existiert oder keine Server-Video-Endung hat — **der Fall „Ordnername / Nicht-Videodatei" wird explizit getestet** (Deckung des manuellen Wegs, [advocatus] V3): ein Ordner-Eintrag in `files[]` → HTTP 400, kein stilles Filtern. Groß-/Kleinschreibungs-Duplikate werden dedupliziert; die Endungsliste `queue_api.py:89` ist die maßgebliche Liste des Verarbeitungspfads (weitere Listen wie `project_api.py:1321` bleiben unberührt — der Client führt keine eigene); ungültige Eingabe → HTTP 400 mit klarer Fehlermeldung.
- [ ] **AK6 — Scope-Festlegung des `files[]`-Jobs [A]:** Es prüft mit einem tmp-Inbox-Aufbau {Gruppe: 3 Folgen + 1 fremde Untertitel-Datei zur Gruppe; Fremdprojekt: Videodatei + Untertitel + `.nfo` + leerer Unterordner; **adversarische Kollisionsdatei**: fremde Nicht-Videodatei, deren Name mit dem `clean_title` einer Gruppenfolge beginnt}, dass ein ausgeführter `files[]`-Job AUSSCHLIESSLICH Gruppe ∪ serverseitig ermittelte Begleitdateien berührt: (a) die Show-Level-Auffangregel `safe_move_recursive(prefix_filter=None)` (`processor.py:516–518`, Aufruf `:1594–1601`) wird bei `files[]`-Jobs übersprungen; (a2) die Per-Folge-Verschiebung `safe_move_recursive(prefix_filter=clean_title)` (`:1498–1505`) wird auf die Helper-Scope-Menge begrenzt — ihr rekursiver Walk über `current_dir` (= Inbox-Root, `:491`) darf keine Präfix-Treffer fremder Dateien einsammeln, und ihr interner Leere-Ordner-Cleanup (`:534–543`) darf bei `src_dir == inbox_root` keine fremden leeren Ordner in die Quarantäne verschieben; die Kollisionsdatei bleibt unberührt; (b) der Inbox-Root-Leerordner-Cleanup (`:974–980`) wird übersprungen — der leere Fremdordner bleibt; (c) `tvshow.nfo`/Poster/Fanart werden bei `files[]`-Jobs NICHT in den Inbox-Root geschrieben (`:1032`), sondern direkt in den Outbox-Serienordner; die Meta-Verschiebung aus `current_dir` (`:1571–1580`) entfällt; (d) `explicit_junk`/`explicit_subs`-Einträge außerhalb der Scope-Menge → Job bricht LAUT ab, bevor irgendetwas bewegt wurde (`:902–909`, `:965–971`); (e) **`mappings`-Schlüssel außerhalb `files` → ablehnender Fehler in Preview UND Process, je eigenem Testfall** ([advocatus] V4: die Endpunkte haben getrennte Validierungsstränge, `queue_api.py:19–772` vs. `:776–831`; ein „UND" im Fließtext reicht nicht); (f) **Key-Vertrag V1:** es prüft, dass bei `files[]`-Jobs die `mappings`-Zuordnung ausschließlich über den mit `files[]` identischen String greift — der dreifache Fallback `mappings.get(rel_f) or mappings.get(f) or mappings.get(basename)` (`queue_api.py:474`) darf bei `files[]`-Jobs nicht still auf abweichende Schreibweisen ausweichen.
- [ ] **AK7 — TOCTOU laut statt still [A]:** Es prüft, dass eine zwischen Preview und Ausführung gelöschte/verschobene `files[]`-Datei den Job in den Fehlerstatus bringt mit namentlicher Nennung (heute: stiller Skip bei `os.path.exists`-False, `processor.py:958–963, :965–971, :902–909` — für `files[]`-Jobs umdefiniert).
- [ ] **AK8 — Abwärtskompatibilität [A]:** Es prüft, dass alle Pfade OHNE `files`-Parameter byte-genau heutiges Verhalten zeigen (Ordner-Projekt, Einzeldatei-Projekt, Movie, **Inbox-Root-Job `project_name=""` ohne `files`** — der bestehende Weg „unsortierte Einzeldateien verarbeiten" bleibt ausdrücklich unverändert, `queue_api.py:78–79`, `processor.py:855–856`); die bestehende Suite bleibt grün, und ein zusätzlicher Regressionstest sichert einen tv-Einzeldatei-Job; `build_job_pipeline` bleibt unverändert (`processor.py:563–589`).
- [ ] **AK9 — Cache-Buster [B]:** `app.js?v=96` in `index.html:2758` UND allen neun ES-Modul-Importen `app.js:1–9`; `style.css?v=49` in `index.html:9`, falls `style.css` geändert wird (erwartet: ja, für Checkbox-/Bulk-Leiste-Blöcke); `tests/frontend/cache_busting.test.js` bleibt grün (prüft Konsistenz; der Bump selbst ist über Abschnitt 11 + Review abgesichert). **Lauf A bumpt nichts** (kein Frontend-Artefakt geändert — [advocatus] A6).
- [ ] **AK10 — Hygiene [A und B]:** `git diff --check` sauber; Tests schreiben nur in tmp-Verzeichnisse; keine echten Timer ohne Abräumen; keine Secrets; `.env` wird nie gelesen.
- [ ] **AK11 — Gruppenzeile ohne Löschpfad (R6) [B]:** Es prüft (Testfall in `tests/frontend/inbox_group.test.js`), dass ein Gruppen-Pseudo-Eintrag **keinen** Quarantäne-Knopf rendert (heute rendert `renderSmartInboxList` ihn bedingungslos, `app.js:12466–12470`, Verdrahtung `:12480–12489`; die reaktive Schleife `app.js:2458–2491` tut dasselbe über `data-project`) und **kein `data-project`** trägt, das `deleteProject(...)` (`app.js:2514–2538`) bedienen könnte — konkret: Gruppenzeilen nutzen eine eigene Klasse (`smart-inbox-group-row`) und einen eigenen Attribut-Schlüssel (z. B. `data-group-key`), sodass der bestehende Selektor `#smart-inbox-list .smart-inbox-item` (`app.js:2458`) sie nie erfasst. **Kollisionstest:** eine Gruppe mit Namen „Show" UND ein realer Ordner-Eintrag „Show" → es wird kein Löschpfad auf den Ordner aufgebaut (`project_api.py:942–983` löst `project` zu `os.path.join(inbox_root, project)` auf). Zusätzlich: kein Pseudo-Eintrag mit Schlüssel `""` oder `__inbox_recursive__` (Sentinel, `app.js:2314`, serverseitig gesperrt u. a. `project_api.py:954`).
- [ ] **AK12 — manuelle Auswahlkästchen + Sammelknopf [B]:** Es prüft, dass Checkboxen nur bei befügbaren Kandidaten erscheinen (`media_type === "tv"` UND `is_dir === false` UND nicht `isProcessing`; **zusätzlich** bei den per AK13 freigegebenen Film-Einträgen — für die ebenfalls der `isProcessing`-Guard gilt, ADR-65-5 — Ordner-Einträge, laufende Projekte und Doku-Einträge erhalten **keine** aktivierbare Checkbox, Doku-Einträge auch keinen Freigabe-Link (bewusste Scope-Enge, Abschnitt 4)), dass ein Knopf „Ausgewählte als Serie gruppieren" mit Zähler („N ausgewählt") und „Auswahl aufheben" in einer Bulk-Leiste zwischen Sortier-Leiste (`index.html:461–466`) und `#smart-inbox-list` (`index.html:467`) erscheint, sobald ≥1 Auswahl besteht, dass die Auswahl in einem **DOM-unabhängigen JS-Zustand** (Set über die Projekt-/Dateinamen) gehalten und beim erneuten Rendern wiederhergestellt wird — Testfälle: (a) `renderSmartInboxList` leert und baut die Liste neu (`app.js:12413`), die Auswahl bleibt erhalten; (b) Sortier-Klick (`app.js:12383–12392`) wirft die Auswahl nicht zurück; (c) doppeltes Anhaken ist idempotent (kein Duplikat in `files[]`); dass der Sammelknopf die Auswahl über denselben `files[]`-Weg übergibt wie die Auto-Gruppe (AK4) und dabei **nie** `mappings` ohne `files` sendet (sonst wäre es der verworfene Weg 1b).
- [ ] **AK13 — Film-Ausnahme PRO EINTRAG [B]:** Es prüft, dass „Trotzdem als Serie freigeben" genau den einen Eintrag ankreuzbar macht (badge-artiger Hinweis am Eintrag), dass mehrere Einträge unabhängig voneinander freigebbar sind (die frühere „genau EIN Eintrag"-Grenze entfällt, Alex-Präzisierung Punkt 2), dass eine Freigabe **keine** automatische Gruppenbildung auslöst (nur Ankreuzbarkeit) und dass der freigegebene Eintrag ebenfalls nicht ankreuzbar ist, solange er verarbeitet wird (`isProcessing`-Guard wie bei den tv-Kandidaten), und dass die Übergabe einer freigegebenen Einzeldatei den relativen Pfad dieser Datei als `files[]`-Eintrag enthält (Semantik: `The Rock (1996).mkv` → `files: ["The Rock (1996).mkv"]`, kein Ordnerpfad).

## 4. Bewusst verworfen (Scope-Eingrenzung)

- **Datei-Verschieben in der Inbox** (Serie-/Staffelordner anlegen): Alex-Bindung, „rein auf der Oberfläche".
- **Drag & Drop / manuelles Ziehen zwischen Gruppen:** Folgepunkt, Bezug ROADMAP #20 (Alex: Regel 3).
- **„Filmreihe am Stück verarbeiten":** ROADMAP #69 (Alex: Regel 3); die neuen Checkboxen sind die Vorarbeit dafür, aber kein Film-Sammelweg in PR1.
- **Weg 1b (`project_name=""` + mappings ohne Server-Änderung):** verworfen mit Belegen — Auffangregel, Subs/Junk-Joins und Root-Cleanup erreichen dabei fremde Inbox-Dateien (`65-uebergabe-optionen.md`, `processor.py:902–909, :965–971, :1594–1601`); [produktberater] hatte 1b befürwortet, [advocatus] widersprach, die Nachprüfung bestätigte die Widerspruchs-Belege. **Neu in Akt 4:** [advocatus] forderte (R6d) zusätzlich ein serverseitiges Verbot von `mappings` ohne `files`. Das ist **abgelehnt**, weil der bestehende Inbox-Root-Job („unsortierte Einzeldateien verarbeiten") genau diese Kombination heute legitim nutzt (`queue_api.py:78–79`, `processor.py:855–856`) und AK8 ihn byte-genau verlangt — ein Server-Verbot wäre ein Verhaltenwechsel an einem Alt-Pfad (= #68-Nachbarschaft, eigenes Risikoprofil). Stattdessen: clientseitige Pflicht AK12 („nie `mappings` ohne `files`") plus dokumentiertes Restrisiko (Abschnitt 6).
- **Weg 1a (N Einzel-Jobs):** sicher, aber 264 Aufträge/Provider-Fetches widersprechen Alex' „ein Ordner"-Bild; nur dokumentierter Fallback.
- **„Alle auswählen" in der Inbox-Liste:** [grafiker] (Akt 4) und [advocatus] (K2, Akt 4) raten für PR1 ab — ein unbeabsichtigter Massen-Job über 264 Einträge ist das genaue Gegenteil des Bestätigungscharakters. PR1: einzeln ankreuzen + „Auswahl aufheben"; ein expliziter „Alle Serien-Einzeldateien auswählen"-Knopf bleibt Nachzug. **Abgrenzung zur archivierten Akt-3-Position:** [grafiker] hatte in Akt 3 eine „Alle auswählen"-Checkbox **im Vorschau-Modal** empfohlen (`grafiker-akt3.md:169–183, 213`) — das ist ein anderer Ort und wird von AK4 nicht gebaut (Modal bleibt unangetastet); es ist bewusst als Nachzug verschoben, nicht als Konsens verworfen.
- **Checkbox-Sperre bei unbestätigtem Banner:** [grafiker] schlug vor, Checkboxen zu deaktivieren, solange ein Auto-Vorschlag unbestätigt ist. **Verworfen** — das erzeugt eine unnötige Zustandskopplung (Banner × Auswahl × Sortierung) und mehr Testfälle, während beide Wege in derselben `files[]`-Übergabe landen und damit funktional keinen Konflikt haben. Begründung der Abweichung in Abschnitt 6 (Dissens 5).
- **Server-seitige Deduplizierung „gemischte Inbox" (grafiker-Vorschlag):** abgelehnt — wäre neue Serverlogik + stilles Ignorieren; gruppiert wird nur, was `is_dir === false` ist.
- **Einklappbare Staffel-Abschnitte im Vorschau-Modal, Virtual Scrolling, Staffel-Zwischenüberschriften:** PR1 bleibt flach mit SxxExx-Kennzeichen (Alex' Akt-3-Entscheidungspunkt 4, in Abschnitt 0 als Punkt 5 geführt); [produktberater] hatte die Modal-DOM-Performance als „primäre Komplexitätsfalle" benannt — Dissens 4, Restrisiko.
- **Doku-Einträge im manuellen Weg:** bewusst **nicht** gruppierbar in PR1 — weder Auto-Kandidat (nur `media_type === "tv"`), noch anhaktbar, noch mit Freigabe-Link (AK12/AK13). Alex' Regel 2 nannte ausdrücklich nur Film-Einträge als Ausnahme; Doku-Serien ohne SxxExx-Muster bleiben wie heute einzeln verarbeitbar. Wer Doku-Gruppen will, braucht eine eigene Entscheidung (Nachzug, nicht still vorausgesetzt).
- **Gruppen-Editier-UI (Folgen zwischen Gruppen verschieben, Schlüssel umbenennen):** nicht in PR1; Korrektur über Abwählen im Modal — `ROADMAP.md:1838` („Vorschlag muss vor Ausführung bestätigbar bleiben").
- **Änderung von `js/parse.js`/`guessSeasonAndEpisode`:** die Funktion hat legitime andere Nutzer (manuelle Titel-Erkennung, `app.js:3681`); #65 bekommt ein eigenes strenges Muster in `app.js`.

## 5. ADR-Blöcke

### ADR-65-1: Übergabe als Server-Parameter `files[]` (Weg 2)
- **Entscheidung:** `/preview_process` und `/process` erhalten optional `files: [relative Pfade]`; bei gesetztem `files` wird die Dateiliste wie ein Ordner-Projekt behandelt (Arbeitsbasis Inbox-Root, Datei-Menge = validierte Liste ∪ Begleitdateien), `project_name` wird dann **nicht** zur Pfadauflösung benutzt. Ohne `files` bleibt alles unverändert (AK8).
- **Alternativen:** Weg 1a (N Jobs); Weg 1b (verworfen, belegt); serverseitiges Verbot von `mappings` ohne `files` (verworfen, Abschnitt 4).
- **Begründung:** Alex-Entscheidung „1–4 ja" + „1–3 wie empfohlen"; erfüllt „virtueller Ordner" mit EINEM Auftrag und begrenztem, serverseitig erzwungenem Scope.
- **Konsequenzen:** Backend-Eingriff im meistgetesteten Verarbeitungspfad; API.md-Abschnitte `/preview_process` + `/process`; Job-Params wachsen mit Gruppengröße (264 Einträge ≈ < 100 KB JSON; `MAX_CONTENT_LENGTH` ist code-seitig nicht gesetzt, waitress-Default ~1 GB, `gui/main.py:294–301`).

### ADR-65-2: Geteilter Group-Scope-Helper in `gui/core/helpers.py` + String-Vertrag
- **Entscheidung:** Eine neue, von Preview UND Process genutzte Funktion (a) validiert `files` (AK5: realpath-Konfinement in Inbox-Root zusätzlich zu `is_path_allowed`, keine Traversals/Absolutpfade, Existenz, Server-Video-Endung `queue_api.py:89`, case-insensitives Dedup, Ordner/Nicht-Videos → 400) und (b) ermittelt deterministisch Begleitdateien: nur Same-Directory-Siblings mit Namenspräfix des Video-Basisnamens (Kern von `is_companion_of_any_video`, `queue_api.py:378–404`, OHNE globalen Inbox-Scan). **Neu (V1):** Der Schlüssel-Vertrag wird festgenagelt — `files[]`-Elemente und `mappings`-Schlüssel sind **identische Strings** (relativ zur Inbox-Root; bei Einzeldateien in der Root-Ebene = Dateiname). Bei `files[]`-Jobs darf die Zuordnung nicht auf die abweichenden Varianten des bestehenden Dreifach-Fallbacks (`queue_api.py:474`) ausweichen.
- **Alternativen:** Logik je Endpunkt dupliziert (driftet auseinander — [advocatus] [wichtig]); globaler Präfix-Match über Ordnergrenzen (zieht Fremddateien, `queue_api.py:393`); lockerer Key-Vertrag („irgendeine Schreibweise passt schon") — abgelehnt, weil die Lücke zwischen zwei getrennten Gate-A2-Läufen von keinem der beiden Teststränge gefangen würde ([advocatus] A1).
- **Begründung:** „Preview zeigt exakt, was der Job ausführt" braucht einen Algorithmus UND einen eindeutigen Schlüssel; bei zwei Läufen ist die Nahtstelle der riskanteste Punkt.
- **Konsequenzen:** `helpers.py` in der erlaubten Liste von Lauf A; O(N²)-Inbox-Scan entfällt für `files[]`-Jobs.

### ADR-65-3: `files[]`-Jobs räumen/schreiben den Inbox-Root nie querschnittlich — Scope-Härtung
- **Entscheidung:** Bei gesetztem `files` gelten im Processor: Show-Level-Auffangregel (`prefix_filter=None`) und Root-Leerordner-Cleanup werden übersprungen; die Per-Folge-Verschiebung (`processor.py:1498–1505`) wird auf die Helper-Scope-Menge als Whitelist begrenzt, und ihr eigener Leere-Ordner-Cleanup (`:534–543`) wird bei `src_dir == inbox_root` deaktiviert; `tvshow.nfo`/Artwork schreiben direkt in den Outbox-Serienordner statt `current_dir` (`:1032`); die Meta-Verschiebung aus `current_dir` entfällt (`:1571–1580`); `explicit_junk`/`explicit_subs` außerhalb Scope → LAUTer Abbruch VOR jeder Bewegung; fehlende Datei zur Ausführungszeit → Fehlerstatus statt stiller Skip (AK7).
- **Alternativen:** Nur die `explicit_*`-Prüfung (reichte laut [advocatus] drei [kritisch]-Befunden nicht — verifiziert); Cleanup mit Präfix-Filter (Restrisiko Namenspräfix-Fänge).
- **Begründung:** Alle drei kritischen Findings entstehen aus `current_dir == inbox_root`; Überspringen + Umleiten + Whitelist ist die einzige dichte Begrenzung.
- **Konsequenzen:** `files[]`-Jobs hinterlassen keine Querschnittsveränderungen; Episode-NFOs und umbenannte Folgen liegen während des Laufs als Gruppen-eigene Dateien im Inbox-Root und wandern per Scope-Menge — dokumentierter Zwischenzustand bei Crash; Wiederaufnahme NUR im selben Job via Queue-Retry/Manifest (`:986, :1330–1357`), KEIN Fortschrittsversprechen über Job-Neustarts.

### ADR-65-4: Frontend-Gruppierung: Pseudo-Eintrag + eigenes strenges Muster + Payload-Diskriminator
- **Entscheidung:** (a) Gruppierung ist reine View-Schicht NACH `sortInboxSuggestions` (`app.js:12259`): Auto-Kandidaten = `media_type==="tv"` && `is_dir===false` && AK1-Muster; Schlüssel = `suggested_query`, LEERE Schlüssel werden nie automatisch gruppiert; Gruppe = Pseudo-Eintrag mit `project`/`modified_at`(max)/`total_size`(sum) durch dieselbe Sortierfunktion; Mitglieder intern nach (S,E); Auto-Vorschlag ab ≥2. Neues Muster in `app.js` (keine `export`s, globalThis-Testmuster wie #64), `js/parse.js` unangetastet. **Neu Akt 4:** Einträge mit leerem Schlüssel (und `1x05`-Namen) sind über AK12/AK13 manuell wählbar — die Automatik ist ein Vorschlag, keine Bedingung. (b) Der Server ergänzt das Payload-Feld `is_dir` (bool), festgemacht am Ordner-/Datei-Diskriminator `project_api.py:1320` (AK1b).
- **Alternativen:** `video_count===1` als Diskriminator (abgelehnt — verfehlt 1-Video-Ordner, plan-reviewer Runde 1); Client-Endungsliste (zweite Liste, Drift); Gruppieren aller tv-Einträge inkl. Ordner (abgelehnt); „manueller Weg braucht dieselbe Musterschärfe" (abgelehnt — der Nutzer hat bewusst ausgewählt, das Muster wäre hier Hindernis ohne Schutzgewinn).
- **Begründung:** Wiederverwendung der #64-Sortierfunktion verhindert doppelte Sortierlogik; `suggested_query` ist der bereinigte Namensanteil (`project_api.py:1421`); leere Schlüssel würden fremde Serien verschmelzen — Nicht-Gruppieren ist der sichere Default für die AUTOMATIK, manuelle Auswahl ist der Ausweichweg, den ROADMAP.md:1835 ausdrücklich verlangt.
- **Konsequenzen:** `project_api.py` (nur additive `is_dir`-Zeile) und `tests/test_inbox_suggestions.py` in Lauf A; Kollisions-Restrisiko „zwei Serien, gleicher Schlüssel" bleibt (`ROADMAP.md:1838`) — Gegenmittel: vollständige Quell-Dateinamen im Modal + Abwählen einzelner Folgen.

### ADR-65-5: UI = Banner + Gruppenzeile + Checkboxen + Bulk-Leiste + bestehendes Modal
- **Entscheidung:** Vorschlag als Info-Banner über der Sortier-Leiste („Ignorieren" für Sitzung via `sessionStorage`); Gruppenzeile mit Chevron (`aria-expanded`, Tastatur), Name, „N Folgen", aggregierter Meta „Σ GB · Datum"; Mitglieder flach mit SxxExx-Badge, keine Staffel-Zwischenüberschriften (Alex' Akt-3-Entscheidungspunkt 4, in Abschnitt 0 als Punkt 5 geführt). **Neu:** Checkbox **links im Eintrag** (Trennung Auswahl/Aktion; Präzedenz Gmail/Outlook/Finder), Bulk-Leiste `#smart-inbox-bulk-actions` zwischen Sortier-Leiste und Liste, sichtbar ab ≥1 Auswahl, mit Zähler, „Auswahl aufheben" und Primär-Knopf „Ausgewählte als Serie gruppieren"; Checkboxen nur für Kandidaten nach AK12, `disabled` analog zum Quarantäne-Knopf bei `isProcessing` (`app.js:12468`); Auswahlzustand als DOM-unabhängiges Set (nicht sessionStorage, nicht DOM-Indizes); Film-Ausnahme „Trotzdem als Serie freigeben" pro Eintrag mit sichtbarem Freigabe-Hinweis am Eintrag; Übergabe über den bestehenden Serien-Modus, Modal ohne Refactoring. Aus [grafikers] Akt-3-Kantenfällen übernommen (gehören in den `style.css`-append-Block): `overflow-wrap: break-word` an langen Seriennamen und `flex-wrap`-Umbruch der Zeile unter 600 px (`grafiker-akt3.md:199–201`).
- **Alternativen:** Sammelknopf in der Sortier-Leiste (verworfen — Sortieren ≠ Handeln); Sammelknopf im Banner (verworfen — Banner ist der Auto-Vorschlag, der manuelle Weg soll ohne ihn bedienbar sein); „Alle auswählen" (verworfen, Abschnitt 4); Checkbox-Sperre bei unbestätigtem Banner (verworfen, Dissens 5); Modal-Virtualisierung (verworfen, MVP).
- **Begründung:** [grafiker] liefert Positionierung und Zustände aus der Akt-4-Konsultation; [advocatus] verlangt die DOM-Unabhängigkeit des Auswahlzustands (K1/K4), sonst verschwinden 200 Haken still beim nächsten Poll.
- **Konsequenzen:** `style.css` braucht einen append-Block (Checkbox/Bulk-Leiste/Fokus) → AK9 v49; die bestehenden Render-Pfade (`app.js:12415–12492` und die reaktive Schleife `app.js:2458–2491`) müssen beide die neuen Elemente kennen, sonst verschwindet die Auswahl oder — schlimmer — Gruppenzeilen bekommen einen Löschknopf (AK11).

### ADR-65-6: #68 (Leere-Ordner-Cleanup) bleibt eigenes PR
- **Entscheidung:** Der bestehende Cleanup-Bug an EINZEL- und Ordner-Jobs (`processor.py:974–980, :533–543`) wird NICHT in #65 mitgelöst; #65 führt nur den Pfad ein, der ihn nie ausführt (AK6(b)). **Von Alex bestätigt (2026-10-08: „ist gemergt; 1–3 wie empfohlen" — sein Entscheidungspunkt 3, in Abschnitt 0 als Punkt 4 aufgeführt; sinngemäß: #68 bleibt ein eigener PR).**
- **Alternativen:** Mitlösung im selben PR.
- **Begründung:** [produktberater]-Veto: #68 ändert Verhalten bestehender Jobs (anderes Risikoprofil, eigener Review).
- **Konsequenzen:** ROADMAP #68 bleibt offen; AK6(b) verhindert, dass NEUE `files[]`-Jobs den Bug nutzen.

### ADR-65-7: Umsetzung in zwei aufeinander aufbauenden Gate-A2-Läufen
- **Entscheidung:** **Lauf A (Server):** `files[]`, Scope-Helper, `processor.py`-Härtung, `is_dir`, AK1b + AK5–AK8 (+ AK10). **Lauf B (Oberfläche, auf gemergtem A):** Muster, Auto-Gruppe, Banner, Gruppenzeile, Checkboxen + Bulk-Leiste, Ausnahme pro Eintrag, Übergabe, AK1–AK4 + AK11–AK13 + AK9 (+ AK10). Jeder Lauf mit eigener Erlaubnisliste, eigener Branch von `main`, eigenem PR, jeweils für sich grün.
- **Alternativen:** Ein Lauf (abgelehnt — ein einziger Worker-Diff aus Server-Kern + Oberfläche ist für Alex' Review-Engpass unteilbar und für den Gate-A2-Testzyklus unübersichtlich); umgekehrte Reihenfolge B→A (abgelehnt — B könnte seine `files[]`-Übergabe nur gegen einen erfundenen Server testen).
- **Begründung:** Der Schnitt ist auf Dateiebene **disjunkt** (A: `project_api.py`/`queue_api.py`/`helpers.py`/`processor.py` + Backend-Tests; B: `app.js`/`index.html`/`style.css` + Frontend-Test) — der risikoreiche Kernpfad-Diff wird isoliert reviewt und gemergt; A ist ohne B grün (`files[]` ist optional, `is_dir` additiv, ohne Aufrufer), B ohne A nicht. [advocatus] hat den Schnitt mit APPROVE bestätigt, aber an die Bedingungen V1–V4 geknüpft, die jetzt AK1b/AK5/AK6(e)(f)/ADR-65-2 sind.
- **Konsequenzen:** Zwei Merges, zwei Freigabepunkte, zwei AK0-Messungen. **Eingekauftes Gegenargument (dokumentiert, nicht verschwiegen):** [advocatus] wies darauf hin, dass die Scope-Härtung in A nur im Kontext des echten Client-Verhaltens aus B voll beurteilbar ist und dass die neuen Checkbox-Fälle (Ordner/Misch-Auswahl) in A noch nicht existieren. Gegenmittel: A's AK5/AK6 testen genau diese Fälle (Ordnername → 400, Misch-Auswahl-Semantik, Key-Vertrag), obwohl der Client sie erst in B baut. **Zwischenzustand nach A:** Server akzeptiert `files[]`, kein Client nutzt es — nach [advocatus] A5 kein Datenrisiko (`files[]` ist strenger validiert als der bestehende `project_name`-Pfad: Inbox-Konfinement zusätzlich zu `is_path_allowed`, nur Video-Endungen; der offene LAN-Endpoint erreicht über `project_name` heute bereits jede Inbox-Datei), sondern toter Code, falls B scheitert.

## 5a. Zusammenspiel mit der Sortierung aus #64 (Pflichtabschnitt)

- **Gruppenzeilen in der sortierten Liste:** Gruppe = Pseudo-Eintrag mit `project` = Gruppenname, `modified_at` = Maximum, `total_size` = Summe; durchläuft `sortInboxSuggestions` (`app.js:12259`) UNVERÄNDERT. Klick auf „Name/Datum/Größe" sortiert Gruppen und Einzel-Einträge gemeinsam; Richtung und `sessionStorage`-Zustand (`app.js:12308–12334`) gelten unverändert.
- **Einträge innerhalb einer Gruppe:** beim Aufklappen IMMER nach (Staffel, Folge), unabhängig von der Listen-Sortierung (AK2).
- **Banner, Bulk-Leiste und Sperren:** Banner sitzt über der Sortier-Leiste und wird vom Sortieren nicht bewegt; die Bulk-Leiste sitzt zwischen Sortier-Leiste und Liste und bleibt beim Sortieren stehen; die Film-Sperre (Regel 2) entscheidet pro Eintrag anhand von `media_type`/`is_dir` und ist damit sortierungsunabhängig.
- **Auswahl überlebt Sortierwechsel:** Die Checkbox-Auswahl wird über Namen geführt, nicht über DOM-Positionen — ein Sortier-Klick rendert die Liste neu (`app.js:12383–12392` → `renderSmartInboxList`), die Auswahl muss danach wiederhergestellt sein (AK12, Testfall (b)).
- **Kein viertes Sortierfeld:** „Staffel" wird nicht eingeführt; `sortInboxSuggestions` ist generisch genug für später (Backlog #69/#70-Nachbarschaft).

## 6. Dissens & Risiken

**Dissens 1 — Übergabeweg (entchieden, dokumentationspflichtig):** [produktberater] empfahl Weg 1b; [advocatus] stufte 1b mit drei [kritisch]-Befunden als datengefährlich ein; die Nachprüfung bestätigte die Befunde (Auffangregel `processor.py:516–518, :1594–1601`; Meta-Schreibpfade `:1032, :1571–1580`; stiller TOCTOU-Skip `:958–971, :902–909`; `is_path_allowed` prüft nur gegen ALLE Roots, `helpers.py:113–140`). Ergebnis: 1b verworfen, Weg 2 mit Scope-Härtung.

**Dissens 2 — gemischte Inbox (entchieden):** [grafiker] wollte Ordner-Einträge server-seitig bevorzugen und Einzeldateien still ignorieren; abgelehnt (neue Serverlogik + unterdrückte Vorschläge). Lösung: nur `is_dir === false` wird gruppiert; Restrisiko: dieselbe Serie bleibt als Ordner UND als Einzel-Gruppe sichtbar. Neu: die Checkboxen machen den Ordner-Fall erst richtig gefährlich — [advocatus] K3 [kritisch]: ein angehakter Ordner würde `files[]` verlassen und HTTP 400 auslösen. gelöst durch AK12 (Ordner nie anhaktbar) + AK5 (Server-400 als zweite Verteidigungslinie).

**Dissens 3 — Staffel-Ebenen in der UI (entchieden):** [grafiker] und [produktberater] gegen Staffel-Zwischenüberschriften; Alex' Originalzitat nennt Staffeln. Auflösung: Staffel-Logik bleibt in den Daten (`mappings`, Zielstruktur `Staffel N`), die Zwischenüberschrift-UI entfällt — von Alex am 2026-10-08 ausdrücklich bestätigt (sein Akt-3-Entscheidungspunkt 4, in Abschnitt 0 als Punkt 5 geführt).

**Dissens 4 — Vorschau-Modal bei ~264 Zeilen (offen als Restrisiko):** [produktberater] nannte die DOM-Performance die „primäre Komplexitätsfalle" und empfahl Teil-Renden; [grafiker] hält 264 Zeilen für akzeptabel (≈800 px). Entscheidung: PR1 nutzt das Modal unverändert (AK4); Restrisiko bleibt, Gegenmittel beim Handtest (Abschnitt 8).

**Dissens 5 — Checkbox-Sperre bei unbestätigtem Banner + „Alle auswählen" (entchieden gegen den Vorschlag):** [grafiker] schlug in der Akt-4-Konsultation vor, Checkboxen zu deaktivieren, solange ein Auto-Vorschlag unbestätigt ist („verhindert Mischzustände"). Verworfen: beide Wege enden in derselben `files[]`-Übergabe, ein Mischzustand ist also funktional folgenlos; die Sperre führt eine dritte Zustandsachse (Banner × Auswahl × Sortierung) ein und damit mehr Testfläche als Nutzen. Ebenso verworfen für PR1 (Akt-4-Position von [grafiker] und [advocatus] K2): „Alle auswählen" auf Listenebene. **Nicht identisch davon betroffen** ist [grafikers] Akt-3-Empfehlung einer „Alle auswählen"-Checkbox **im Vorschau-Modal** (`grafiker-akt3.md:169–183`) — dieser andere Ort wird durch AK4 (Modal unangetastet) bewusst nicht gebaut und bleibt als Nachzug dokumentiert (Abschnitt 4), nicht als Konsensverwerfung.

**Dissens 6 — Briefing-Widerspruch gegen Alex' neue Entscheidung (behoben):** [advocatus] fand in der Akt-4-Prüfung vier Stellen, die dem neuen Auftrag widersprachen und den Worker instruiert hätten, das Falsche zu bauen: AK2 („Mehrfach-Auswahlweg wird NICHT eingeführt"), AK3 („genau EIN Eintrag"), ADR-65-4, ADR-65-5. Alle vier sind in dieser Fassung umgeschrieben (Abschnitt 0, AK2/AK3/AK12/AK13, ADR-65-4/5). Der Befund war [kritisch] und ist eingearbeitet, nicht nur zur Kenntnis genommen.

**Dissens 7 — Darstellung der Film-Sperre (entchieden zugunsten der Warn-Variante):** [grafiker] (Akt 3, `grafiker-akt3.md:142–156`) schlug einen **deaktivierten Gruppen-Button mit Tooltip** plus Ausnahme-Link vor; [produktberater] (Akt 3, `produktberater-akt3.md:16`) eine **klare Warnung** mit Sekundär-Button als bewusster Entscheidung. AK3 folgt der produktberater-Variante (Sperr-Hinweis + dezenter Ausweich-Link, kein extra deaktivierter Button), weil ein dritter Knopf pro Zeile die Aktionsseite überlädt und der Nutzer ohnehin keinen Gruppen-Button an einem Film erwartet. Verworfene Alternative hier dokumentiert.

**Archiv-Hinweis (Belegbarkeit):** Die Akt-4-Konsultationen ([grafiker] Kästchen-UI, [advocatus] Schnitt + R6) liefen in dieser Session; ungekürzte Rohoutputs archiviert Claude Code per `opencode export` in diesen Ordner. Die Akt-3-Dateien (`*-akt3.md`) sind bereits archiviert. **Betroffen von dem noch offenen IOU** (ein Review gegen die Archivdateien ist erst ab Nacharchivierung dicht) sind **u. a.**: die [grafiker]-Positionen in ADR-65-5 (Checkbox links, Bulk-Leiste, Freigabe-Hinweis) und in Abschnitt 4/Dissens 5 (Banner-Sperr-Vorschlag, Abkehr von „Alle auswählen" auf Listenebene, sessionStorage-Vorschlag für die Auswahl — bewusst nicht übernommen, Abschnitt 6), die [advocatus]-Zitate in ADR-65-7 (Schnitt-APPROVE, V1–V4, A5/A6) und ADR-65-2 (A1), in AK5 (V3), AK6 (V4), AK9 (A6), Abschnitt 4 (K2 „Alle auswählen", R6d) und Dissens 2 (K3 Ordner anhakbar), sowie die R6-Zuordnung in AK11/AK12/AK13. Vollständigkeitsanspruch: die Liste ist eine Orientierung, keine Erschöpfung — maßgeblich ist, dass **alle** Akt-4-Rollenzitate des Briefings erst mit den archivierten Rohoutputs belegbar sind.

**Verbleibende Risiken:**
- **Backend-Eingriff im Kernpfad (Lauf A):** Dichte der AK5–AK8-Regressionstests ist die Absicherung; Alex' Einzelreview des Server-Diffs der Rest.
- **Nahtstelle A→B:** Der Key-Vertrag (V1) und `is_dir`-Semantik (V2) sind die einzigen Annahmen, die beide Läufe teilen; sie sind jetzt als AK1b/AK4/AK6(f) testfest formuliert. **Restrisiko:** Kein Lauf prüft die End-zu-End-Kette gegen den echten Server — die B-Tests mocken `fetch`. Abhilfe: Handtest (Abschnitt 8) ist Pflicht-Abnahmeschritt, nicht optional.
- **Serverseitiges Verbot von `mappings` ohne `files` bewusst NICHT umgesetzt** (Abschnitt 4): Der Alt-Pfad `project_name=""` + `mappings` bleibt bestehen und kann bei fehlerhaftem Client-Code fremde Inbox-Dateien erreichen (der verworfene Weg 1b). Gegenmittel in PR1: clientseitige Pflicht (AK12) + AK6-Scope nur für `files[]`-Jobs. Wer das serverseitig dicht haben will, braucht #68-artige Arbeit am Alt-Pfad — bewusst ausgelagert.
- **Fehlertoleranz im 264er-Job:** Manifest-Fortschritt gilt nur innerhalb desselben Jobs; ein komplett neuer Job startet bei Null.
- **Gruppenschlüssel-Kollision** (ADR-65-4) bleibt UX-Restrisiko; Gegenmittel: vollständige Quell-Dateinamen im Modal + Abwählen.
- **Auswahl-Zustand bei Reload:** bewusst NICHT persistiert (kein `sessionStorage` für Haken) — Reload wirft die Auswahl zurück; das ist der sicherere Default (kein verwaister Massen-Auswahlzustand), aber eine bewusste Abweichung von [grafikers] sessionStorage-Vorschlag.
- **Timing:** Lauf B setzt den gemergten Lauf-A-Stand voraus; abgesichert durch Schritt 0 + STOP-Protokoll in Abschnitt 11.

## 7. Quellen, Referenzen & Lizenzen

- Kein Third-Party-Code, keine neuen Assets/Fonts/Icons. Verwendete Chevron-/Banner-/Raster-Grafiken: Lucide-Inline-SVG-Muster (ISC), bereits im Projekt vorhanden (`app.js:12419–12429`); keine neuen Icon-Sets.
- Referenz-Apps nur als Muster, nicht kopiert: macOS Finder, Gmail, Outlook, Spotify, Plex, Sonarr, Dropbox, Google Drive, GitHub, VS Code ([grafiker], Akt 3 + Akt 4).
- Interne Referenzen: `ROADMAP.md:1822–1842` (#65), `#20` (Drag&Drop-Folge), `#68`/`#69`/`#70`, `65-uebergabe-optionen.md`, `briefing-64.md`, `rueckkanal-64.md` (R6), `briefing-64.md` Abschnitt 11 (Gate-A2-Format).

## 8. Offene Fragen

1. **Handtest als Abnahme (kein Blocker, aber Pflichtschritt):** Nach Merge von B mit der echten 11-Staffel-Serie prüfen: 264-Zeilen-Modal (Dissens 4), Payload-Größe, `files[]`-End-to-End (Restrisiko Nahtstelle). Empfehlung: vor dem NAS-Deploy auf der lokalen Instanz durchführen.
2. **„Alle auswählen" bewusst raus** (Abschnitt 4): Wenn Alex den expliziten „Alle Serien-Einzeldateien auswählen"-Knopf doch in PR1 will, ist das ein Planwechsel → neue AK, nicht autonome Worker-Entscheidung.
3. **Start der beiden Gate-A2-Läufe:** Jeder scharfe Lauf braucht ein Alex-Go (Klasse B je Kette), der Merge jeweils Klasse C. AK0-Messung im Worker-Image liefert Claude Code vor jedem Lauf nach `ak0-ausgangsmessung-65.md`.

## 9. Aufwand (KI-Implementierung vs. menschlicher Engpass)

- **KI/Pipeline (schnell):** Lauf A (Server + Backend-Tests + API.md) und Lauf B (UI + Frontend-Test + Cache-Buster) — je realistisch 1–3 Gate-A2-Runden.
- **Menschlicher Engpass (Alex, der eigentliche Takt):** je Lauf AK0-Beleg zur Kenntnis + Freigabe des scharfen Laufs; **nach A: Review des Server-Diffs** (Scope-Logik ADR-65-2/3 — Kernstück, bewusst einzeln ansehen) + Merge; nach B: UI-Review + Handtest mit der echten Serie + Merge; danach ROADMAP-Status #65. Grob 45–75 min Menschenzeit über zwei Zyklen, nicht Laufzeit.

## 10. Git-Zustand (geliefert von Claude Code, wörtlich; ich habe kein bash)

```
$ git status --short --branch
## feat/roadmap-65-als-serie-gruppieren
 M docs/sessions/2026-10-08-roadmap64-65-inbox/ALEX_ZUSAMMENFASSUNG.md
?? docs/sessions/2026-10-08-roadmap64-65-inbox/advocatus-akt3.md
?? docs/sessions/2026-10-08-roadmap64-65-inbox/briefing-65.md
?? docs/sessions/2026-10-08-roadmap64-65-inbox/grafiker-akt3.md
?? docs/sessions/2026-10-08-roadmap64-65-inbox/plan-reviewer-akt3.md
?? docs/sessions/2026-10-08-roadmap64-65-inbox/produktberater-akt3.md
$ git log --oneline -2
c66cb20 docs(roadmap): add #70 inbox type filter, note #45 size summary and semantics
6152839 feat(inbox): sortable smart inbox by name, date and size (ROADMAP #64) (#148)
```

Feature-Branch `feat/roadmap-65-als-serie-gruppieren` auf `main` @ `6152839` (enthält den gemergten #64) plus dem Docs-Commit `c66cb20`. Kein main-Stop. **Akt-4-Zusatz:** Dieser Lauf hat ausschließlich `briefing-65.md` und `ALEX_ZUSAMMENFASSUNG.md` in diesem Session-Ordner verändert — kein Pfad außerhalb des Ordners, keine Code-Datei, kein Git-Befehl. Für das Staging in diesem Worktree sind also genau diese zwei Dateien der eigene Beitrag; der Akt-4-Rohoutput-Nacharchivierung (Claude Code, `opencode export`) folgt später. **Ausführung:** die beiden Gate-A2-Läufe laufen in eigenen Clone/Workspaces der Kit-Pipeline (Branches von `main`, Vorschlag `feat/roadmap-65a-files-server-scope` und `feat/roadmap-65b-inbox-grouping-ui`), nicht in diesem Session-Worktree; Patch-Übernahme, Commits und PRs bleiben bei Claude Code nach Alex-Go.

## 11. Worker-Aufträge für die Gate-A2-Pipeline (zwei Läufe)

**Kontext für beide Läufe:** Briefing-Abschnitte 3–7 sind verbindlich; AKs sind Testfälle, keine Wünsche. `test_cmd` identisch zu #64 (ohne eigenes `timeout`; Pipeline-Limit `test_timeout_s`, wegen der pip-Installation wie bei #46/#64 auf 600 gesetzt):

```bash
python3 -m pip install -q --user --break-system-packages -r requirements.txt pytest && python3 -m pytest -q -p no:cacheprovider --deselect tests/test_utils.py::TestMediawerkzeugLogic::test_conversion_estimation_test_encode && npm run test:frontend
```

### 11a. Lauf A — Server: `files[]`, Scope-Härtung, `is_dir` (AK1b, AK5–AK8, AK10)

```text
Serien-Gruppierung in der Inbox: Dateiliste files[] als Projektbasis mit hartem
Scope — ROADMAP #65, Lauf A (nur Server; kein Frontend in diesem Lauf).

Kontext: gui/api/project_api.py, get_inbox_suggestions() (:1299-1507) liefert die
Inbox-Vorschlaege (Payload-Dict :1490-1502, is_dir existiert nur intern :1320);
gui/api/queue_api.py loest project_name zu current_dir auf (:73-88, video_exts :89,
is_companion_of_any_video :378-404); gui/workers/processor.py bewegt Dateien
(safe_move_recursive :479-543, current_dir :846-856, explicit_* :896-980,
tvshow.nfo :1032, Per-Folge-Move :1498-1505, Show-Level-Move :1594-1601).

NUR diese Aenderungen:
1. project_api.py: Payload-Dict um EIN additives Feld is_dir (bool) ergaenzen,
   abgeleitet aus dem bestehenden os.path.isdir(full_path) (:1320). Ein Ordner mit
   genau einem Video liefert true, eine Einzeldatei false. Sonst nichts an der
   Funktion aendern (kein Refactoring, Cache und video_files bleiben).
2. helpers.py: neuer geteilter Helper (von Preview UND Process genutzt):
   (a) validiert files (Liste relativer Pfade): keine Absolutpfade, kein "..",
       os.path.realpath beider Seiten, Konfinement unterhalb realpath(inbox_root)
       ZUSAETZLICH zu is_path_allowed, Existenzpruefung, Endung in der Liste
       queue_api.py:89; case-insensitives Dedup; jeder Verstoess -> HTTP 400 mit
       klarer Meldung (kein stilles Filtern — ein Ordnername/Nicht-Video in files
       muss 400 ausloesen).
   (b) ermittelt Begleitdateien NUR als Same-Directory-Siblings mit Namensprafix
       des Video-Basisnamens (Kern von is_companion_of_any_video, OHNE globalen
       Inbox-Scan).
3. queue_api.py: /preview_process und /process erhalten optional files. Bei
   gesetztem files: Arbeitsbasis Inbox-Root, Datei-Menge = validierte Liste plus
   Begleitdateien, project_name wird nicht zur Pfadauflösung benutzt. Ohne files
   bleibt jedes Verhalten byte-genau wie heute (auch project_name="" ohne files).
   mappings-Konsistenzprüfung (jeder mappings-Schluessel muss in files vorkommen)
   in BEIDEN Endpunkten, identischer Check. Bei files-Jobs darf die
   Episoden-Zuordnung nur über den mit files identischen String greifen (kein
   Ausweichen auf basename-Varianten des bestehenden Dreifach-Fallbacks :474).
4. processor.py (Scope-Haertung bei gesetztem files, ADR-65-3):
   - Show-Level-Auffangregel safe_move_recursive(prefix_filter=None) ueberspringen
     (:1594-1601, Regel :516-518).
   - Per-Folge-Verschiebung (:1498-1505) auf die Helper-Scope-Menge als Whitelist
     begrenzen; ihren internen Leere-Ordner-Cleanup (:534-543) bei
     src_dir == inbox_root deaktivieren.
   - Root-Leerordner-Cleanup (:974-980) ueberspringen.
   - tvshow.nfo/Poster/Fanart direkt in den Outbox-Serienordner schreiben statt in
     current_dir (:1032); Meta-Verschiebung aus current_dir entfaellt (:1571-1580).
   - explicit_junk/explicit_subs außerhalb der Scope-Menge: LAUT abbrechen, bevor
     etwas bewegt wird (:902-909, :965-971).
   - files-Eintrag fehlt zur Ausführungszeit: Fehlerstatus mit namentlicher Nennung
     statt stiller Skip (:958-971).

Akzeptanzkriterien (Tests NEU tests/test_inbox_group_files.py; tests/
test_inbox_suggestions.py NUR um is_dir-Faelle ergaenzen, bestehende unveraendert):
- Es prüft, dass ein Ordner mit genau einer Videodatei is_dir=true liefert und
  eine Einzeldatei false (nicht ueber video_count abgeleitet).
- Es prüft, dass jede files-Validierungsregel ablehnt (absolut, .., außerhalb
  Inbox-Root per realpath, nicht existierend, fremde Endung, Ordnername) — je
  eigener Fall, HTTP 400, keine stille Filterung; Duplikate case-insensitive.
- Es prüft, dass mappings-Schluessel außerhalb von files in PREVIEW und in
  PROCESS je eigenständig abgelehnt werden.
- Es prüft, dass bei files-Jobs die Zuordnung nur über den exakten files-String
  greift (kein basename-Fallback).
- Es prüft mit tmp-Inbox {Gruppe 3 Folgen + Gruppen-Untertitel; Fremdprojekt
  Video+Untertitel+.nfo+leerer Ordner; adversarische Kollisionsdatei mit
  Praefix eines Gruppen-Titels}, dass ein files-Job AUSSCHLIESSLICH Gruppe und
  Begleitdateien berührt: Kollisionsdatei bleibt, fremder leerer Ordner bleibt,
  tvshow.nfo liegt nicht im Inbox-Root, explicit_* außerhalb Scope bricht laut ab.
- Es prüft, dass eine zur Ausführungszeit fehlende files-Datei den Job
  fehlerhaft macht und den Dateinamen nennt.
- Es prüft, dass alle Pfade ohne files unverändert bleiben (Ordner, Einzeldatei,
  movie, Inbox-Root-Job project_name="" ohne files) — bestehende Suite grün.
- git diff --check sauber; Tests nur in tmp-Verzeichnissen; keine Secrets;
  .env wird nie gelesen; KEIN Cache-Buster-Bump in diesem Lauf.

ERLAUBTE DATEIEN (ausschliesslich):
gui/api/project_api.py (nur additive is_dir-Zeile), gui/api/queue_api.py,
gui/core/helpers.py, gui/workers/processor.py, API.md (files-Parameter + is_dir),
tests/test_inbox_group_files.py (neu), tests/test_inbox_suggestions.py (nur
ergänzen).

NICHT ANFASSEN (auch nicht "nebenbei"): gui/static/** (komplett — kein Frontend
in Lauf A), ROADMAP.md, STAND.md, VERLAUF.md, docs/**, scripts/**, package.json,
pytest.ini, gui/api/uebrige, gui/core/uebrige, gui/workers/uebrige,
bestehende tests/** (nur die erlaubte Ergänzung), .env (nie lesen), data/**.
```

**Schritt 0 vor dem ersten Code-Diff (Lauf A):** `main` enthält den gemergten #64 (`sortInboxSuggestions` in `app.js`, `app.js?v=95`, Payload mit `modified_at`/`total_size`). Bei Abweichung: STOPP und Rückmeldung an Claude Code/Alex — AKs werden NICHT autonom angepasst (Planänderung = Freigabepunkt).

### 11b. Lauf B — Oberfläche: Erkennung, Gruppe, Banner, Checkboxen, Übergabe (AK1–AK4, AK11–AK13, AK9, AK10)

```text
Serien-Gruppierung in der Inbox: automatische Gruppen, manuelle Auswahlkästchen
und Übergabe an den files[]-Weg — ROADMAP #65, Lauf B (nur Oberfläche; der
Server-Pfad aus Lauf A ist bereits gemergt und unveraenderlich).

Kontext: gui/static/app.js rendert die Smart Inbox (renderSmartInboxList
:12396-12497, Sortieren :12259-12306, sessionStorage :12308-12334, reaktive
Schleife :2458-2491, deleteProject :2514-2538, Klick-Uebergabe
handleSmartInboxClick :12499, Vorschau-Modal openPreviewModal :10182,
Process-Fetch :10612-10616, Serien-Payload-Bau executeSeriesWorkflow :4290-4409);
gui/static/index.html: Inbox-Karte :427-478, Sortier-Leiste :461-466,
Liste :467. Server liefert pro Eintrag media_type, suggested_query, video_count,
modified_at, total_size und seit Lauf A is_dir.

NUR diese Aenderungen:
1. app.js: EIGENE strenge Muster-Funktion fuer S/E (kein Aufruf von
   guessSeasonAndEpisode aus js/parse.js, keine export-Keyword, Muster wie
   sortInboxSuggestions). Automatische Kandidaten: media_type==="tv" und
   is_dir===false und Muster-Treffer und nicht-leerer suggested_query; Gruppe ab
   >=2 Mitgliedern mit gleichem Schluessel.
2. app.js: Gruppe als Pseudo-Eintrag (project=Gruppenname, modified_at=max,
   total_size=summe) durch dieselbe sortInboxSuggestions; Mitglieder beim
   Aufklappen nach (Staffel, Folge); Gruppenzeile mit Chevron, aria-expanded,
   Tastatur, SxxExx-Badges, KEINE Staffel-Zwischenüberschriften.
3. app.js/index.html: Info-Banner "Als Serie gruppieren" UEBER der Sortier-Leiste
    (Serienname, N Folgen, erkannte Staffeln), Bestätigung per Klick, "Ignorieren"
    in sessionStorage.
 4. app.js/index.html: Auswahlkästchen links im Eintrag NUR fuer
    (media_type==="tv" und is_dir===false und nicht isProcessing) sowie fuer
    per "Trotzdem als Serie freigeben" freigegebene Film-Einträge (Freigabe gilt
    PRO EINTRAG, mehrere unabhaengig; Freigabe loest keine automatische Gruppe
    aus). Doku-Einträge sind in PR1 weder automatische Kandidaten noch anhaktbar
    und erhalten keinen Freigabe-Link (bewusste Scope-Enge, Abschnitt 4).
    Bulk-Leiste id smart-inbox-bulk-actions zwischen Sortier-Leiste und
    Liste, sichtbar ab >=1 Auswahl, mit Zaehler "N ausgewaehlt", Knopf
    "Auswahl aufheben" und "Ausgewaehlte als Serie gruppieren". Auswahlzustand in
    einem DOM-unabhaengigen JS-Set ueber die Eintragsnamen (kein sessionStorage,
    keine DOM-Indizes), nach erneutem Rendern und nach Sortierwechsel
    wiederhergestellt, idempotent gegen doppeltes Anhaken. Ordner-Eintraege
    (is_dir===true) sind nie anhaktbar.
5. app.js: Uebergabe beider Wege (Banner-Gruppe und Sammelknopf) in den
   bestehenden Serien-Modus: Suche mit Gruppennamen vorfuellen, Mitglieder als
   files (relative Pfade = Eintragsnamen) plus mappings (Schluessel exakt gleich
   den files-Strings) in die basePayload; Modal selbst NICHT refaktoriert; nie
   mappings ohne files senden.
6. app.js: R6-Absicherung — Gruppenzeilen erhalten eine eigene Klasse
   (smart-inbox-group-row) und eigenen Schluessel (data-group-key), KEIN
   data-project und KEINEN Quarantaene-Knopf; beide Render-Pfade
   (renderSmartInboxList und die reaktive Schleife) muessen Gruppenzeilen
   ausdruecklich ausnehmen; kein Pseudo-Eintrag mit Schluessel "" oder
   "__inbox_recursive__".
 7. Cache-Buster: app.js?v=95 -> ?v=96 (index.html:2758 UND alle neun Importe
    app.js:1-9); style.css?v=48 -> ?v=49 (index.html:9), style.css nur um den
    append-Block fuer Checkbox/Bulk-Leiste/Fokus sowie overflow-wrap bei langen
    Seriennamen und flex-wrap unter 600px ERGAENZEN.

Akzeptanzkriterien (Tests NEU tests/frontend/inbox_group.test.js, Muster
app_warning.test.js: eigene DOM-Mocks, globalThis-Zuweisung vor eval,
gemocktes sessionStorage, KEINE echten Timer stehen lassen):
- Es prüft, dass "Show.S01E01.720p.mkv" erkannt wird, "Movie.1920x1080.x264.mkv",
  "The Rock (1996).mkv", "Show.1x05.mkv" und "Staffel 2 Folge 3 – Show.mkv" aber
  NICHT automatisch gruppiert werden.
- Es prüft, dass leere suggested_query und Ordner-Eintraege (is_dir true, auch mit
  video_count 1) nie automatisch gruppiert werden.
- Es prüft, dass die Gruppe als Pseudo-Eintrag an der Sortierung teilnimmt und
  Mitglieder intern nach Staffel/Folge stehen.
- Es prüft, dass der Banner erst nach Klick gruppiert und "Ignorieren" ihn fuer
  die Sitzung entfernt.
- Es prüft, dass Checkboxen nur an zulaessigen Eintraegen aktiv sind (tv, Einzeldatei,
  nicht verarbeitend, freigegebene Filme — freigegebene Filme ebenfalls nur, wenn
  sie nicht gerade verarbeiten), und dass Ordner-, Doku- und
  Verarbeitungslauf-Eintraege nicht waehlbar sind.
- Es prüft, dass die Auswahl einen erneuten Render und einen Sortierwechsel
  uebersteht, dass doppeltes Anhaken keine Duplikate erzeugt und dass
  "Auswahl aufheben" zuruecksetzt.
- Es prüft, dass beide Uebergabewege ein Payload mit files und passendem mappings
  erzeugen (Schluessel identisch zu files) und nie mappings ohne files.
- Es prüft, dass eine Gruppenzeile keinen Quarantaene-Knopf und kein data-project
  hat — auch dann nicht, wenn ihr Name mit einem realen Ordner-Eintrag
  uebereinstimmt (deleteProject wird mit dem Gruppenschluessel nie aufgerufen).
- Es prüft, dass die Film-Freigabe pro Eintrag wirkt und genau diese Datei als
  files-Eintrag uebergibt.
- cache_busting.test.js bleibt grün (v96/v49); git diff --check sauber; Tests nur
  in tmp-Verzeichnissen; keine Secrets; .env nie gelesen.

ERLAUBTE DATEIEN (ausschliesslich):
gui/static/app.js, gui/static/index.html, gui/static/style.css (nur append-Block),
tests/frontend/inbox_group.test.js (neu).

NICHT ANFASSEN (auch nicht "nebenbei"): gui/api/**, gui/core/**, gui/workers/**
(der Server-Pfad ist gemergt und unveraendert), js/parse.js und uebrige
gui/static/js/**, ROADMAP.md, STAND.md, VERLAUF.md, docs/**, scripts/**,
package.json, pytest.ini, bestehende tests/** (nur NEUE Testdatei), .env (nie
lesen), data/**.
```

**Schritt 0 vor dem ersten Code-Diff (Lauf B):** Basis ist `main` NACH Merge von Lauf A; Verifikation: `/api/inbox/analyze` liefert `is_dir`, `/preview_process` akzeptiert `files` (API.md), `app.js?v=95` unverändert vorhanden. Bei Abweichung: STOPP + Rückmeldung an Claude Code/Alex — keine autonome AK-Anpassung.

### 11c. Übergabe-Pflicht (beide Läufe)

**Pflicht: feste Liste WÖRTLICHER Rohausgaben bei der Übergabe** (keine rekonstruierten oder „sinngemäß"-Belege; jede Ausgabe mit Exit-Code):

1. `git status --short --branch`
2. `git log --oneline -5`
3. `git diff --stat <basis>..HEAD` (basis = Merge-Commit der Vorgängerstufe auf `main`)
4. `git diff --check <basis>..HEAD`
5. Volle Ausgabe `python3 -m pytest -q -p no:cacheprovider --deselect tests/test_utils.py::TestMediawerkzeugLogic::test_conversion_estimation_test_encode` + Exit-Code
6. Volle Ausgabe `npm run test:frontend` + Exit-Code
7. `git diff --stat` je eigenem Commit

**Freigabe- und Merge-Pfad:** Start jedes scharfen Laufs braucht Alex-Go (Klasse B je Kette); AK0 misst Claude Code vor jedem Lauf im Worker-Image und legt die Ausgabe in `ak0-ausgangsmessung-65.md` ab (keine Testläufe auf dem Host). Nach `APPROVED`: Patch-Übernahme nur auf Alex' separate Anweisung; Commits/PR durch Claude Code, nie durch den Worker. ROADMAP-Status #65 erst nach Merge von Lauf B.
