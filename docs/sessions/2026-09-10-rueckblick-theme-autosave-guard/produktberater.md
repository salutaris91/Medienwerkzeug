# Produktberater-Rohoutput — Rückblick-Session Theme-Autosave-Request-Guard (#62)

## Session: 2026-09-10, Request-Guard beim Theme-Autosave (Abnahme)

**Datum:** 10.09.2026
**Rolle:** Produktberater (Scope-Wächter)
**Gegenstand:** Roadmap-Item #62, Branch `a2/20260910T064759Z`
**Geprüfte Artefakte:** `gui/static/app.js` (Zeilen 479–545), `tests/frontend/theme_autosave.test.js` (Zeilen 289–438), `ROADMAP.md` (Zeilen 1750–1764), `docs/sessions/2026-09-08-theme-autosave-rueckblick/advocatus.md`

> Ungekürzter Rohoutput des produktberater aus der Rückkanal-Konsultation.

---

## 1. Trifft das Ergebnis das eigentliche Nutzerbedürfnis?

**Ja, direkt.**

Die Nutzererwartung lautet: *„Ich klicke schnell durch Themes, und am Ende wird genau das gespeichert und angezeigt, was ich zuletzt gewählt habe — ohne verwirrende Fehlerhinweise."*

Die Umsetzung erfüllt das in allen drei Teilaspekten:

| Nutzererwartung | Umsetzung | Bewertung |
|---|---|---|
| Schnelles Durchklicken ohne Verzögerung | `applyTheme()` läuft sofort synchron; der Guard blockiert nichts, er bricht nur den *alten* Save ab. Kein Debounce, der das letzte Klick-Erlebnis verzögert. | ✓ Erfüllt |
| Gespeichert wird, was zuletzt gewählt wurde | `AbortController` bricht den laufenden Request ab, bevor der neue startet. Nur der letzte Request läuft bis zum Server durch. | ✓ Erfüllt |
| Kein Geister-Fehlerhinweis | `AbortError` wird im `catch` erkannt (`e.name === "AbortError" \|\| signal.aborted`) und mit `return` als Nicht-Fehler behandelt — weder `console.error` noch Fehler-Banner. | ✓ Erfüllt |

Der Nutzer sieht sein Theme *sofort*, der Speichervorgang läuft sauber im Hintergrund, und bei einem schnellen Wechsel verschwindet der alte Request still. Das ist exakt das erwartete Verhalten.

---

## 2. Aufwand-Nutzen-Verhältnis: verhältnismäßig oder Over-Engineering?

**Verhältnismäßig — weder zu dick noch zu dünn.**

Zur Einordnung: Der advocatus hat das Problem selbst als „praktische Auswirkung heute gering" eingestuft (localhost, kein Save-Fehler im Normalbetrieb). Die Frage ist also berechtigt, ob man das überhaupt anfasst.

**Argumente für die Lösung (pro):**

- **Aufwand minimal:** Der Guard besteht aus 4 funktionalen Zeilen — `let themeSaveController = null` (Deklaration), `abort()` + Neuzuweisung (3 Zeilen), `signal`-Übergabe an `fetch` (1 Attribut), und der `AbortError`-Check im `catch` (2 Zeilen). Das sind ~10 Zeilen Code-Änderung.
- **Keine neuen Abhängigkeiten:** `AbortController` ist Standard-Browser-API, kein npm-Paket, kein Build-Schritt.
- **Etabliertes Muster:** Die Codebase nutzt dieses Anti-Race-Muster bereits an anderer Stelle (`lastQualityRequestIds`, `selectShowRequestId` — vom advocatus selbst referenziert). Es wird also kein neues Konzept eingeführt, sondern ein vorhandenes Pattern an einer Stelle nachgezogen, wo es gefehlt hat.
- **Kein Debounce nötig:** Ein Debounce wäre eine Alternative gewesen, hätte aber das letzte Klick-Erlebnis um z. B. 200 ms verzögert. Der AbortController-Ansatz ist hier die präzisere Lösung: sofortiges visuelles Feedback, sofortiger Save-Start, nur der alte Request wird gekillt.

**Gegenargumente (contra) — und warum sie nicht ziehen:**

- *„Braucht man auf localhost nie"* — Richtig, aber der Fehlerhinweis-Mechanismus wurde erst durch Item #60 eingeführt. Wenn man ihn einführt, muss man auch die Race-Condition bedenken, die *durch ihn* sichtbar wird. Sonst produziert man ein neues Problem, während man ein altes löst.
- *„Warum kein Debounce?"* — Debounce verzögert das visuelle Feedback. Für ein Theme-Auswahl-Dropdown, bei dem der Nutzer sofort sehen will, wie es aussieht, ist AbortController die bessere Wahl.
- *„Zu dünn — warum keine `finally`-Absicherung?"* — `finally` würde hier keinen Mehrwert bringen. Es gibt keinen Zustand (z. B. Spinner, Disabled-Flag), der in jedem Fall zurückgesetzt werden müsste. Der Guard ist: alter Request weg, neuer Request läuft. Das ist in `try`/`catch` vollständig abgebildet.

**Fazit:** Aufwand-Nutzen-Verhältnis stimmt. Die Lösung ist so schlank wie möglich und so vollständig wie nötig.

---

## 3. Scope sauber gehalten?

**Ja — keine versteckten Zusatzänderungen.**

Ich habe den Abschnitt `app.js:479–545` Zeile für Zeile auf fremde Änderungen geprüft. Die einzigen *neuen* Elemente gegenüber dem vorherigen Stand (Item #60) sind:

| Zeile | Änderung | Gehört zu #62? |
|---|---|---|
| 481 | `let themeSaveController = null;` — Deklaration der Guard-Variable | ✓ Kern |
| 494–496 | `if (themeSaveController) { themeSaveController.abort(); }` — alten Request abbrechen | ✓ Kern |
| 497–498 | `themeSaveController = new AbortController(); const signal = themeSaveController.signal;` — neuen Controller erzeugen | ✓ Kern |
| 524 | `signal: signal` — Signal an `fetch` übergeben | ✓ Kern |
| 534–536 | `if (e && (e.name === "AbortError" \|\| signal.aborted)) { return; }` — AbortError als Nicht-Fehler behandeln | ✓ Kern |

Alle anderen Zeilen (479–480, 482–493, 500–533, 537–545) sind unverändert aus Item #60 übernommen. Keine fremden Zeilen, keine unbeabsichtigten Refactorings, keine Formatierungsänderungen.

**Akzeptanzkriterien aus Nutzersicht:**

1. ✓ Schnelles Durchklicken erzeugt keinen Fehlerhinweis für den abgebrochenen Request.
2. ✓ Der zuletzt gewählte Theme-Wert wird gespeichert (nur der letzte Request läuft durch).
3. ✓ Echte Fehler (Netzwerkfehler, Serverfehler) zeigen weiterhin den Hinweis.
4. ✓ Keine sichtbare Verzögerung beim Theme-Wechsel.

Alle Kriterien erfüllt.

---

## 4. Lücken aus Nutzersicht?

Ich habe drei potenzielle Lücken geprüft:

### a) Theme visuell angewendet, aber nicht gespeichert (Fehlschlag)

`applyTheme()` läuft sofort (Zeile 484), der Save kann aber fehlschlagen. Der Nutzer sieht das neue Theme, das nach Reload verschwindet.

**Bewertung:** Das ist kein neues Problem — es besteht seit Item #60 und wurde vom advocatus (Punkt 8) ausdrücklich als „bewusst außerhalb des Scopes" eingeordnet. Der Fehlerhinweis („Farbthema konnte nicht gespeichert werden") informiert den Nutzer. Ein Nachziehen (Retry-Logik, „Theme zurücksetzen bei Fehlschlag") wäre ein eigenes Item, kein Nachzieh-Punkt für #62.

→ **Bewusst ignorierbar.** Kein Nachzieh-Punkt.

### b) `currentSettings.app_theme = newTheme` vor dem Save (Zeile 500)

Der In-Memory-Wert wird sofort gesetzt. Wenn der Save abgebrochen wird, bleibt `currentSettings` auf dem neuen Wert.

**Bewertung:** Unkritisch. Beim nächsten erfolgreichen Save wird der korrekte Wert geschrieben. Bei einem Reload lädt `loadSettings()` den echten Server-Zustand. Es gibt kein Szenario, in dem ein inkonsistenter `currentSettings`-Wert einen Schaden anrichtet — er wird entweder überschrieben oder beim nächsten Save bestätigt.

→ **Bewusst ignorierbar.** Kein ROADMAP-Eintrag nötig.

### c) `currentSettings` noch nicht geladen beim ersten Theme-Wechsel

Wenn der Nutzer das Dropdown ändert, bevor `loadSettings()` abgeschlossen ist, greift der `if (currentSettings)`-Check (Zeile 493) und der Save unterbleibt still.

**Bewertung:** Bestehendes Verhalten aus Item #60 (advocatus Punkt 6). Kein neues Problem durch #62. Das Dropdown ist im UI Teil des Settings-Panels, das erst nach `loadSettings()` befüllt wird — in der Praxis tritt dieser Fall nicht auf.

→ **Bewusst ignorierbar.** Kein Nachzieh-Punkt.

**Gesamtbewertung der Lücken:** Keine relevante Lücke aus Nutzersicht, die ein Nachziehen oder einen ROADMAP-Eintrag rechtfertigt. Die verbleibenden Punkte aus dem advocatus (`role="alert"` für Accessibility, hartcodierte Farbe statt CSS-Variable) sind separate Items und kein Grund, diese Lösung zurückzuhalten.

---

## 5. Abnahme-Empfehlung

### **Annehmen.**

**Begründung:**

1. **Nutzerbedürfnis erfüllt.** Die Lösung löst exakt das beschriebene Problem: kein Geister-Fehlerhinweis bei schnellen Themenwechseln, letztes Theme wird gespeichert, keine sichtbare Verzögerung.

2. **Scope diszipliniert.** Nur die vier funktionalen Änderungen, die zum Guard gehören. Keine fremden Zeilen, keine versteckten Refactorings. Die Umsetzung ist so schlank wie das Problem es erlaubt.

3. **Aufwand minimal, Risiko gering.** ~10 Zeilen Änderung, keine neuen Abhängigkeiten, etabliertes Pattern. Der AbortController ist die technisch präzisere Lösung gegenüber einem Debounce (kein verzögertes visuelles Feedback).

4. **Tests decken die Kernpfade ab.** Drei neue Tests:
   - Guard bricht ersten Request ab, zweiter läuft durch, kein Fehlerhinweis.
   - AbortError wird still behandelt, kein `console.error`.
   - ROADMAP-Doku-Test sichert die Nachvollziehbarkeit des Items.

5. **Keine nutzerseitigen Lücken.** Die verbleibenden Punkte aus dem advocatus sind separate Items (Accessibility, CSS-Konsistenz) und kein Grund, diese Lösung zurückzuhalten.

**Keine Auflagen.** Die Lösung ist aus Produktsicht merge-fähig.

---

*Hinweis am Rand (nicht Scope von #62):* Die vom advocatus benannten Punkte 3 (`role="alert"` / `aria-live` für Screenreader) und 4 (hartcodierte Farbe `#ef4444` statt CSS-Variable) sind aus Accessibility- und Konsistenzsicht sinnvoll als eigene kleine Items zu tracken. Sie blockieren diese Abnahme nicht.
