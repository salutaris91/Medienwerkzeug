Ich habe den relevanten Code gelesen (masked_input.js vollständig, index.html 1560–1719, style.css 3660–3833, Tests vollständig, ROADMAP 1690–1739, VERLAUF 1–20, persistence.py 380–439) sowie den tatsächlichen Save-Pfad in app.js (9789–9920), den `/api/settings`-Endpoint (system_api.py 82–143) und den `/api/keys`-Endpoint (onboarding_api.py 236–284) nachgezogen. Der Löschweg endet also nicht im Frontend, sondern ich habe ihn bis ins Backend verfolgt.

---

## 1. Kurzurteil

**Keine Blocker in der Kern-Löschlogik — aber nachbessern vor Merge.** Der zweistufige Löschweg ist für alle 6 Felder grundsätzlich funktional verdrahtet (env-basiert für TMDb/TVDb, settings-basiert für Telegram/WhatsApp), und der W1-Schutz für normales Leeren bleibt erhalten. Es gibt jedoch **einen real nicht erreichbaren dokumentierten Pfad (Escape-Abbruch) samt falsch-positivem Test**, ein **konkretes Cache-Busting-Risiko** und **fehlende End-to-End-Verifikation**. Diese drei Punkte müssen vor dem Merge geklärt werden.

---

## 2. Findings nach Schwere

### [wichtig] Escape-Abbruch ist real nicht erreichbar — der zugehörige Test ist falsch-positiv

Die Roadmap-Vorgabe (ROADMAP.md:1717) lautet explizit: *„Bei Abbruch oder `Escape`: Ausgangszustand wird wiederhergestellt."* Die Umsetzung erfüllt das in der Praxis **nicht**:

- Der `keydown`/`Escape`-Listener hängt **nur am Input-Element** (`masked_input.js:248-265`), nicht am Bestätigungsdialog, an den Buttons und nicht als globaler `document`-Handler.
- Der Dialog wird ausschließlich über den `×`-Button geöffnet (`masked_input.js:196-202`). Beim Klick wird **kein Fokus transferiert**; stattdessen wird der `×`-Button per `deleteBtn.style.display = "none"` versteckt (`masked_input.js:201`). Ein Element, das `display:none` wird, verliert den Fokus — der Browser setzt ihn auf `document.body`. Der Fokus liegt danach also **nicht mehr auf dem Input**.
- Folge: Drückt der Nutzer nach dem Öffnen des Dialogs `Escape`, feuert der Input-Listener nicht, der Dialog bleibt offen. Der einzige funktionierende Abbruch ist der „Abbrechen"-Button.
- Der Test *„Item 59: Escape key resets delete confirmation"* (`masked_input.test.js:707-727`) ruft `input.dispatch("keydown", { key: "Escape" })` direkt am Mock auf (`:720`) und modelliert damit eine Fokus-Situation, die real nach dem `×`-Klick nie vorliegt. **Der Test beweist nichts über das tatsächliche Verhalten.**

Bewertung: kein totaler Blocker (Kernlöschung + Abbrechen-Button funktionieren), aber eine explizit dokumentierte Anforderung ist unerfüllt, während die Testsuite sie als grün ausweist. Das ist der stärkste Einzelbefund.

### [wichtig] Cache-Busting: neue `masked_input.js`/`style.css` werden vermutlich nicht ausgeliefert

- `masked_input.js` wird ausschließlich über `import … from './js/masked_input.js?v=92'` geladen (`app.js:9`). `app.js` steht **nicht** in der Liste der geänderten Dateien des Auftrags — der Versions-String `?v=92` ist dort hartcodiert.
- `style.css` lädt über `style.css?v=46` (`index.html:9`).
- `index.html` selbst lädt nur `app.js?v=92` (`index.html:2752`).

Wenn `masked_input.js` und `style.css` inhaltlich geändert wurden, deren Referenzversionen (`v=92` bzw. `v=46`) aber nicht erhöht wurden, erhalten Browser mit gecachten Assets **weder die neue Lösch-Logik noch die neuen Styles** — der neue `×`-Button würde schlicht nie erscheinen.

**Unsicherheit:** Ich kann ohne `git diff` (Branch ungemergt, kein Push) nicht verifizieren, ob die Versionen beim Item #59 gebumpt wurden. Konkreter Hinweis darauf, dass **nicht** gebumpt wurde: `app.js` ist laut Auftrag unangetastet, und der Import-String `masked_input.js?v=92` steht genau dort. **Das muss vor Merge verifiziert werden.**

### [wichtig] Keine End-to-End-Verifikation des Lösch-Payloads (Testlücke)

Die Tests decken nur die JS-Pure-Logik mit Mocks ab. Nicht abgedeckt ist die Kette, die das Löschen tatsächlich bewirkt:

- `validateMaskedInput` liefert bei Bestätigung korrekt `{ valid: true, changed: true, value: "" }` (`masked_input.js:376-381`).
- Aber dass `app.js` daraus den richtigen Payload baut — `payload.telegram_token = ""` (`app.js:9861-9862`) bzw. `keyPayload.TMDB_API_KEY = ""` (`app.js:9883-9884`) — und dass das Backend den leeren Wert wirklich entfernt (`save_env_keys` bei `val == ""`, `persistence.py:410-413`; `/api/keys` in `onboarding_api.py:253-277`), ist **kein Test**, der die Gesamtstrecke prüft. Der zweistufige Save (erst `/api/settings`, dann `/api/keys`, `app.js:9881-9905`) wird in keinem Test durchlaufen.

Ich habe die Backend-Löschfähigkeit nur durch **Code-Lesen** bestätigt (und Backend-Tests wie `test_env_handling.py:46-48` existieren), nicht durch Ausführung. Die Frontend→Backend-Integration für den Löschfall ist eine echte, unbewiesene Lücke.

### [wichtig] Nicht-atomarer Save: partielle Löschung möglich (vorbestehend, aber für den Löschweg relevant)

Telegram/WhatsApp werden über `/api/settings` gespeichert (`app.js:9875`), TMDb/TVDb erst in einem **zweiten** Request über `/api/keys` (`app.js:9882-9905`) — und nur, wenn der erste `response.ok` war (`app.js:9881`). Löscht ein Nutzer zugleich z. B. `telegram_token` und `TMDB_API_KEY` und der zweite Request schlägt fehl, ist Telegram bereits gelöscht, TMDb nicht. Die UI meldet das zwar (`app.js:9910`), aber eine atomare Löschung über alle 6 Felder gibt es nicht. Das ist kein durch Item #59 neu eingeführter Fehler, aber der explizite Löschweg macht erstmals alle 6 Felder gleichzeitig löschbar — das Restrisiko ist daher jetzt real relevanter.

### [kosmetisch] „AK1–AK7" stehen nicht als nummerierte Liste in der ROADMAP

Der Auftrag verweist für AK1–AK7 auf ROADMAP.md Zeilen 1701–1722. Dort steht aber nur Lösungsidee + Umsetzungsbeschreibung (`ROADMAP.md:1711-1720`), **keine** nummerierte AK-Liste. Die Bezeichnungen AK1–AK7 existieren ausschließlich in den Testnamen (`masked_input.test.js:517-705`) und in VERLAUF.md:13. Inhaltlich sind die AKs durch die Tests abgedeckt, aber die Rückverfolgbarkeit „AK-Nummer → ROADMAP-Vorgabe" ist nicht gegeben. Diskrepanz zur Auftragsbeschreibung.

### [kosmetisch] Barrierefreiheit des Inline-Dialogs

- Kein `aria-expanded` am `×`-Button, kein Fokus-Transfer in den Dialog beim Öffnen, kein Fokus-Rücktransfer beim Schließen, kein Fokus-Trap (`masked_input.js:196-202, 205-230`). Screenreader-Nutzer erfahren das Erscheinen des Dialogs (`role="group"`, `index.html:1585`) nicht aktiv. Das `disabled`/`aria-hidden`-Handling am `×`-Button selbst ist dagegen sauber (`masked_input.js:49-60`) und getestet (AK1/AK2).

### [kosmetisch] Dialog bleibt offen, wenn Nutzer nach dem `×`-Klick stattdessen das Feld bearbeitet

Es gibt kein Schließen des `confirmEl` bei Feld-Edit/Blur außerhalb der beiden Buttons und Escape. Klickt der Nutzer `×` und tippt dann direkt in das Input, bleibt der Bestätigungsdialog sichtbar, während der Inhalt sich ändert (`masked_input.js:288-308` setzt nur `deleted`/`pendingDelete` zurück, schließt den Dialog aber nicht). Kein Datenverlust, aber inkonsistenter UI-Zustand.

### [kosmetisch] `dataset.hasKey` bleibt nach bestätigtem Löschen auf `"true"`

Der `confirmYes`-Handler setzt `deleted`/`pendingDelete`/`editing`/`masked`, aber **nicht** `hasKey` (`masked_input.js:217-230`). Bis zum nächsten `loadSettings()`/`setMaskedInputValue` bleibt `hasKey === "true"` und damit `wrapper.dataset.hasKey = "true"` (`masked_input.js:44-46`). Funktional unkritisch (der `×`-Button bleibt über `isDeleted` korrekt versteckt, `masked_input.js:50`), aber ein inkonsistenter interner Zustand.

---

## 3. Regressionsrisiken und fehlende Verifikationen

- **W1-Schutz:** Als intakt bestätigt (per Code-Analyse). Normales Leeren über Clear-on-Edit setzt `deleted=false`/`pendingDelete=false` (`masked_input.js:274-278`) und wird von `validateMaskedInput` als `changed:false, value:orig` behandelt (`masked_input.js:385-390`); Blur-Restore stellt den Originalwert wieder her (`masked_input.js:318-321`). Tests AK6, W1 (mehrere) decken das ab. **Kein Regressionsbefund.**
- **Tests wurden von mir nicht ausgeführt.** Die Behauptung in VERLAUF.md:13 (*„25 Tests in masked_input.test.js, 134 Tests gesamt grün"*) ist **nicht** von mir verifiziert. `npm run test:frontend` / `pytest` wurden hier nicht ausgeführt.
- **Git-Zustand nicht verifiziert:** Branch `a2/20260914T093720Z` ungemergt, kein Push; ich habe weder `git status` noch `git log` gesehen. Preflight für einen etwaigen Commit/PR liegt nicht vor.
- **Nicht verifizierte Punkte:** reale Fokus-/Escape-Situation im Browser, reale Cache-Auslieferung (`?v=`-Bump), Backend-Verhalten bei leerem Telegram-/WhatsApp-Wert über `update_settings` (Code-Pfad `system_api.py:96-128` gelesen, aber nicht ausgeführt).

---

## 4. Empfehlung für Alex

**Nachbessern — nicht merge-ready.**

Konkret vor Merge:
1. **Escape-Vorgabe auflösen** (empfohlene Reihenfolge): entweder den `Escape`-Abbruch real implementieren (Listener auf `document`/Dialog bzw. Fokus in den Dialog transferieren) oder die ROADMAP-Zusage auf „Abbruch per Button" reduzieren. Aktuell stimmt dokumentierte Vorgabe (`ROADMAP.md:1717`) und Testbehauptung nicht mit dem realen Verhalten überein. Das ist der Punkt, der am ehesten eine Nachbesserungsrunde rechtfertigt.
2. **Cache-Busting verifizieren:** `style.css?v=` und der Import `masked_input.js?v=92` in `app.js:9` müssen gebumpt werden, da `app.js` laut Auftrag unangetastet blieb. Ohne Bump läuft die alte Logik weiter.
3. **Mindestens einen Integrations-/E2E-Test** für den Löschfall ergänzen (UI-Bestätigung → Payload → Backend entfernt Key), statt nur JS-Mocks.

Trade-off/Risiko: Punkt 1 (Escape) ist der einzige Befund mit echtem Funktionsdefizit; 2 und 3 sind Absicherungen gegen „funktioniert im Test, scheitert in Produktion". Wenn Alex bewusst auf echten Escape-Verzicht geht und das in der ROADMAP dokumentiert, wären 2 und 3 die verbleibenden Merge-Voraussetzungen.

**Alex-Entscheidung:** Soll ich die drei Punkte als konkrete Nachbesserungsaufträge formulieren (insb. ob Escape real nachgezogen oder die Vorgabe angepasst werden soll)?
