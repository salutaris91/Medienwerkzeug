# Kickoff: ROADMAP #75 — Inbox-Gruppen: alle Vorschläge sichtbar, „Ignorieren“ umkehrbar

Datum: 2026-10-16
Status: Akt 1 abgeschlossen — wartet auf Alex (Freigabepunkt 1)
Scope dieser Datei: nur Kickoff und read-only-Prüfung gegen den Code im Worktree.
Keine Subagenten konsultiert. Kein Briefing erstellt. Keine Code-, ROADMAP-, STAND- oder VERLAUF-Änderung.

## Git-Zustand

Der Git-Zustand wurde nicht vom aktuellen Agenten ausgeführt, sondern ist die wörtliche Vormeldung aus dem Kickoff-Prompt:

```text
$ git status --short --branch
## feat/roadmap-75-inbox-gruppen...origin/main
$ git log --oneline -3
34d621e fix(inbox): keep selection limited to current selectable entries (ROADMAP #77) (#154)
5c72af2 fix(search): match spelled-out season/episode names (ROADMAP #78) (#153)
b2adc8c fix(search): match episodes by season before episode number (ROADMAP #76) (#152)
```

Damit ist der Branch bekannt und kein harter `main`-Stop aktiv. Ein Commit/PR wird hier nicht vorgeschlagen; Git-Schreibaktionen bleiben nach Alex-Go bei Claude Code.

## Alex-Vorgaben aus dem Prompt (nicht neu verhandelt)

Diese Vorgaben gelten als Rahmen für Akt 2:

1. **Scope:** ROADMAP #75 plus nur die Banner-Stelle aus ROADMAP #80.
   - Scheitert der Start aus dem Banner, muss der Fehler sichtbar gemeldet und per `console.error` protokolliert werden.
   - `appliedInboxGroups` muss im Fehlerfall zurückgenommen werden.
   - Bulk-Weg (`updateBulkActionsBarUI`) und Gruppenzeile bleiben in #80 und werden nicht angefasst.
   - #74 (Staffel-Schnellauswahl) ist nicht Teil dieser Kette, aber das Banner-Layout darf #74 nicht verbauen.

2. **Darstellung:** Der erste offene Vorschlag bleibt wie bisher prominent im Banner. Darunter ein aufklappbarer Bereich „Weitere Vorschläge (n)“ mit je „Als Serie gruppieren“ und „Ignorieren“. Die Liste ist höhenbegrenzt/scrollbar. Feinheiten klärt der grafiker in Akt 2.

3. **Speicherort „Ignorieren“:** `localStorage` statt `sessionStorage`. Zähler und Rückweg berücksichtigen nur Gruppen, die aktuell erkannt werden; verwaiste Schlüssel stören nicht.

4. **Rückweg:** „Ausgeblendete Vorschläge (n) – wieder anzeigen“, einzeln und „alle“. Der Rückweg bleibt sichtbar, auch wenn kein aktiver Vorschlag mehr übrig ist; das Banner darf dann nicht komplett verschwinden.

5. **Prüfstrategie:**
   - Gruppennamen mit `\"`, `'`, `<`, `&` müssen in Anzeige, Apply, Ignorieren und Wiederanzeigen funktionieren.
   - Keine `querySelector`-Selektoren mit eingesetztem Gruppennamen ohne `CSS.escape`; besser Elementreferenzen statt Selektoren.
   - Keine Test-Weichen im Produktivcode. Der bestehende Export-Block in `gui/static/app.js` darf um neue Funktionen ergänzt werden, aber Produktivcode darf keine globalen Variablen lesen, die nur Tests setzen.
   - Tests decken mehrere Gruppen, Ignorieren, Einzel- und Alle-Wiederanzeige, Persistenz über erneutes Rendern, Sortierung und den Fehlerfall beim Start ab.
   - Danach zusätzliche Browser-Probe, Rot-Probe ohne neue Symbole und volle Suite im Worker-Image durch Claude Code.

6. **Ablauf:** EIN Gate-A2-Lauf; eine Nachbesserung wäre Lauf 2 auf dem committeten Stand von Lauf 1. Danach Plausibilitätsprüfung, Rückkanal, Handtest, Push/PR, Merge durch Alex.

## Read-only-Prüfung der Behauptungen

### B1 — Banner nimmt nur den ersten offenen Vorschlag

**Ergebnis: bestätigt.**

`updateGroupBannerUI` in `gui/static/app.js:12594–12663` läuft über `Object.entries(validGroups)` und bricht beim ersten Kandidaten ab, der weder angewendet noch ignoriert ist:

- `gui/static/app.js:12599–12610`: Kandidatensuche mit `break`.
- `gui/static/app.js:12612–12615`: Wenn kein Kandidat übrig ist, wird das Banner ausgeblendet und geleert.

Damit ist die Beschreibung „zeigt immer nur einen Vorschlag“ korrekt.

### B2 — „Ignorieren“ schreibt nur sessionStorage, kein Rückweg

**Ergebnis: bestätigt.**

- `gui/static/app.js:12602–12604`: Liest `sessionStorage['smart-inbox-ignore-group-' + groupKey]`.
- `gui/static/app.js:12634–12641`: Klick auf „Ignorieren“ schreibt `sessionStorage['smart-inbox-ignore-group-' + groupKey] = 'true'` und rendert die Inbox neu.

Ein Suchlauf über `smart-inbox-ignore-group` in JavaScript-Dateien findet nur diese zwei Produktivstellen und eine Teststelle:

- `gui/static/app.js:12603`
- `gui/static/app.js:12637`
- `tests/frontend/inbox_group.test.js:864`

Es gibt keinen `removeItem`- oder UI-Weg, der den Schlüssel wieder entfernt.

### B3 — Apply-Markierung wird bei Fehler nicht zurückgenommen

**Ergebnis: bestätigt, mit wichtiger Nuance.**

- `gui/static/app.js:12653`: `appliedInboxGroups.add(groupKey)` vor dem Workflow.
- `gui/static/app.js:12654`: sofortiges `renderSmartInboxList(...)`.
- `gui/static/app.js:12656`: `await startSeriesGroupWorkflow(groupKey, files)`.
- `gui/static/app.js:12657–12662`: `catch` gibt nur den Knopf wieder frei.

Es gibt keine Rücknahme von `appliedInboxGroups`, keine Meldung und kein `console.error`.

Zusatzbefund: Weil `renderSmartInboxList` vor dem `await` aufgerufen wird und `updateGroupBannerUI` das Banner neu zeichnet, ist der im Handler referenzierte Button nach einem Fehler wahrscheinlich nicht mehr dasselbe sichtbare DOM-Element. Der `catch` kann also im Browser einen abgehängten Button reaktivieren, während das Banner bereits den nächsten Kandidaten zeigt oder ausgeblendet ist. Das verschärft den Bedarf aus ADR 1.

### B4 — Banner-Reihenfolge folgt `validGroups`, nicht der Sortierleiste

**Ergebnis: bestätigt.**

- `gui/static/app.js:13045`: `const validGroups = detectInboxGroups(suggestions);`
- `gui/static/app.js:13046`: `updateGroupBannerUI(validGroups);`
- `gui/static/app.js:13048–13049`: erst danach werden die Vorschläge gruppiert und über `sortInboxSuggestions` für die Liste sortiert.

`detectInboxGroups` in `gui/static/app.js:12509–12539` baut `groups` in Durchlaufreihenfolge der eingehenden `suggestions` und übernimmt daraus Gruppen mit mindestens zwei Mitgliedern in `validGroups`. Die Banner-Reihenfolge ist daher die Objekt-Reihenfolge der Erkennung, nicht die sichtbare Sortierung der Inbox-Liste.

### B5 — Frontend-Tests zum Banner existieren, aber Mocks sind unterschiedlich stark

**Ergebnis: teilweise bestätigt.**

Die genannten Dateien existieren und laden `app.js` per `readFileSync`:

- `tests/frontend/inbox_group.test.js:1–10`
- `tests/frontend/inbox_selection.test.js:1–10`

**Wichtige Unterschiede:**

1. `inbox_group.test.js` mockt `sessionStorage` funktional (`tests/frontend/inbox_group.test.js:12–19`), aber `localStorage` nur als No-op:

   - `tests/frontend/inbox_group.test.js:452–456`

   Die Banner-Tests prüfen `sessionStorage`-Ignorieren (`tests/frontend/inbox_group.test.js:838–866`). Für die neue `localStorage`-Persistenz müsste der Mock echte `getItem`/`setItem`/`removeItem`-Semantik bekommen.

2. `inbox_group.test.js` wirft bei ungültigen Selektoren nicht:

   - `tests/frontend/inbox_group.test.js:349–357` verwendet `splitSelectorParts`/`findDescendants`, aber keine Selektorvalidierung.

3. `inbox_selection.test.js` hat einen strengeren Selektor-Mock:

   - `tests/frontend/inbox_selection.test.js:20–58`: `validateSelector(sel)` wirft `SyntaxError` bei ungültigen Attributselektoren.
   - `tests/frontend/inbox_selection.test.js:368–378`: Element-`querySelector`/`querySelectorAll` validieren.
   - `tests/frontend/inbox_selection.test.js:492–519`: Dokument-`querySelector`/`querySelectorAll` validieren.

4. `inbox_selection.test.js` mockt `localStorage` ebenfalls nur als No-op:

   - `tests/frontend/inbox_selection.test.js:473–477`

**Konsequenz für Akt 2:** Neue Tests dürfen nicht blind auf dem losen `inbox_group`-Mock aufbauen, wenn sie Selektorfehler oder `localStorage`-Persistenz wirklich abdecken sollen. Entweder muss der Mock gezielt gestärkt oder die neue Testdatei mit funktionalem `localStorage`-Mock und Selektorvalidierung geschrieben werden.

### B6 — Cache-Buster steht aktuell auf `app.js?v=102`

**Ergebnis: bestätigt.**

- `gui/static/index.html:2760`: `<script type="module" src="app.js?v=102"></script>`
- `gui/static/app.js:1–9`: alle neun ES-Module-Importe tragen `?v=102`.
- `gui/static/index.html:9`: `style.css?v=50`.

`tests/frontend/cache_busting.test.js:13–48` prüft, dass die `app.js`-Version in `index.html` und alle Importversionen in `app.js` übereinstimmen. Die Kette muss also auf `app.js?v=103` und alle neun Importe auf `?v=103` springen.

`tests/frontend/cache_busting.test.js:50–56` prüft für `style.css` nur, dass ein nicht leerer `?v=`-Wert vorhanden ist. Ein Style-Bump ist durch den Test nicht erzwungen, aber browserseitig sinnvoll, falls `style.css` geändert wird.

### B7 — `localStorage` ist bereits ein vorhandenes Muster

**Ergebnis: bestätigt.**

Beispiele:

- `gui/static/app.js:459`: `localStorage.getItem("app_theme")`
- `gui/static/app.js:2043`: `localStorage.getItem(`expanded_${secId}`)`
- `gui/static/app.js:2063`: `localStorage.setItem(`expanded_${secId}`, "true")`
- `gui/static/app.js:10468`: `localStorage.setItem("conversionSettings", JSON.stringify(settings))`

Damit ist `localStorage` kein neues Architekturprinzip. Die neue Ignorier-Liste sollte aber robust mit `try/catch` arbeiten, weil Browserkontexte Speicher verweigern können; das bestehende Ignorieren nutzt für `sessionStorage` bereits `try/catch` (`gui/static/app.js:12601–12605`, `gui/static/app.js:12635–12639`).

## O3 — Gibt es eine allgemeine Toast-/Meldungsfunktion?

**Ergebnis: keine allgemeine Toast-Funktion gefunden.**

Die im Prompt genannte spezielle Funktion `showFskBatchError` existiert:

- `gui/static/app.js:18056–18062`

Sie schreibt aber nur in ein bestimmtes Element `#fsk-batch-error-inline` und ist nicht allgemein für Inbox-Banner nutzbar.

Ein Suchlauf nach `toast`, `notification`, `status-message`, `error-message` und `show...Error` findet keine passende allgemeine UI-Meldungsfunktion für diesen Pfad. Es gibt viele `alert(...)`-Aufrufe im Produktivcode, aber das ist ein blockierendes Browser-Dialogmuster, kein Toast.

**Vom aktuellen Agenten empfohlene Form:** Inline-Meldung im Banner selbst, plus `console.error`. Das bleibt nah am Auslöser, ohne neue Bibliothek und ohne `alert`-Blockade.

## Was der Befund für Akt 2 bedeutet

1. **Banner-Logik muss von „erster Kandidat“ auf „alle offenen Kandidaten + ausgeblendete Kandidaten“ umgebaut werden.**
   Die aktuelle Funktion ist klein und zentral; die Änderung betrifft primär `updateGroupBannerUI` und eventuell die Renderreihenfolge in `renderSmartInboxList`.

2. **Ignorier-Zustand braucht ein funktionales `localStorage`-Mock in Tests.**
   Der bestehende No-op-Mock in `inbox_group.test.js` würde Persistenz nicht wirklich prüfen.

3. **Selektorsicherheit ist real gefährdet, wenn neue Listen per `data-group-key` selektiert werden.**
   Der bestehende Banner-Code verwendet `banner.querySelector(".btn-banner-ignore-group")` nur statisch. Wenn neue Listen für mehrere Gruppen oder „wieder anzeigen“ mit `querySelector('[data-group-key="${groupKey}"]')` arbeiten, würde ein Name mit `"` oder `'` im Browser `SyntaxError` werfen. Besser: Elementreferenzen beim Rendern behalten oder `CSS.escape` verwenden.

4. **Fehlerfall muss nicht nur den Button reaktivieren, sondern `appliedInboxGroups.delete(groupKey)` und erneutes Rendern/Meldung enthalten.**
   Der aktuelle `catch` ist nachweislich zu schwach und durch das frühe Re-Render zusätzlich unzuverlässig.

5. **Cache-Buster ist Pflicht für `app.js`:** `v=102` → `v=103` in `index.html` und allen neun Importen in `app.js`.
   Falls `style.css` geändert wird, sollte `style.css?v=50` → `v=51` erhöht werden, auch wenn der Test das nicht hart verlangt.

6. **Keine Server-, API- oder Worker-Änderung nötig.**
   Der Befund bleibt in `gui/static/app.js`, optional `gui/static/style.css`, `gui/static/index.html` nur Cache-Buster und Frontend-Tests.

## Offene Scope-Fragen an Alex

Diese Fragen sind echte Entscheidungen für den Scope bzw. die Freigabe des späteren Briefings. Die ADR 1–6 werden nicht neu verhandelt.

### Q1 — Soll ein ignorierter Vorschlag automatisch wiederkommen, wenn neue Folgen eintreffen?

**Hintergrund:** Alex’ Anlass ist, eine Serie „erstmal raushaben“ zu wollen, solange noch nicht alle Folgen da sind. ADR 4 gibt bereits einen manuellen Rückweg. O1 fragt, ob zusätzlich automatisch zurückgeholt werden soll, wenn z. B. eine neue Folge derselben Gruppe erkannt wird.

**Empfehlung:** Nein für diese Kette. Nur manuelles Wiederanzeigen. Optional als ROADMAP-Follow-up notieren.

**Kurzbegründung:** Der Kernnutzen ist der fehlende Rückweg. Eine automatische Rückholung erfordert zusätzliches Zustandsmodell (z. B. Folgenzahl beim Ignorieren, Vergleich bei jedem Rendern, Umgang mit entfernten/unvollständigen Folgen) und erzeugt neue Edge-Cases.

**Trade-off/Risiko:** Manuell ist einfacher und sicherer, aber weniger bequem für den Fall „ich habe ignoriert, weil Folge 3 fehlte, jetzt ist Folge 3 da“.

**Entscheidungspunkt:**
- A: Nur manuelles Wiederanzeigen (empfohlen).
- B: Automatisch zurückholen, wenn neue Folgen erkannt werden.
- C: Nur manuell jetzt, automatisches Zurückholen als separater ROADMAP-Punkt danach.

### Q2 — Alte `sessionStorage`-Schlüssel `smart-inbox-ignore-group-*` ignorieren oder übernehmen?

**Hintergrund:** ADR 3 entscheidet `localStorage`. Bestehende Ignorier-Markierungen liegen aktuell in `sessionStorage`.

**Empfehlung:** Ignorieren, kein Migrationscode.

**Kurzbegründung:** `sessionStorage` ist tab-flüchtig und war nie als dauerhafte Benutzereinstellung gedacht. Migrationscode wäre zusätzlicher Code mit eigener Fehlerfläche.

**Trade-off/Risiko:** Wenn Alex in einem offenen Tab gerade etwas ignoriert hat und dann neu lädt, erscheint dieser Vorschlag wieder. Das ist akzeptabel, weil der neue Rückweg sofort sichtbar ist.

**Entscheidungspunkt:**
- A: Alte Schlüssel ignorieren (empfohlen).
- B: Beim ersten Rendern einmalig aus `sessionStorage` nach `localStorage` übernehmen.

### Q3 — Fehler beim Start aus dem Banner als Inline-Meldung im Banner anzeigen?

**Hintergrund:** ADR 1 verlangt sichtbare Fehlermeldung und `console.error`. O3 fragt nach der vorhandenen Form. Eine allgemeine Toast-Funktion existiert nicht.

**Empfehlung:** Inline-Meldung im Banner selbst, plus `console.error`. Kein `alert`, keine neue Bibliothek.

**Kurzbegründung:** Die Meldung gehört zum Banner und zum ausgelösten Button. Inline hält den Kontext sichtbar und blockiert die Oberfläche nicht.

**Trade-off/Risiko:** Inline braucht etwas mehr Markup/CSS als ein `alert`; dafür ist es ruhiger, testbarer und näher am Fehlerort.

**Entscheidungspunkt:**
- A: Inline-Meldung im Banner (empfohlen).
- B: `alert` wie an vielen anderen Stellen im Projekt.
- C: Andere vorhandene Meldeform nennen.

### Q4 — Darf `gui/static/style.css` geändert und der Style-Cache-Buster erhöht werden?

**Hintergrund:** Die geplante Liste „Weitere Vorschläge (n)“ mit Höhenbegrenzung/Scroll und Inline-Fehler braucht wahrscheinlich CSS. Der bisher geplante Worker-Auftrag lässt `style.css` nur „ggf.“ zu.

**Empfehlung:** Ja, aber eng begrenzt: nur Banner-Liste, Scroll/Max-Höhe, Aufklapp-Optik und Inline-Fehlerstil. Wenn `style.css` tatsächlich geändert wird, zusätzlich `style.css?v=50` → `v=51`.

**Kurzbegründung:** Ohne CSS wäre die Liste vermutlich nur mit Inline-Styles baubar, was schlechter wartbar ist. Ein gezielter Style-Bump verhindert veraltete Caches.

**Trade-off/Risiko:** Größerer Diff und mehr UI-Feinschliff; dafür sauberere Umsetzung.

**Entscheidungspunkt:**
- A: `style.css` erlauben und bei Änderung auf `v=51` bumpen (empfohlen).
- B: Nur `app.js` + `index.html` erlauben, alle Optik per Inline-Styles im JS.
- C: `style.css` erlauben, aber Cache-Buster nicht ändern.

## Keine weiteren echten Scope-Fragen

Keine zusätzlichen Fragen, die Alex vor Akt 2 beantworten muss. Designfeinheiten (Wortlaut, Anordnung, Aufklapp-Zustand, genaue Liste) können in Akt 2 mit dem grafiker und produktberater vorbereitet und dann im Briefing zur Abnahme vorgelegt werden.

## Risiken und Hinweise für Akt 2

- **Browser-Selektorrisiko:** Neue Tests müssen Selektorfehler sichtbar machen. Der `inbox_group`-Mock wirft aktuell nicht; der `inbox_selection`-Mock tut es.
- **Persistenztest-Lücke:** Der bestehende `localStorage`-Mock ist in beiden Testdateien No-op. Für ADR 3 muss ein funktionales Mock her.
- **Zustandsrücknahme:** `appliedInboxGroups` darf bei Fehlstart zurückgenommen werden; der aktuelle Code lässt die Markierung stehen.
- **Banner-Verschwinden:** Der Rückweg muss sichtbar bleiben, auch wenn keine offenen Vorschläge mehr da sind. Wenn aber keine aktuell erkannte Gruppe existiert, darf das Banner leer/ausgeblendet sein.
- **#74-Kompatibilität:** Das Banner darf keinen Gruppenkopf verdecken oder Selektoren/IDs verbauen, die Staffel-Schnellauswahl in #74 blockieren.
- **Lizenz-/Referenzrisiko:** Keine neuen Third-Party-Assets oder Bibliotheken vorgesehen. Falls Akt 2 Icons oder CSS-Muster aus Referenzen übernimmt, müssen Quelle und Lizenz dokumentiert werden.
- **Stichproben-pflichtige Themen:** Keine Geld-, Rechts-, Registrierungs- oder Kaufentscheidung. Relevant sind nur UI-Logik und lokaler Browser-Speicher.

## Geplanter Akt-2-Rahmen nach Alex-Antwort

1. Subagenten-Konsultation: produktberater, grafiker, advocatus; ggf. plan-reviewer erst nach technischem Briefing.
2. Technisches Briefing in `docs/sessions/2026-10-16-roadmap75-inbox-vorschlaege/briefing.md` nach Inline-Vorlage.
3. Nicht-technische Zusammenfassung in `docs/sessions/2026-10-16-roadmap75-inbox-vorschlaege/ALEX_ZUSAMMENFASSUNG.md`.
4. Worker-Auftrag mit engem Dateiscope:
   - `gui/static/app.js`
   - `gui/static/index.html` nur Cache-Buster
   - `gui/static/style.css` nur wenn Q4 A gewählt wird
   - `tests/frontend/inbox_group.test.js` und/oder neue Frontend-Testdatei unter `tests/frontend/`
5. `test_cmd` wie in `docs/sessions/2026-10-12-inbox-ordnerfolgen/briefing.md` Abschnitt 11:

```bash
python3 -m pip install -q --user --break-system-packages -r requirements.txt pytest && python3 -m pytest -q -p no:cacheprovider --deselect tests/test_utils.py::TestMediawerkzeugLogic::test_conversion_estimation_test_encode && npm run test:frontend
```

6. Handtest-Liste mit mindestens drei Seriengruppen, davon eine mit `\"` bzw. `'` im Namen.

## Stop

Akt 1 endet hier. Freigabepunkt 1 ist erreicht: Alex muss die offenen Scope-Fragen Q1–Q4 beantworten oder die Empfehlungen ausdrücklich freigeben. Erst danach beginnt Akt 2 mit Subagenten und Briefing.
