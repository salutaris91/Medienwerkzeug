<!-- Mechanisch aus `opencode export ses_eafa2bc8fffel14nUWS1ha77LV` extrahiert (Claude Code, 2026-10-18): alle Assistant-Textteile in Reihenfolge, ungekürzt, unverändert (nur Trailing Whitespace entfernt). Rohdatei: Kit-Worktree clever-mclaren-94c19f scripts/gate-a2/logs/2026-10-18-roadmap74-kette/akt2/export-produktberater-eafa2bc8fffe.json -->

Ich lese zunächst die relevanten Code-Abschnitte, um meine Einschätzung am echten Stand zu verankern.



Jetzt habe ich den vollständigen Code-Stand. Hier meine strukturierte Einschätzung.

---

## 1. Bedienfluss nach F1 — „Knopf gedrückt, nichts passiert"

**Zwei Flüsse, ein Kontext:** Der Banner-Knopf heißt in beiden Fällen „Als Serie gruppieren", verhält sich aber unterschiedlich:

| Fall | Banner-Klick | Danach |
|------|-------------|--------|
| 1 Staffel | Startet sofort (bisheriges Verhalten) | Serie läuft |
| ≥2 Staffeln | Nur registrieren + neu rendern | Gruppenzeile erscheint mit Staffel-Knöpfen → manuell starten |

**Drei Verwirrungsstellen:**

1. **„Nichts passiert"-Effekt:** Der Nutzer kennt aus dem 1-Staffel-Fall: Klick → Banner weg → Serie läuft. Bei ≥2 Staffeln verschwindet der Banner, die Gruppenzeile taucht auf — aber es läuft nichts. Ohne Erklärung denkt der Nutzer „kaputt" oder „hat nicht reagiert".

2. **Implizite Regel „1 vs. ≥2":** Der Nutzer muss nicht wissen, wie viele Staffeln die Gruppe hat — er sieht es aber an der Reaktion. Wenn der Banner bei 1 Staffel sofort startet und bei 2 Staffeln nicht, ist das inkonsistent aus Nutzersicht. Die Regel „ab 2 Staffeln ist die Auswahl absichtlich" muss im UI-Moment sichtbar werden.

3. **Gruppenzeile als zweiter Schritt:** Die Gruppenzeile ist neu als *Start*-Ort etabliert. Bisher war sie nur Info. Der Nutzer muss lernen: Staffel-Knopf = Start dieser Staffel. Das ist nur dann selbsterklärend, wenn die Knöpfe wie *Aktion* aussehen, nicht wie *Label*.

**Was der Banner-Hinweis leisten muss (grobe Richtung, Wortlaut ist Sache des grafikers):**

- **Unmittelbar nach dem Klick** bei ≥2 Staffeln: ein kurzer Hinweistext unterhalb der erscheinenden Gruppenzeile, der sagt „Staffeln einzeln oder alle starten". Keine lange Erklärung, ein Satz.
- **Präventiv im Banner-Text selbst:** Der Banner-Content-Zeile (:12691) könnte man bei ≥2 Staffeln einen Halbsatz anhängen wie „(Staffelauswahl möglich)" — das setzt die Erwartung *vor* dem Klick.
- **Visueller Hinweis:** Die Staffel-Knöpfe in der Gruppenzeile müssen klar als *klickbare Aktion* erkennbar sein (Button-Stil, nicht Badge-Stil). Sonst sieht der Nutzer „Staffel 1 (12), Staffel 2 (14) …" und denkt, es sind Info-Badges.

**Empfehlung:** Der Banner-Text selbst braucht keine Änderung — „Als Serie gruppieren" ist korrekt für beide Fälle. Der Zusatz-Hinweis kommt als *einzeiliger Hinweistext* unter der Gruppenzeile (nur beim ersten Rendern nach dem Banner-Klick, nicht dauerhaft). Das ist die einfachste Lösung und vermeidet Sonderlogik im Banner.

---

## 2. Wortlaut-Vorschläge

### 2a) Staffel-Knöpfe

**Empfehlung:** `"Staffel 1 (12 Folgen)"` — mit ausgeschrieben „Folgen".

**Begründung gegen Alternative:**
- `"Staffel 1 (12)"` — die Zahl ohne Einheit ist mehrdeutig. Könnte Dateigröße, Sekunden, irgendetwas sein. In der Inbox sind zwar primär Folgen gemeint, aber „12 Folgen" ist explizit und kostet nur 6 Zeichen.
- `"S1 (12)"` — zu technisch, passt nicht zum restlichen UI (das „Serie (Gruppe)" schreibt auch „Serie" aus).
- `"Staffel 1 · 12 Folgen"` — der Mittelpunkt als Trenner ist uneinheitlich zum bestehenden `·`-Trenner in den Meta-Segmenten (:1275/:1283), der *zwischen* verschiedenen Meta-Arten steht. Innerhalb eines Knopfs wäre ein Leerzeichen + Klammer natürlicher.

**UTF-8-konkret:** `Staffel 1 (12 Folgen)` — keine Sonderzeichen, reine ASCII-Klammer, UTF-8 nur für Umlaute falls der Serienname welche enthält (der Knopf-Label selbst ist deutsch-ASCII).

### 2b) Umbenannter Alle-Knopf (bisher „Auswählen", :13302)

**Empfehlung (genau ein Wortlaut):** `"Alle starten"`

**Begründung:**
- `"Alle Staffeln starten"` — präziser, aber 18 Zeichen vs. 12. In der Gruppenzeile mit 11 Staffel-Knöpfen + diesem Knopf ist Platz knapp. „Alle" ist in Kontext der Gruppenzeile eindeutig — es kann sich nur auf Folgen/Staffeln beziehen.
- `"Alle Folgen starten"` — 17 Zeichen, „Folgen" ist redundant (was sonst startet in einer Serien-Gruppenzeile?).
- `"Als Serie starten"` — mehrdeutig mit dem Banner-„Als Serie gruppieren".
- **Warum nicht „Auswählen" beibehalten?** Der bisherige Name suggeriert „markieren, dann weiterbestätigen". Tatsächlich startet der Knopf aber sofort den kompletten Workflow. „Alle starten" bildet das echte Verhalten ab — kein zweistufiger Flow, sondern ein Klick = Start.

### 2c) Fehlermeldung Gruppenzeile + Bulk-Leiste

**Empfehlung:** Identischer Wortlaut zur Banner-Meldung: `"Serien-Start fehlgeschlagen. Bitte erneut versuchen."`

**Begründung:**
- **Einheitlichkeit schlägt Ort-Info.** Drei verschiedene Fehlermeldungen für denselben Fehler (Workflow-Start gescheitert) wären drei Texte, die Alex pflegen muss und die der Nutzer unterschiedlich interpretiert. Der Fehler ist derselbe, egal ob er aus dem Banner, der Gruppenzeile oder der Bulk-Leiste kommt.
- **Ort-Info ist visuell bereits vorhanden:** Die Meldung erscheint *in* der Gruppenzeile bzw. *in* der Bulk-Leiste — der Nutzer sieht am Ort, wo der Fehler auftrat. Ein zusätzlicher Text-Hinweis „(Gruppenzeile)" wäre redundant.
- **Bulk-Leiste-Sonderfall:** Die Bulk-Leiste hat kein Banner-Element. Empfehlung: Fehler als `alert()` (einfachster Weg, passt zum bestehenden Muster der „Eintrag nicht mehr in der Inbox"-Meldung :12970/:12982). Gruppenzeile: Inline-Text unter dem Knopf (gleicher Stil wie Banner-Fehler, `role=alert`).
- **`console.error`** zusätzlich an allen drei Stellen (existiert bereits im Banner :12851, muss in Gruppenzeile :13369 und Bulk-Leiste :12992 ergänzt werden).

### 2d) E3-Timeout-Meldung im Suchbereich

Bestehende Form (:3212): `"Suchfehler: ${e.message}"`

**Empfehlung — exakter Wortlaut:**

```
Suchfehler: Zeitüberschreitung nach 30 Sekunden. Bitte erneut versuchen.
```

**Begründung:**
- **„30 Sekunden"** — der Nutzer soll wissen, dass es ein Timeout war und wie lange er gewartet hat. Sonst sieht er nur „Suchfehler" und denkt, die Suche sei kaputt.
- **„Bitte erneut versuchen"** — Handlungsaufforderung, identisch zum Rest der Fehler-Sprache (Banner: „Bitte erneut versuchen.").
- **Kein technischer Jargon** wie „AbortError" oder „fetch timeout" — der Nutzer ist Alex als Einzelnutzer, aber die Meldung folgt dem bestehenden Muster („Suchfehler:" als Präfix).
- **Implementierung:** Der Timeout wird über `AbortController` mit `setTimeout(abort, 30000)` realisiert. Im Catch-Block wird `e.name === 'AbortError'` unterschieden: wenn der *eigene* Timeout-Abort (nicht der Query-Wechsel-Abort von :3085–3087), dann die Timeout-Meldung statt des stillen Returns.

---

## 3. Verhalten bei 11 Staffeln

**Empfehlung:** Umbrechende Reihe (`flex-wrap: wrap`), keine Obergrenze, kein Dropdown.

**Begründung:**
- 11 Staffel-Knöpfe + 1 „Alle starten"-Knopf = 12 Knöpfe. Bei `btn-xs`/`btn-sm` und kompaktem Padding (6–10px horizontal) passt das in 2–3 Zeilen.
- **Kein Dropdown/„mehr"-Button:** Das wäre ein zweites Aufklapp-System neben dem bestehenden Banner-Aufklappen. Over-Engineering für einen Fall, der bei Alex als Einzelnutzer vielleicht 1× pro Woche vorkommt.
- **Keine Obergrenze:** Wenn man bei 11 aufhört und „+3 weitere" zeigt, muss der Nutzer zweimal klicken, um Staffel 14 zu starten. Das Gegenteil des Ziels (Schnellauswahl).
- **CSS-Minimallösung:** Die Header-Div der Gruppenzeile hat bereits `flex-wrap: wrap` (:13292). Die Staffel-Knöpfe kommen als eigene Flex-Zone zwischen Header und Members-Div, ebenfalls mit `flex-wrap: wrap; gap: 6px`. Fertig.

**Einzige Einschränkung:** Bei extrem vielen Staffeln (20+) wird die Zeile lang. Aber das ist bei Alex' realem Bestand (11 Staffeln als Maximum bekannt) kein Thema. Falls es je vorkommt, reicht immer noch `flex-wrap`.

---

## 4. Scoping-Kritik

### Wo die Kette angemessen ist

- **E2 (#80-Rest):** Minimaler Scope, maximaler Nutzen. Stille Catch-Blöcke sind ein echtes Problem (siehe #77-Befund). Zwei Stellen (Gruppenzeile :13369, Bulk-Leiste :12992), je ein `console.error` + eine Fehlermeldung. Kein Design-Risiko, keine neuen Konzepte. **MVP = voller Scope.**

- **E3 (#83):** 30s-Timeout via `AbortController` + `setTimeout`. Eine Stelle in `searchSeries` (:3088), ein neuer Catch-Zweig für `AbortError` (Timeout vs. Query-Wechsel). **MVP = voller Scope.**

### Wo ich zur Vereinfachung rate

**E1 (#74) — der Banner-Verhaltenswechsel (F1):**

Alex hat F1 bereits entschieden („ja"). Ich lege trotzdem ein **partielles Veto** ein — nicht gegen die Entscheidung, sondern gegen den Umfang der Umsetzung:

**MVP-Vorschlag für E1, der F1 einfacher umsetzt:**

Der Banner-Knopf „Als Serie gruppieren" macht bei ≥2 Staffeln *genau das, was er heute tut* — `appliedInboxGroups.add`, re-render, `console.error` im Fehlerfall — nur **ohne** `startSeriesGroupWorkflow` aufzurufen. Das ist im bestehenden Handler (:12843–12848) eine einzige `if`-Abfrage:

```
if (seasonCount >= 2) {
    // nur registrieren, nicht starten
} else {
    await startSeriesGroupWorkflow(groupKey, files);
}
```

Das ist die Minimalversion von F1. Kein neuer Text im Banner, kein Hinweistext unter der Gruppenzeile — nur das *Unterbleiben* des Starts. Die Gruppenzeile erscheint durch das Re-Render (wie heute), und darin stehen die Staffel-Knöpfe + „Alle starten".

**Was ich NICHT mitliefern würde:**

1. **Kein separater Hinweistext „Staffeln einzeln starten" unter der Gruppenzeile.** Der Banner-Knopf heißt „Als Serie gruppieren" — wenn danach kein Start passiert, ist das im Wortlaut korrekt. Der Nutzer sieht die Gruppenzeile mit den Staffel-Knöpfen und *kann* selbst schließen, dass er jetzt dort weitermacht. Falls sich im Handtest zeigt, dass es Verwirrung gibt, kann der Hinweis als Kette #82+ nachgereicht werden.

2. **Keine Sonderbehandlung des Banner-Texts bei ≥2 Staffeln.** Kein „(Staffelauswahl möglich)" oder ähnliches. Der Banner-Text bleibt „Als Serie gruppieren: {Name} ({n} Folgen, {seasons})" — die `seasons`-Anzeige (`formatGroupSeasonsLabel`, :12643) zeigt bereits „Staffeln 1, 2, … 11" an. Das ist Hinweis genug.

3. **Kein „K2 — Rest der Gruppe auswählen"** (aus :1261 erwähnt). Das ist ein eigener Punkt für später.

### Zusammenfassung: MVP je Etappe

| Etappe | MVP | Was weglassen |
|--------|-----|---------------|
| E1 (#74) | Staffel-Knöpfe in Gruppenzeile + „Alle starten" statt „Auswählen"; Banner bei ≥2 Staffeln nur gruppieren, nicht starten | Hinweistext unter Gruppenzeile; Banner-Text-Sonderfall; K2 „Rest auswählen" |
| E2 (#80-Rest) | `console.error` + sichtbare Meldung an beiden Stellen (Gruppenzeile inline, Bulk-Leiste `alert()`), identischer Wortlaut | Ortsspezifische Meldungen; Fehlerklassifikation |
| E3 (#83) | 30s-Timeout via `setTimeout` + `AbortController`; Timeout-Abort zeigt „Zeitüberschreitung nach 30 Sekunden. Bitte erneut versuchen." | Watchdog mit Sperren-Freigabe (komplexer, weniger präzise); konfigurierbare Timeout-Dauer |

### Was Alex besser NICHT mitliefern sollte

- **Konfigurierbare Timeout-Dauer** (E3): 30 Sekunden sind ein fester Wert. Ein Settings-Feld dafür ist Flexibilität ohne Nachfrage.
- **Fehlerklassifikation nach HTTP-Status** (E2): Ein 500er und ein 503er sind für Alex als Einzelnutzer derselbe Fehler — „fehlgeschlagen, erneut versuchen". Keine Aufspaltung nach Fehlercodes.
- **Staffel-Knopf-Layout-Experimente** (E1): Kein Dropdown, kein „mehr anzeigen", keine horizontale Scrollbar. `flex-wrap: wrap` reicht.
