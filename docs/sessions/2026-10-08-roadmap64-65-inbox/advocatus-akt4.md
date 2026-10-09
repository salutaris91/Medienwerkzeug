# Rohoutput advocatus — Kreativteam 2026-10-08 (Akt 4, #65)
Hinweis Claude Code (2026-10-09): Mechanisch aus `opencode export ses_ee2dc847cffeefAVh2xzGtKoRQ` (ceo-planner, Akt 4b–4d im #65-Worktree) abgelegt, nicht vom Moderator abgeschrieben (Lehre 59). Einzige Änderung: Trailing Whitespace entfernt. Der in Akt 4c hängengebliebene plan-reviewer-Aufruf (Subagent-Sitzung ses_ee2c4d97bffe3qpBcSH5O8ZJ1P, Modell-Stream abgerissen, von Claude Code beendet) hat keinen Output und erscheint hier nicht. Volle Daten: Kit `scripts/gate-a2/logs/2026-10-08-roadmap64-65/export-akt4.json`.

---

## advocatus: Gate-A2-Schnitt + R6 (Subagent-Sitzung ses_ee2d0d6f2ffezMqWvZvowb6Wbc, Status: completed)

<task id="ses_ee2d0d6f2ffezMqWvZvowb6Wbc" state="completed">
<task_result>
Analyse abgeschlossen. Alle Lesezugriffe lagen innerhalb des Worktrees. Hier die Befunde.

---

# Übergeordneter Befund (gilt für beide Prüfaufträge)

**Das approvte `briefing-65.md` widerspricht der neuen Alex-Entscheidung an vier Stellen.** Das ist der eigentliche REVISE-Auslöser, vor allen Detailbefunden:

| Briefing-Stelle | Wortlaut (widersprechend) | Neue Alex-Entscheidung |
|---|---|---|
| AK2 (`briefing-65.md:29`) | „…ein neuer Mehrfach-Auswahlweg wird in PR1 NICHT eingeführt" | manuelle Auswahlkästchen + Sammelknopf |
| ADR-65-4 (`:72`) | „kein neuer Mehrfach-Auswahlweg in PR1, ADR-65-5" | Kästchen |
| ADR-65-5 (`:78`) | „Übergabe über den bestehenden Serien-Modus" (kein Kästchen-Sammelweg) | Sammelknopf |
| AK3 (`:30`) | „…funktioniert für genau EINEN bewussten Eintrag" | „Trotzdem freigeben" PRO EINTRAG + Sammelweg |

Solange diese Stellen nicht umgeschrieben sind, instruiert der Task-Text den Worker, genau das NICHT zu bauen, was Alex will. Beide Prüfaufträge sind davon betroffen: Der Schnitt (Auftrag 1) und die R6-/Kästchen-Absicherung (Auftrag 2) hängen beide an einer konsistenten Briefing-Grundlage.

---

# Prüfauftrag 1 — Schnitt in zwei Gate-A2-Läufe

## Technische Dichtigkeit (verifiziert am Code)

Der Schnitt ist **disjunkt auf Dateiebene** — das ist sein stärkstes Argument:

- **Lauf A** fasst ausschließlich `gui/api/queue_api.py`, `gui/core/helpers.py`, `gui/workers/processor.py`, `gui/api/project_api.py` (nur `is_dir`), `tests/test_inbox_group_files.py` (neu), `tests/test_inbox_suggestions.py` (AK1b), `API.md` an.
- **Lauf B** fasst ausschließlich `gui/static/app.js`, `gui/static/index.html`, `gui/static/style.css`, `tests/frontend/inbox_group.test.js` an.

**Die zentrale Sorge „zwei Merges in denselben Kernpfad" ist damit eine Fehlannahme:** Der Kernpfad (`processor.py`/`queue_api.py`/`helpers.py`) wird **nur von A** angefasst. B ist reines Frontend. Das ist genau der ideale Schnitt: der risikoreiche Server-Diff wird isoliert reviewt/gemergt.

## Läuft A grün ohne B? — Ja, belegt.

- `is_dir` ist additiv am Payload-Dict (`project_api.py:1490–1502`, heute ohne `is_dir`); der bestehende Client ignoriert unbekannte Felder.
- `files[]` ist optional; heute existiert es an beiden Endpunkten nicht (`queue_api.py:27–37` liest nur `mappings`, kein `files`; `:776–831` `/process` liest kein `files`). Ohne `files` bleibt der `project_name`-Pfad byte-genau — AK8 erzwingt das.
- Die Scope-Härtung (ADR-65-3) greift nur bei gesetztem `files[]`: Auffangregel (`processor.py:516–518` `prefix_filter is None → belongs = True`), Root-Cleanup (`:974–980`), `tvshow.nfo`-Schreibziel `current_dir` (`:1036`), Meta-Move (`:1571–1580`). Die AK5–AK8-Tests sind mit tmp-Inbox-Fixtures ohne Frontend testbar.

## Ist B ohne A testbar? — Ja, aber mit Vertrags-Lücke.

Die Frontend-Tests mocken `fetch` (Muster `app_warning.test.js:96–119`), prüfen also nur die Payload-**Struktur**. Das ist ohne echten Server machbar. Die End-zu-End-Wahrheit (Server liefert `is_dir`, Client gruppiert) entsteht erst nach beiden Merges — das ist kein Blocker, aber die Nahtstelle muss festgenagelt sein (siehe Forderungen).

## Befunde

**[wichtig] A1 — Vertrags-Lücke an der Nahtstelle `files[]`/`mappings`-Keys.** Der Server matcht mappings-Keys dreifach (`queue_api.py:474`: `mappings.get(rel_f) or mappings.get(f) or mappings.get(basename)`). Bei `files[]` muss die Semantik eindeutig sein, sonst driften AK4 (Client erzeugt Keys) und AK5/AK6 (Server erwartet Keys) auseinander — und **kein Test der beiden Läufe fängt es**: B-Tests mocken fetch, A-Tests bauen synthetische Fixtures. Der Schnitt verlagert genau diese einzige gemeinsame Annahme in zwei getrennte Reviewer-Sichtfenster. → Forderung V1.

**[wichtig] A2 — `is_dir`-Semantik muss in A den 1-Video-Ordner-Fall erzwingen.** `is_dir` ist heute nur serverintern (`project_api.py:1320`: `is_dir = os.path.isdir(full_path)`). Genau deshalb wurde der `video_count===1`-Diskriminator verworfen (ADR-65-4b: „trifft auch einen Ordner mit genau einem Video"). Implementiert der Worker in A `is_dir` stattdessen als `video_count > 1`, liefe AK1b grün (Feld existiert) und AK2 in B grün (Fixture setzt `is_dir:true` hart) — aber real würde ein 1-Video-Ordner fälschlich gruppiert. → Forderung V2.

**[wichtig] A3 — Kästchen erweitern `files[]` um Ordner-Einträge; A's Scope-Annahme deckt das nicht ab.** ADR-65-4/ADR-65-2 gehen davon aus, `files[]` enthalte **nur Einzeldateien** („Ordner sind keine Gruppen-Mitglieder, ihr Projektname ist kein Einzelfilm-Pfad"). Mit den Kästchen kann der Nutzer einen Ordner-Eintrag anhaken → `item.project` = Ordnername ohne Endung. AK5 validiert „keine Server-Video-Endung → 400". Das ist zwar die korrekte Abwehr, aber A muss diesen Fall **explizit testen**, sonst bleibt der Vertrag „nur Einzeldateien" ungesichert, während B Ordner anbietet. → Forderung V3.

**[wichtig] A4 — `mappings⊆files`-Check (AK6e) muss in beiden Endpunkten identisch sein.** Preview und Process haben getrennte Validierungsstränge (`queue_api.py:19–772` vs. `:776–831`). Der Check darf nicht nur in Preview landen. AK6e fordert „identischer Check" — das muss als nicht-verhandelbarer A-Bestandteil fixiert werden (nicht als „Preview UND Process" im Fließtext versickern). → Forderung V4.

**[kosmetisch] A5 — Zwischenzustand „Server akzeptiert `files[]`, kein Client nutzt es" ist kein Sicherheits-/Datenrisiko.** `files[]` ist strenger validiert als der bestehende `project_name`-Pfad (AK5: realpath-Konfinement in `inbox_root` **zusätzlich** zu `is_path_allowed` aus `helpers.py:113–140`, das nur gegen ALLE Roots prüft). Der offene LAN-Endpoint (ROADMAP #58) erreicht über `project_name` bereits jede Inbox-Datei; `files[]` verengt das sogar (nur Video-Endungen). Restrisiko ist ausschließlich toter Code, falls B scheitert — kein Datenpfad.

**[kosmetisch] A6 — AK9 (Cache-Buster v96) gehört korrekt in B, nicht A.** A ändert kein frontend-relevantes Asset (`project_api.py`/`queue_api.py`/`processor.py`/`helpers.py`), also kein Bump nötig. Konsistent — kein blinder Fleck.

## Argumente GEGEN den Schnitt (ein Lauf) — Gewichtung

Das einzige **schwerwiegende** Gegenargument: Die Scope-Härtung (A) ist nur im Kontext des tatsächlichen Client-Verhaltens (B) reviewbar. Ein Reviewer, der nur A sieht, kann nicht beurteilen, ob „nur Einzeldateien, selbe Ebene" die richtige Annahme ist — und genau diese Annahme kippt durch die Kästchen (A3). Gegenmittel: A's AKs müssen die neuen Kästchen-Fälle **mit** abdecken (Ordner → 400, Misch-Auswahl), auch wenn die Kästchen erst in B gebaut werden. Dann wiegt kein Gegenargument den Vorteil (isolierter Kernpfad-Review) auf.

## VERDICT: APPROVE (Schnitt) — REVISE (Briefing-Grundlage)

Der Schnitt selbst ist technisch dicht und gut; freigegeben wird er nur unter den Forderungen V1–V4 plus dem übergeordneten Briefing-Umbau.

**Forderungen, die ins Briefing müssen:**

- **V1 [wichtig]** — Vertrags-AK: „Es prüft, dass `mappings`-Keys exakt die relativen Pfad-Strings aus `files[]` sind (gleiche Schreibweise, relativ zu `inbox_root`, mit Trennzeichen), und dass die dreifache Server-Zuordnung (`queue_api.py:474`) bei files[]-Jobs nur auf `rel_f` matcht." Wo: AK4 (B) formuliert die Client-Erzeugung, AK6e (A) die Server-Prüfung — beide referenzieren denselben String-Vertrag wörtlich.
- **V2 [wichtig]** — AK1b verschärfen: „Es prüft, dass ein Ordner mit **genau einer** Videodatei `is_dir: true` liefert (und eine Einzeldatei `false`) — nicht nur, dass das Feld existiert." Wo: Lauf A.
- **V3 [wichtig]** — AK5 ergänzen: „Es prüft, dass ein `files[]`-Eintrag ohne Server-Video-Endung (z. B. ein Ordnername) zu HTTP 400 führt, NICHT still gefiltert wird." Wo: Lauf A — deckt den Kästchen-Ordner-Fall ab, bevor B ihn anbietet.
- **V4 [wichtig]** — AK6e als getrennte Prüfung je Endpunkt: „Es prüft, dass `mappings`⊆`files` sowohl in `/preview_process` **als auch** in `/process` ablehnt." Wo: Lauf A.
- **V0 [kritisch]** — Die vier widersprechenden Briefing-Stellen (AK2, AK3, ADR-65-4, ADR-65-5) umschreiben: Kästchen + Sammelknopf + „Trotzdem freigeben" pro Eintrag sind jetzt Bestandteil, nicht „nicht eingeführt".

---

# Prüfauftrag 2 — Risiko R6 + neue Kästchen-Führung

## R6 verifiziert (nicht behauptet — am Code belegt)

Die Verdrahtung ist real:
- `app.js:12452` setzt `data-project = item.project`; `:12480–12489` verdrahtet `deleteBtn.onclick → deleteProject(item.project)`.
- `app.js:2458–2491` (reaktive Schleife) tut dasselbe über `p = getAttribute("data-project")` → `deleteProject(p)` (`:2460`, `:2484`).
- `deleteProject` (`app.js:2514–2538`) POSTet `{project}` an `/api/delete-project`; bei `currentProject === project` ruft es `selectProject("")` (`:2527–2529`).
- Server `project_api.py:942–983`: `project = params.get("project")`; `__inbox_recursive__`-Guard (`:954`); `target_dir = os.path.join(inbox_root, project)` (`:962`); Konfinement `startswith(inbox_root_abs + os.sep)` (`:967`); `trash.send_to_trash(target_dir_abs)` (`:974`).

## Missbrauchsfälle (schärfste Form)

**[kritisch] R6a — Gruppenname == realer Ordnername → Löscht den falschen Ordner.** Inbox enthält Ordner `Show/` **und** Einzeldateien `Show.S01E01.mkv … S11E22.mkv`. Die Gruppe erhält `project = "Show"` (= `suggested_query`). Trüge der Pseudo-Eintrag einen Quarantäne-Knopf, würde `deleteProject("Show")` den **realen** Ordner `Show/` in Quarantäne verschieben (`project_api.py:962/974`) — Datenverlust des realen Projekts. Der Pseudo-Eintrag hat keinen realen Ordner; jede Lösch-Semantik ist entweder wirkungslos (`:970–971` „Ordner existiert nicht") oder (bei Namenskollision) destruktiv.

**[kritisch] R6b — Gruppen-Pseudo-Eintrag darf NIE einen Quarantäne-Knopf rendern.** Dies ist die einzige dichte Gegenmaßnahme zu R6a. Heute rendert `renderSmartInboxList` den Knopf bedingungslos für jeden Eintrag (`app.js:12466–12470`, `:12480–12489`); die reaktive Schleife ebenso (`:2473–2488`). Der Gruppen-Pseudo-Eintrag muss als solcher markiert sein (`is_group`-Flag) und beide Render-Pfade müssen den Knopf dafür unterdrücken.

**[wichtig] R6c — „Trotzdem freigeben" bei einem FILM-Eintrag übergibt den Einzeldatei-Pfad, keinen Ordner.** Film-Eintrag = `is_dir:false`, `item.project` = Dateiname (z. B. `The Rock (1996).mkv`). Der Ausnahme-Weg wird zu `files[]=["The Rock (1996).mkv"]` + `media_type:"tv"`. Der Server akzeptiert (`.mkv` in `video_exts`, `queue_api.py:89`). Semantik-Folge: Eine Filmdatei wandert als „Episode" in die Serienstruktur — das ist die gewünschte Ausnahme, aber sie ist **nicht mehr „genau EINER"** (AK3), sobald der Sammelknopf Mehrfachauswahl erlaubt (siehe K2). Kein neuer Datenverlust, aber die Grenze der Ausnahme muss neu gefasst werden.

**[wichtig] R6d — `selectProject("")` = Inbox-Root ist der verworfenen Weg-1b-Zustand.** `selectProject("")` setzt `currentProject = ""` (`app.js:2674–2675`), was im UI „Unsortierte Einzeldateien verarbeiten" = ganze Inbox-Root bedeutet (`app.js:2811`). Der Sammelknopf **muss** über `files[]` (Weg 2) laufen und darf `project_name:""` + `mappings` **nie** kombinieren — sonst reintroduziert er exakt das [kritisch]-verworfenen Datenrisiko (Auffangregel/Root-Cleanup erreichen fremde Dateien, `briefing-65.md:44`, `processor.py:516–518/:974–980`).

**[kosmetisch] R6e — `__inbox_recursive__` ist als Gruppenschlüssel auszuschließen.** `suggested_query` könnte theoretisch `__inbox_recursive__` ergeben; der Sentinel ist ein realer UI-Eintrag (`app.js:2314`) und serverseitig mehrfach gesperrt (`project_api.py:267/680/874/954/1000`). Defensiv-AK: kein Pseudo-Eintrag mit Schlüssel `""` oder `__inbox_recursive__`.

## Neue Risiken durch die manuellen Kästchen

**[wichtig] K1 — Auswahlzustand über Rerender/fetch-Hinweg.** `renderSmartInboxList` leert `smartInboxList.innerHTML = ""` (`app.js:12413`) und baut alles neu. `loadStatus` pollt periodisch neu. Checkbox-DOM-Zustände überleben das nicht. Die Auswahl muss in einem DOM-unabhängigen JS-State (Set aus `data-project`-Keys) liegen und beim Rerender wiederhergestellt werden — sonst verschwinden 200 gesetzte Haken still.

**[wichtig] K2 — Misch-Auswahl (tv + freigegebene Filme).** Der Sammelknopf gruppiert alles Angehakte und sendet `media_type:"tv"` für alle. Die „genau EINER"-Regel (AK3) wird durch Mehrfachauswahl ausgehebelt: mehrere Film-Einträge würden gemeinsam als Serie verarbeitet. Regel nötig: Sammelknopf akzeptiert nur `media_type==="tv" && is_dir===false`; „Trotzdem freigeben" bleibt ein Einzelweg pro Eintrag.

**[kritisch] K3 — Ordner-Einträge gemischt mit Einzeldateien.** Der wichtigste neue Fall. Ein angehakter Ordner-Eintrag liefert `item.project` = Ordnername (ohne Endung). Server-AK5 lehnt das ab → HTTP 400 **nach** Absenden, aus Nutzersicht „Gruppieren funktioniert einfach nicht". Das Frontend muss (a) Ordner-Einträge nicht anhaktbar machen (Kästchen disabled) **oder** (b) beim Sammeln ausschließen und sichtbar melden. Ohne das ist der Kästchen-Weg für gemischte Inboxes (Dissens 2: dieselbe Serie als Ordner **und** als Einzeldatei) fehleranfällig.

**[wichtig] K4 — Auswahl nach Sortierwechsel.** Sortier-Klick (`app.js:12383–12392`) ruft `renderSmartInboxList` neu. Die Auswahl muss über `data-project`-Keys (nicht DOM-Indizes) überleben. Eigener Testfall zusätzlich zu K1.

**[wichtig] K5 — Duplikate.** (a) Doppel-Toggle idempotent halten; (b) Ordner `Show/` + Einzeldatei `Show.S01E01.mkv` haben denselben Schlüssel `Show` — der Ordner darf nie in die Datei-Gruppe rutschen (deckt sich mit K3); (c) Server-Dedup ist case-insensitiv (AK5), aber mappings-Keys müssen eindeutig bleiben.

**[kosmetisch] K6 — 264 Dateien im Payload.** `files[]` + `mappings` ≈ < 100 KB; `MAX_CONTENT_LENGTH` nicht gesetzt, waitress-Default ~1 GB (`briefing-65.md:126`). Kein Risiko, aber der 264er-Handtest muss den Job real starten (deckt auch Modal-Performance, Dissens 4).

## Konkrete, testbare AKs (Formulierung „es prüft, dass …")

**Backend (`tests/test_inbox_group_files.py`, Lauf A):**
1. **R6a/R6b-Ergänzung AK5:** „…dass ein `files[]`-Eintrag, der ein Ordnername ohne Video-Endung ist, zu HTTP 400 führt (nicht still gefiltert) und nie in einen Job mündet." *(deckt K3 serverseitig ab)*
2. **AK6e (V4):** „…dass `mappings`-Schlüssel außerhalb `files` in Preview UND Process ablehnen."

**Frontend (`tests/frontend/inbox_group.test.js`, Lauf B):**
3. **R6b-AK:** „…dass ein Gruppen-Pseudo-Eintrag **keinen** Quarantäne-Knopf (`.btn-delete-smart`) rendert, während normale Einträge ihn behalten — und dass `deleteProject` nie mit einem Gruppenschlüssel aufgerufen wird." *(zwingt R6a/R6b)*
4. **R6d-AK:** „…dass der Sammelknopf einen `basePayload` mit `files` (relativer Pfad je Mitglied) baut und `project_name` **nicht** leer übermittelt, wenn `files` gesetzt ist."
5. **K1/K4-AK:** „…dass die Auswahl (Set aus `data-project`-Keys) einen erneuten fetch/render **und** einen Sortierwechsel übersteht und wiederhergestellt wird."
6. **K2-AK:** „…dass der Sammelknopf nur Einträge mit `media_type==='tv' && is_dir===false` in `files[]` aufnimmt; Film-/Ordner-Einträge werden ausgeschlossen oder der Knopf deaktiviert."
7. **K3-AK:** „…dass ein angehakter Ordner-Eintrag (`is_dir===true`) nicht in `files[]` landet bzw. das Anhaken unterbunden ist."
8. **K5-AK:** „…dass doppeltes Anhaken desselben Eintrags idempotent ist (kein Duplikat in `files[]`)."
9. **AK3-Neuformulierung:** „Trotzdem als Serie freigeben" gilt pro Eintrag und bleibt ein Einzelweg; er übergibt den Einzeldatei-Pfad als `files[]` (R6c).

## VERDICT: REVISE

R6 ist real und datengefährlich in der Namenskollisions-Variante (R6a); die Kästchen-Führung macht es akut (Ordner anhakbar, Misch-Auswahl, Auswahl-Verlust). Kein AK des aktuellen Briefings erzwingt die Gegenmaßnahmen. Die oben gelisteten Forderungen (R6a/R6b/R6d + K1–K5) **müssen** in `briefing-65.md` als AKs landen, bevor Lauf A oder B startet — zusammen mit dem übergeordneten Widerspruchs-Umbau (V0).

**Kurzfassung der Einwände:**
1. [kritisch] R6a/R6b — Gruppen-Pseudo-Eintrag ohne Quarantäne-Knopf-Ausschluss (Namenskollision = Löschen realer Ordner).
2. [kritisch] R6d/K3 — Sammelknopf ohne `files[]`-Zwang bzw. Ordner-Einträge in `files[]` reintroduzieren Weg-1b-Datenrisiko.
3. [wichtig] K1/K4 — Auswahlzustand muss Rerender + Sortierwechsel überleben.
4. [wichtig] K2 — Misch-Auswahl hebelt „genau EINER"-Regel aus.
5. [wichtig] V1–V4 — Vertrags-/`is_dir`-/Ordner-400-/mappings⊆files-Lücken des Läufe-Schnitts.
6. [kosmetisch] A5/A6/K6/R6e — Zwischenzustand toter Code, Cache-Buster-Zuordnung, Payload-Größe, `__inbox_recursive__`-Sentinel.
</task_result>
</task>
