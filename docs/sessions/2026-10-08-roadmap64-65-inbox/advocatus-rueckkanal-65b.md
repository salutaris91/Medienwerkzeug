# Rohoutput advocatus — Rückkanal-Abnahme #65 Lauf B, 2026-10-11

Hinweis Claude Code (2026-10-11): Mechanisch aus `opencode export ses_ed5ab38dbffeCFt68B8VTGCsW7` (ceo-planner, Rückkanal-Sitzung) abgelegt, nicht vom Moderator abgeschrieben (Lehre 59). Einzige Änderung: Trailing Whitespace entfernt. Volle Daten: Kit `scripts/gate-a2/logs/2026-10-11-roadmap65-lauf-b/export-rueckkanal.json`.

---

## advocatus: Risiken Lauf B (Subagent-Sitzung ses_ed59f14b6ffeKm9PuHy6l9pcxx, Status: completed)

<task id="ses_ed59f14b6ffeKm9PuHy6l9pcxx" state="completed">
<task_result>
Ich habe die drei Lauf-A-Runden, das Briefing (11b, AK1–AK4, AK9–AK13, ADR-65-4/5, Abschnitt 5a), den kompletten Lauf-B-Diff (`app.js`, `index.html`, `style.css`, `inbox_group.test.js`) sowie die unveränderlichen Server-Nahtstellen (`project_api.py`, `helpers.py`, `queue_api.py`, `processor.py`) gelesen. Hier der Bericht.

---

# Rückkanal-Report ROADMAP #65, Lauf B (Oberfläche) — [advocatus]

**Prüfgegenstand:** Head `7424f2a` „feat(inbox): group SxxExx episodes as a series … (ROADMAP #65, run B)". Nur Lesezugriff im exklusiven Worktree, keine Git-/Shell-/Webaktionen. Referenzen: `rueckkanal-65a.md` + `-r2.md` + `-r3.md` (alle drei gelesen; sie sind **Server-Läufe** — alles unten ist damit automatisch **neu gegenüber R1–R4/N1–N6/D1–D4**, außer wo explizit „Vorbestand" markiert).

**Gesamteindruck vorab:** Kein neuer [kritisch]-Befund (kein stiller Datenverlust über legitime Client-Aktionen; die drei Lauf-A-Runden haben die Server-Ziel-/Quell-Seite dichtgemacht). Aber drei [wichtig]-Befunde, die alle an der **Nahtstelle A→B** bzw. am **264-Folgen-Kern** liegen — genau die zwei Restrisiken, die ADR-65-2/ADR-65-7 als riskanteste Punkte benannt haben.

---

## (A) Verifikation/Widerlegung der Verdachtspunkte 1–9

**1. XSS/Attribut-Injection bei Dateinamen — TEILWEISE bestätigt, Schwere niedriger als befürchtet.**
- Die **neuen** Renderpfade escapen korrekt, inkl. `"`: `escapeHTML` (`app.js:245–253`, `"`→`&quot;` in `:251`); Banner `:12501/12504/12505`, Gruppenzeile `:12714/12719`, Mitglieder `:12736`, Einträge `:12819/12828/12841/12858/12859` — alle über `escapeHTML`. ✅
- Die **bestehenden** Pfade sind weiter unescaped: `renderMatchingMatrix` `data-file="${file}"` + nacktes `${file}` im `innerHTML` (`app.js:3715/3716` manuell, `:3818/3819/3820` normal) und Preview-Modal `data-old="${item.old}"`/`${item.old}` (`app.js:10347/10349`). **Aber:** Diese Pfade sind Vorbestand und waren über den Ordner-Flow (gleiche `projectFiles`-Eingabeklasse) schon vor #65 erreichbar — die Injektionsfläche ist **nicht neu**, nur die Einspeisung über die Gruppe.
- **Neu** (echte Konsequenz von #65): Ein `"` im Dateinamen bricht den **Key-Vertrag** — `data-file="${file}"` wird beim HTML-Parsen abgeschnitten, `row.getAttribute("data-file")` (`app.js:4323/4343`) liefert den gestutzten String, der nicht in `files` liegt → Server-400 „Ungültiger Mapping-Schlüssel" (`queue_api.py:87–90`). Folge unten als Finding B2/B4.

**2. AK4-Nahtstelle — BESTÄTIGT (toter Code, realer Vertrag ungetestet).**
- `createSeriesGroupPayload` (`app.js:12588–12619`) wird **produktiv nie aufgerufen** — Reposuche: nur Definition (`:12588`) und `globalThis`-Export (`:12923`), kein Aufruf. Der AK4-Test (`inbox_group.test.js:888–902`) testet damit toten Code.
- Der echte Payload entsteht in `executeSeriesWorkflow` (`app.js:4307–4467`): `files` aus `activeSeriesGroupFiles` (`:4424–4426`), `mappings`-Schlüssel aus DOM-`data-file` (`:4318–4377`). Der Vertrag „mappings-Schlüssel ≡ files-Strings" ist **nicht statisch**, sondern nur dynamisch über das DOM garantiert und bricht bei: (a) nicht-client-Video-Endung (→ kein Row, Finding B1), (b) `"` im Namen (→ gestutzter `data-file`, Finding B4), (c) „skip" (bewusst, harmlos — Server prüft nur mappings⊆files, `queue_api.py:85–90`, und der Processor iteriert `mappings`, `processor.py:1194`, lässt Geskippte liegen). Happy Path stimmt, aber kein Test deckt den echten Pfad.

**3. Endungs-Asymmetrie — BESTÄTIGT, Mechanismus KORRIGIERT.**
- Client-Filter `renderMatchingMatrix` `['mp4','mkv','avi','webm','mov']` (`app.js:3681`) vs. Server `GROUP_VIDEO_EXTENSIONS` = 10 Endungen inkl. `.ts/.m2ts/.flv/.3gp/.wmv` (`helpers.py:798`) und Inbox-Listung `.ts` (`project_api.py:1321`). ✅
- **Korrektur der behaupteten Folge:** Die `.ts`-Datei wird **nicht** „halb umbenannt". Die Vorschau iteriert `all_files`, liest bei `files`-Jobs `ep_num = mappings.get(f)` (`queue_api.py:498`); ohne Mapping greift `else: pass` (`:634–635`) → **kein** Rename-Eintrag → kein `explicit_renames` → Processor iteriert `mappings` (`processor.py:1194`) → Datei bleibt **unberührt** liegen. Kein Datenverlust.
- **Die reale Folge ist schlimmer als „kein Mapping", aber anders:** Die Datei wird **stillschweigend ausgelassen**, die Gruppenzeile zählt aber `video_count = members.length` inkl. `.ts` (`app.js:12450`) → „264 Folgen" angezeigt, nur 263 verarbeitet, keine Warnung. Das ist exakt das von ADR-65-4 verworfenen „Client-Endungsliste (zweite Liste, Drift)"-Szenario, jetzt materialisiert. Bewertung: **[wichtig]** (Finding B1).

**4. Zustand nach Rerender/Polling — BESTÄTIGT (Aufklapp-Zusammenfall), Doppelstart nur teilweise.**
- (a) **Bestätigt:** `setInterval(loadStatus, 6000)` (`app.js:556`) → `loadStatus` → `updateHomepageData` (`:2274–2275`) → `fetchSmartInboxSuggestions` → `renderSmartInboxList` (`:12272`) → **vollständiger DOM-Neuaufbau** (`smartInboxList.innerHTML=""`, `:12685`). Der Gruppen-Aufklappzustand (`aria-expanded`, `:12748–12750`) ist reine DOM-Zustand und fällt damit **alle 6 Sekunden** zusammen. Selection (`selectedInboxProjects`, `:12372`) und `appliedInboxGroups`/`unlockedMovieProjects` überleben (Modul-Sets, `checked` re-abgeleitet `:12817`). AK12 ist korrekt; der Aufklapp-Fall ist ein eigenständiger UX-Defekt (Finding B3).
- (b) **Doppelstart:** Der Guard `activeProjectsProcessing.has(currentProject || "")` (`app.js:4308`) läuft in Gruppenmodi mit `currentProject=""` (`:12570`) **nicht ins Leere, wenn** der Server `project_name=""` zurückmeldet (dann enthält `activeProjectsProcessing` `""`, `app.js:10765–10768`). **Aber** die Gruppenzeilen-Knöpfe (`btn-select-group`, `:12719/12765`) und Banner-Apply (`:12518`) tragen **keinen** `isProcessing`-Guard (anders als Einzel-Checkbox/-Knopf). Restrisiko → Finding B5.
- (c) Stale `activeSeriesGroupFiles`: **weitgehend entkräftet** — wird bei `scanProject` (`:2870–2873`) und `handleSmartInboxClick` (`:12931–12934`) zurückgesetzt; dadurch kein Leak in einen Ordner-Job (siehe C).

**5. Fehlerdarstellung — BESTÄTIGT, [klein].** Preview-400: `if (!response.ok) throw new Error("Fehler beim Abrufen der Vorschau")` (`app.js:10286`) **verwirft** den Server-Body (die spezifische 400-Meldung aus `queue_api.py:82–90` wird nie gelesen); `catch` → `alert("Fehler: " + e.message)` (`:10370–10372`). Process-400: nur `appendConsoleLog("[System] Fehler beim Starten des Prozesses.")` (`:10641`), Modal bereits geschlossen (`:10628`). Generisch, aber Vorbestand; **neu relevant**, weil die neuen 400-Klassen (Mapping-Schlüssel, files-Validierung) jetzt genau hier maskiert werden (verschärft B2/B4).

**6. Tests — weitgehend entkräftet, eine Deckungslücke.**
- Keine echten Timer im Test; `searchSeries` wird über `startSeriesGroupWorkflow` zwar echt aufgerufen, aber mit gemocktem `fetch` (`:380–384`), und `searchSeries` fängt seinen eigenen Fehler intern (`:3203–3207`) → keine Unhandled Rejection. Das `eval`-Muster ist das bewährte #64-Muster; `setupTestEnvironment` pro Test erzeugt frische `let`-Bindungen (App-Zeilen `:12372–12375`), Tests sind idempotent. `DOMContentLoaded`-Handler wird via No-Op-`addEventListener` (`:376`) nie ausgeführt → kein `setInterval(loadStatus,6000)` im Test.
- **Deckungslücke:** AK4 testet `createSeriesGroupPayload` (tot) statt `executeSeriesWorkflow` (Finding B2); der Mode-Wechsel („wechselt in den Serien-Modus") wird durch No-Op-`modeCard.click()` faktisch **nicht** geprüft; Endungs-Lücke und `"`-Fall sind ungetestet.

**7. AK1-Muster / is_dir-Asymmetrie — Muster entkräftet, is_dir-Asymmetrie [kosmetisch].**
- Regex `(?:^|[._\s\-\[])[sS](\d{1,2})[eE](\d{1,3})(?:[._\s\-\]]|$)` (`app.js:12379`) ist durch den **Server-Vorfilter** (`tv_pattern`, `project_api.py:1413`) abgesichert — die Automatik greift nur bei `media_type==="tv"` && nicht-leerem `suggested_query` (`:12396–12398`). Die 4 AK1-Fälle passen (getestet `:428–449`). „Bastille.S04E…", „S02E99x", „Staffel 2 Folge 3" landen korrekt nicht/anders. Rest: `e(\d{1,3})` vs. Server `e\d{1,2}` (`project_api.py:1413`) — kosmetischer Drift ohne Gruppenwirkung.
- `detectInboxGroups` prüft `is_dir === true` (skip, `:12396`), Checkbox-Eligibility `is_dir === false` (`:12811`). Die Asymmetrie ist real, aber **theoretisch**: `is_dir` wird vom Server **immer** als bool geliefert (`project_api.py:1502`), Cache-Buster v96 (`index.html:2760`) koppelt JS/Server atomar; ein „altes Payload ohne is_dir"-Mix ist beim monolithischen NAS-Image-Deploy praktisch ausgeschlossen. → [kosmetisch] (C/D).

**8. AK11 — BESTÄTIGT erfüllt.** Gruppenzeile: Klasse `smart-inbox-group-row`, Attribut `data-group-key`, **kein** `data-project`, **kein** Quarantäne-Knopf (`app.js:12690–12693`, `:12723`); reaktive Schleife selektiert nur `#smart-inbox-list .smart-inbox-item` (`:2458`) + Guard `:2460`. Kollision Gruppe „Show" vs. Ordner „Show" sind getrennte DOM-Knoten; der Ordner behält seinen Löschpfad (Test `:847–872`). `deleteProject` nie über Gruppenzeile erreichbar. ✅

**9. 264-Folgen-Performance — [klein], eng mit B3 verkoppelt.** `item.items.forEach` baut alle Mitglieder flach als `display:none`-Elemente (`app.js:12729–12743`) — ~264×~6 Knoten ≈ 1500 Knoten, die **alle 6 s** (via B3-Rebuild) neu erzeugt werden. Für Einzelnutzer-LAN CPU-seitig unkritisch; das eigentliche Problem ist der Zusammenfall (B3), nicht die Rechenzeit. Das vom Briefing (Dissens 4) akzeptierte Modal-Restrisiko bleibt unverändert.

---

## (B) NEUE Findings (sortiert nach Schwere)

### B1 [wichtig] — Nicht-Client-Video-Endungen werden stillschweigend aus der Gruppe ausgelassen (Endungs-Drift)
- **Mechanismus:** `detectInboxGroups` gruppiert jede tv-Einzeldatei mit SxxExx — ohne Endungsfilter (`app.js:12396–12405`). `.ts`/`.m2ts`/`.flv`/`.3gp`/`.wmv` landen in `activeSeriesGroupFiles` und in `video_count` (`:12450`), aber `renderMatchingMatrix` filtert sie aus (`:3677–3682`, nur 5 Endungen). Folge: keine Matching-Row → kein Mapping → Vorschau `pass` (`queue_api.py:498/634`) → Processor lässt sie liegen (`processor.py:1194`). Gruppenzeile sagt „N Folgen", verarbeitet werden N−k, **ohne Hinweis**.
- **Repro (legitim):** Inbox enthält `Show.S01E01.ts` + `Show.S01E02.ts` (Server klassifiziert beide tv, `.ts` ist in `project_api.py:1321`). Auto-Gruppe „Show" → Banner/Gruppenzeile „2 Folgen" → Bestätigen → Vorschau zeigt **0** Renames, beide `.ts` bleiben unverarbeitet in der Inbox.
- **Frontend-Test fängt es?** Nein — kein Test legt eine `.ts`-Gruppe an; AK4 testet zudem toten Code.
- **Fix-Richtung:** Client-Filter in `renderMatchingMatrix` auf die Server-Liste (`helpers.py:798`) angleichen, oder Gruppierungs-Kandidaten serverseitig/über die Server-Endungsliste filtern; mindestens die Gruppen-Zählung (`video_count`) nur über verarbeitbare Mitglieder führen.

### B2 [wichtig] — AK4 testet toten Code; der reale Key-Vertrag ist ungetestet und bricht an zwei Stellen
- **Mechanismus:** `createSeriesGroupPayload` (`app.js:12588`) ist tot (nur Definition + `globalThis`-Export `:12923`). Der AK4-Test (`inbox_group.test.js:888–902`) assertiert damit eine Funktion, die nie läuft. Der echte Vertrag wird in `executeSeriesWorkflow` aus dem DOM gebaut (`mappings` aus `data-file` `:4318–4377`, `files` aus `activeSeriesGroupFiles` `:4424`); seine einzige statische Garantie ist die ADR-65-2-Zusage, die kein Frontend-Test verifiziert.
- **Bruchbedingungen:** (a) B1 (keine Row → kein Mapping); (b) `"` im Dateinamen (→ gestutzter `data-file`, Server-400 `queue_api.py:87–90`); (c) der Mode-Wechsel selbst ist im Test ein No-Op (`modeCard.click()` auf Mock ohne Listener).
- **Repro (legitim):** Datei `Show.S01E01.The "Best".mkv` (Server tv, `tv_pattern` matcht `S01E01`). Auto-Gruppe → Handover → `renderMatchingMatrix` setzt `data-file="Show.S01E01.The "Best".mkv"` (ungescaped, `:3818`) → `getAttribute` liefert `"Show.S01E01.The "` → Server-400, maskiert durch B4.
- **Frontend-Test fängt es?** Nein (toter Code; kein `"`-Fall, kein Endungs-Fall, keine echte `executeSeriesWorkflow`-Ausführung).

### B3 [wichtig] — Gruppen-Aufklappzustand fällt alle 6 Sekunden zusammen (264-Folgen-Inspektion de facto unbenutzbar)
- **Mechanismus:** `setInterval(loadStatus, 6000)` (`app.js:556`) → `updateHomepageData` (`:2274–2275`) → `renderSmartInboxList` → `smartInboxList.innerHTML=""` (`:12685`) und vollständiger Neuaufbau. `aria-expanded`/`membersDiv.style.display` (`:12747–12753`) sind DOM-only und gehen verloren.
- **Repro (legitim):** Gruppe „Show" aufklappen → innerhalb ≤6 s klappt die Liste wieder zu; bei 264 Folgen ist die laut AK2 geforderte (Staffel,Folge)-geordnete Mitglieder-Inspektion praktisch nicht durchführbar.
- **Frontend-Test fängt es?** Nein — kein Test simuliert den 6-s-`loadStatus`-Rebuild; AK12 prüft nur Selection-Persistenz (die hält), nicht den Aufklapp-Zustand.

### B4 [klein] — Spezifische Server-400-Meldungen werden im Handover verschluckt
- **Mechanismus:** `openPreviewModal` verwirft den Body bei `!response.ok` (`app.js:10286`) und alertet nur den generischen Text (`:10370`); `data.error`-Zweig (`:10289`) wird nie erreicht, weil Validierungs-400er nicht `ok` sind. Process-400 nur generisches Log (`:10641`), Modal zu (`:10628`).
- **Wirkung:** Die neuen, präzisen Server-Fehlermeldungen (welcher Mapping-Schlüssel, welche Datei, warum — `queue_api.py:82–90`, `helpers.py:801–867`) erreichen den Nutzer nie. Verschärft B1/B2 (stiller Leerlauf bzw. kryptischer 400 ohne Dateiname).
- **Frontend-Test fängt es?** Nein (Mock-Fetch liefert immer `ok:true`).

### B5 [klein] — Gruppenzeilen-Knöpfe ohne `isProcessing`-Guard; Doppelstart-Schutz hängt an Server-Meldung `project_name=""`
- **Mechanismus:** `btn-select-group` (`app.js:12719/12765`) und Banner-Apply (`:12518`) sind nicht `isProcessing`-gegated (anders als Einzel-Eintrag `:12818`). Der einzige Schutz ist `executeSeriesWorkflow`-Guard `:4308`, der bei `currentProject=""` nur greift, **wenn** `/api/queue` den Job mit `project_name:""` meldet (`app.js:10765–10768`) — das ist serverseitig nicht durch einen Frontend-Test abgesichert.
- **Repro (legitim):** Gruppe anwenden → Prozess starten → vor Abschluss erneut „Als Serie gruppieren" auf derselben (weiter sichtbaren) Gruppenzeile → zweiter Durchlauf. Rückhalt: Lauf-A-TOCTOU/Kollisions-Guards (`processor.py`, Runde 3) machen einen zweiten Lauf laut, nicht still.
- **Frontend-Test fängt es?** Nein (kein Test für Doppelklick während Verarbeitung; `renderQueue`-Pfad nicht abgedeckt).

### B6 [klein] — `anime`-Medientyp ist vollständig von der Gruppierung ausgeschlossen (ohne Sperr-Hinweis)
- **Mechanismus:** Server kann `media_type="anime"` setzen (`project_api.py:1470–1471`). `detectInboxGroups` verlangt `media_type !== "tv"` (`app.js:12396`); Checkbox-Eligibility nur `tv`/freigegebener `movie` (`:12811–12813`). Anime bekommt weder Auto-Gruppe noch Checkbox noch Freigabe-Link — aber auch keinen Film-Sperr-Hinweis. Scope-Lücke (Briefing nennt nur tv + Film-Ausnahme), kein Datenrisiko.
- **Frontend-Test fängt es?** Nein (kein Anime-Fall; Verhalten implizit „korrekt" im Sinne des Briefings, aber unkommuniziert).

### B7 [kosmetisch] — `is_dir`-Asymmetrie (`=== true` skip vs. `=== false` eligibility)
- Siehe (A)7. Real folgenlos (Server liefert immer bool), aber inkonsistente Defensiv-Codierung; bei künftigem Payload-Refactoring fällt der Ordner-Fall ggf. still auseinander. Fix: beide Stellen auf `item.is_dir === true` bzw. `!== true` vereinheitlichen.

---

## (C) Geprüft und entkräftet (keine Findings)

- **XSS über neue Renderpfade:** alle neuen Pfade escapen inkl. `"` (`app.js:245–253`, `:12501/12714/12719/12736/12819/12828/12841`).
- **Unescaped `renderMatchingMatrix`/Preview-Modal als *neue* Fläche:** Vorbestand, bereits über Ordner-Flow erreichbar — nicht durch #65 eingeführt (nur neu eingespeist).
- **`.ts` wird „halb umbenannt":** widerlegt — Vorschau erzeugt ohne Mapping keinen Rename (`queue_api.py:498/634`), Datei bleibt unangetastet liegen (das eigentliche Problem ist die stille Auslassung, B1).
- **Stale `activeSeriesGroupFiles` leakt in Ordner-Job:** widerlegt — `scanProject` (`app.js:2870–2873`) und `handleSmartInboxClick` (`:12931–12934`) setzen zurück, bevor ein Ordner-Matching aufgebaut wird.
- **AK11/Löschpfad-Freiheit:** erfüllt (eigene Klasse, eigener Schlüssel, kein `data-project`; reaktive Schleife `:2458/2460` erfasst Gruppenzeilen nie).
- **Test-Hygiene:** keine echten Timer, keine Unhandled Rejections (searchSeries fängt intern, `:3203`), idempotente `setupTestEnvironment`-Aufrufe, Mock-Fetch abgedeckt.
- **`is_dir===undefined`-Deploy-Mix:** praktisch ausgeschlossen (Server liefert immer bool `project_api.py:1502`, Cache-Buster v96 koppelt atomar, monolithisches Image).
- **CSRF:** Wrapper `app.js:14–30` umhüllt alle `fetch`-Aufrufe (inkl. der neuen Preview/Process/Search-Fetches); kein neuer ungetokenter POST.
- **`appendConsoleLog` XSS:** nutzt `textContent` (`app.js:2187`), kein `innerHTML` — safe.
- **sessionStorage-/id-Kollisionen:** Ignore-Keys präfixiert (`smart-inbox-ignore-group-`, `:12512`), Bulk-IDs werden per `innerHTML`-Ersatz nie dupliziert.
- **Cache-Buster AK9:** `app.js?v=96` (`index.html:2760`, alle 9 Importe `app.js:1–9`) und `style.css?v=49` (`:9`) korrekt; `style.css`-Append-Block vorhanden (`:3866–4068`, inkl. 600px-`flex-wrap` `:4062–4066`).
- **AK12/AK13-Kern:** Checkbox nur für tv-Einzeldatei + freigegebenen Film, `isProcessing`-Guard greift (Tests `:724–775`), Auswahl überlebt Re-Render/Sortierung (getestet).

---

## (D) Restunsicherheiten (nicht selbst prüfbar)

- **Kein bash/git:** Head-Identität `7424f2a`, Diff-Umfang (4 Dateien), `git diff --check` und die gemeldeten Testergebnisse (Frontend grün) sind fremde Berichte — ich habe nur Code gelesen, nichts ausgeführt.
- **Server-Meldung `project_name=""`:** Ob `/api/queue` für einen `files[]`-Job wirklich `project_name:""` zurückliefert (wodurch der Doppelstart-Guard greift), konnte ich nur indirekt aus dem Client-Code (`app.js:10765`) ableiten, nicht gegen den Server-Job-Payload verifizieren — der eigentliche Prozess-Payload sendet `project_name:""` (`app.js:4405`), die Status-Serialisierung habe ich nicht gegengeprüft.
- **End-to-End-Kette gegen echten Server:** B-Tests mocken `fetch`; die reale Nahtstelle (B1/B2) ist nur per Handtest mit der echten 11-Staffel-Serie (Briefing Abschnitt 8) belegbar — dort sollten `.ts`-Mitglieder und ein Dateiname mit `"` explizit mitgetestet werden.
- **`renderQueue`/6-s-Interaktion:** Das genaue Zusammenspiel von `loadStatus`-Rebuild und dem 2-s-`pollQueue`-Reactive-Loop (`:2458`) im laufenden Betrieb (kein Flackern/doppeltes Rendern) ist statisch plausibel, aber nicht ausgeführt.

---

*Ende des Lauf-B-Rückkanals. Gemäß Auftrag: nur gelesen, keine Schreib-/Git-/Webaktion. Es gibt keinen [kritisch]-Befund; die vier Befunde B1–B3 ([wichtig]) und B4–B7 ([klein]/[kosmetisch]) liegen sämtlich im Oberflächen-Scope von Lauf B und setzen auf dem in Lauf A hart abgesicherten Server-Pfad auf.*
</task_result>
</task>
