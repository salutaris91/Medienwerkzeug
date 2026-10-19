# Zusammenfassung für Alex: Staffel-Schnellauswahl, sichtbare Fehlermeldungen, Such-Timeout (Kette #74 + #80-Rest + #83)

## Was wird gemacht?

- **Etappe 1:** In einer Serien-Gruppe mit mehreren Staffeln erscheint künftig eine Reihe kleiner Knöpfe „Staffel 1 (12)", „Staffel 2 (15)" … — jeder Knopf startet genau diese Staffel. Der bisherige Knopf „Auswählen" heißt neu **„Alle starten"** und startet wie bisher alles. Der Banner-Knopf „Als Serie gruppieren" startet bei Mehrstaffel-Gruppen nicht mehr automatisch, sondern gruppiert nur noch — dazu steht im Banner der neue Hinweis: **„Mehrere Staffeln erkannt – nach dem Gruppieren wählst du in der Liste eine einzelne Staffel oder startest alle."**
- **Etappe 2:** Wenn ein Start fehlschlägt, steht die Fehlermeldung („Serien-Start fehlgeschlagen. Bitte erneut versuchen.") sichtbar in der Gruppenzeile bzw. der unteren Auswahlleiste — bisher passierte im Fehlerfall stumm „nichts".
- **Etappe 3:** Eine feststeckende Serien-Suche wird nach 30 Sekunden abgebrochen mit der Meldung „Suchfehler: Zeitüberschreitung nach 30 Sekunden. Bitte erneut versuchen." — vorher blieb die Anwendung gesperrt, bis die Seite neu geladen wurde.

## Warum?

Die 173-Folgen-/11-Staffeln-Gruppe war praktisch nicht staffelweise verarbeitbar (Einzelklick-Kästen gibt es nach dem Gruppieren nicht mehr), und die beiden bekannten stillen Fehlerstellen haben dich schon einmal (in #77) Zeit gekostet, weil ein Fehler unsichtbar war.

## Risiken in Klartext

- **30 Sekunden können zu kurz sein:** In einem seltenen Extremfall (mehrere Metadendienste hängen gleichzeitig) bricht eine noch legitime Suche ab. Du kannst sie einfach erneut starten — das war der bewusste Kompromiss deiner FP1-Entscheidung.
- **Neues Klick-Verhalten:** Nach dem Gruppieren bei mehreren Staffeln passiert bewusst *erst mal nichts* — der Start kommt einen Klick später aus der Gruppenzeile. Der Hinweis im Banner soll das erklären; falls dich das im Handtest stört, ist das ein späterer Feinschliff.
- **Ein bestehender Test muss mitziehen:** Der Test, der bisher den Namen „Auswählen" festgeschrieben hat, wird auf „Alle starten" umgeschrieben (benannt und begründet im Briefing) — nur der Name, nichts abgeschwächt.
- **Aufwand:** Die Maschine (Gate-A2-Läufe) ist schnell — je Etappe ein Lauf. Der Engpass bist du: Ampel-Prüfung und Browser-Probe macht Claude Code, dich kosten Rückkanal-Lesen und der eine Handtest (ca. 20–30 Min, lokal, vorbereitete Testdaten) Zeit. Ein PR am Ende der ganzen Kette.
- **Stichproben-pflichtige Themen (Geld, Außenwirkung, Recht, Käufe):** keine berührt — reine lokale Oberfläche. Die Rohantworten der Planungsrunden (Produktberater, Designer, Risikoprüfer) archiviert Claude Code mechanisch unter `docs/sessions/2026-10-18-roadmap74-staffel-kette/`, damit du die Dissens-Stellen im Briefing stichproben kannst.

## Offene Fragen an dich

Keine blockierenden. Du entscheidest an FP2 implizit über zwei Wortlaute mit (oben fett): der neue Knopfname **„Alle starten"** und der **Banner-Hinweis** — ändern oder bestätigen. Der Produktberater wollte den Hinweis am liebsten ganz weglassen („Knopfname erklärt es schon"); Designer und Plan empfehlen ihn — ich stimme der Empfehlung zu, weil dein FP1-Satz Verständlichkeit ausdrücklich verlangt.

## Deine Entscheidung

- [ ] Freigabe — weiter zur Ausführung (Etappe 1 als erster Gate-A2-Lauf)
- [ ] Rückfragen — Session geht in eine weitere Runde

## Ergebnis Freigabepunkt 2 (nachgetragen von Claude Code)

Alex, wörtlich 2026-10-19: „FP2: Briefing freigegeben mit „Alle verarbeiten“ und Banner-Hinweis „Diese Serie hat mehrere Staffeln – nach dem Gruppieren kannst du in der Liste eine einzelne Staffel oder alle Folgen verarbeiten.“ Starte AK0 und E1.“ — Die oben genannten Wortlaute „Alle starten“ und „Mehrere Staffeln erkannt – …“ sind damit ersetzt.
