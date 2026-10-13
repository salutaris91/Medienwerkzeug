# Rückkanal: Abnahme Handtest-Nachbesserung „Einzelvideo-Ordner“ (2026-10-12)

**Auftraggeber:** Claude Code (Rolle Reviewer/Vermittler), **nicht Alex.**
**Alex' Sätze, wörtlich:** „1 wie empfohlen, ich mache erst den Handtest fertig“ und „mitnehmen wie empfohlen, ich mache mit HT1/HT2 weiter“.
**Prüfer:** Pomodoro (Worker-Rückkanal), statisch, Arbeitsbaum (uncommitteter Patch auf HEAD `6b7771d`).
**Methode und Grenze:** `bash: deny` → **keine Tests ausgeführt, kein `git`-Kommando ausgeführt.** Der Diff-Umfang (`app.js` +21/−14, 4 Dateien, Suite 513/1d + Frontend 186/186, „4 neue Tests gegen alten Stand rot“) ist **Behauptung von Claude Code, nicht von mir verifiziert**; meine Inhalte-Prüfung ist dazu konsistent (siehe §5). Alle folgenden Zeilenangaben habe ich selbst im Arbeitsbaum nachgelesen.

## ABNAHME: JA

Alle drei Auftragspunkte sind vorhanden und im gemeldeten (Desktop-)Szenario wirksam; Key-Vertrag unberührt; keine Regressionen gefunden. **Kein [kritisch]-Befund.** Zwei [wichtig]-Befunde als Vor-Commit-Auflagen bzw. Handtest-/ROADMAP-Punkte (§3, Befund 1 und 2).

---

## 1. Aufträge (1)–(3): korrekt und vollständig umgesetzt

### (1) Bulk-Leiste `position: sticky` — vorhanden, auf Desktop wirksam
- CSS-Regel: `gui/static/style.css:3896–3910` — `position: sticky; top: 0; z-index: 10`, opak unterlegter Hintergrund (`--bg-sticky`-Fallback), `margin-bottom: 12px` erhalten.
- JS zeigt die Leiste mit `display: flex` (`gui/static/app.js:12686`), überschreibt das CSS-`display: none` (style.css:3897) — Sticky gilt damit im sichtbaren Zustand.
- Layout-Kette geprüft (Befund (c), siehe §2): auf Desktop (>1024 px) **wirksam**; auf ≤1024 px **unwirksam** → Befund 2.
- Mobil-Media-Query `style.css:4064–4071` ergänzt nur `flex-wrap: wrap` für `#smart-inbox-bulk-actions` — deaktiviert Sticky nicht, aber Leiste wird auf schmalen Screens höher (kleben dann ohnehin nicht, s. Befund 2).

### (2) Zeilen-`title` bei Einzelvideo-Ordnern — vorhanden, aber Doppel-Maskierung → Befund 1
- Neu: `gui/static/app.js:13175–13179` — Guard identisch zur Checkbox-Logik (`item.is_dir === true && item.single_video_relpath`), setzt `itemDiv.title` **und** `setAttribute("title", …)`.
- Checkbox-`title` (bestehend): `app.js:13156`, korrekt.
- Lose Dateien und Multi-Video-Ordner erhalten **kein** title (Guard schließt sie aus; Test (a) prüft exakt das, `tests/frontend/inbox_group.test.js:2138–2146`).
- Gruppenzeilen (`app.js:13106–13109`, early return) erhalten keinen Zeilen-title — außerhalb des Auftrags, Notiz in §4.

### (3) `guess*`/`cleanFilenameForManualTitle` nur mit Dateinamen — vollständig
- Manueller Serienmodus: `app.js:3702` leitet `fileName = file.split(/[/\\]/).pop()` ab; alle drei Aufrufe nutzen jetzt `fileName` (`:3705 guessSeasonAndEpisode`, `:3713 guessEpisodeNumber`, `:3719 cleanFilenameForManualTitle`).
- All-Seasons-Fallback: `app.js:3814` gleiches Muster; `:3819`/`:3821` rufen mit `fileName`.
- **Alle Aufrufer geprüft:** weitere Aufrufstellen in `app.js` nur `:5243 guessEpisodeNumber(seg)` — das ist die **YouTube-Finalize-Zuordnung** (`renderYtMappingRows`, Segmente aus `data.segments` des YT-Tasks, `:5324`), **kein Inbox-relpath**, nicht Teil des Auftrags → nicht angefasst, korrekt so (Notiz §4). `js/parse.js` selbst ist unverändert (Auftrags-/Briefing-Grenze, Präzedenz ADR-65-4, `briefing.md:97`).
- `file` selbst unverändert: `data-file="${escapeHTML(file)}"` (`:3722`, `:3826`), Anzeige-Text `${escapeHTML(file)}` (`:3723`, `:3828`), Backend-Match `matches[file]` (`:3816`) — überall voller relpath.

### Key-Vertrag (mappings-Schlüssel == files-Strings) — unberührt ✓
- Mappings werden aus `row.getAttribute("data-file")` gebaut (`app.js:4348`/`4359` manuell, `4368`/`4388–4397` normal) — relpath.
- `payload.files = [...activeSeriesGroupFiles]` (`app.js:4449–4450`); `activeSeriesGroupFiles`/`projectFiles` kommen unverändert aus `startSeriesGroupWorkflow(groupName, files)` (`:12746/:12753`).
- `fileName` wird **ausschließlich** an die guess-/clean-Funktionen übergeben — kein einziger Schlüssel-/Payload-Pfad damit gebaut. Test H2 (`inbox_group.test.js:1113–1164`, inkl. Dateiname mit `"` ) und der Bulk-Test (`:2078–2094`, `files[] == single_video_relpath`) stehen weiterhin grün-erwartbar (statisch geprüft, nicht ausgeführt).

## 2. Hinweise (a)–(c) — Bewertung

**(a) Doppel-Maskierung: BESTÄTIGT.** `escapeHTML` (`app.js:245–253`) maskiert `& < > " '`. Der Zeilen-title wird per **DOM-Property** (`itemDiv.title`, `:13177`) und **`setAttribute`** (`:13178`) gesetzt — beide Pfade **parsen keine HTML-Entities**; die Maskierung wird wörtlich übernommen. Ein relpath `Film & Kino/Folge.mkv` zeigt im Zeilen-Tooltip `Verarbeitet wird: Film &amp; Kino/Folge.mkv`. Der Checkbox-Tooltip (`:13156`, läuft über `innerHTML` → Parser dekodiert) zeigt denselben Text **richtig** → ein und dieselbe Datei zeigt je nach Hover-Ziel zwei unterschiedliche Tooltips. **Kein Sicherheitsproblem** (Property/setAttribute sind inert), aber ein sichtbarer Fehler im neuen Code. Test (a) (`inbox_group.test.js:2107`) nutzt einen Pfad ohne Sonderzeichen und kann den Fehler nicht fangen → Testlücke.

**(b) Stub-Zeilen `\d` → `\\d`: Korrektur ist NÖTIG und für bestehende Tests WIRKUNGSNEUTRAL.** Die Stubs (`inbox_group.test.js:572–579`) werden in einem Template-Literal gebaut; `\d` im Template ergibt das generierte Regex `(d+)` (matcht Buchstabe „d“, nie Ziffern) — der Stub war vorher faktisch tot (`guessSeasonAndEpisode` immer `null`, `guessEpisodeNumber` immer Fallback `1`). Ohne `\\d` wäre **der neue Test (c) auch gegen den gepatchten Code rot** (Select fände nie `S02E05`) → die Änderung war zwingend, nicht nur „Ergänzung“. Neutralitätsprüfung: keine der bestehenden `renderMatchingMatrix`-Tests (Zeilen 1125, 1191, 1731, 1820, 1833, 1848, 1862) assertet **geratene Staffel-/Folgenwerte** — nur `data-file`-Schlüssel, Zeilenanzahl, Alerts/Preview-Aufrufe; die Werte, die sich durch den lebendigen Stub ändern (z. B. H2 Zeile 2 statt 1), werden dort nicht geprüft. Die formale „nur ergänzen“-Verletzung ist damit gerechtfertigt und sollte im Commit-Message genannt werden.

**(c) Sticky im realen Layout:**
- **Desktop (>1024 px): WIRKT.** Scroll-Container der Startseite ist `main.detail-content` (`style.css:1583–1590`, `overflow-y: auto`, Höhe durch `.master-detail-layout` `style.css:1549–1557` begrenzt; `body` selbst `overflow: hidden`, `style.css:170–183`). Zwischen Leiste und diesem Scrollport liegt **kein** overflow-Vorfahr: `div` (`index.html:456`, nur inline `margin-top`) → `.card` (`style.css:424–434`, kein overflow) → `.view-panel` (`style.css:1592–1598`, kein overflow). `top: 0` klebt am Rand von `detail-content`, **unterhalb** des `app-header` (der klebt am Viewport-Rand, `style.css:218–233`, und liegt außerhalb des Scrollports) → keine Überlappung; `z-index: 10` gegen statische Zeilen ausreichend; opaker Hintergrund verhindert Durchscheinen.
- **Mobil/schmal (≤1024 px): WIRKT NICHT.** Media-Query `style.css:2322–2350` verlagert das Scrollen auf `body` (`overflow-y: auto !important`) und setzt `.detail-content { overflow-y: visible !important; height: auto }` — **aber** `.master-detail-layout` behält `overflow: hidden` (Zeile 1553, im Media-Query nicht überschrieben). Ein `overflow: hidden`-Element ist per Spec ein Scrollcontainer, der auf Mobil nie scrollt (Höhe = Inhaltshöhe) → das Sticky-Element wird an diesem nie scrollenden Scrollport ausgerichtet und klebt **nie**. Die Leiste läuft auf Mobil/Tablet-Width also weiterhin mit ~9800 px außer Sicht. → Befund 2.

## 3. Befunde

- **Befund 1 [wichtig] — Doppel-Maskierung im neuen Zeilen-title** (`app.js:13176`): `escapeHTML(...)` + Property/`setAttribute` → `&`, `'`, `"`, `<`, `>` erscheinen als `&amp;`/`&#039;`/`&quot;`/`&lt;`/`&gt;` im Tooltip; inconsistent zum Checkbox-Tooltip (`:13156`, korrekt). **Vor dem Commit nachziehen:** in `:13176` das rohe `item.single_video_relpath` verwenden (Property-Setzung braucht keine Maskierung); `setAttribute` (`:13178`) kann entfallen — die Property-Setzung spiegelt das Attribut. Test (a) um einen Fall mit `&` ergänzen (aktuelle Testdaten `inbox_group.test.js:2107` fangen den Fehler nicht).
- **Befund 2 [wichtig] — Sticky greift erst oberhalb 1024 px** (`style.css:1553` vs. `2322–2350`): auf ≤1024 px kein Kleben (Analyse §2c). Der Handtest-Befund (100+ Einträge) ist ein Desktop-Szenario, daher **keine** Rückkehr zum alten Verhalten — aber die Nachbesserung ist nur teilweise wirksam. Empfehlung: **nicht** in diesem Patch die Layout-Kaskade umbauen (Scope, Risiko); Verhalten im Handtest HT1/HT2 an einem schmalen Fenster prüfen und als Punkt in `ROADMAP.md` festhalten.
- **Befund 3 [kosmetisch] — doppelter title-Setzer** (`app.js:13177–13178`): Property **und** `setAttribute` für dasselbe Attribut; Test (a) assertet beide Varianten (`:2131–2132`), formal ok, aber eine Zeile ist überflüssig.
- **Befund 4 [kosmetisch] — Stub driftdet weiter von echtem parse.js** (`inbox_group.test.js:574`): Stub-`guessEpisodeNumber` fällt auf `1` zurück, reales parse.js liefert `null` — bestehende Divergenz, durch die (b)-Korrektur kleiner, aber nicht beseitigt. Kein Handeln required.

## 4. Notizen am Rand (nicht angefasst, außerhalb Auftrag)

- `app.js:3736`: `value="${cleanTitle}"` in der manuellen Zeile **unescaped** — bei `"` im Dateinamen bricht das Attribut. **Bestandscode, vor dem Patch genauso** (der Patch änderte nur das Argument `file`→`fileName`) → nicht Teil dieser Nachbesserung; Kandidat für eigene kleine Fix-Runde.
- `app.js:5243` (`renderYtMappingRows`): `guessEpisodeNumber(seg)` auf YT-Segmentnamen — eigene Sicht, keine Inbox-relpaths, bewusst nicht geändert.
- Gruppenzeilen/Gruppenmitglieder (`app.js:13106–3110`, `:13040–13054`) erhalten keinen „Verarbeitet wird“-title — der Auftrag nannte nur die Einzelvideo-Ordner-Zeile; für Gruppen ist die Member-Anzeige existing behavior.
- Test (d) (`inbox_group.test.js:2210–2221`) prüft nur die **CSS-Regel-Existenz** per Regex, nicht die Wirksamkeit — die eigentliche Wirksamkeit ist Handtest-Materie (HT-Punkt: Leiste bleibt bei 100+ Einträgen sichtbar; plus schmaler Viewport laut Befund 2).

## 5. Regressionen (Auftrag 3)

- **Aufträge ohne `files[]`** (normaler Einzelprojekt-Pfad): `payload.files` wird nur bei `activeSeriesGroupFiles` gesetzt (`app.js:4449–4450`) — unverändert; `projectFiles`-Listings behalten vollen relpath in `data-file`/Anzeige; nur Vorauswahl/Titel-Default ändert sich beabsichtigt (bei flachen Dateien ist `fileName === file` → **identisches Verhalten** wie vorher).
- **Lose Dateien:** `inboxFilesEntryForItem` (`app.js:12494–12500`) unverändert (`item.project`); Eligibility `:13147–13149` unverändert; Zeilen-title-Guard schließt lose Dateien aus (Test (a) `:2138–2141`).
- **Cache-Buster konsistent:** `index.html:2760` `app.js?v=101`, `index.html:9` `style.css?v=50`; **alle neun** Modul-Importe `app.js:1–9` auf `?v=101` — zwingend, weil `cache_busting.test.js:13–47` Index↔Import-Identität erzwingt (HEAD war v100 laut `rueckkanal.md:32`); das erklärt die Diff-Größe `app.js` +21/−14 plausibel (9 Importzeilen + Logik). `style.css`-Version ist test-seitig nur „nicht leer“ gefordert (`cache_busting.test.js:50–56`) → v50 unkritisch.
- **Die 4 neuen Tests** (a) `:2101`, (b) `:2149`, (c) `:2180`, (d) `:2210` sind gegen den alten Stand erwartbar rot (Zeilen-title neu; Titel-Default ohne Ordneranteil nur mit basename; S02E05-Vorauswahl nur mit basename + lebendigem Stub; sticky-Regel neu) — Plausibilität von Claude Code statisch bestätigt.

## 6. Empfehlung an Claude Code

1. **Vor dem Commit:** Befund 1 beheben (eine Zeile in `app.js:13176`, `setAttribute`-Zeile optional löschen) + Test (a) um `&`-Fall erweitern. Minimales Risiko, behebt einen sichtbaren Fehler im neuen Code.
2. **Im Handtest HT1/HT2:** (i) Ordner mit `&`/`'` im Namen als Sticky- und Tooltip-Fall aufnehmen; (ii) Bulk-Leiste bei 100+ Einträgen **und** in schmalstem Fenster prüfen (Befund 2: ≤1024 px erwartet **kein** Kleben — wenn das als Akzeptanzlücke gewertet wird, ist ein Follow-up nötig, nicht dieser Patch).
3. **Bei Alex/ROADMAP dokumentieren:** Befund 2 (Mobil-Limitation) und Notiz „`manual-title`-value unescaped“ (§4) als eigene Punkte.
4. Suite-Zahlen (513/1d, 186/186) und Git-Umfang vor dem Commit von Claude Code mit echtem `git status --short --branch` + `git diff --stat` offenlegen — mir lag kein Git-Zustand vor (bash verwehrt); **kein Commit-Vorschlag dieser Abnahme ohne diesen Beleg.**

**Dissens-Notiz:** Gate-A2 (2 Runden, APPROVED) hat Befunde 1 und 2 nicht markiert; diese Abnahme weicht in der Tiefe ab und führt sie als [wichtig] auf. Verworfen als Alternative zu Befund-1-Fix: Escape im Attribut-Pfad belassen und nur `innerHTML`-Variante bauen — mehr Codeumbruch als nötig; Property-Setzung ohne Escape ist die einfachste korrekte Form.

*Ende des Rückkanals. STOPP gemäß Auftrag — keine Code-Änderung, kein Git, keine weitere Datei.*
