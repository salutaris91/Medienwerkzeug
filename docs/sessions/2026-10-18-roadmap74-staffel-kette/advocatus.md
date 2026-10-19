<!-- Mechanisch aus `opencode export ses_eafa1bf4fffeI463PwzJNwVKuZ` extrahiert (Claude Code, 2026-10-18): alle Assistant-Textteile in Reihenfolge, ungekürzt, unverändert (nur Trailing Whitespace entfernt). Rohdatei: Kit-Worktree clever-mclaren-94c19f scripts/gate-a2/logs/2026-10-18-roadmap74-kette/akt2/export-advocatus-eafa1bf4fffe.json -->

## Risikoprüfung „advocatus" — Feature-Kette #74/#80-Rest/#83, Akt 2

Verifizierter Code-Stand stimmt mit der Vorgabe überein (alle Zeilenangaben geprüft). Hier die Funde, sortiert nach deinen 9 Fragen.

---

### 1. S3-Sperre an vier Startstellen

**[kritisch] F1.1 — `btn.disabled` ist als Sperre wertlos, weil der 6-s-Takt die Knöpfe neu baut.**
`renderSmartInboxList` :13265 (`smartInboxList.innerHTML = ""`) hängt alle Gruppenzeilen-Knöpfe ab und baut sie neu. Der Gruppenzeilen-Handler setzt :13362 `btn.disabled = true`, aber spätestens nach 6 s existiert ein frischer, aktiver Knopf. Da der Handler `groupWorkflowRunning` NICHT kennt (:13357–13375), startet ein Klick auf den neuen Knopf einen zweiten `startSeriesGroupWorkflow` → B5 (Überschreiben von `activeSeriesGroupFiles/currentProject/projectFiles` :13007–13014). **Die einzige robuste Sperre ist der Modulzustand `groupWorkflowRunning` — `btn.disabled` ist nur Kosmetik, kein Schutz.** Gleiches gilt für die Bulk-Leiste: deren Button wird bei jedem `updateBulkActionsBarUI` neu gebaut (:12909 `innerHTML`), und `updateBulkActionsBarUI` wird beim Staffel-Start NICHT erneut aufgerufen → der Bulk-Knopf bleibt klickbar.

**[kritisch] F1.2 — Prüfen+Setzen muss ein atomarer Synchronblock sein.**
Der Handler ist async. Nur wenn zwischen `if (groupWorkflowRunning) return;` und `groupWorkflowRunning = true;` kein `await` steht, ist die Sperre wirksam. Der Banner-Handler :12835→:12838 ist korrekt (synchron, kein await dazwischen). Der Briefing-Worker muss das für Gruppenzeile und Bulk exakt kopieren. Vor dem Disable-Text-Tausch prüfen, sonst bleibt ein Button auf „wird gestartet…" hängen.

**[wichtig] F1.3 — Abgewiesener Zweitstart: still, konsistent mit Banner, aber als AK festhalten.**
Banner :12835 returned still (kein Feedback). Für Gruppenzeile/Bulk identisch still-returnen ist konsistent und verhindert Meldungs-Spam. ABER: Es muss als AK fixiert werden („zweiter Start während Lauf → stiller no-op, kein Text-/Disabled-Wechsel"), sonst rätselt der Worker oder erfindet eine Meldung, die mit P3 kollidiert.

**[wichtig] F1.4 — Deadlock, wenn der Timeout-Callback selbst wirft.**
`groupWorkflowRunning = false` liegt im `finally` der Aufrufer (Banner :12855, künftig auch Gruppenzeile/Bulk). Wird `searchSeries` nie aufgelöst (genau #83) und wirft der Timeout-Callback (z. B. beim Rendern der Frist-Meldung im Callback), läuft die Exception NICHT ins `try/catch` von `searchSeries` (setTimeout-Callbacks sind asynchron, außerhalb des try) → kein resolve, kein reject → `finally` wird nie erreicht → `groupWorkflowRunning` bleibt dauerhaft `true`. **Gegenmaßnahme:** Timeout-Callback macht NUR `didTimeout = true;` + `controller.abort()`. Die Frist-Meldung wird im `catch` von `searchSeries` gerendert (dort ist sie im try/catch-Kontext). Das deckt sich mit S4, muss aber explizit als „Callback rendert nichts, darf nicht werfen" ins Briefing.

---

### 2. finally-Freigabe

**[wichtig] F2.1 — Vier Stellen sind NICHT konsistent: nur der Banner hat `finally`.**
Banner :12843–12856 hat try/catch/finally. Gruppenzeile :13366–13374 und Bulk :12937–12997 haben nur try/catch — **kein `finally`**. Ohne nachgerüstetes `finally` bleibt `groupWorkflowRunning` bei jedem Fehlerpfad (auch synchronem Wurf) `true` → dauerhafte Totalsperre. Der Briefing muss für Gruppenzeile und Bulk ein `finally { groupWorkflowRunning = false; ... }` vorschreiben.

**[wichtig] F2.2 — `startSeriesGroupWorkflow` ist NICHT `async` deklariert → synchroner Wurf statt rejected Promise.**
:13005 `function startSeriesGroupWorkflow(...)` ist eine normale Funktion. `modeCard.click()` :13171 (oder jeder andere Wurf im Top, z. B. `getCatIdBySub`-Seiteneffekte) wirft **synchron**. Das wird nur gefangen, weil alle drei Aufrufer den Aufruf innerhalb ihres `try` awaiten (Banner :12848, Gruppenzeile :13368, Bulk :12991). Solange der Aufruf im try steht, fängt ein `try/catch` BEIDE Fehlerarten (synchroner Wurf + async rejection vom await). Das ist aktuell erfüllt — muss der Worker aber nicht kaputtmachen (z. B. darf er den Aufruf nicht aus dem try herausziehen). **Kein Änderungsbedarf, aber als Invariante ins Briefing.**

**[kosmetisch] F2.3 — `await` ist überall vorhanden.**
Alle drei Handler awaiten bereits. Kein Handlungsbedarf, nur Bestätigung.

---

### 3. R2 Ablösung vs. Frist

**[kritisch] F3.1 — „lokaler AbortController" darf die Ablösungs-Abort-Logik :3085–3087 nicht zerstören.**
Heute bricht Suche B die Suche A über den **globalen** `currentSearchSeriesController` ab. Wird der Controller vollständig lokal (S4 wörtlich genommen), weiß B nicht mehr, wie es A abbricht. Folge: A läuft weiter, A's fetch löst auf, Stale-Guard :3114 (`query !== lastSearchSeriesQuery`) ist bei identischem Query-Text `false` → A überschreibt B's Ergebnisse. **Gegenmaßnahme:** Der letzte aktive Controller muss weiterhin global auffindbar bleiben (z. B. `currentSearchSeriesController` als Ablöse-Registry behalten, lokaler Controller zusätzlich für den Timeout). Briefing muss „lokal" präzisieren: *pro Aufruf lokal, aber der aktive Controller bleibt global referenzierbar*.

**[kritisch] F3.2 — Timeout-Callback darf NIE `currentSearchSeriesController.abort()` rufen, sonst bricht er B ab.**
Edge „Timeout A feuert nach B's Start": ruft der Callback den globalen Controller auf, abrichtet er B statt A. Der Callback muss **seinen eigenen, per Closure referenzierten Controller A** abbrechen. Das ist die eigentliche Bedeutung von „lokaler AbortController" — im Briefing als genau diesen Punkt verankern.

**[wichtig] F3.3 — `lastSearchSeriesQuery` unterscheidet identische Query-Texte nicht.**
Manuelle Suche mit gleichem Text zweimal (oder zwei Staffel-Knöpfe, die zufällig denselben `group_key`-String erzeugen): Stale-Guard :3114/:3211 greift nicht, weil beide `query === lastSearchSeriesQuery` sind. A's später Timeout/Ergebnis überschreibt B. **Gegenmaßnahme:** monotonen Request-Zähler einführen (`let searchSeriesRequestSeq = 0;`, lokal `const seq = ++searchSeriesRequestSeq;`, Guard `seq !== searchSeriesRequestSeq`) statt/ergänzend zum Query-String-Vergleich. Der Guard muss an beiden Stellen (:3114 nach fetch, :3211 im catch) umgestellt werden.

**[wichtig] F3.4 — Frist-Meldung braucht den Stale-Guard, nicht nur `didTimeout`.**
Edge „Timeout A feuert genau bevor B startet": A's catch rendert die Frist-Meldung; startet B dazwischen, setzt B :3091 den Spinner, A's catch überschreibt ihn. Schutz nur über `query === lastSearchSeriesQuery` — und das scheitert bei identischem Query (→ F3.3). Bedingung im catch: `if (didTimeout && query === lastSearchSeriesQuery)` (bzw. `seq === searchSeriesRequestSeq`). Im Briefing als exakte Bedingung formulieren.

---

### 4. R1 Timer-Harness

**[kritisch] F4.1 — Sofort-Stub lässt den 30-s-Timeout in jedem searchSeries-Durchlauf feuern.**
Alle drei Harnesses: `setTimeout = (fn) => { fn(); return 0; }` (inbox_group :536, banner :644, selection lt. Vorgabe :557). Ein `setTimeout(…, 30000)` in `searchSeries` würde SOFORT `didTimeout = true` + abort setzen → normaler Suchpfad tot in Tests wie inbox_group :1713/:1826/:1839/:2163/:2198, Banner-AK9, Selection-AK5/AK6/AK9. Gegenmaßnahme (Queue) ist korrekt geplant.

**[wichtig] F4.2 — Queue-Replace muss nach Delay unterscheiden, sonst bricht er E2.**
Sauberste, etappen-konfliktfreie Lösung: Timer mit kleinem Delay (die bestehenden `scrollIntoView`-Timer :3194/:3201 mit 200 ms) weiterhin **sofort** ausführen; nur Timer mit dem Frist-Delay (benannte Konstante) in die steuerbare Queue legen. Dann bleiben E2-Fehlerpfad-Tests (fetch-Fehler) grün, und nur E3-Timeout-Tests lösen den 30-s-Timer gezielt aus. Ein globaler „nichts feuert mehr automatisch"-Replace würde E2-Tests und ggf. `scrollIntoView`-abhängige Tests still brechen.

**[wichtig] F4.3 — Rot-Probe-Pflicht konkret machen.**
Der Briefing-Worker muss (a) neue Timeout-Tests gegen den Vor-Etappen-Stand **rot** laufen lassen (ohne Timeout-Code existiert kein Timeout-Zweig → Test schlägt fehl), und (b) den Bestand (die drei Dateien) mit dem neuen Queue-Harness **ohne Abschwächung** grün halten. `queueMicrotask` :12972 ist NICHT betroffen (nativ, kein setTimeout) — R5: nicht anfassen.

---

### 5. Selektor-Strenge B11a

**[wichtig] F5.1 — Der bestehende Gruppenzeilen-Handler bindet bereits per Closure, kein data-Season-String im Selektor.**
:13357 `headerDiv.querySelector(".btn-select-group")` + `item.group_key` aus der Closure. Strukturell erfüllt B11a also schon. Aber: `item.group_key` wird zusätzlich in `data-group-key="${escapeHTML(item.group_key)}"` :13301/:13272 gerendert. Der Worker darf im neuen Staffel-Knopf KEINEN Selektor `[data-group-key="…"]` mit dem rohen `group_key` bauen — nur Klassenselektor + Closure.

**[wichtig] F5.2 — Der Pflicht-Test gehört in die Banner-Datei (strenger Mock), nicht in inbox_group.test.js.**
`inbox_group.test.js` `matchesSelector` :21–62 wirft bei ungültigen Selektoren NICHT (gibt `false` zurück) → der Test „group_key mit `"`, `'`, `<`, `&` wirft nicht" wäre dort wertlos (immer grün). Strenger Mock mit `validateSelector` existiert in `inbox_group_banner.test.js` :55–93 und `inbox_selection.test.js` :20–58. AK8 :1051–1095 ist das Vorbild (Sonderzeichen im Banner). **Empfehlung:** Staffel-Knopf-Sonderzeichen-Test in `inbox_group_banner.test.js` ergänzen (Mock + `renderSmartInboxList`-Export vorhanden) — ODER neue Datei `inbox_group_staffel.test.js` mit kopiertem strengem Mock, falls E1 viele Staffel-Knopf-Tests bringt (S3, Staffel-Filterung). Letztere vermeidet Bloat; Entscheidung ins Briefing.

**[wichtig] F5.3 — Für S1 fehlt die Staffel-Datenstruktur im Pseudo-Entry.**
Der Pseudo-Entry :12572–12583 hat nur flache, sortierte `items` — **kein** `seasons`-Feld. Ein Staffel-Knopf, der „genau die Staffel-Folgen" übergeben soll, braucht die Staffel-Zuordnung. E1 muss die Struktur um Staffel-Gruppierung erweitern (z. B. `seasons: {1:[…], 2:[…]}`), und die bestehenden Fixtures sind Einzelstaffel (`makeThreeGroupsSuggestions` :741–748). Für S1-Tests braucht der Worker eine **Mehrstaffel-Fixture** — existiert nicht, muss neu. Das ist ein echtes E1-Arbeitspaket, kein reiner Umbau.

---

### 6. E2-Modulzustand

**[wichtig] F6.1 — Gruppenzeilen-Fehler-Map: Schlüssel `group_key` kollidiert Alle- vs. Staffel-Fehler — semantisch ok, aber dokumentieren.**
Pro Gruppe ein Eintrag: Staffel-Fehler überschreibt Alle-Fehler derselben Gruppe. Da in der Gruppenzeile nur ein Fehlerbereich pro Gruppe existiert, ist das korrekt. Der Banner (`bannerApplyErrors`) ist getrennt und darf NICHT mit der neuen Map verschmelzen. Kein Blocker, aber als AK festhalten.

**[wichtig] F6.2 — Leeren beim „nächsten erfolgreichen Start" muss PRO `group_key` sein, sonst Leck.**
Analog `bannerApplyErrors.delete(groupKey)` :12844 beim neuen Banner-Apply. Die neue Map pro Gruppe beim nächsten erfolgreichen Staffel-Start dieser Gruppe löschen. Zusätzlich beim Löschen der Gruppe aus `appliedInboxGroups` (Rücknahme :12850) den zugehörigen Map-Eintrag entfernen — sonst wächst die Map über lange Sitzungen mit vielen Staffeln (unsichtbares Leck). P3 sagt „Leeren beim nächsten erfolgreichen Start" — im Briefing auf „pro Gruppe" präzisieren.

**[wichtig] F6.3 — Bulk-Fehlermeldung als Einzelvariable: 6-s-/Neubau-Verhalten klären.**
Die Bulk-Leiste wird bei jedem `updateBulkActionsBarUI` via `innerHTML` :12909 komplett neu gebaut — eine DOM-gerenderte Meldung verschwindet beim nächsten Aufruf automatisch. Damit die Meldung den 6-s-Neuaufbau überlebt (P3), muss sie als **Modulvariable** gehalten und bei jedem `updateBulkActionsBarUI` neu gerendert werden — NICHT als einmalig eingefügtes DOM-Element. Clearen: beim nächsten erfolgreichen Bulk-Start, beim „Auswahl aufheben" (:12918–12927), und beim Leeren der Auswahl. Der Bulk-catch :12992–12997 ist heute **still** (nur btn-Restore) — E2 muss entscheiden, ob dort eine Meldung + `console.error` ergänzt wird (E2 verlangt `console.error`). R5 beachten: die bestehenden `alert()` für „nicht mehr in der Inbox" nicht anfassen.

---

### 7. #86 F-C

**[unkritisch, bestätigt] F7.1 — These hält.**
`appliedInboxGroups.add` existiert genau einmal :12845 (Banner). Staffel-Knopf (:13368) und Bulk (:12991) rufen nur `startSeriesGroupWorkflow`, ändern `appliedInboxGroups` nicht — und der Staffel-Knopf existiert ohnehin nur in Zeilen, deren Gruppe bereits angewendet ist (`buildGroupedInboxSuggestions` :12554 prüft `appliedInboxGroups.has(groupKey)`). Rücknahme :12850 bleibt. **Bedingung:** Der Briefing muss explizit verbieten, dass Staffel-/Bulk-catch aus „Symmetrie" `appliedInboxGroups.delete/add` einbauen — die Gruppe soll beim Staffel-Fehler angewendet bleiben (Wiederholen möglich). Das ist die einzige Stelle, an der E2/E3 die These brechen könnte.

---

### 8. Etappen-Übergaben

**[wichtig] F8.1 — E3-Harness-Replace kollidiert mit E2-Tests, die den Sofort-Stub implizit nutzen.**
E2 schreibt Staffel-Knopf-Fehlerpfad-Tests (vermutlich via fetch-Fehler). E3 ersetzt den Stub. Lösung aus F4.2 (Delay-abhängige Queue) minimiert das: Kleine Delays sofort, nur Frist-Delay in die Queue. Damit bricht E3 keine E2-Tests. Im Briefing als Harness-Spezifikation festschreiben.

**[unkritisch] F8.2 — Cache-Buster v103→v104 in E1, E2/E3 lassen stehen: kein Risiko.**
`cache_busting.test.js` erzwingt Gleichheit app.js-Version zwischen index.html :2760 und Importen :1–9. Solange E2/E3 keine neue `import`-Datei hinzufügen und die Versionsnummer nicht zurücksetzen, bleibt es konsistent. Einziges Restrisiko: Ein Worker „repariert" versehentlich den Buster oder fügt einen neuen Import mit abweichender Version hinzu — als „nicht anfassen"-Notiz ins Briefing.

**[wichtig] F8.3 — Etappen-Grenzen exakt definieren, sonst überschneiden sich E1/E2/E3 in `searchSeries`.**
E1 = Staffel-Knopf + Sperre + Staffel-Datenstruktur (renderSmartInboxList/Pseudo-Entry). E2 = Fehlermeldungen (catch-Pfade der Aufrufer). E3 = searchSeries-Timeout + Harness-Umbau. Die Berührfläche: `searchSeries` wird von `startSeriesGroupWorkflow` :13184–13185 aufgerufen, das E1/E2 über die Aufrufer erreichen. E3 ändert das Verhalten des Aufrufs, den E1/E2 getestet haben. Reihenfolge-abhängige Falle: Wenn E3 den Timeout VOR dem fetch setzt und der Harness bis dahin noch Sofort-Stub ist, feuert der Timeout sofort und E2's fetch-Fehler-Test läuft in den Timeout-Zweig. → Der Queue-Harness (F4.2) muss **mit E3 gleichzeitig** landen, nicht nach E2.

---

### 9. Leicht übersehbare Punkte (Gate-A2-Risiko)

**[wichtig] F9.1 — `groupWorkflowRunning`, `bannerApplyErrors`, `searchSeries`, `currentSearchSeriesController` sind NICHT im Prod-Export-Block :13533–13559.**
Die Tests exportieren sie aktuell per Harness-Anhang (`cleanAppJs += "globalThis.…"`). Der Worker muss wissen, dass neue Modulzustände (E2-Map, Frist-Konstante) entweder im Prod-Export-Block **ergänzt** (darf laut Vorgabe) oder per Harness-Anhang erreichbar gemacht werden müssen. Sonst scheitern E2/E3-Tests am fehlenden Zugriff.

**[wichtig] F9.2 — Benannte Frist-Konstante muss testreferenzierbar sein.**
Tests, die den Timeout auslösen, brauchen den Wert (30 000 ms). Hart im Test kodieren → bricht bei Konstanteänderung still. Konstante exportieren (oder Test liest sie aus app.js). AK13 „keine Test-Weichen": Die Konstante ist eine echte Prod-Konstante, kein Env-Override — Tests dürfen sie NUR über die Fake-Timer-Queue „erreichen", nicht kürzen.

**[wichtig] F9.3 — Präzedenzfall #75 (Button-Reaktivierung im catch verpufft).**
Gruppenzeilen-/Bulk-Buttons sind nach 6 s abgehängte Knoten. `finally`-Code, der `btn.disabled=false`/`btn.innerHTML=original` setzt, wirkt auf abgehängte Knoten (harmlos), aber `groupWorkflowRunning=false` MUSS unabhängig vom Button-Zustand im finally laufen. Briefing: „Freigabe im finally hat Vorrang vor Button-Restore; Button-Restore darf die Freigabe nie überspringen."

**[wichtig] F9.4 — F1-Änderung (Banner startet bei ≥2 Staffeln nicht mehr) ist ein eigenes Arbeitspaket am Banner-Handler :12834–12857 und derzeit nicht spezifiziert.**
Bestehende Banner-Tests sind alle Einzelstaffel → bleiben grün, ABER: Wie genau der Banner bei Mehrstaffel-Gruppen reagiert (kein Apply-Knopf? deaktivierter Knopf? Verweis auf Gruppenzeile?) ist offen und beeinflusst E1/E2. Das gehört als expliziter AK/Entscheid ins Briefing, sonst erfindet der Worker etwas.

**[kosmetisch] F9.5 — F2-Labeltest :1407/:1447 („Auswählen") bricht durch Umbenennung.**
Bestätigt; benannte Testanpassung ins Briefing (nicht still „mitreparieren").

---

### Verdichtete Gegenmaßnahmen-Pflichten fürs Briefing

1. Sperre nur über `groupWorkflowRunning`; Prüfen+Setzen atomar-synchron; `finally` an Gruppenzeile **und** Bulk nachrüsten.
2. Timeout-Callback: nur `didTimeout=true` + lokalen Controller abrichten, **nichts rendern, nicht werfen**; Frist-Meldung im catch mit `seq === searchSeriesRequestSeq`-Guard (Request-Zähler statt nur `lastSearchSeriesQuery`).
3. Ablöse-Abort :3085–3087 nicht verlieren — globaler Controller bleibt Registry, lokaler Controller für den Timeout.
4. Harness: Fake-Timer-Queue mit Delay-Unterscheidung (klein=sofort, Frist=Queue), mit E3 gleichzeitig einführen, Rot-Probe gegen Vor-Etappen-Stand.
5. B11a-Test in strengem Mock (Banner-Datei oder neue Datei), Mehrstaffel-Fixture + `seasons`-Struktur im Pseudo-Entry neu.
6. E2-Map pro Gruppe löschen beim nächsten Erfolg + bei Rücknahme; Bulk-Meldung als Modulvariable (überlebt innerHTML-Neubau).
7. Verbieten, dass Staffel-/Bulk-Handler `appliedInboxGroups` anfassen.
8. Frist-Konstante exportieren/testreferenzierbar; F1-Banner-Verhalten bei Mehrstaffel explizit spezifizieren.

VERDICT für das Briefing: **REVISE** — die Vorgaben S1/S3/S4/P3 sind tragfähig, aber F3.1 (Ablöse-Abort vs. lokaler Controller), F3.3 (identischer Query), F1.1 (btn.disabled wirkungslos vs. 6-s-Neubau) und F4.2 (Harness-Delay-Unterscheidung) sind im aktuellen Vorgabentext nicht präzise genug und treiben den Worker sonst in genau die B5-/Deadlock-Fallen, die die Kette beheben soll.
