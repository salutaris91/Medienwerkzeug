<!-- Mechanisch aus `opencode export ses_eaf93c1b1ffe7ilRhzwz0Zjm55` extrahiert (Claude Code, 2026-10-18): alle Assistant-Textteile in Reihenfolge, ungekürzt, unverändert (nur Trailing Whitespace entfernt). Rohdatei: Kit-Worktree clever-mclaren-94c19f scripts/gate-a2/logs/2026-10-18-roadmap74-kette/akt2/export-plan-reviewer-eaf93c1b1ffe.json -->

Ich beginne die formelle Planprüfung. Zuerst lese ich das Prüfobjekt und die bindenden Bezugsdokumente.

Struktur und Kickoff sind erfasst. Jetzt verifiziere ich die Bezugsdokumente und die reale Code-Realität. Zuerst das Präzedenz-Briefing (test_cmd-Identität) und die ersten app.js-Bereiche.

test_cmd ist identisch zur Referenz (Zeile 194 des Präzedenz-Briefings = Zeile 180 des Prüfobjekts, wörtlich). Modul-States :12471–12482, `inboxFilesEntryForItem` :12499–12505 und Sortierung :12567–12570/:12581 sind verifiziert. Jetzt die Handler- und Render-Bereiche.

Banner-Handler :12834–12857, Bulk-Handler :12928–12998 (still catch :12992–12997, alert :12970/:12982–12984, „Auswahl aufheben" :12918–12927) und Bulk-Template :12909–12917 sind zeilengenau verifiziert. Weiter mit `startSeriesGroupWorkflow`-Top, Workflow-Ende und der Gruppenzeile.

Workflow-Ende :13184–13185 und Zuordnungstabelle :13163/:13171 bestätigt. Jetzt die Gruppenzeile und `searchSeries`.

Gruppenzeile :13271–13379 (Knopf „Auswählen" :13302, Handler :13357–13375, stiller catch :13369–13374) und `searchSeries` :3079–3214 (Registry :3085–3088, Guards :3114/:3211, AbortError :3210, Suchfehler :3212, scrollIntoView-Timer :3194/:3201) sind zeilengenau bestätigt. Jetzt die übrigen app.js-Stellen.

`:556`, `:245`, `:2521`, `:7564/:7566` bestätigt. Jetzt Export-Block, Checkbox-Label, app.js-Importe und die weiteren `searchSeries`-Aufrufer.

Export-Block :13533–13559 (nur `globalThis.X = X`), Checkbox-Label :13428, neun Importe `app.js:1–9` mit `?v=103` und die sechs `searchSeries`-Aufrufer (:2989/:3017/:3069/:7564/:7566/:13185) sind bestätigt. Jetzt cache_busting-Test, index.html und style.css.

cache_busting.test.js (:13–48 Konsistenz-Zwang, :50–64 nur Nicht-Leere), index.html:9 (`style.css?v=51`), :2760 (`app.js?v=103`) und style.css:3977 (unscopierte Fehlerklasse) sind bestätigt — der 10-Stellen-Sprung ist zwingend korrekt, da der Test Versionsidentität erzwingt. Jetzt die drei Testdateien.

Harness-Struktur inbox_group.test.js bestätigt (Sofort-Stub :536, Präambel-Binding :564, Export-Anhang :583–618, Getter :608). Jetzt die Bestandstests :1348–1366, F2-Labeltest :1407–1448 und :1630–1673.

F2-Labeltest :1407–1448 (Assertion :1447, Negativ-Assertion :1448) und Klick-Bestandstest :1348–1366/:1630–1673 sind exakt bestätigt. Jetzt inbox_group_banner.test.js.

Banner-Test-Verifikation: validateSelector :55–93, Injektionsweg :52/:551/:1100, Sofort-Stub :644, Einzelstaffel-Fixtures :741–748/:1058–1061 — alle bestätigt. Jetzt prüfe ich, ob wirklich KEINE Mehrstaffel-Fixtures in den Banner-Tests existieren (E1-AK6-Behauptung), plus inbox_selection.test.js und das Session-Verzeichnis.

Wichtiger Befund: Das Session-Verzeichnis enthält NUR `00-kickoff.md` und `briefing.md` — keine Subagenten-Rohoutputs, obwohl das Briefing extensively [produktberater]/[grafiker]/[advocatus]-Findings zitiert. Ich prüfe das Präzedenz-Verzeichnis zum Vergleich und die mögliche Mehrstaffel-Stelle :729 in inbox_group.test.js.

Das #75-Präzedenz-Verzeichnis enthält alle Rollen-Rohoutputs (produktberater.md, grafiker.md, advocatus.md, plan-reviewer.md, ALEX_ZUSAMMENFASSUNG.md) — das 2026-10-18-Verzeichnis enthält KEINE davon, obwohl das Briefing sie zitiert bzw. auf ALEX_ZUSAMMENFASSUNG.md verweist. Der Test :710–753 ist ein reiner Datenstruktur-Test (kein UI-Render, kein Banner) — unproblematisch für E1. Jetzt ROADMAP.md und die Server-Stellen.

ROADMAP-Referenzen (:2045–2065, :2057, :2170–2183, :2217–2228, :2268–2269, :1986) sind alle zeilengenau bestätigt. Jetzt die letzten Verifikationen: Rest des #75-Referenz-Briefings (Rohausgaben-Muster), setTimeout-Delays in app.js (Queue-Tragfähigkeit), mw_metadata.py und das sessions-Verzeichnis.

Das sessions-Verzeichnis bestätigt: Für 2026-10-18 existieren keine Akt-2-Rohoutputs (Rollen-Dateien) und keine ALEX_ZUSAMMENFASSUNG.md — anders als im #75-Präzedenz. Jetzt prüfe ich den longWaitTimer :9314 (Queue-Tragfähigkeit bei Delay ≥ 30000) und den Rest des #75-Abschnitts 11 (Rohausgaben-Muster).

Die Delay-Schwelle ist tragfähig (longWaitTimer :9314 = 8000 ms < 30000; alle app.js-Timer-Verwendungen in den vier Testdateien-Flows liegen deutlich darunter), und die Rohausgaben-Liste entspricht dem #75-Muster (:376) inkl. sinnvoller Etappen-Erweiterung. Letzte Verifikation: mw_metadata.py-Kontext.

# Formelle Planprüfung (Runde 1) — briefing.md der Kette #74/#80-Rest/#83

## Verifizierte Bestätigungen (Eigenprüfung gegen Code und Bezugsdokumente)

**A. Struktur-/Formvertrag — vollständig erfüllt:**
- Frontmatter korrekt: `status: draft`, `source: roadmap#74,#80,#83`, `approval_quote`/`approved_on` Platzhalter — keine erfundene Freigabe (ADR-0002-Vertrag erfüllt).
- 12 Abschnitte in korrekter Folge; „## Etappen" steht direkt nach Abschnitt 3. AK0 + E1-/E2-/E3-Präfixe, alle AKs als „Es prüft, dass …" formuliert; die komplette Mindestliste des Akt-2-Auftrags (E1-AK1–AK9, E2-AK1–AK7, E3-AK1–AK5, ALL-AK1–AK3) ist abgedeckt.
- **test_cmd byte-identisch** zur Referenz (2026-10-16-Briefing :194 = Prüfobjekt :180), ohne eigenes `timeout`, `test_timeout_s` 600 benannt.
- Rohausgaben-Liste (:288–299) entspricht dem #75-Muster (:376: git status/log/diff --stat/diff --check, pytest- + npm-Vollausgaben mit Exit, diff --stat je Commit) und ist um Etappen-Rot-Probe + E3-GRÜN-Nachweis sinnvoll erweitert.
- Ampel-Regeln ausschließlich als Verweis auf Kit-Betriebsanleitung §9 (Etappen-Abschnitt :66, Freigabepfad :305) — korrekt.
- FP1-Zitat (:16) und Plan-Go-Zitat (:14) **wörtlich identisch** mit den bindenden Vorgaben; keine Agenten-Entscheidung über Freigabepunkte (Wortlaute korrekt an FP2 delegiert, Abschnitt 8).

**B. Code-Treue — alle ~60 gestichprobenen Zeilenangaben stimmen:** Banner-Handler :12834–12857 (einziger `appliedInboxGroups`-Schreiber :12845, Rücknahme :12850, finally :12855, atomares Prüfen+Setzen :12835→:12838); Gruppenzeile :13271–13379 („Auswählen" :13302, Handler :13357–13375, stiller catch :13369–13374, rechter Block :13300); Sortierung :12567–12570/:12581; `inboxFilesEntryForItem` :12499–12505; `searchSeries` :3079–3214 (Registry :3076/:3085–3088, Guards :3114/:3211, AbortError still :3210, Suchfehler :3212, scrollIntoView-Timer :3194/:3201); Export-Block :13533–13559 (nur `globalThis.X = X`); 6-s-Takt :556→:13234/:13265; `escapeHTML` :245; „Auswählen" normaler Einträge :2521; Checkbox-Label :13428; :7564/:7566; **sechs** `searchSeries`-Aufrufer (:2989/:3017/:3069/:7564/:7566/:13185 — B7-korrigiert korrekt); F2-Labeltest :1407–1448 (Assertion :1447, Negativ-Assertion :1448 — E1-AK9-Anpassung passt exakt); Klick-Bestand :1348–1366/:1630–1673; Sofort-Stubs :536/:644/:557; validateSelector :55–93/:20–58; Präambel-Bindings :564/:585; Injektionsweg :52/:551/:1100; **Einzelstaffel-Behauptung der Banner-Fixtures bestätigt** (:741–748, :1058–1061; grep über alle Testdateien: keine Mehrstaffel-Banner-Fixtures; der einzige Mehrstaffel-Fall :710–753 ist ein reiner Datenstruktur-Test ohne UI-Render); lockerer Mock :21–62/:349–352; cache_busting :13–48 (Konsistenz-Zwang — deshalb sind die **10 Stellen** = index.html:2760 + 9 Importe app.js:1–9 zwingend und korrekt) /:50–64; index.html:9 `v=51`/:2760 `v=103`; style.css:3977 unscopiert; mw_metadata.py :323/:122–150 (`timeout=15, attempts=3`); ROADMAP :1986/:2045–2065/:2057/:2170–2183/:2217–2228/:2268–2269.

**C. Technische Tragfähigkeit — tragfähig, mit einer Lücke (Finding 3):**
- E1-AK6-Nachweis ohne globales Binding-Überschreiben tragfähig (Ansichtswechsel-Bestandstest-Muster + `activeSeriesGroupFiles`-Getter über Harness-Anhang; Symbol existiert im Basis-Stand :12481 — konsistent mit „Harness-Anhang nur für im Basis-Stand existierende Symbole").
- E2-Injektionsweg: Präambel-Binding-Risiko in der neuen E1-Datei ist erkannt und als E2-Abbruchkriterium abgesichert — sauber.
- Kein Widerspruch Sofort-Stub (E1/E2) vs. Queue (E3): Reihenfolge E1→E2→E3 + R1 decken es; Rot-Probe-Regel („keine neuen globalen Symbole **aus app.js**") kollidiert nicht mit dem testseitigen Harness-Anhang.
- advocatus-Maßnahmen widerspruchsfrei eingearbeitet: atomares Prüfen+Setzen, lokaler Controller bei bleibender Ablöse-Registry, Seq-Guard (schließt die reale String-Guard-Lücke bei identischem Query — verifiziert: `lastSearchSeriesQuery` :3077/:3114/:3211), Delay-Schwelle ≥ 30000 (verifiziert: alle app.js-Timer in betroffenen Flows liegen darunter, longWaitTimer :9314 = 8000), finally-Vorrang, Timeout-Callback rendert/wirft nicht.
- E3-AK2-Szenario (A's Timer nach B's Start) durch Seq-Guard korrekt abgedeckt.

**D. Scope-/Regeltreue:** Nicht-anfassen-Liste vollständig (inkl. `pytest.ini`, `data/**` über Auftrag hinaus); höchstens eine neue Testdatei je Etappe (E1: seasons, E2: keine, E3: timeout); Lizenz-Abschnitt vorhanden und gepflegt (kein Third-Party, Lucide-ISC, „unklare Lizenzen: keine"); Aufwand KI vs. Engpass getrennt; Handtest lokal (S5), nach Etappen gegliedert, Testdaten-Aufbereitung inkl. `&`/`"`-Namen und `single_video_relpath`-Staffel, 6-s-Wartepflicht.

**E. Konsistenz:** v104/v=51/v=52, 10 Stellen, 30 000 ms, Klassennamen, Frontmatter-Muster, Etappen-AK-Referenzen — durchgängig konsistent. UI-Texte: 4 von 5 Tabellentexten durch AKs exakt geprüft — der Banner-Hinweis fehlt (Finding 3).

## Findings

1. **[wichtig] Akt-2-Subagenten-Rohoutputs fehlen vollständig — Dissens-Dokumentation unbelegbar, vorgeschriebene Gegenprüfung blockiert.** `docs/sessions/2026-10-18-roadmap74-staffel-kette/` enthält nur `00-kickoff.md` + `briefing.md`; die Rollen-Dateien ([produktberater]/[grafiker]/[advocatus]) existieren nicht — anders als im #75-Präzedenz (dort 12 Dateien inkl. aller Rollen-Outputs, und das #75-Briefing dokumentierte in Abschnitt 6 den IOU-Mechanismus: „Alle Rollenzitate … erst mit den archivierten Rohoutputs voll belegbar"). Das Briefing zitiert ~16 nummerierte advocatus-Findings (F1.1–F9.3) sowie produktberater/grafiker-Positionen (briefing.md:136–144) — alle aktuell unbelegbar. Die Prüfung „wurden wesentliche Einwände ignoriert, verfälscht oder gingen sie verloren" ist damit **nicht durchführbar**; die Belege der Akt-2-Konsultation gingen (bislang) verloren. Vor FP2 zwingend: Rohoutputs archivieren (Pflicht-Update, Klasse A) **oder** IOU-Vermerk ins Briefing aufnehmen. Alex darf bei FP2 nicht auf eine unbelegte Dissens-Dokumentation entscheiden.
2. **[wichtig] Toter Verweis auf `ALEX_ZUSAMMENFASSUNG.md`.** Abschnitt 8 (briefing.md:164) referenziert sie im Präsens („beide sind in der ALEX_ZUSAMMENFASSUNG ausdrücklich genannt"), die Datei existiert im Session-Ordner nicht — obwohl sie Alex' FP2-Grundlage ist (Kickoff :101: „… + ALEX_ZUSAMMENFASSUNG.md + plan-reviewer, dann Freigabepunkt 2"). Vor FP2 erstellen und sicherstellen, dass beide Wortlaute („Alle starten", Banner-Hinweis) darin tatsächlich genannt sind, oder den Verweis als ausstehend kennzeichnen.
3. **[wichtig] ADR-K-2-Konsequenz für den Banner-Hinweis ohne AK-Abdeckung.** ADR-K-2 (briefing.md:108) verlangt: „Tests prüfen jeden Tabellen-Text mindestens einmal exakt." Geprüft werden: „Alle starten" (E1-AK1), „Staffel N (k)" (E1-AK1), E2-Fehlermeldung (E2-AK1), E3-Fristmeldung (E3-AK1) — der Banner-Hinweis (Tabelle :101, ein FP2-freizugebender Wortlaut mit Gedankenstrich U+2013) wird von **keinem** AK exakt assertiert (E1-AK6 prüft nur Verhalten, nicht den Text). Entweder E1-AK6 um eine exakte Hinweistext-Assertion ergänzen oder die ADR-K-2-Konsequenz ausdrücklich auf die vier getesteten Texte einschränken.
4. **[kosmetisch] E3-AK1 setzt einen abort-sensitiven fetch-Spy voraus, ohne es zu sagen.** „`fetch` nie auflöst" + „signal-Abbruch am fetch-Spy" + „sichtbare Meldung" + „Sperre frei" (briefing.md:55) ist nur erfüllbar, wenn der Spy bei `signal`-abort mit `AbortError` **rejected** (Browser-treu); ein abort-blind gebauter Spy lässt Meldung und Sperre-Frei unerreichbar. Klarstellung im E3-Worker-Text wünschenswert; die AK-Kombination determiniert den Weg faktisch, und Rot-/Grün-Beleg + Ampel-Prüfung fangen Fehlbuilds.

## Potenziale-Block (keine Bedingungen, nur Anregungen)

- Die Fake-Timer-Queue (E3) könnte künftig auch den Debounce-Pfad (:259) testbar machen — nicht Teil dieser Kette.
- Die String-Guard-Lücke bei identischem Query (F3.3) existiert analog für den Spinner-Überbau — Seq-Guard deckt die Frist-Meldung; B's Spinner wird von B selbst verwaltet, kein Handlungsbedarf.
- #86 F-D-Altschuld (Banner-Index-Bindung :12820/:12830/:12861) bleibt korrekt als ROADMAP-Notiz (:2269) referenziert und unangetastet — bei einem künftigen Banner-Umbau direkt binden.
- E1-AK9 deckt die Testnamens-Anpassung (:1407 enthält „Auswählen" wörtlich) bereits ab — bei der Umsetzung daran erinnern, dass der Name nicht länger „Auswählen" behaupten darf.

## Nicht geprüft (Werkzeug-/Grenzen)

- **Git-Zustand** (Branch `feat/roadmap-74-staffel-schnellauswahl` auf `origin/main` `d011499`, clean): vom Kickoff/Claude Code ausgeführt und wörtlich übernommen; ohne bash nicht selbst verifizierbar.
- **test_cmd-Ausführbarkeit** (pip/pytest/npm): nicht ausgeführt (Review-Modus, kein bash).
- **Kit-Betriebsanleitung §9** (Ampel-Regeln): liegt im Kit außerhalb des Worktrees — nur Verweis-Korrektheit geprüft.
- **Inhaltliche Übereinstimmung der Rollenzitate mit den Akt-2-Originalen**: mangels Rohoutputs unmöglich (Finding 1).
- **ALEX_ZUSAMMENFASSUNG-Inhalt**: Datei fehlt (Finding 2).

## Urteil

Die Briefing-Substanz ist außergewöhnlich präzise: Struktur, Code-Treue (alle gestichprobenen Zeilenangaben korrekt), Tragfähigkeit der AKs, Scope- und Regeltreue sowie Konsistenz sind nahezu fehlerfrei. Blockierend sind allein die Beleg- und Entscheidungsgrundlagen für FP2: die nie archivierten Akt-2-Subagenten-Belege (inkl. fehlendem IOU-Vermerk entgegen dem #75-Präzedenz-Format), der Verweis auf eine nicht existierende ALEX_ZUSAMMENFASSUNG und der nicht testabgedeckte FP2-Wortlaut (Banner-Hinweis). Alle drei Punkte sind eng behebbar, bevor Alex Freigabepunkt 2 beantwortet.

VERDICT: REVISE

1. [wichtig] Akt-2-Subagenten-Rohoutputs fehlen im Session-Ordner (nur `00-kickoff.md`, `briefing.md`); das Briefing zitiert [advocatus] F1.1–F9.3, [produktberater], [grafiker] ohne Beleg und ohne IOU-Vermerk (Präzedenz #75: Rollen-Dateien + IOU in Abschnitt 6) — die vorgeschriebene Prüfung gegen Rohoutputs ist unmöglich, die Dissens-Dokumentation damit unbelegbar (briefing.md:136–144; docs/sessions/2026-10-18-roadmap74-staffel-kette/).
2. [wichtig] Toter Verweis auf `ALEX_ZUSAMMENFASSUNG.md` — Abschnitt 8 behandelt sie als existent („beide sind in der ALEX_ZUSAMMENFASSUNG ausdrücklich genannt"), die Datei fehlt; sie ist Alex' FP2-Grundlage (briefing.md:164; Kickoff :101).
3. [wichtig] ADR-K-2-Konsequenz „Tests prüfen jeden Tabellen-Text mindestens einmal exakt" ist für den Banner-Hinweis von keinem AK abgedeckt (E1-AK1/E2-AK1/E3-AK1 decken die vier übrigen Texte; E1-AK6 prüft nur Verhalten) — FP2-Wortlaut ohne automatisierte Exakt-Prüfung (briefing.md:101, :108, :44).
4. [kosmetisch] E3-AK1 impliziert, aber nennt nicht, dass der fetch-Spy bei `signal`-abort mit `AbortError` rejecten muss — sonst sind Meldung und Sperre-Frei unerreichbar (briefing.md:55).

Ich verifiziere die vier Einarbeitungen. Zuerst lese ich das aktualisierte Briefing vollständig, um Edits und eventuelle neue Inkonsistenzen zu prüfen.

Ich lese den Rest der Datei, um die Vollständigkeit der Prüfung sicherzustellen.

# Formelle Planprüfung (Runde 2) — Verifikation der vier Einarbeitungen

## 1. Verifikation der Einarbeitungen (jeweils eigenständig geprüft)

**Finding 1 [wichtig] — Beleg-IOU: eingearbeitet und formell tragfähig.** Neuer Absatz „**Beleg-IOU (Präzedenz #75, Abschnitt 6):**" steht korrekt direkt zu Beginn von Abschnitt 6 (briefing.md:136, vor „Dokumentierter Dissens" :138). Er genügt dem #75-Präzedenz-Mechanismus (Referenz :152: mechanische Archivierung per `opencode export` durch Claude Code, Ziel Session-Ordner, Vorbehalt vor FP2): Verantwortlicher (Claude Code), Mechanismus (`opencode export`), Zielort (`docs/sessions/2026-10-18-roadmap74-staffel-kette/`), Frist („vor Freigabepunkt 2") und Alex' Stichprobenrecht sind alle benannt — äquivalent zum #75-Satz „Alle Rollenzitate … erst mit den archivierten Rohoutputs voll belegbar". Die Begründungskette macht den Beleganspruch tragfähig: Gerade dass der Orchestrator die Rohoutputs **nicht selbst abschreibt**, sondern Claude Code sie **mechanisch** archiviert, schützt vor Filterung/Verfälschung durch den Zitierenden — das ist der Kern des #75-Mechanismus. Damit ist der Formvertrag erfüllt; die physische Archivierung bleibt eine nachvollziehbare, im Briefing selbst verankerte Vor-FP2-Pflicht.

**Finding 2 [wichtig] — ALEX_ZUSAMMENFASSUNG-Verweis: geklärt, kein Widerspruch zur Kickoff-Reihenfolge.** Abschnitt 8 (briefing.md:166) formuliert jetzt: „diese Datei wird nach dem plan-reviewer-APPROVE und VOR FP2 erstellt". Kickoff :101 („… technisches Briefing … + `ALEX_ZUSAMMENFASSUNG.md` + plan-reviewer, dann Freigabepunkt 2") ist eine **Artefakt-Aufzählung** mit der verbindlichen Aussage „alle Akt-2-Artefakte vor FP2" — keine zeitliche Kette zwischen Zusammenfassung und plan-reviewer; Alex' bindende Vorgaben 1–8 (Abschnitt 0) sagen zur internen Reihenfolge nichts. Die Präzisierung ist zudem die robustere Variante: Eine Zusammenfassung vor dem plan-reviewer müsste bei REVISE (wie Runde 1) nachgezogen werden; nach APPROVE referenziert sie den stabilen Stand. Verbindlich bleibt: Datei existiert vor FP2 und nennt beide Wortlaute — jetzt explizit zugesagt.

**Finding 3 [wichtig] — Banner-Hinweis-AK: eingearbeitet und konsistent.** E1-AK6 (briefing.md:44) heißt jetzt „Banner-Split + Hinweiszeile" und assertiert: „bei ≥ 2 Staffeln im Banner die Hinweiszeile mit dem exakten Wortlaut der UI-Text-Tabelle (ADR-K-2, inkl. Gedankenstrich U+2013) steht und bei genau 1 Staffel keine Hinweiszeile erscheint". Konsistenzprüfung:
- ADR-K-2-Konsequenz (:108 „Tests prüfen jeden Tabellen-Text mindestens einmal exakt") ist jetzt **vollständig** erfüllt: „Staffel N (k)" (E1-AK1), „Alle starten" (E1-AK1), Banner-Hinweis (E1-AK6), E2-Fehlermeldung (E2-AK1), E3-Fristmeldung (E3-AK1) — alle 5 Tabellentexte exakt getestet.
- Etappen-Zuordnung korrekt: Der Hinweis wird in **E1** implementiert (ADR-K-1 mit Tag „(E1)" :88; E1-erlaubte Dateien nennen explizit „`updateGroupBannerUI`-Hinweiszeile" :68; Worker-Auftrag E1: „Banner-Split + Hinweiszeile (ADR-K-1)" :222) und in **E1** getestet (E1-AK6 in der E1-AK-Liste der Etappe :68 enthalten).
- Negation („bei genau 1 Staffel keine Hinweiszeile") konsistent mit ADR-K-1 („bei ≥ 2 Staffeln eine zweite Zeile") und der Tabelle (:101 „nur ≥ 2 Staffeln"); kollidiert nicht mit den Einzelstaffel-Bestands-Banner-Tests (bei 1 Staffel entsteht keine Hinweiszeile). Handtest Schritt 1 („Hinweiszeile sichtbar") deckungsgleich.

**Finding 4 [kosmetisch] — fetch-Spy-Abort-Semantik: eingearbeitet, formuliert und widerspruchsfrei.** E3-AK1 (briefing.md:55) ergänzt: „Der fetch-Spy muss browser-treu gebaut sein: bei Abort des übergebenen `signal` rejectet er mit einem `AbortError` (ein abort-blinder Spy macht Meldung und Sperre-Frei unerreichbar)" — inklusive Begründung des Warum. Die Erfahrungswerte des Worker-Auftrags (briefing.md:270–273) ergänzen verbindlich: „fetch-Spy in E3-Tests browser-treu — bei Abort des signals mit AbortError REJECTEN (sonst erreichen Frist-Meldung und Sperre-Frei den Test nie)". Widerspruchsfreiheit mit ADR-K-6 (:129) bestätigt: Der Spy liefert genau den `AbortError`, den der bestehende catch-Zweig (:3210) behandelt; Frist-Meldung nur bei `didTimeout && seq === searchSeriesRequestSeq` — die Ergänzung schließt die Lücke zwischen Beobachtung (signal-Abbruch) und Wirkung (Meldung + Sperre frei). Die Doppelung AK/Erfahrungswerte ist gewollt (Testfall-Beschreibung + verbindliche Worker-Regel) und inhaltlich deckungsgleich; der Einschub im Codeblock hält den dort deklarierten Umschrift-Stil ein (kein UI-Text).

## 2. Neue Fehler durch die Edits

Keine gefunden — im Einzelnen:
- **Frontmatter unangetastet** (briefing.md:1–8 byte-identisch zu Runde 1: `status: draft`, Platzhalter, `source: roadmap#74,#80,#83`).
- **Nummerierung intakt:** E1-AK6 behält seine Nummer (nur Titel erweitert); E1-AK7–AK9, E2-AK1–AK7, E3-AK1–AK5, ALL-AK1–AK3 alle unverändert, keine Doppelungen, keine Lücken.
- **Abschnittsreihenfolge unverändert** (1–12, Etappen direkt nach 3); der IOU steht als erster Absatz innerhalb von Abschnitt 6, verdrängt nichts.
- **Zeilenverschiebung +4 sauber erklärbar** (IOU-Absatz +2, fetch-Spy-Einschub in den Erfahrungswerten +2); alle Zeilenangaben des Briefings referenzieren externe Dateien (app.js, Tests, ROADMAP), keine Selbstreferenzen gebrochen.
- **Alle übrigen Inhalte byte-identisch** zu Runde 1 (Kopf, Abschnitte 1–5, Etappen, 4, Dissens 1–7, Risiken R-A–R-E, 7, 9, 10, 11 inkl. test_cmd :182 und Rohausgaben-Liste, Freigabepfad, 12) — durch Vergleich beider Lesungen verifiziert.

## 3. Bedingungen (im Briefing selbst verankert — keine Einwände, aber Vor-FP2-Pflichten)

1. **Rohoutput-Archivierung:** Der IOU ist eine Verpflichtung, kein Erfüllungsnachweis — die `opencode export`-Archivierung der Akt-2-Rollenantworten muss vor FP2 tatsächlich erfolgen, sonst ist der IOU unerfüllt und FP2 läuft erneut auf unbelegte Dissens-Zitate.
2. **ALEX_ZUSAMMENFASSUNG.md:** Muss vor FP2 erstellt werden und beide FP2-Wortlaute („Alle starten", Banner-Hinweis) nennen — jetzt explizit zugesagt (briefing.md:166).

## 4. Nicht geprüft

- Die Nebenbehauptung „auf Anweisung des Akt-2-Auftrags NICHT vom Orchestrator abgeschrieben" (briefing.md:136) — der Akt-2-Auftrag ist nicht im Session-Ordner archiviert und damit nicht gegenprüfbar; sie ist für den IOU-Kern nicht tragend (der Mechanismus gilt unabhängig davon) und wird mit der Archivierung belegbar.
- Git-Zustand, `test_cmd`-Ausführbarkeit, Kit-Betriebsanleitung §9 — wie Runde 1 (kein bash, Worktree-Grenze).

## Urteil

Alle vier Runde-1-Findings sind sauber, widerspruchsfrei und an den richtigen Stellen eingearbeitet; die Edits haben keine neuen Fehler, Nummerierungs- oder Reihenfolge-Probleme erzeugt; der Formvertrag (inkl. #75-IOU-Mechanismus) ist jetzt vollständig erfüllt. Verbleibend sind zwei physische Vor-FP2-Pflichten, die das Briefing selbst verankert, sowie ein kosmetischer Formulierungshinweis.

VERDICT: APPROVE

1. [kosmetisch] IOU-Schlussformulierung „Alex möge die Dissens-Punkte gegen die archivierten Originale stichprobenfähig halten" (briefing.md:136) ist sperrig — gemeint ist, dass Alex die Dissens-Punkte stichprobenartig gegen die archivierten Originale prüfen können soll. Verständlich, kein Handlungszwang; bei Gefallen bei der ALEX_ZUSAMMENFASSUNG-Erstellung glätten.
