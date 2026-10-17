<!-- Mechanisch aus `opencode export ses_eb760a95dffesBRgPU3W8iehe8` extrahiert (Claude Code, 2026-10-17): alle Assistant-Textteile in Reihenfolge, ungekürzt, unverändert (nur Trailing Whitespace entfernt). Rohdatei: Kit scripts/gate-a2/logs/2026-10-16-roadmap75-inbox-vorschlaege/akt2/export-direkt/export-plan-reviewer.json -->

Ich beginne mit der Sichtung der Session-Ordner und der Kern-Dokumente.

---

Der Session-Ordner enthält `briefing.md` und `00-kickoff.md`. Ich lese jetzt Prüfgegenstand und Maßstäbe parallel.

---

Das Briefing wurde bei Zeile 339 gekappt — ich lese den Rest und parallel das Referenz-Briefing (Abschnitt 11 / test_cmd).

---

`test_cmd` stimmt auf den ersten Blick mit dem Referenz-Briefing überein. Jetzt die Code-Stichproben — zuerst `app.js`-Kernstellen.

---

Kernstellen in `app.js` stimmen bisher. Weiter mit den übrigen `app.js`-Stellen.

---

`app.js`-Belege stimmen. Jetzt `index.html`, `style.css`, `ROADMAP.md` und die Testdateien.

---

ROADMAP- und HTML/CSS-Belege stimmen. Jetzt die Testdateien und das Frontmatter-Muster.

---

Zentrale Test-Belege bestätigt. Jetzt die restlichen Stichproben: `inbox_selection.test.js`, `cache_busting.test.js`, `briefing-65.md`-Frontmatter, Chevron-SVG, Responsive-CSS, `detectInboxGroups`, laxer Mock.

---

`cache_busting`- und `validateSelector`-Belege stimmen; `briefing-65.md` bestätigt das Platzhalter-Muster im Draft. Jetzt die letzten Code-Stichproben.

---

Alle Code-Belege sind verifiziert. Zwei Punkte vertiefe ich noch: das Muster des vorherigen plan-reviewers (Umgang mit IOU/wichtigen Findings) und die Randreferenz ROADMAP #61.

---

# Plan-Review: `docs/sessions/2026-10-16-roadmap75-inbox-vorschlaege/briefing.md`

**Prüfumfang:** Kickoff-Bindungen (Vorgaben 1–6, Q1–Q4-Antworten), Akt-2-Auftrag (AK0, Mindest-Testthemen, Erlaubnis-/Nicht-anfassen-Listen, test_cmd, Erfahrungswerte, Handtest), Vorlagen-Struktur, Hausregeln, Code-Realität (Stichproben mit Datei:Zeile), innere Konsistenz. Read-only; kein bash, kein Web, keine `.env` gelesen, nichts außerhalb des Worktrees.

## 1. Verifizierte Code-Belege (alle Stichproben bestätigt)

**app.js:** `updateGroupBannerUI` :12594–12664 ✓ (break-Suche :12599–12610, sessionStorage-Lesung :12601–12605, `innerHTML` :12623, Ignore-Handler :12634–12641, Apply-Handler :12643–12663 mit `add` :12653 → Re-Render :12654 → `await` :12656, `catch` :12657–12662 nur Button-Freigabe, `btn.disabled` :12645/:12648); Modul-States :12471–12477 ✓; `triggerQualityHintUpdates` synchron :12887–12889 ✓; `searchSeries`-Rückgabe :12969–12971 ✓, Wurfquellen :3107/:3111 ✓; Aufrufstelle :13045–13049 ✓; Leer-Zweig :13302–13315 ✓; Export-Block :13318–13344 nur `globalThis.X = X` ✓; `escapeHTML` :245 ✓; neun Importe `?v=102` :1–9 ✓; Lucide-SVGs :12625 (Layers) / :13079 (Chevron) ✓; `showFskBatchError` :18056–18062 an `#fsk-batch-error-inline` gebunden ✓; `detectInboxGroups` :12509–12540 ✓; Zustandsüberschreibung :12792–12799 ✓.

**index.html/style.css:** `style.css?v=50` :9 ✓, `app.js?v=102` :2760 ✓; Banner-Block :3866–3894 ✓; Responsive `#smart-inbox-group-banner` :4067 ✓; Theme-Variablen `--text-main/--text-muted/--danger/--radius-md` :20/:21/:26/:34 ✓.

**Tests:** `inbox_group.test.js` funktionaler sessionStorage-Mock :12–19 ✓, No-op-`localStorage` :452–456 ✓, Timer-Stubs :536–538 ✓, eval-Harness :554–620 (Präambel :560–581, `const`-Binding :564, Harness-Export-Block :583–618, `eval` :620) ✓, Setup-try/catch :622–627 ✓, Bestandstest :838–866 (Assertion `sessionStorage … 'true'` :864, „Banner must be hidden" :865) ✓, laxer Mock :349–357 ✓; `inbox_selection.test.js` `validateSelector` :20–58 (wirft `SyntaxError`) ✓, validierte querySelector :368–378/:492–519 ✓, No-op-`localStorage` :473–477 ✓; `cache_busting.test.js` :13–48 nur Konsistenz, :50–56 style.css nur nicht-leer → Briefing-These „erzwingt nur Konsistenz, nicht den Bump" ✓.

**ROADMAP:** #75 :2068–2089 ✓, Alex-Zitat :2070 ✓, Wortlaut „Ausgeblendete Vorschläge (n) – wieder anzeigen" :2077 ✓, #80 :2168–2179 ✓, #74 :2045–2065 ✓, #61 :1751 ✓.

**ADR-75-6-Kernthesen selbst verifiziert:** (a) `globalThis.startSeriesGroupWorkflow` nach dem `eval` zu überschreiben verpufft tatsächlich — der Apply-Handler ruft die Funktionsdeklaration des evalten Scopes (:12656), eine spätere `globalThis`-Zuweisung ändert die lokale Binding nicht ✓; (b) `fetch`-Stub wirkt zur Laufzeit (`searchSeries` ruft `fetch(...)` :3102 ohne lokale Binding) ✓; (c) `triggerQualityHintUpdates` muss vor dem `eval` gestubbt werden (`const`-Binding in der Präambel :564) ✓.

**Struktur/Bindungen:** Frontmatter `status: draft`, Platzhalter für `approved_on`/`approval_quote` (Muster `briefing-65.md` konform, keine erfundene Freigabe) ✓; 12 Abschnitte vollständig, 7 ADR-Blöcke (Grenze 3–7 eingehalten) ✓; Freigabepunkt-1-Antwort wörtlich und korrekt zugeordnet („Q1 C, Q2 A, Q3 A, Q4 A – starte Akt 2.") ✓; alle 14 Pflicht-Testthemen des Akt-2-Auftrags in AK1–AK14 abgedeckt ✓; Nicht-anfassen-Liste vollständig (plus zulässige Ergänzungen `pytest.ini`, `data/**`, `gui/static/js/**`) ✓; `test_cmd` identisch zum Referenz-Briefing (2026-10-12, Zeile 182; visuell byte-identisch, ohne eigenes `timeout`, `test_timeout_s` 600 dokumentiert) ✓; Erfahrungswerte alle vorhanden ✓; Abschnitt 12 erfüllt den Auftrag (lokal, ≥3 Seriengruppen, `\"`/`'`/`</&`, Fehler-Provokation durch Claude Code, NAS nur kurzer Blick) ✓; Dissens-Pflicht erfüllt (Dissens 1–6, alle drei Rollen mit Rollen-Tags, verworfene Alternativen + Risiken-Block) ✓; Lizenz-Abschnitt 7 vorhanden und gepflegt (kein neuer Third-Party-Code, Lucide ISC korrekt, Referenz-Apps nur Muster) → **kein Lizenz-Blocker** ✓; keine Agenten-Entscheidung über Freigabepunkte (Apply-Sperre und Bestandstest-Anpassung ausdrücklich Alex in Abschnitt 8 Frage 2a/2b vorgelegt, beides streichbar) ✓.

## 2. Findings

### Blocker

Keine.

### Sollte behoben werden

**F1 — Bestandstest-Anpassung ist mit dem bestehenden Mock nicht grün zu bekommen (Erlaubnislisten-Konflikt).** AK11 (briefing.md:45), ADR-75-6 (briefing.md:97) und der Worker-Text (briefing.md:256–258, Erlaubnisliste :310) ordnen an: `inbox_group.test.js` NUR an :838–866 von `sessionStorage`- auf `localStorage`-Assertions umstellen. Aber der `localStorage`-Mock in `inbox_group.test.js` ist No-op (`getItem: () => null`, tests/frontend/inbox_group.test.js:452–456) — eine umgestellte Assertion `localStorage.getItem('smart-inbox-ignore-group-Show') === '{"ignored":true}'` (analog :864) liefert mit diesem Mock immer `null` und fällt ROT. Technisch nötig wäre entweder (a) ein Mock-Override mit funktionalem Store INNERHALB des Testblocks :838–866 (vom Briefing nirgends beschrieben) oder (b) die Änderung des Mocks an :452–456 — eine zweite Stelle, die die Erlaubnisliste ausdrücklich NICHT deckt und zudem Sub-Regessionsrisiko für die übrigen Tests der Datei birgt (`localStorage` wird im evalten Code vielfach genutzt). Der Worker läuft also vorhersehbar in ROT/STOPP („Bei Abweichung: STOPP", briefing.md:321) oder füllt die Lücke eigenmächtig — an genau der einen Abweichung, die Alex in Freigabepunkt 2 Frage 2b abnehmen soll. Vor der Freigabe präzisieren: Mock-Lösung ausdrücklich vorschreiben (empfohlen: funktionaler Store-Override im Testblock, Muster :12–19) oder :452–456 als zweite benannte Stelle erlauben und in Dissens 6 + Abschnitt 8 Frage 2b nachziehen.

**F2 — Ziel-Assertions und Testname des angepassten Bestandstests sind nicht spezifiziert.** Die bestehende Assertion :865 („Banner must be hidden after ignore", `display === 'none'`) ist mit der NEUEN Spezifikation unvereinbar: AK6 (briefing.md:40) und ADR-75-3 (briefing.md:79) schreiben vor, dass nach Ignorieren der einzigen Gruppe das Banner SICHTBAR bleibt (nur Rückweg-Zone „Ausgeblendete Vorschläge (1)"). Die Anweisungen „die Versteck-Assertion bleibt sinngemäß erhalten" (briefing.md:97) und „letzterer Teil bleibt als Assertion erhalten" (briefing.md:45) sind mehrdeutig — „letzterer Teil" („Vorschlag aus offenen entfernt") existiert so nicht als bestehende Assertion, und „sinngemäß" lässt offen, ob :865 wörtlich bleibt (dann ROT) oder durch was genau sie ersetzt wird. Zudem enthält der Testname :838 („… saves to sessionStorage and hides banner for session") zwei Aussagen, die nach der Umstellung falsch sind, und muss mit angepasst werden — unbenannt. Der Worker erhält hier Interpretationsfreiheit an der einzigen Stelle, für die das Briefing selbst „AKs werden NICHT autonom angepasst (Planänderung = Freigabepunkt)" (briefing.md:321) fordert. Ziel-Assertions wörtlich vorgeben (z. B.: `localStorage`-Schlüssel mit JSON-Wert; Banner `display !== 'none'`; Rückweg-Zone mit Zähler (1) vorhanden; Gruppe nicht mehr unter offenen Vorschlägen) und Testname-Anpassung ausdrücklich einschließen.

### Optional

**F3 — sessionStorage-Mock-Anforderung für AK7 ungenannt.** AK7 (briefing.md:41) verlangt „einen vorab gesetzten `sessionStorage`-Schlüssel" — mit einem No-op-Mock (getItem → null) wäre der Test trivial-grün ohne echte Prüfung; AK7 braucht in der NEUEN Datei zwingend einen funktionalen `sessionStorage`-Mock. ADR-75-6 (briefing.md:97) spezifiziert für die neue Datei nur den funktionalen `localStorage`-Mock („analog sessionStore :12–19"). Einen Satz ergänzen: funktionaler `sessionStorage`-Mock in `inbox_group_banner.test.js` nach Muster :12–19.

**F4 — Quellen-Zuschreibung „Rücknahme appliedInboxGroups" an #80 ungenau.** briefing.md:12 zählt „Fehlermeldung + `console.error` + Rücknahme `appliedInboxGroups`" als Inhalt der „Banner-Stelle aus #80 (`ROADMAP.md:2168–2179`)". #80 verlangt nur Meldung + `console.error` (ROADMAP.md:2172–2176); die Rücknahme-Pflicht stammt aus Alex' bindender Kickoff-Vorgabe 1 (00-kickoff.md:29) — die ADR-75-4 (briefing.md:85) korrekt zuschreibt. Präzisieren, damit die Bindung nachvollziehbar bleibt.

**F5 — „wörtlich" gefolgt von Paraphrase.** briefing.md:20 kündigt Alex' Anlass „(wörtlich, zitiert in `ROADMAP.md:2070`)" an und gibt dann eine geglättete Paraphrase (das Original in :2070 enthält „ähm"-Filler). Formulierung auf „sinngemäß, wörtliches Zitat siehe ROADMAP.md:2070" ändern.

**F6 — Tippfehler im Worker-Text.** briefing.md:285: „verpueft" → „verpufft" (kein Umlaut-Ersatz, sondern ein echter Tippfehler im ASCII-Block).

**F7 — Basis-Formulierung ohne docs-only-Klarstellung.** briefing.md:321 (Schritt 0) nennt nur „Basis ist `origin/main` @ `34d621e` (Stand des Kickoff-Git-Zustands)". Der Präzedenz (2026-10-12-briefing.md:35) klärt ausdrücklich, dass ein etwaiger Session-Head (docs-only) nicht Teil der Worker-Basis ist. Wenn die Session-Dateien vor dem Lauf committet werden, entsteht exakt die vom Präzedenz aufgelöste Mehrdeutigkeit. Klarstellung ergänzen (funktional unkritisch, da Schritt 0 die Verifikation erzwingt).

## 3. Restrisiken / nicht ausgeführte Prüfungen

- **Session-Rohoutputs fehlen vollständig** (Ordner enthält nur `briefing.md` + `00-kickoff.md`). Die Dissens-Dokumentation (Dissens 1–6) und alle Rollenzitate ([produktberater] Findings 1/2/3/6/7/10, [grafiker] Punkte 4/6 + Skizze inkl. 220px/Klassennamen, [advocatus] W1/W3/W5/K1–K6/C1/Frage 8) sind damit NICHT gegen Rohoutputs verifizierbar. Ich habe keinen positiven Befund für Ignorieren/Verfälschung/Verlust — der IOU ist transparent dokumentiert (briefing.md:132) und Muster-konform (Präzedenz 2026-10-12, dort später archiviert; der events damalige Reviewer behandelte den IOU ebenso als Restrisiko). **Bedingung an den Vermittler:** Archivierung der Rollen-Dateien VOR Freigabepunkt 2, damit Alex die Dissens-Dokumentation gegen die Original-Outputs prüfen kann.
- **Git-Ausgaben ungeprüft übernommen** (Abschnitt 10): Ich habe kein bash; Branch, Head `34d621e` und „kein main-Stop" sind vom Kickoff-Prompt übernommen, nicht selbst verifiziert (das Briefing dokumentiert dieselbe Einschränkung für sich selbst, briefing.md:156).
- **`test_cmd`-Byte-Identität nur visuell geprüft** (beide einzeilig, Token-für-Token identisch mit 2026-10-12/briefing.md:182); ein diff-Tool stand nicht zur Verfügung.
- **Keine Testausführung** durch mich (Review-Modus, read-only) — Ausführbarkeit der AKs nur formal und gegen den Code geprüft.
- [grafiker]-Skizze, [produktberater]-Faustzahl (1–3 Gruppen) und [advocatus]-Verifikationen sind nur aus Briefing-Zitaten bekannt.

## 4. Potenziale-Block (optional, keine Bedingungen)

- **Rot-Probe auf den angepassten Bestandstest ausweiten:** Abschnitt 11 (briefing.md:323) verlangt die Rot-Probe nur für „die neuen Banner-Tests". Auch der ANGEPASSTE Bestandstest :838–866 gegen den ALTEN `app.js` als ROT nachzuweisen, würde belegen, dass die Anpassung die Semantik wirklich verschärft (Storage-Format + Banner-Sichtbarkeit) statt nur umbenennt.
- **AK7-Stärkung per Schreib-Spy:** „der Ignorier-Pfad kein `sessionStorage` mehr liest oder schreibt" (briefing.md:41) ließe sich mit einem setItem/getItem-Spy am funktionalen sessionStorage-Mock automatisiert prüfen statt nur per Review.
- **IOU-Nachbelegung:** [grafiker]-Klassenskizze (ADR-75-7) und [produktberater]-Faustzahl nach Archivierung der Rohoutputs verifizieren.

---

**Zusammenfassung:** Alle Code-Belege des Briefings stimmen in den Stichproben (inklusive der drei selbst verifizierten ADR-75-6-Injektionsthesen), alle Kickoff-Bindungen und Q1–Q4-Entscheidungen sind korrekt operationalisiert, Struktur, Erlaubnis-/Nicht-anfassen-Listen, `test_cmd`, Dissens-Pflicht und Lizenz-Abschnitt sind erfüllt. Die eine bewusste Abweichung vom Akt-2-Rahmen (Bestandstest-Anpassung, Dissens 6) ist als Abweichung transparent dokumentiert und Alex vorgelegt — das genügt formal. **Inhaltlich ist genau diese Anpassung aber technisch unterbestimmt:** sie ist mit dem bestehenden No-op-Mock nicht grün zu bekommen (Erlaubnislisten-Konflikt) und ihre Ziel-Assertions sind nicht spezifiziert (bestehende Assertion :865 widerspricht AK6). Das ist ein vorhersagbares, vermeidbares ROT/STOPP-Risiko für den einzigen Gate-A2-Lauf (bindende Vorgabe 6) und untergräbt den eigenen Anspruch „AKs werden NICHT autonom angepasst". Keine Blocker, aber zwei wichtige Einwände — daher REVISE mit engen, schnell einarbeitbaren Präzisierungen vor Freigabepunkt 2.

VERDICT: REVISE

1. [wichtig] Bestandstest-Anpassung :838–866 mit vorhandenem Mock unausführbar: No-op-`localStorage` (inbox_group.test.js:452–456) macht die geforderte `localStorage`-Assertion (analog :864) immer ROT; die Erlaubnisliste „NUR Anpassung Test :838–866" (briefing.md:310, :256–258) deckt die nötige Mock-Lösung nicht (Store-Override im Testblock vorschreiben ODER :452–456 als zweite benannte Stelle erlauben und in Dissens 6/Abschnitt 8 Frage 2b nachziehen).
2. [wichtig] Ziel-Assertions/Testname des angepassten Bestandstests unterbestimmt: Assertion :865 („Banner must be hidden") ist mit AK6/ADR-75-3 (Banner bleibt sichtbar, Rückweg-Zone) unvereinbar und muss ersetzt werden — „sinngemäß erhalten" (briefing.md:97) und „letzterer Teil bleibt als Assertion erhalten" (briefing.md:45) lassen offen wodurch; Testname :838 („saves to sessionStorage and hides banner") muss mit angepasst werden. Ziel-Assertions wörtlich vorgeben.
3. [kosmetisch] AK7 (briefing.md:41) braucht in der neuen Datei zwingend einen funktionalen `sessionStorage`-Mock (No-op machte den Test trivial-grün); ADR-75-6 (briefing.md:97) spezifiziert nur den `localStorage`-Mock — ergänzen (Muster inbox_group.test.js:12–19).
4. [kosmetisch] briefing.md:12 schreibt die „Rücknahme `appliedInboxGroups`" der Banner-Stelle aus #80 (ROADMAP.md:2168–2179) zu; #80 verlangt nur Meldung + `console.error` (ROADMAP.md:2172–2176), die Rücknahme stammt aus Kickoff-Vorgabe 1 (00-kickoff.md:29) — Zuschreibung präzisieren.
5. [kosmetisch] briefing.md:20 kündigt „(wörtlich, zitiert in ROADMAP.md:2070)" an und liefert eine Paraphrase — als „sinngemäß" kennzeichnen.
6. [kosmetisch] briefing.md:285: „verpueft" → „verpufft" (Tippfehler im Worker-ASCII-Block).
7. [kosmetisch] briefing.md:321 (Schritt 0): Basis-Formulierung ohne die Präzedenz-Klarstellung (2026-10-12-briefing.md:35), dass ein etwaiger docs-only Session-Head nicht Teil der Worker-Basis ist — ergänzen, falls die Session-Dateien vor dem Lauf committet werden.

---

Runde 2 — ich lese das überarbeitete Briefing vollständig und prüfe parallel die technische Kernbehauptung (localStorage-Swap-Wirksamkeit im eval-Pfad).

---

Die Kernbehauptung ist verifiziert: `localStorage` ist im Produktivcode eine freie globale Referenz (keine `const/let/var`-Binding, grep leer), `:459` läuft innerhalb der Init-Funktion (vor dem Swap, mit No-op — Bestandsverhalten), die neuen Zugriffe entstehen erst in `updateGroupBannerUI`/Handlern nach dem Swap. Jetzt der Rest des Briefings (Worker-Auftrag, Schritt 0, Übergabe).

---

Die Fixstellen sind alle im Text. Zwei letzte Sicherheitsprüfungen zur Swap-Behauptung: Top-Level-`localStorage`-Zugriffe und Referenz-Freezes im evalten Code.

---

# Plan-Review Runde 2: `briefing.md` (Fixstellen-Verifikation)

**Prüfumfang:** Nur die 7 Fixstellen und ihre Konsistenz zum Rest; technische Kernbehauptungen selbst verifiziert (read-only, kein bash, keine `.env`, nichts außerhalb des Worktrees).

## Bestätigung je Einwand (Runde 1)

**F1 — erledigt.** Die Bestandstest-Anpassung ist jetzt an allen fünf Stellen als reiner Testblock-Swap definiert: AK11 (briefing.md:45), ADR-75-6 (briefing.md:97), Dissens 6 (briefing.md:120), Abschnitt 8 Frage 2b (briefing.md:143), Worker-Text (briefing.md:258–261) — jeweils identisch: `globalThis.localStorage` wird NACH `setupTestEnvironment()` INNERHALB des Testblocks :838–866 durch ein funktionales Inline-Speicher-Objekt ersetzt, Harness-Mock `:452–456` bleibt unangetastet. **Die Wirksamkeitsbehauptung habe ich selbst verifiziert:** (a) grep `^localStorage` → keine Modul-Top-Level-Zugriffe in app.js; (b) grep nach Referenz-Freezes → die drei Treffer (`:459`, `:10473`, `:16176`) binden nur `getItem`-ERGEBNISSE, nie die `localStorage`-Referenz selbst; (c) `app.js:459` liegt in einer Init-Funktion und läuft im Harness innerhalb von `setupTestEnvironment()` (via `DOMContentLoaded`/`initEventListeners`, inbox_group.test.js:622–627), also VOR dem Swap mit dem No-op-Mock — das ist exakt das heutige grüne Bestandsverhalten und bricht nichts; (d) die NEUEN `localStorage`-Zugriffe entstehen ausschließlich im umgebauten `updateGroupBannerUI`/Ignore-Handler und laufen im Test erst nach dem Swap (erster relevanter Aufruf ist der explizite `renderSmartInboxList`-Aufruf). Die Behauptung „Produktcode liest `localStorage` erst zum Aufrufzeitpunkt dynamisch" stimmt. **Erlaubnislisten-Konflikt aufgelöst:** Der Swap geschieht innerhalb :838–866, die Erlaubnisliste (briefing.md:320) deckt ihn damit, `:452–456` wird nicht mehr gebraucht — kein Konflikt, keine zweite Stelle, kein Test-Interdependenzrisiko (jedes Setup setzt den No-op-Mock neu zurück).

**F2 — erledigt.** Ziel-Assertions wörtlich festgelegt und an beiden Stellen identisch: AK11 (briefing.md:45) und Worker-Text (briefing.md:262–267) — (a) `localStorage.getItem('smart-inbox-ignore-group-Show') === '{"ignored":true}'`, (b) kein `.btn-banner-apply-group` für „Show" mehr im Banner, (c) Banner bleibt sichtbar (`display !== 'none'`) mit „Ausgeblendete Vorschläge (1)" — mit ausdrücklicher Erklärung, dass die alte `:865`-Assertion ERSETZT wird (nicht ersatzlos gestrichen), (d) `sessionStorage.getItem(...) === null`. Testname-Anpassung angeordnet („darf nicht ‚saves to sessionStorage' behaupten"). Konsistent mit AK6/ADR-75-3; Dissens 6 (briefing.md:120) begründet jetzt auch die `:865`-Widersprüchlichkeit korrekt.

**F3 — erledigt, mit einer kosmetischen Restinkonsistenz (siehe Findings).** Funktionaler `sessionStorage`-Mock gefordert in AK7 (briefing.md:41), ADR-75-6c (briefing.md:97, Unterpunkt (c) existiert und passt) und Worker-Text (briefing.md:256–257). Die Begründung „ohne ihn wäre AK7 trivial grün" ist logisch korrekt (No-op `getItem → null` würde „alter Schlüssel wirkt nicht" ohne echte Prüfung bestätigen).

**F4 — erledigt.** briefing.md:12 schreibt die Rücknahme-Pflicht jetzt korrekt Alex' bindender Kickoff-Vorgabe 1 (`00-kickoff.md:29` — verifiziert, dort wörtlich „`appliedInboxGroups` muss im Fehlerfall zurückgenommen werden") zu und grenzt sie vom #80-Text ab (der nur Meldung + `console.error` verlangt, ROADMAP.md:2172–2176).

**F5 — erledigt.** briefing.md:20: „sinngemäß geglättet; das wörtliche Zitat inkl. Füllwörter steht in `ROADMAP.md:2070`".

**F6 — erledigt.** briefing.md:295: „verpufft".

**F7 — erledigt.** Schritt 0 (briefing.md:331) klärt jetzt ausdrücklich, dass ein etwaiger docs-only Session-Head NICHT Teil der Worker-Basis ist, mit korrektem Präzedenz-Verweis (2026-10-12-briefing.md AK0). Rot-Probe (2) ergänzt (briefing.md:333). **Die Rot-Probe-(2)-These habe ich durchgerechnet:** Angepasster Test gegen ALTEN `app.js` — alter Ignore-Handler schreibt `sessionStorage['…-Show'] = 'true'` und alter `updateGroupBannerUI` blendet das Banner aus → Assertion (a) rot (Inline-Store liefert `null` ≠ `'{"ignored":true}'`), (c) rot (`display === 'none'`), (d) rot (`sessionStorage.getItem` liefert `'true'` ≠ `null`); nur (b) wäre grün. Test damit zuverlässig ROT — die These „Anpassung verschärft die Semantik statt nur umzubenennen" stimmt.

## Konsistenz-Checks (alle bestanden)

- **Erlaubnisliste vs. Harness-Mock `:452–456`:** kein Konflikt mehr (Swap innerhalb des Testblocks, Mock bleibt unangetastet — in allen fünf Stellen identisch formuliert).
- **AK-Nummerierung AK0–AK14:** unverändert und konsistent; AK11-Titel erweitert („+ benannte Bestandstest-Anpassung"), alle Verweise (Abschnitt 3-Einleitung :32, Dissens 6 :120, Frage 2b :143, Worker :304) passen.
- **Frontmatter:** weiterhin `status: draft`, `approved_on: TBD`, Platzhalter-Quote — keine erfundene Freigabe.
- **Keine neuen unbelegten Behauptungen:** die zwei neuen technischen Behauptungen (Swap-Wirksamkeit, Rot-Probe 2) habe ich selbst gegen den Code verifiziert (siehe oben); „technisch zwingend" in Frage 2b ist korrekt begründet (ohne Anpassung rot gegen die neue Spezifikation).
- **Diff-Hygiene:** nur die Fixstellen geändert (Datei 340 → 350 Zeilen, +10 passend zu den Ergänzungen); Abschnitte 1–12, ADR-75-1 bis 75-7, Dissens 1–5, Risiken, Quellen/Lizenzen, Aufwand, Git, Handtest inhaltlich unverändert.

## Neue Findings

**Blocker:** keine. **Sollte behoben werden:** keine.

**Optional:**

1. **Spy-Formulierung zwischen den F3-Fixstellen inkonsistent:** AK7 (briefing.md:41) formuliert den Zähler/Spy als Prüfweg („wird über einen Zähler/Spy am Mock geprüft"), ADR-75-6c (briefing.md:97) nennt ihn „optional", der Worker-Text (briefing.md:256–257) nennt nur den funktionalen `sessionStorage`-Mock ohne Spy. Ein Worker, der AK7 wörtlich nimmt, baut den Spy; einer, der dem ADR folgt, könnte ihn weglassen und den „liest/schreibt nicht"-Nachweis nur funktional führen (vorab gesetzter Schlüssel wirkt nicht + kein neuer Schlüssel im Store — was ausreicht). Angleichen (z. B. AK7: „per Spy oder Store-Inhalts-Check"), damit kein scheinbarer Widerspruch zwischen verbindlichem AK und optionalem ADR beim Worker ankommt.

## Restrisiken / nicht ausgeführte Prüfungen

- **Session-Rohoutputs weiterhin nicht archiviert** (Ordner enthält nur `briefing.md` + `00-kickoff.md`) — Dissens-/Rollen-Zitate bleiben IOU gemäß briefing.md:132, Muster-konform; **Archivierung vor Freigabepunkt 2 einfordern**, damit Alex die Dissens-Dokumentation gegen die Original-Outputs prüfen kann.
- Git-Ausgaben (Abschnitt 10) weiterhin ungeprüft übernommen (kein bash); `test_cmd`-Identität weiterhin nur visuell verifiziert; keine Testausführung durch mich (Review-Modus).

---

**Zusammenfassung:** Alle 7 Einwände aus Runde 1 sind korrekt eingearbeitet und an allen relevanten Stellen (AK11, ADR-75-6, Dissens 6, Frage 2b, Worker-Auftrag, Erlaubnisliste) konsistent formuliert. Die beiden neuen technischen Behauptungen (Inline-Swap-Wirksamkeit, Rot-Probe 2) habe ich selbst gegen den Code verifiziert und bestätigt. Keine Blocker, keine wichtigen Einwände — eine kosmetische Angleichung der Spy-Formulierung empfohlen.

VERDICT: APPROVE

1. [kosmetisch] briefing.md:41 (AK7) vs. :97 (ADR-75-6c) vs. :256–257 (Worker-Text): Zähler/Spy am `sessionStorage`-Mock wird in AK7 als Prüfweg, im ADR als „optional" und im Worker-Text gar nicht genannt — Angleichen (z. B. „per Spy oder Store-Inhalts-Check"), damit der Worker keinen scheinbaren AK/ADR-Widerspruch auflösen muss.
