<!-- Mechanisch aus `opencode export ses_eb76ded1fffevy6pqe3GaXdZYv` extrahiert (Claude Code, 2026-10-17): alle Assistant-Textteile in Reihenfolge, ungekürzt, unverändert (nur Trailing Whitespace entfernt). Rohdatei: Kit scripts/gate-a2/logs/2026-10-16-roadmap75-inbox-vorschlaege/akt2/export-direkt/export-advocatus.json -->

## Advocatus-Risikoanalyse ROADMAP #75 — Smart-Inbox-Gruppenbanner

Alle Belege stammen ausschließlich aus dem Worktree. Ich habe die zitierten Stellen selbst gelesen; wo der Kickoff eine Zeile nennt, habe ich sie gegen den Code verifiziert.

---

# [KRITISCH] — Muss ins Briefing

## K1 · Selektor-Falle in der Wiederanzeigen-Liste (Frage 1)

**Befund:** Der heutige Banner-Code baut `data-group-key="${escapeHTML(groupKey)}"` in das innerHTML-Template (`app.js:12629–12630`) und holt die Buttons danach **nur** über statische Klassen-Selektoren zurück (`banner.querySelector(".btn-banner-ignore-group")`, `app.js:12634/12643`). Das ist heute ungefährlich — `escapeHTML` schützt die **Anzeige**, und der Key wird **nicht** in einen Selektor-String eingesetzt.

Die geplante Wiederanzeigen-Liste („Ausgeblendete Vorschläge (n) – wieder anzeigen“, einzeln + alle) braucht aber zwingend **pro-Eintrag-Handles**. Genau dort lauert die Falle:

```js
// GEFAHR — groupKey = `Show "Special" 'x' <&>`
banner.querySelector(`[data-group-key="${groupKey}"]`)
```

Bei `"` im Namen wirft der Browser einen echten `SyntaxError: '...' is not a valid selector`, der **nicht** als Exception in den `try/catch` des Handlers läuft, sondern das gesamte `updateGroupBannerUI`-Rendering abbricht. Das ist exakt der #77-Befund aus ROADMAP #80: **stille catch-Blöcke (hier `app.js:12657–12662`) verbargen genau diesen Fehler** — der `catch` fängt nur Fehler *im* Handler, nicht beim Rendern des nächsten Banner-Durchlaufs.

**Sichere Muster (Reihenfolge nach Robustheit):**
1. **Elementreferenzen beim Rendern behalten** — beim Listenaufbau pro Gruppe die Button-DOM-Knoten in eine `Map<groupKey, element>` legen; Klicks binden sich direkt an die Referenz. Kein Selektor, kein Sonderzeichen-Problem.
2. **Event-Delegation** — ein `click`-Listener auf dem Banner-Container, der über `e.target.closest('[data-group-key]')` / `getAttribute('data-group-key')` den Key **als Attributwert liest**, nie in einen Selektor einsetzt. `closest()` muss im Mock nachgerüstet werden.
3. **Numerische data-Attribute** (`data-group-index="0"`) + Index→Key-Map — sicher, aber mehr Buchhaltung über Re-Renders.
4. **`CSS.escape`** — funktioniert, ist aber fehleranfälliger als 1–3 und im Test-Mock nicht vorhanden (muss zusätzlich gemockt werden).

**Briefing-Forderung (Test):** „Es prüft, dass ein Gruppennamen mit `\"`, `'`, `<`, `&` in Anzeige, Apply, Ignorieren **und einzelnem Wiederanzeigen** funktioniert — und zwar in einer Testdatei, deren Selektor-Mock bei ungültigen Selektoren `SyntaxError` wirft (siehe K3). Zusätzlich Implementierungsregel: `updateGroupBannerUI` und die Wiederanzeigen-Liste bauen **keinen** dynamischen Selektor-String mit eingesetztem Gruppennamen; stattdessen Elementreferenzen oder Delegation über `getAttribute`."

---

## K2 · Fehlerfall-Test: `globalThis.startSeriesGroupWorkflow`-Mock greift NICHT (Frage 5)

**Befund:** Der Apply-Handler ruft `await startSeriesGroupWorkflow(groupKey, files)` über das **lokale Function-Binding** auf (`app.js:12656`), nicht über `globalThis.startSeriesGroupWorkflow`. Der Export `globalThis.startSeriesGroupWorkflow = startSeriesGroupWorkflow` (`app.js:13323`) ist nur eine **Referenzkopie zur eval-Zeit**. Ein Test, der *nach* dem `eval` `globalThis.startSeriesGroupWorkflow = () => { throw … }` setzt, **greift nicht** — der Handler ruft weiterhin die lokale Funktion.

Der reale Fehlerpfad ist `searchSeries()`, die `startSeriesGroupWorkflow` bei gesetztem `groupName` zurückgibt (`app.js:12969–12971`); `searchSeries` wirft bei HTTP-/Formatfehlern (`app.js:3107`, `app.js:3111`). Im Harness existiert `searchSeries` als in app.js definierte Funktion (wird in der Präambel `:560–581` **nicht** gestubbt) und ruft das `fetch`-Stub.

**Sauber testbar ist der Fehlerfall daher nur über eine der beiden Injektionen VOR dem `eval` (keine davon ist eine Produktivcode-Weiche):**
- **(a) realitätsnah:** `globalThis.window.fetch` bzw. `globalThis.fetch` vor dem eval auf eine Funktion setzen, die **gezielt für den Serien-Such-Endpunkt** `{ok:false, status:500}` liefert (sonst kippen die `initEventListeners`-Pfade mit). → `searchSeries` wirft, Fehler propagiert durch den `await`.
- **(b) robuster:** `globalThis.triggerQualityHintUpdates` vor dem eval auf eine werfende Funktion setzen — die Präambel bindet sie als Stub (`const triggerQualityHintUpdates = globalThis.triggerQualityHintUpdates || (() => {})`, Harness `:564`), und `startSeriesGroupWorkflow` ruft sie synchron auf (`app.js:12887`). Der Throw läuft über den `await`-Ausdruck korrekt in den `catch`.

**Verboten** (Test-Weiche): eine globale Fehlerinjektion wie `globalThis.__forceBannerError` oder ein `bannerDebugState`-Flag, das der Produktivcode liest.

**Briefing-Forderung:** „Der Fehlerfall-Test triggert den Wurf über einen werfenden `searchSeries`-Stub (fetch-Mock, Variante a) oder einen werfenden `triggerQualityHintUpdates`-Stub VOR dem eval. `globalThis.startSeriesGroupWorkflow` nach dem eval zu überschreiben ist wirkungslos und als Ansatz ausdrücklich ausgeschlossen. Der Produktivcode liest keine globalen Variablen, die nur Tests setzen."

---

## K3 · Der laxere `inbox_group`-Mock verschluckt Browser-SyntaxErrors (Frage 6c, #77-Befund)

**Befund:** Der Mock in `inbox_group.test.js` hat **keine** `validateSelector`-Prüfung (`inbox_group.test.js:349–357` nutzt nur `splitSelectorParts`/`findDescendants`). Ein ungültiger Selektor `[data-group-key="A"B"]` wird dort **nicht** geworfen, sondern liefert still falsche Treffer → Test grün, Browser rot. Der strenge Mock steht in `inbox_selection.test.js:20–58` (wirft `SyntaxError`), `:368–378` und `:492–519` (validiert Element-/Dokument-`querySelector`).

**Empfehlung:** **Neue Testdatei `inbox_group_banner.test.js` mit Kopie des strengen selection-Mocks** + funktionalem `localStorage`-Mock. Der bestehende 2221-Zeilen-Test bleibt unangetastet. Begründung: Der Umbau des bestehenden laxen Mocks auf strenges Verhalten riskiert, dass bestehende innerHTML-Templates, die bisher still durchliefen, plötzlich werfen (Sub-Regression in 2221 Zeilen). Die Codeduplikation (~500 Zeilen Mock) ist der etablierte Zustand — `inbox_group` und `inbox_selection` teilen bereits ~90 % Mock-Code und pflegen ihn trotzdem doppelt.

**Briefing-Forderung:** „Neue Banner-/Persistenz-Tests liegen in einer eigenen Datei mit dem strengen Selektor-Mock aus `inbox_selection.test.js`. Der bestehende `inbox_group`-Mock wird nicht umgebaut. Jeder neue Test, der eine Gruppe mit `\"`/`'` im Namen rendert, MUSS im strengen Mock laufen, damit ein Browser-`SyntaxError` nicht stumm untergeht."

---

## K4 · Fehlerfall-Reihenfolge: Rücknahme + Inline-Meldung über State-Flag (Frage 3)

**Befund:** Heute: `add` (12653) → `render` (12654) → `await` (12656) → `catch` reaktiviert nur den Button (12657–12662). Wegen des Re-Renders in 12654 ist der referenzierte `btn` ein **abgehängter Knoten** — das Reaktivieren verpufft im Browser, und das Banner zeigt nach dem Fehler bereits den nächsten Kandidaten (B3-Nuance bestätigt).

**Empfohlene Reihenfolge** (Option B, behält das sofortige visuelle Feedback):
```
btn.disabled = true; "wird gestartet…"
try {
    appliedInboxGroups.add(groupKey);
    renderSmartInboxList(...);              // sofortiges Pseudo-Entry-Feedback
    await startSeriesGroupWorkflow(groupKey, files);
} catch (err) {
    appliedInboxGroups.delete(groupKey);    // ← fehlt heute
    console.error(...);                      // ← fehlt heute
    renderSmartInboxList(...);               // Banner/Liste auf korrekten Stand
    setBannerError(groupKey, message);       // ← Meldung NACH dem letzten Render
}
```
Option A (`add → await → render bei Erfolg`) wäre einfacher, aber dann sieht der Nutzer während des (potenziell langsamen) `searchSeries`-API-Calls kein Feedback und der bestehende „sofort gruppiert"-Effekt ginge verloren. Ich empfehle B.

**Wo die Inline-Meldung herkommen MUSS:** `updateGroupBannerUI` überschreibt das Banner vollständig per `innerHTML = …` (`app.js:12623`). Jede Meldung, die *vor* dem letzten `renderSmartInboxList` ins DOM geschrieben wird, wird überschrieben. Daher **entweder** ein Modul-State-Flag (`bannerErrorMessage`), das `updateGroupBannerUI` beim Rendern ins Template einfügt (Meldung überlebt jedes Re-Render, wird beim nächsten erfolgreichen Render/Ignorieren explizit gelöscht), **oder** die Meldung wird in ein Element geschrieben, das `updateGroupBannerUI` NICHT per innerHTML ersetzt (außerhalb des ersetzten Containers). Das State-Flag ist testbarer und eindeutiger — ich empfehle es.

**Race-Fälle:**
- **Doppelklick Apply:** Der initiale `btn.disabled`-Guard (`12645/12648`) schützt nur den *ersten* Button. Nach dem Re-Render (12654) ist der abgehängte Button irrelevant; ein **neu gerenderter** Button für den nächsten Kandidaten ist NICHT disabled. Ein Klick darauf startet einen **zweiten Workflow parallel** → `startSeriesGroupWorkflow` überschreibt globale Zustände (`activeSeriesGroupFiles`, `currentProject`, `:12792–12799`). **Forderung:** während eines laufenden Gruppen-Starts alle weiteren Banner-Apply-Klicks blockieren (ganzes Banner disabled oder `groupWorkflowRunning`-Flag).
- **Fehler bei Gruppe 2 von 3:** Nach `delete` + Render zeigt das Banner wieder **Gruppe 1** (erste nicht-angewandte, nicht-ignorierte). Korrekt, aber im Briefing als erwartetes Verhalten dokumentieren.
- **Apply während ein anderes Ignorieren rendert:** Beide Pfade rufen `renderSmartInboxList`; ohne zentrale Sperre kann das State-Flag verloren gehen → die Sperre aus dem Doppelklick-Punkt deckt das mit ab.

**Briefing-Forderung:** „Im Fehlerfall: `appliedInboxGroups.delete(groupKey)`, `console.error` und Re-Render, danach Inline-Meldung über ein State-Flag, das `updateGroupBannerUI` rendert. Ein laufender Gruppen-Start blockiert weitere Apply-Klicks bannerweit. Test: ‚es prüft, dass nach einem fehlschlagenden Start die Gruppe wieder als offener Vorschlag erscheint (nicht mehr als angewendet), eine Inline-Meldung im Banner steht und `console.error` aufgerufen wurde.'"

---

## K5 · localStorage: try/catch auf allen Zugriffspfaden + funktionaler Persistenz-Mock (Fragen 2a/c, 6a/b)

**Befund:** `localStorage` kann im Privacy-/Inkognito-Modus bei `getItem`/`setItem` **werfen**. Der bestehende `sessionStorage`-Code hat deshalb `try/catch` (`app.js:12601–12605`, `12635–12639`) — aber mit **leerem catch** (`catch (e) {}`), also stillem Scheitern. Der neue localStorage-Code MUSS drei Pfade absichern:
1. **Lesen** (Ist-Gruppe-ignoriert, Zähler „Ausgeblendete (n)") — bei Wurf Default `false`/`0` annehmen, Rendern darf nicht crashen.
2. **Schreiben** (Ignorieren) — bei Wurf den Ignore-Zustand **trotzdem für die Sitzung** in einem In-Memory-`Set` festhalten, sonst verschwindet der Button nicht und der Nutzer klickt endlos.
3. **Entfernen** (`removeItem` einzeln + alle) — bei Wurf idempotent ignorieren, aber In-Memory-`Set` konsistent nachführen.

**UX-Fallback:** Bei verweigertem Speicher gilt Ignorieren nur bis zum Reload (in-memory), das ist akzeptabel und dokumentierbar. **Wichtig:** Der neue Code darf nicht in den alten „leerer catch"-Stil verfallen — mindestens `console.warn` bei Speicherfehler, damit es nicht erneut ein stilles Scheitern gibt (gleiche Lektion wie #77/#80).

**Test-Mock:** Der Bestands-`localStorage`-Mock ist in beiden Dateien No-op (`inbox_group.test.js:452–456`, `inbox_selection.test.js:473–477`). Für den Persistenz-AK muss ein **funktionales** Mock her, dessen `store`-Objekt **außerhalb des evalten Codes** liegt (im Test-Modul-Scope, wie `sessionStore` in `:13`) und den frischen `eval`-Durchlauf übersteht. **Fallstrick:** `setupTestEnvironment` leert `mockSessionStorage` bei jedem Aufruf (`:375`). Der localStorage-Store darf **nicht** analog bei jedem Aufruf geleert werden, sonst bricht der Persistenz-Test (zwei `setupTestEnvironment`-Aufrufe = zwei evals). Der Store muss separat, explizit im Persistenz-Test gemanagt werden.

**Risiko bei Umstellung auf funktional:** Bestands-Codes, die im eval-Pfad `localStorage` lesen, sind `app_theme` (`:459`), `expanded_*` (`:2043`/`:2063`) und `conversionSettings` (`:10468`). Ein initial leerer funktionaler Mock mit `getItem → null` für unbekannte Keys ist für diese Stellen unschädlich → **geringes Kipp-Risiko**, sofern der Mock für unbekannte Keys `null` liefert und nicht wirft.

**Briefing-Forderung:** „Alle localStorage-Zugriffe (getItem/setItem/removeItem) in try/catch; bei Speicherfehler In-Memory-Fallback + `console.warn` (kein leerer catch). Persistenz-Test mit funktionalem localStorage-Mock, dessen Store außerhalb des evals liegt und zwischen zwei eval-Durchläufen überlebt (nicht auto-clear in `setupTestEnvironment`)."

---

## K6 · Zähler & „Alle wieder anzeigen" nur über die aktuell erkannten Gruppen (Frage 2b)

**Befund:** ADR 3 verlangt: Zähler/Rückweg berücksichtigen **nur aktuell erkannte Gruppen**; verwaiste Schlüssel stören nicht. Die fehlerresistente Logik ist zwingend: **NICHT über `Object.keys(localStorage)` iterieren**, sondern über die bereits vorhandene `validGroups`-Map (`detectInboxGroups`-Ergebnis, `app.js:12509–12539`).

- **Zähler** `n` = Anzahl der `validGroups`-Keys, deren `localStorage.getItem('smart-inbox-ignore-group-' + key)` `true`/gesetzt ist.
- **„Alle wieder anzeigen"** = für **jede** erkannte Gruppe `removeItem` aufrufen (idempotent, auch wenn kein Key existiert) — nicht über localStorage-Schlüssel iterieren.
- Verwaiste Keys (Gruppe wird nicht mehr erkannt) bleiben liegen, werden nicht gezählt, nicht angezeigt, nicht entfernt. Das ist die gewollte Semantik und vermeidet jede `Object.keys(localStorage)`-Parserei (Präfix-Splitting, andere Tabs/Sitzungen).

**Kollision/Länge/Steuerzeichen (Frage 2a):** Das Key-Format `smart-inbox-ignore-group-<groupKey>` ist eine 1:1-Abbildung (groupKey wird in `detectInboxGroups` getrimmt, `:12516`, und ist pro Sitzung als Objekt-Key eindeutig) → keine echten Kollisionen. Länge/Steuerzeichen sind für localStorage-Keys praktisch unkritisch. Das **einzige** Sonderzeichen-Problem entsteht beim Einsetzen in Selektoren (K1), nicht beim Key selbst.

**Briefing-Forderung:** „Zähler und ‚Alle wieder anzeigen' arbeiten ausschließlich über `detectInboxGroups`/`validGroups`, niemals über `Object.keys(localStorage)`. Test: ‚es prüft, dass verwaiste localStorage-Schlüssel weder gezählt noch durch ‚Alle wieder anzeigen' angetastet werden, und dass der Zähler nur aktuell erkannte ignorierte Gruppen zählt.'"

---

# [WICHTIG] — Sollte ins Briefing

## W1 · Speicherformat (Frage 2d, Q1=C)

**Bewertung des Spannungsfelds:** Reiner String `'true'` deckt die heutige Boolean-Semantik ab. Ein späteres Zurückholen „wenn neue Folgen eintreffen" (Q1) bräuchte zusätzlich die Folgenzahl. Da #75 localStorage **neu einführt** und Q2=A den sessionStorage-Altbestand verwirft, existiert **kein** Migrationszwang — man kann das Format frei wählen. Deshalb kostet ein JSON-Objekt `{ "ignored": true }` heute **nichts extra** (nur Struktur, kein „mehr speichern") und vermeidet den späteren Formatbruch (beim Lesen beide Formate erkennen zu müssen). Umgekehrt: reiner `'true'`-String verbaut die Erweiterung *nicht irreversibel* (eine spätere Migration ist trivial), erfordert aber dann doch einen Lesepfad, der String und Objekt unterscheidet.

**Empfehlung:** JSON-Objekt `{"ignored": true}` jetzt einführen, beim Lesen `JSON.parse` mit try/catch + Default `{ignored:false}`. Das ist der „kostenlose" Zukunftspunkt, ohne heute Folgenzahl-Logik zu bauen. Im Briefing als explizite Format-Festlegung festschreiben (sonst entscheidet der Worker ad hoc).

## W2 · AK3-Test :838–866 wird umgestellt, nicht abgeschwächt (Frage 6d)

Der bestehende Test prüft `sessionStorage.getItem('smart-inbox-ignore-group-Show') === 'true'` (`inbox_group.test.js:864`). Nach #75 schreibt der Produktivcode kein `sessionStorage` mehr → der Test würde rot. Saubere Lösung: **ersetzen durch einen localStorage-Test mit gleichem Assertions-Niveau** („Ignorieren blendet aus") plus neue Assertions für Rückweg und Persistenz. Das ist eine **Anpassung an die geänderte Spezifikation**, keine Abschwächung. Das Briefing muss das explizit anordnen („AK3 sessionStorage-Test wird ersetzt, nicht gelöscht"), damit der Worker den Test nicht still löscht.

## W3 · Cache-Buster erzwingt KEINEN Bump — nur Konsistenz (Frage 7)

`cache_busting.test.js:13–48` prüft **nur die Übereinstimmung** zwischen `index.html`-Version und allen neun Importversionen in `app.js`. Der Test bleibt grün, auch wenn man `v=102` lässt. Er erzwingt **kein** `v=103`. Der Bump auf `app.js?v=103` + alle neun Importe `?v=103` ist trotzdem **manuell Pflicht** (Browser-Cache). Für `style.css` prüft der Test nur „nicht leerer `?v=`" (`:50–56`) — ein Bump auf `v=51` ist durch den Test **nicht** erzwungen, aber browserseitig nötig, falls `style.css` geändert wird. (Dieser Umstand ist als ROADMAP #61 bereits bekannt: „Cache-Busting-Test erzwingt keine Erhöhung bei geänderter Datei".) Briefing: Bump explizit als Pflicht aufzählen, nicht auf den Test verlassen.

## W4 · Re-Render während `await` / Listener (Frage 4)

`innerHTML`-Neuraufbau pro `renderSmartInboxList` erzeugt bei jedem Durchlauf neue Knoten; die alten Handler-Closures hängen an abgehängten Knoten. **Harmlos im Sinne von „kein Crash", aber der Reaktivierungs-Effekt im catch verpufft** (K4). Event-Listener-Leaks entstehen im Browser nicht nennenswert (abgehängte Knoten werden GC-bereinigt); **im Test-Mock** hält `elementsById`/`__children` alle erzeugten Elemente lebendig — das ist ein Test-Artefakt, kein Produktivproblem. Keine akute Gefahr, aber der Fix aus K4 eliminiert die abgehängte-Knoten-Klasse ohnehin.

## W5 · Timer-Hygiene im Banner-Pfad (Frage 7)

Das Harness stubbt `setInterval = () => 0` (`inbox_group.test.js:538`) und `setTimeout = (fn) => { fn(); return 0; }` (`:536`). Konsequenzen für den neuen Code: (1) `setTimeout` führt **sofort** aus — Zeitverhalten ist nicht testbar, nur Zustand; eine verzögert eingeblendete Inline-Meldung wird im Test sofort sichtbar (ok für Zustands-Asserts, aber kein Timing-Test). (2) Ein `setInterval` im Banner würde stumm nie laufen. Der Banner-Pfad braucht weder `setTimeout` noch `setInterval` — das Briefing sollte festhalten, dass die Inline-Meldung **ohne** Timer gerendert wird (State-Flag + synchroner Render), damit sie im Test deterministisch prüfbar ist.

## W6 · Diff-Größe / Review-Grenze

`app.js` hat 18352 Zeilen. Der Worker soll die Änderung eng auf `updateGroupBannerUI` (+ ggf. einen kleinen Helper für „ist ignoriert"/„zähle ausgeblendet") begrenzen; `renderSmartInboxList`/`detectInboxGroups` bleiben unangetastet (nur Aufruf-Erweiterung für das State-Flag-Feedback). Ein kleiner, lokaler Diff hält den Reviewer-Aufwand unter der ~120-KB-Grenze und schützt vor unbeabsichtigten Regressionen im 13000er-Block.

---

# [KOSMETISCH]

## C1 · `appliedInboxGroups`/`currentSmartInboxRawSuggestions` Deklarationskontext

`appliedInboxGroups = new Set()` (`app.js:12474`), `currentSmartInboxRawSuggestions = []` (`:12471`) sind `let`-Deklarationen. Das In-Memory-Fallback-`Set` für verweigerten Speicher (K5) sollte als eigene `let`-Variable in derselben Sektion (`:12471–12477`) liegen, nicht als globales Flag — das hält den Export-Block (`:13318–13344`) sauber auf „nur Zuweisungen, keine Lesungen".

## C2 · style.css 3866–3894 erweitern

Das bestehende Banner-CSS kennt nur `#smart-inbox-group-banner` + `.smart-inbox-group-banner-content/actions` (`style.css:3866–3894`). Die neue Liste (scrollbar/höhenbegrenzt) + Inline-Fehlerstil brauchen neue Klassen. Falls CSS geändert wird: `style.css?v=50 → v=51` (Q4=A, W3). Kein Blocker, aber ohne CSS wird es Inline-Style-Gefrickel.

## C3 · `searchSeries`-Fehlerpfad ist der einzige reale Wurf

`startSeriesGroupWorkflow` wirft selbst nicht; der einzige reale Wurf kommt aus `searchSeries` (`:3107`, `:3111`). Das sollte im Briefing als Kontext für den Fehlerfall-Test stehen (K2), damit der Worker nicht nach einer nicht-existierenden internen Wurfquelle sucht.

---

# Was die Kette NICHT testen kann (Frage 8) → Handtest-Pflichten

Die Kette (Node `eval`-Mock) kann nicht abdecken:
1. **Echter Browser-Selektorwurf** — der strenge Mock simuliert `SyntaxError`, aber echtes `querySelector`-Verhalten, `CSS.escape`, `closest()`, `dataset` sind Browser-spezifisch.
2. **Echte Storage-Verweigerung** — Privacy-/Inkognito-Modus wirft bei `getItem`/`setItem`; im Mock nur simulierbar.
3. **Echtes Persistenz-über-Reload** — der Mock simuliert nur zwei eval-Durchläufe, nicht echte Seiten-Neuladung/Mehr-Tab-Sichtbarkeit.
4. **Echtes NAS/`searchSeries`-API** — der Fehlerfall ist nur gemockt.
5. **Echtes Timing** — `setTimeout`/`setInterval` sind gestubbt.

**Handtest-Pflichten (mindestens):**
- ≥ 3 Seriengruppen, davon eine mit `"` und `'` im Namen (`Show "Special" 'Cut'`), ggf. eine mit `<`/`&`.
- Apply, Ignorieren, einzeln + alle wieder anzeigen, Persistenz über einen echten Seiten-Reload (F5).
- Fehlerfall real provozieren (NAS/Server-Fehler beim Start aus dem Banner) und prüfen: Inline-Meldung sichtbar, `console.error` in DevTools, Gruppe wieder offen, kein doppelter Gruppen-Eintrag.
- Rot-Probe ohne neue Symbole, volle Suite im Worker-Image.

---

## Kern-Empfehlung für das Briefing (komprimiert)

1. **Selektoren:** nie dynamisch bauen — Elementreferenzen oder Delegation über `getAttribute`; Test im strengen Mock mit Sonderzeichen-Namen.
2. **Fehlerfall:** `delete` + `console.error` + Re-Render + State-Flag-Meldung; bannerweite Apply-Sperre während laufendem Start.
3. **Fehlerfall-Test:** Wurf über `searchSeries`-Stub (fetch) oder `triggerQualityHintUpdates`-Stub VOR eval — **nicht** über `globalThis.startSeriesGroupWorkflow`.
4. **localStorage:** try/catch überall + In-Memory-Fallback + `console.warn`; funktionaler Persistenz-Mock ohne auto-clear.
5. **Zähler/„Alle":** nur über `validGroups`, nie `Object.keys(localStorage)`.
6. **Format:** JSON `{"ignored":true}` festlegen (Q1=C-Zukunftsfenster, kostet nichts).
7. **AK3-Test ersetzen statt löschen; `app.js?v=103` + 9 Importe + ggf. `style.css?v=51` manuell.**

Keine Server-/API-/Worker-Änderung nötig — Scope bleibt `app.js`, optional `style.css`, `index.html` (nur Cache-Buster), Frontend-Tests.
