---
kind: plan
status: approved
approved_by: alex
approved_on: 2026-10-19
approval_quote: "FP2: Briefing freigegeben mit „Alle verarbeiten“ und Banner-Hinweis „Diese Serie hat mehrere Staffeln – nach dem Gruppieren kannst du in der Liste eine einzelne Staffel oder alle Folgen verarbeiten.“ Starte AK0 und E1."
source: roadmap#74,#80,#83
---

# Feature Briefing: Medienwerkzeug Feature-Kette (Pilot) — #74 Staffel-Schnellauswahl (E1) + #80-Rest (E2) + #83 Timeout (E3)

**Quelle präzise:** `roadmap#74` (`ROADMAP.md:2045–2065`, Staffel-Schnellauswahl; Umsetzungspunkt 2 „setzt `selectedInboxProjects`" ist durch Alex' S1=A überschrieben — Textanpassung bei Abschluss macht Claude Code, nicht der Worker), `roadmap#80` Rest (`ROADMAP.md:2170–2183`: Bulk-Weg + Gruppenzeile; Banner-Stelle bereits in #75 erledigt), `roadmap#83` (`ROADMAP.md:2217–2228`: Sperre bei hängender Seriensuche → Timeout-Variante S4). Nicht in der Kette: #72 Punkt 9, #82, #84, K2, #86 F-D (Altschuld Index-Bindung im Banner).

**Bindende Alex-Vorgaben** (Kickoff `00-kickoff.md` Abschnitt 0, Vorgaben 1–8; Plan-Go wörtlich 2026-10-18: „Plan-Go: Kettenplan #74 + #80-Rest + #83 wie empfohlen (S1 A, S2 Bündel, S3 gemeinsame Sperre, S4 Timeout in searchSeries, S5 lokal), P1 als F1 an FP1, P2–P4 ins Briefing. Starte Akt 1." — nicht neu verhandelt): S1=A (Staffel-Knopf ruft `startSeriesGroupWorkflow(group_key, files)` direkt mit genau den Staffel-Folgen), Darstellung (Knöpfe nur bei ≥ 2 Staffeln, aufsteigend, Zeile darf umbrechen, Handler direkt an Knoten, `group_key`/Staffel nie in Selektoren, echte Umlaute), S2-Bündel (E1=#74, E2=#80-Rest, E3=#83), S3 (gemeinsame Sperre + Freigabe in `finally` an allen vier Startstellen), S4 (Timeout in `searchSeries` selbst, wirkt auf alle Aufrufer; lokale Controller-Referenz + `didTimeout`-Flag + `clearTimeout` in `finally`), P3 (Meldungen überleben 6-s-Neuaufbau via Modulzustand + `console.error`), S5 (Handtest lokal), Ablauf (EIN Briefing, je Etappe ein Gate-A2-Lauf, EIN Rückkanal, EIN Handtest, EIN PR).

**Freigabepunkt 1 beantwortet (Alex, wörtlich 2026-10-18):** „FP1: E1-F1 ja (Banner bei ≥2 Staffeln nur gruppieren), E1-F3 ja (umbenennen, Wortlaut in Akt 2), E2-F4 ja (vorhandene Fehlerform), E3-F2 30 s. Starte Akt 2." → E1-F1: Banner trägt bei ≥ 2 Staffeln nur `appliedInboxGroups` ein und rendert neu, KEIN Start; bei genau 1 Staffel bleibt der Sofortstart. E1-F3: „Auswählen" in der Gruppenzeile wird umbenannt (Wortlaut unten, Teil von FP2). E2-F4: vorhandene Inline-Fehlerform (`.smart-inbox-group-banner-error`, `role="alert"`, `aria-live="polite"`, `escapeHTML`) + `console.error`; kein Toast, keine `style.css`-Änderung. E3-F2: Frist 30 000 ms als benannte Konstante.

**Freigabepunkt 2 beantwortet (Alex, wörtlich 2026-10-19):** „FP2: Briefing freigegeben mit „Alle verarbeiten“ und Banner-Hinweis „Diese Serie hat mehrere Staffeln – nach dem Gruppieren kannst du in der Liste eine einzelne Staffel oder alle Folgen verarbeiten.“ Starte AK0 und E1.“ → Wortlaute in ADR-K-2 entsprechend gesetzt (Alle-Knopf `Alle verarbeiten`, Banner-Hinweis neu; Begründung Alex: Rückfrage, ob mehrere Staffeln einer Serie oder mehrere Serien gemeint sind — gemeint sind Staffeln derselben Serie). Änderung durch Claude Code als reiner Wortlaut-Austausch, sonst unverändert gegenüber plan-reviewer-APPROVE.

**Verifizierter Git-Zustand (Kickoff, von Claude Code ausgeführt):** Branch `feat/roadmap-74-staffel-schnellauswahl` auf Stand `origin/main` (`d011499`), clean. Feature-Branch, kein main-Stop.

## 1. Problemstellung

Alle Befunde gegen den Code verifiziert (Kickoff B1–B11, Akt-2-Nachprüfung; Zeilenangaben `gui/static/app.js`):

- **Gruppen mit vielen Staffeln sind nur als Ganzes startbar.** Die Gruppenzeile (:13271–13379) hat genau einen Knopf „Auswählen" (:13302), dessen Handler direkt `startSeriesGroupWorkflow(item.group_key, files)` mit ALLEN Folgen aufruft (:13367–13368) — die Einzelkästchen sind nach dem Gruppieren weg (Live-Fall: 173 Folgen / 11 Staffeln; ROADMAP #71 warnt bei 173 Zeilen vor Einfrier-Risiko der Zuordnungstabelle, `ROADMAP.md:1986`). Der Banner-Apply (:12834–12857) startet bei Mehrstaffel-Gruppen sofort mit allen Folgen (:12847–12848) und nimmt dem Nutzer damit genau die Staffel-Auswahl weg, die #74 ermöglichen will.
- **Der Knopfname lügt.** „Auswählen" startet direkt den Serien-Dialog und berührt `selectedInboxProjects` nicht (Kickoff F3) — neben neuen Staffel-Knöpfen endgültig irreführend (Alex: umbenennen, FP1).
- **Zwei stille `catch`-Blöcke (#80-Rest).** Gruppenzeilen-Handler :13369–13374 und Bulk-Handler :12992–12997 geben im Fehlerfall nur den Knopf wieder frei — ohne Meldung, ohne Log, ohne `finally`. In #77 hat genau dieses Muster einen Selektor-Fehler verborgen.
- **Hängende Seriensuche blockiert alles (#83).** `startSeriesGroupWorkflow` endet mit `return searchSeries()` (:13184–13185); `searchSeries` (:3079–3214) hat einen `AbortController`, aber keine Frist. Hängt `/api/search`, bleibt die geplante gemeinsame Sperre (S3) bis zum Neuladen gesetzt. Server-Worst-Case: bis zu 4 Provider sequenziell + Umlaut-Fallback, je `timeout=10` bzw. Retry `timeout=15 × 3` (`gui/mw_metadata.py:323`, `:122–150`) — mehrere Minuten möglich.
- **Der 6-Sekunden-Takt überschreibt alles.** `setInterval(loadStatus, 6000)` (:556) → `renderSmartInboxList` (:13234) baut die Liste komplett neu (:13265). Knopf-Zustände (`disabled`, Text) sind nach 6 s Makulatur; nur Modulzustand überlebt (Muster `bannerApplyErrors` :12477, Präzedenz #75 F-A/F-H).

## 2. Zielnutzer

Alex, Einzelnutzer der lokalen Instanz und des NAS. Reale Situation: große Serien-Gruppen (bis 11 Staffeln / 173 Folgen) staffelweise verarbeiten, ohne 23 Einzelkästchen zu klicken; bei Fehlern sehen, was schiefging; nach hängender Suche ohne Neuladen weiterarbeiten können. Reine Frontend-Änderung: kein Server-, API-, Worker- oder Datenbankschema-Eingriff; keine Außenwirkung über die eigene Instanz hinaus.

## 3. Akzeptanzkriterien

AK0 ist Aufgabe von Claude Code (nicht des Workers). E1-/E2-/E3-AKs sind ausführbare Frontend-Tests; ALL-AKs sind Review-/Hygiene-Kriterien. Bestehende Tests bleiben grün, mit einer explizit benannten Ausnahme: der F2-Label-Bestandstest `tests/frontend/inbox_group.test.js:1407–1448` (assertiert wörtlich „Auswählen" :1447) wird an den neuen Wortlaut angepasst (E1-AK9 — Anpassung, keine Abschwächung; Folge der von Alex bestätigten Umbenennung E1-F3). Alle UI-Texte sind wörtlich durch die Tabelle „Verbindliche UI-Texte (UTF-8, exakt)" in ADR-K-2 gebunden: echte Umlaute, Gedankenstrich U+2013; ASCII-Umschrift in Oberfläche oder Tests verboten (Präzedenz #75 F2).

- [ ] **AK0 — Ausgangsmessung:** **Claude Code** misst VOR dem ersten scharfen Gate-A2-Lauf im Worker-Image (kein Testlauf auf dem Host) die volle Suite mit `test_cmd` aus Abschnitt 11 und schreibt die wörtlichen Ausgaben mit Exit-Codes in `docs/sessions/2026-10-18-roadmap74-staffel-kette/ak0-ausgangsmessung.md`.
- [ ] **E1-AK1 — Staffel-Knöpfe bei Mehrstaffel-Gruppen:** Es prüft, dass eine Gruppenzeile mit ≥ 2 Staffeln genau einen Knopf pro Staffel trägt, Wortlaut exakt `Staffel N (k)` (k = Folgenzahl dieser Staffel), aufsteigend sortiert; dass eine Einzelstaffel-Gruppe KEINE Staffel-Knopf-Reihe hat; dass der Alle-Knopf in beiden Fällen exakt `Alle verarbeiten` heißt.
- [ ] **E1-AK2 — Klick übergibt genau die Staffel:** Es prüft, dass ein Klick auf „Staffel 11" `startSeriesGroupWorkflow` genau die Folgen dieser Staffel übergibt — in Folgenreihenfolge, Ordner-Folgen über `inboxFilesEntryForItem` (Eintrag mit `single_video_relpath` → Relpath, sonst `project`); Nachweis über testseitigen Getter auf das Modul-Closure (`activeSeriesGroupFiles`) plus Ansichtswechsel wie im Bestandstest `inbox_group.test.js:1348–1366`.
- [ ] **E1-AK3 — Alle-Knopf unverändert:** Es prüft, dass der umbenannte Alle-Knopf weiterhin alle Folgen der Gruppe in Items-Reihenfolge übergibt und den Workflow startet (Bestandsverhalten, neuer Label).
- [ ] **E1-AK4 — Knöpfe nach Neuaufbau:** Es prüft, dass Staffel-Knöpfe und Alle-Knopf nach erneutem `renderSmartInboxList` (Nachbau des 6-s-Takts) erneut existieren und korrekt starten.
- [ ] **E1-AK5 — Sonderzeichen im strengen Mock:** Es prüft mit `group_key` aus `"`, `'`, `<`, `&` (z. B. `Show "Special" <'Cut' & Co>`) in der neuen E1-Testdatei mit `validateSelector`-Mock (Muster `tests/frontend/inbox_group_banner.test.js:55–93`, wirft bei ungültigen Selektoren `SyntaxError`): Name maskiert angezeigt (kein rohes Markup), Staffel-Reihe gerendert, Staffel-Klick und Alle-Klick ohne Wurf. (Im lockeren `inbox_group`-Mock :21–62/:349–352 wäre dieser Test wertlos — B11a.)
- [ ] **E1-AK6 — Banner-Split + Hinweiszeile:** Es prüft, dass „Als Serie gruppieren" bei einer Gruppe mit ≥ 2 Staffeln die Gruppe nur in `appliedInboxGroups` einträgt und neu rendert (Gruppenzeile erscheint; KEIN Start: Ansicht wechselt nicht, `activeSeriesGroupFiles` bleibt unangetastet — `startSeriesGroupWorkflow` wird nachweislich nicht durchlaufen; ein nachträgliches Überschreiben von `globalThis.startSeriesGroupWorkflow` ist wirkungslos, Handler ruft das lokale Binding), **und dass bei ≥ 2 Staffeln im Banner die Hinweiszeile mit dem exakten Wortlaut der UI-Text-Tabelle (ADR-K-2, inkl. Gedankenstrich U+2013) steht und bei genau 1 Staffel keine Hinweiszeile erscheint**, und dass bei genau 1 Staffel der bisherige Sofortstart inklusive Fehlerpfad unverändert bleibt (Bestands-Banner-Tests grün; alle Banner-Fixtures sind Einzelstaffel-Gruppen, verifiziert `makeThreeGroupsSuggestions` :741–748 und AK8-Fixture :1058–1061).
- [ ] **E1-AK7 — Gemeinsame Sperre:** Es prüft, dass bei laufendem erstem Start (fetch hängt) ein zweiter Start von JEGLICHER der vier Startstellen (Banner-Apply, Alle-Knopf, Staffel-Knopf, Bulk-Leiste) still abgewiesen wird: kein zweiter `fetch` auf `/api/search` (Spy-Zähler), keine Fehlermeldung, kein Textwechsel an anderen Knöpfen.
- [ ] **E1-AK8 — Freigabe in `finally` auch bei Erfolg:** Es prüft, dass nach erfolgreichem Abschluss des ersten Starts (Pending-fetch auflösen lassen) die Sperre frei ist: ein weiterer Start von einer anderen Stelle läuft; Staffel-/Alle-Knöpfe nach Neuaufbau wieder aktiv.
- [ ] **E1-AK9 — benannte Bestandstest-Anpassung:** Der Test `inbox_group.test.js:1407` (F2-Labeltest) wird WÖRTLICH angepasst: Assertion :1447 prüft künftig `includes('Alle verarbeiten')` (Name des Tests entsprechend), die Negativ-Assertion :1448 bleibt; keine weiteren inhaltlichen Änderungen an Bestands-Tests. Der angepasste Test muss gegen den E1-Basis-Stand ROT sein (alter Label „Auswählen").
- [ ] **E2-AK1 — Fehler aus dem Alle-Knopf:** Es prüft: erzwungener Start-Fehler (einziger Injektionsweg: werfender `triggerQualityHintUpdates`-Stub vor dem `eval`, testseitige Weiche, Muster `inbox_group_banner.test.js:52`/:551/:1100 — KEIN `fetch`-Stub, da `searchSeries` ihre Fehler intern fängt, Kickoff B6) → sichtbare Inline-Meldung in der betroffenen Gruppenzeile (`div` mit Klasse `smart-inbox-group-banner-error`, `role="alert"`, `aria-live="polite"`, Text exakt nach UI-Text-Tabelle, `escapeHTML`), `console.error` aufgerufen, Knopf nach Neuaufbau wieder benutzbar, Sperre frei (Anschlusstest: zweiter, erfolgreicher Start läuft).
- [ ] **E2-AK2 — Fehler aus dem Staffel-Knopf:** Es prüft denselben Fall für einen Staffel-Knopf: Meldung in der Gruppenzeile derselben Gruppe, `console.error`, Sperre frei; `appliedInboxGroups` bleibt UNVERÄNDERT (Gruppe bleibt angewendet, kein Rücknahme-Verhalten wie im Banner).
- [ ] **E2-AK3 — Fehler aus der Bulk-Leiste:** Es prüft denselben Fall für „Ausgewählte als Serie verarbeiten": INLINE-Meldung in der Bulk-Leiste (Klasse `smart-inbox-group-banner-error`, `width: 100%`-Zeile zwischen Info und Buttons — KEIN `alert()`), `console.error`, Knopf wieder benutzbar, Sperre frei.
- [ ] **E2-AK4 — Meldung überlebt den 6-s-Neuaufbau:** Es prüft, dass die Meldung aus E2-AK1/AK2 nach erneutem `renderSmartInboxList` unverändert in der Gruppenzeile steht (Modul-Map analog `bannerApplyErrors`) und die Bulk-Meldung nach erneutem `updateBulkActionsBarUI` (vollständiger `innerHTML`-Neubau :12909) erneut gezeichnet wird (Modul-Variable, kein einmalig eingefügter DOM-Knoten).
- [ ] **E2-AK5 — Leeren beim nächsten Erfolg:** Es prüft, dass ein erfolgreicher Start DERSSELBEN Stelle die Meldung löscht (Gruppe: jeder Startknopf dieser Gruppenzeile; Bulk: nächste erfolgreiche Bulk-Verarbeitung), und dass „Auswahl aufheben" die Bulk-Meldung löscht.
- [ ] **E2-AK6 — Bulk-Auswahl bleibt:** Es prüft, dass `selectedInboxProjects` nach einem Start-Fehler unverändert gesetzt bleibt.
- [ ] **E2-AK7 — Bestand unverändert:** Es prüft, dass die bestehenden `alert()`-Pfade im Bulk-Handler („nicht mehr in der Inbox" :12970/:12982–12984) unverändert bleiben (Bestands-Tests `inbox_selection.test.js` AK5 etc. grün) und dass Staffel-/Bulk-Fehlerpfade `appliedInboxGroups` niemals ändern (bedient auch #86 F-C: Banner bleibt einziger Schreiber :12845, Rücknahme :12850 bleibt der einzige Löscher — [advocatus] F7.1 bestätigt unkritisch unter dieser Bedingung).
- [ ] **E3-AK1 — Frist bei hängender Suche:** Es prüft, dass eine Suche, deren `fetch` nie auflöst, nach Auslösen des Frist-Timers aus der steuerbaren Queue (30 000 ms) abgebrochen wird: `signal`-Abbruch am fetch-Spy, sichtbare Meldung exakt nach UI-Text-Tabelle in `series-search-results`, Sperre frei (nachfolgender Start möglich). Der fetch-Spy muss browser-treu gebaut sein: bei Abort des übergebenen `signal` rejectet er mit einem `AbortError` (ein abort-blinder Spy macht Meldung und Sperre-Frei unerreichbar).
- [ ] **E3-AK2 — Ablösung bleibt still:** Es prüft: Suche A hängt, Suche B startet → A endet still (keine Meldung, B's Spinner/Ergebnisse nicht überschrieben); selbst wenn A's Frist-Timer NACH B's Start ausgelöst wird, bleibt A still (Seq-Guard, ADR-K-6) und B's Ergebnisse bleiben stehen.
- [ ] **E3-AK3 — normale Suche unberührt:** Es prüft, dass eine Suche, die vor der Frist auflöst, ihre Ergebnisse wie bisher rendert, keine Frist-Meldung erscheint und der Frist-Timer im `finally` zurückgebaut ist (Queue danach leer).
- [ ] **E3-AK4 — Pfadabdeckung:** Es prüft E3-AK1/AK2/AK3 je auf dem manuellen Pfad (`btn-search-series`-Klick bzw. Enter im Suchfeld, :7564/:7566) UND auf dem Workflow-Pfad (`startSeriesGroupWorkflow` → `searchSeries` :13184–13185).
- [ ] **E3-AK5 — Timer-Harness:** Es prüft die Harness-Umstellung selbst: steuerbare Fake-Timer-Queue ersetzt in allen vier betroffenen Testdateien die Sofort-Stubs (`inbox_group.test.js:536`, `inbox_group_banner.test.js:644`, `inbox_selection.test.js:557`, neue E1-Datei); Frist-Timer (`delay >= 30000`) werden registriert und NUR testseitig ausgelöst, kleinere Delays laufen weiterhin sofort (scrollIntoView-Timer :3194/:3201 bleiben verträglich); sämtliche Bestands-Tests bleiben grün, keine Löschung/Abschwächung bestehender Assertions.
- [ ] **ALL-AK1 — Cache-Buster:** `app.js?v=104` in `index.html:2760` UND allen neun Importen `app.js:1–9` (10 Stellen; Sprung in E1, E2/E3 lassen stehen); `style.css` unverändert ⇒ `index.html:9` bleibt `style.css?v=51`; `cache_busting.test.js` grün ohne Anpassung (erzwingt nur Konsistenz app.js, :13–48; style.css nur „nicht leer", :50–64). Falls entgegen R3/B10 doch `style.css` nötig würde: Begründung im Rückkanal PFLICHT + `v=52`.
- [ ] **ALL-AK2 — keine Test-Weichen:** Produktivcode liest keine globalen Variablen, die nur Tests setzen; Export-Block `app.js:13533ff.` nur um `globalThis.X = X` ergänzt oder unangetastet; werfender Stub liegt ausschließlich testseitig (Präzedenz #75 AK13).
- [ ] **ALL-AK3 — Hygiene:** `git diff --check` sauber; keine Trailing Whitespace; keine echten Timer in Tests.

## Etappen (nur bei Feature-Ketten)

Je Etappe EIN Gate-A2-Lauf mit `--task "Setze Etappe En aus dem Briefing um"`; Basis ist jeweils der committete Stand der Vor-Etappe (E1-Basis: Stand `d011499`-Äquivalent des Branches; ein docs-only Session-Head ist NICHT Teil der Worker-Basis, Präzedenz `docs/sessions/2026-10-12-inbox-ordnerfolgen/briefing.md` AK0). Der Worker setzt NUR die AKs seiner Etappe um und fasst Folgeetappen nicht an. Ampel-Regeln (Prüftiefe, Stopp-Bedingungen) stehen in der Kit-Betriebsanleitung §9 und werden von Claude Code geprüft — hier nur Verweis.

- **E1 — #74 Staffel-Schnellauswahl + Banner-Split + Umbenennung.** Ziel: Staffel-Knopf-Reihe in der Gruppenzeile (nur ≥ 2 Staffeln, „Staffel N (k)", aufsteigend, Closure-Handler), Alle-Knopf „Alle verarbeiten", Banner verhält sich gesplittet (E1-AK6), gemeinsame Sperre S3 an allen vier Startstellen inkl. `finally` (E1-AK7/AK8), Cache-Buster v103→v104 (10 Stellen). AKs: E1-AK1…AK9 + ALL-AK1 (Sprung) + ALL-AK2/AK3. Erlaubte Dateien: `gui/static/app.js` (Banner-Handler :12834–12857, `updateGroupBannerUI`-Hinweiszeile, `renderSmartInboxList`-Gruppenzeile :13271–13379, Sperren-Nutzung, Export-Block nur `globalThis.X = X`), `gui/static/index.html` (nur :2760), `tests/frontend/inbox_group.test.js` (NUR benannte Anpassung :1407–1448), NEU `tests/frontend/inbox_group_seasons.test.js` (strenger `validateSelector`-Mock nach Banner-Muster :55–93, Mehrstaffel-Fixtures inkl. `single_video_relpath`, Harness-Anhang nur für im Basis-Stand existierende Symbole). Abbruchkriterium: Schritt-0-Verifikation fehlt/abweichend; Banner-Bestands-Tests (Einzelstaffel-Fixtures) nicht ohne inhaltliche Änderung grün; Streng-Mock nicht übernehmbar.
- **E2 — #80-Rest: sichtbare Fehler in Gruppenzeile + Bulk-Leiste.** Ziel: `catch`/`finally` mit Inline-Meldung + `console.error` an Alle-/Staffel-/Bulk-Start; Modulzustand `groupRowStartErrors` (Map nach `group_key`) + `bulkStartError` (Einzelvariable) überleben den 6-s-Neuaufbau; Leeren beim nächsten Erfolg. AKs: E2-AK1…AK7. Erlaubte Dateien: `gui/static/app.js` (Handler-Catches der drei Startstellen + `updateBulkActionsBarUI`-Template :12909–12917 + Modul-Deklarationen neben :12477–12478), `tests/frontend/inbox_group_seasons.test.js` (E2-Tests ergänzen; Harness darf um werfenden `triggerQualityHintUpdates`-Stub nach Banner-Muster erweitert werden). Cache-Buster bleibt v104. Abbruchkriterium: Injektionsweg (Präambel-Binding) in der E1-Datei nicht vorhanden/nicht ergänzbar; E1-Tests nur durch Abschwächung grün zu bekommen.
- **E3 — #83: Frist 30 s in `searchSeries` + Timer-Harness.** Ziel: `SERIES_SEARCH_TIMEOUT_MS = 30000`, lokaler Controller pro Aufruf (globale Registry bleibt Ablöse-Mechanismus), `didTimeout` + Seq-Guard, Frist-Meldung im `catch`, `clearTimeout` in `finally`; steuerbare Fake-Timer-Queue in allen vier Testdateien. AKs: E3-AK1…AK5. Erlaubte Dateien: `gui/static/app.js` (nur `searchSeries` :3079–3214 + Konstante + Modul-Deklaration Seq-Zähler), `tests/frontend/inbox_group.test.js`, `tests/frontend/inbox_group_banner.test.js`, `tests/frontend/inbox_selection.test.js`, `tests/frontend/inbox_group_seasons.test.js` (in allen VIER NUR Ersatz der Timer-Stubs :536/:644/:557 bzw. analog), NEU `tests/frontend/series_search_timeout.test.js` (Frist-Tests; Harness mit Queue). `tests/frontend/cache_busting.test.js` nur falls nötig (erwartet: nicht nötig). Abbruchkriterium: Bestands-Tests brechen durch die Queue und wären nur durch Abschwächen grün → STOPP statt Harness-Verwässerung.

Reihenfolge E1→E2→E3 nach [advocatus] F8.3: E2 härtet die von E1 erzeugten Handler ab, E3 ändert `searchSeries` + Harness aller Dateien; der Frist-Timer darf erst existieren, wenn die Queue landet (sonst feuert er in jedem Sofort-Stub-Lauf — R1).

## 4. Bewusst verworfen (Scope-Eingrenzung)

- **K2 „Rest der Gruppe auswählen", #72 Punkt 9, #82, #84:** nicht Teil des von Alex bestätigten S2-Bündels.
- **Dropdown/Obergrenze/Scrollbar für > 10 Staffeln:** [grafiker] und [produktberater] unabhängig gleich — umbrechende Reihe reicht (real max. 11 Staffeln bekannt); Sonderlogik wäre Over-Engineering.
- **`seasons`-Struktur im Pseudo-Entry ([advocatus] F5.3 vorgeschlagen):** verworfen — Staffel-Zuordnung lässt sich im Render aus dem bereits sortierten `items` (:12567–12570/:12581) per `filter(m => m._se.season === N)` ableiten; neue Datenstruktur = größerer Diff ohne Nutzen.
- **Eigene Fehler-Map-Löschung beim Banner-Rollback ([advocatus] F6.2):** verworfen nach Durchdringung — Banner-Rollback (:12850) trifft nur NOCH NICHT angewendete Gruppen; diese haben keine Gruppenzeile und damit keinen `groupRowStartErrors`-Eintrag. Map wächst pro Sitzung höchstens um die Gruppenzahl — kein Leck.
- **`alert()` für Bulk-Fehler ([produktberater] Vorschlag):** verworfen — Alex' FP1-Antwort E2-F4 schreibt die vorhandene Inline-Form an BEIDEN Stellen vor.
- **Toast-Funktion, neue CSS-Klasse, `style.css`-Änderung, `GUI`-Umbau:** verworfen (E2-F4 bindend; Klassename „banner" in `.smart-inbox-group-banner-error` zugunsten der Wiederverwendung hingenommen — Kickoff E2-F4-Trade-off).
- **Konfigurierbare Timeout-Dauer, Fehlerklassifikation nach HTTP-Code, Provider-Diagnose-Zusatztext ([grafiker] zweite Zeile):** verworfen — nicht nachgefragt, einfachste Lösung zuerst.
- **Umbau der Banner-Index-Bindung (#86 F-D, :12820/:12830/:12861):** außerhalb Scope, Notiz in `ROADMAP.md:2269`, nicht anfassen.
- **NAS-Auslieferung/Deployment:** S5 bindend — Handtest lokal; NAS erst nach Merge mit eigenem Go.

## 5. ADR-Blöcke

### ADR-K-1 — Banner-Verhaltenssplit bei ≥ 2 Staffeln + Hinweiszeile (E1)
- **Entscheidung:** Im Banner-Apply-Handler (:12834–12857) wird der Start auf `seasonCount < 2` beschränkt (`seasonCount = new Set(members.map(m => m._se.season)).size`, Closure-Variable `members` :12833); bei ≥ 2 Staffeln nur `add` + Re-Render. Handler-Struktur (Sperre, `try/catch/finally`, Rücknahme) bleibt bestehen — der Lock wird im Nichtstart-Fall trivial sofort wieder freigegeben. Im Banner-Content-Span erscheint bei ≥ 2 Staffeln eine zweite Zeile (`display: block; font-size: 0.85em; color: var(--text-muted); margin-top: 2px;`) mit dem Hinweis exakt nach UI-Text-Tabelle (ADR-K-2).
- **Alternativen:** (a) Kein Hinweis, nur Verhaltensunterschied ([produktberater] MVP-Veto) — verworfen: Alex' FP1-Antwort verlangt ausdrücklich, den Unterschied verständlich zu machen; (b) eigener Knopftext „Gruppieren" bei Mehrstaffel — verworfen: zwei Zustände desselben Knopfs vergrößern die kognitive Last gegenüber einer Erklärung; (c) Hinweis unterhalb des Banners — verworfen ([grafiker]: gehört semantisch zur Aktion).
- **Begründung:** Der Sofortstart bei 173 Folgen führt direkt in die große Zuordnungstabelle (:13163) mit Einfrier-Risiko (#71) und nimmt die Staffel-Auswahl weg; bei einer Staffel gibt es nichts auszuwählen, also bleibt dort der direkte Weg.
- **Konsequenzen:** Banner bleibt einziger `appliedInboxGroups`-Schreiber (#86 F-C unverändert unkritisch, [advocatus] F7.1); Banner-Text „Als Serie gruppieren" ist erstmals akkurat; alle Bestands-Banner-Tests (Einzelstaffel-Fixtures, verifiziert) bleiben grün.

### ADR-K-2 — Verbindliche UI-Texte (UTF-8, exakt) + Staffel-Leiste (E1)
- **Entscheidung:**

| Element | Wortlaut (exakt, UTF-8) |
|---|---|
| Staffel-Knopf | `Staffel 1 (12)` — Muster `Staffel N (k)`, k = Folgenzahl dieser Staffel |
| Alle-Knopf (Gruppenzeile, rechter Block :13300) | `Alle verarbeiten` |
| Banner-Hinweis (nur ≥ 2 Staffeln, zweite Zeile; Gedankenstrich U+2013) | `Diese Serie hat mehrere Staffeln – nach dem Gruppieren kannst du in der Liste eine einzelne Staffel oder alle Folgen verarbeiten.` |
| E2-Fehlermeldung (Gruppenzeile + Bulk-Leiste; Banner unverändert) | `Serien-Start fehlgeschlagen. Bitte erneut versuchen.` |
| E3-Fristmeldung (Suchbereich, eine Zeile im Muster `:3212`) | `Suchfehler: Zeitüberschreitung nach 30 Sekunden. Bitte erneut versuchen.` |

  Staffel-Leiste = neues `div.smart-inbox-group-seasons` ZWISCHEN `headerDiv` und `membersDiv`, NUR bei ≥ 2 Staffeln, inline `cssText`: `display: flex; flex-wrap: wrap; align-items: center; gap: 6px; padding-top: 4px; border-top: 1px dashed rgba(139, 92, 246, 0.15);`. Staffel-Knöpfe: `button type=button`, `class="btn btn-secondary btn-xs"`, `cssText "white-space: nowrap;"`, Aufsteigend aus `items`-Filter; Handler per Closure direkt ans Element (kein Selektor mit `group_key`/Staffel; `data-*`-Attribute erlaubt, aber nie selektiert). Der Alle-Knopf bleibt an seiner Stelle im rechten Header-Block (btn-sm, zap-Icon, nur Label getauscht :13302); Umbenennung betrifft AUSSCHLIESSLICH die Gruppenzeile — der „Auswählen"-Button normaler Einträge (:2521) und die Checkbox-`aria-label` (:13428) bleiben unverändert.
- **Alternativen:** (a) Knöpfe im rechten Header-Block mit `flex-wrap` — verworfen ([grafiker]: 12+ Knöpfe zerstören die Header-Zeile); (b) Wortlaut `Staffel 1 (12 Folgen)` ([produktberater]) — verworfen: Muster `Staffel N (k)` ist Alex' bindende Vorgabe 1 und bei 11 Knöpfen kompakter; (c) `Alle Staffeln (173)` als eigener Knopf am Ende der Staffel-Leiste ([grafiker]) — verworfen: der Label-Wechsel gehört an den BESTEHENDEN Knopf (minimaler Diff, eine Stelle), und „Alle Staffeln" wäre bei Einzelstaffel-Gruppen (ohne Staffel-Leiste) irreführend — „Alle verarbeiten" gilt in beiden Fällen; (d) „Starten" ([grafiker]) — verworfen: sagt nicht, WAS gestartet wird.
- **Begründung:** [grafiker]-Variante (b) mit funktionaler Hierarchie (Zeile 1 Identität + Hauptaktion, Zeile 2 Bereichswahl); sekundäre btn-xs-Knöpfe vs. primärer Alle-Knopf mit ⚡ machen Rang und Startsemantik sichtbar; E2-Text bewusst identisch an allen drei Stellen ([produktberater]: ein Fehler, eine Meldung; der Ort zeigt die Quelle).
- **Konsequenzen:** Tests prüfen jeden Tabellen-Text mindestens einmal exakt; `style.css` bleibt unverändert (R3 gelöst über inline `cssText`); Klassename `.smart-inbox-group-banner-error` wird außerhalb des Banners weiterverwendet (bewusst hingenommen).

### ADR-K-3 — Staffel-Filterung aus bestehender Sortierung (E1)
- **Entscheidung:** `files` pro Staffel = `item.items.filter(m => m._se.season === N).map(m => inboxFilesEntryForItem(m))` — Reihenfolge ist bereits Staffel- dann Folge-aufsteigend (:12567–12570, B8); keine neue Sortierung, keine neue Datenstruktur. Klick ruft `await startSeriesGroupWorkflow(item.group_key, files)` im try — exakt das Muster des Bestandshandlers (:13367–13368).
- **Alternativen:** Umweg über `selectedInboxProjects` (ROADMAP-Originaltext Punkt 2) — verworfen: von Alex mit S1=A überschrieben; `seasons`-Feld im Pseudo-Entry ([advocatus] F5.3) — verworfen (siehe Abschnitt 4).
- **Begründung:** KI-seitig ~20 Zeilen; die Live-Fälle (173/11) brauchen keine weitere Ableitungsschicht.
- **Konsequenzen:** Bei Fehlern in Staffel- oder Alle-Start bleibt die Gruppe angewendet (kein `appliedInboxGroups`-Zugriff in den neuen Catches — E2-AK7); Wiederholung ist direkt möglich.

### ADR-K-4 — Gemeinsame Sperre S3 an vier Startstellen (E1, Fehlerästhetik E2)
- **Entscheidung:** `groupWorkflowRunning` (:12478) wird an allen vier Startstellen (Banner :12835, Alle-Knopf, Staffel-Knöpfe, Bulk :12928) gelesen und gesetzt — Prüfen+Setzen strikt synchron ohne `await` dazwischen (Muster :12835→:12838, [advocatus] F1.2) — und im `finally` freigegeben (P2). Abgewiesene Zweitstarts geschehen STILL (kein Feedback, konsistent zum Banner :12835, [advocatus] F1.3). `btn.disabled`/„wird gestartet…" bleiben Kosmetik: Der 6-s-Neuaufbau (:13265/:12909) macht Knopfzustände wertlos, nur der Modul-Flag schützt ([advocatus] F1.1); `finally`-Freigabe hat Vorrang vor Button-Restore und darf ihn nie überspringen ([advocatus] F9.3). Invariante: Der Aufruf von `startSeriesGroupWorkflow` bleibt IM `try` (Funktion ist synchron im Top — :13005; nur so erreichen synchrone Würfe den catch, [advocatus] F2.2).
- **Alternativen:** Map offener Läufe je Gruppe (parallele Starts verschiedener Gruppen) — verworfen: B5 (Überschreiben von `activeSeriesGroupFiles`/`currentProject` :13007–13014) verbietet Parallelstarts; Sperre pro Knopf — wirkungslos gegen 6-s-Neubau.
- **Begründung:** Ein einziger Workflow-Kontext ist Architekturrealität der Funktion; die gemeinsame Sperre ist Alex' bindende Vorgabe S3.
- **Konsequenzen:** Deadlock-Risiko bei hängender Suche besteht weiter, bis E3 greift (explizit so geplant, R6); Timeout-Callback selbst darf nichts rendern und nicht werfen — sonst kein resolve/reject und die Sperre bliebe stehen ([advocatus] F1.4, in ADR-K-6 operationalisiert).

### ADR-K-5 — E2-Fehlerzustand: Modul-Map + Einzelvariable, vorhandene Fehlerform
- **Entscheidung:** Neu: `groupRowStartErrors = new Map()` (Schlüssel `group_key`, Wert Melde-Text) und `bulkStartError = null` (String), deklariert neben `bannerApplyErrors`/`groupWorkflowRunning` (:12477–12478). Zeichnung: Gruppenzeile — `div.smart-inbox-group-banner-error` (`role="alert"`, `aria-live="polite"`, `textContent`-Setzung über die Map; bei Fehlern ohne Staffel-Leiste direkt nach `headerDiv`, sonst nach der Staffel-Leiste — [grafiker]); Bulk-Leiste — Fehlerblock im `innerHTML`-Template zwischen `.smart-inbox-bulk-info` und `.smart-inbox-bulk-buttons` mit `style="width: 100%;"` (eigene Zeile im Space-between-Flex). Leeren: Gruppen-Eintrag beim nächsten ERFOLGREICHEN Start eines beliebigen Knopfs derselben Gruppe (`delete group_key` vor dem Start, Muster :12844); Bulk beim nächsten erfolgreichen Bulk-Start, bei „Auswahl aufheben" (:12918–12927) und beim Verschwinden der Leiste (count 0). `console.error` mit kurzer Beschreibung an allen drei Stellen. Fehlermeldung pro Gruppe, NICHT pro Staffel-Knopf ([grafiker]: eine Gruppe = ein Fehlerbereich; Staffel-Fehler überschreibt Alle-Fehler derselben Gruppe bewusst).
- **Alternativen:** Meldung nur im DOM (verschwindet nach 6 s — verworfen, P3); Toast-System (verworfen, E2-F4); `alert()` in der Bulk-Leiste ([produktberater], verworfen — FP1-Antwort bindend); Pro-Staffel-Map-Schlüssel `group_key + Staffel` ([advocatus] R4-Option) — verworfen: mehr Schlüssel, kein Erkenntnisgewinn, eine Meldung pro Zeile reicht.
- **Begründung:** `bannerApplyErrors` (:12477/:12844/:12852) ist das bewährte, überlebende Muster aus #75; die Klasse ist in `style.css:3977` unscopiert (F4 verifiziert) — Wiederverwendung ohne CSS-Änderung.
- **Konsequenzen:** Bestehende `alert()`-Pfade bleiben (R5); Bulk-Fehlerpfad zeichnet künftig zusätzlich inline — die Leiste zeigt Meldung UND Auswahl (Auswahl bleibt erhalten, E2-AK6).

### ADR-K-6 — E3: Frist in `searchSeries`, Ablösung bleibt erhalten, steuerbare Timer-Queue
- **Entscheidung:** Konstante `const SERIES_SEARCH_TIMEOUT_MS = 30000;` (nahe :3076). Pro Aufruf: `const localController = new AbortController()` (Closure, NUR dieser wird im Timeout abgerissen — NIEMALS der globale Registry-Inhalt, [advocatus] F3.2), Registry `currentSearchSeriesController` bleibt bestehen: neue Suche abortiert weiterhin das Vorgänger-Objekt (:3085–3087 bleiben wirksam, [advocatus] F3.1); neu: Modul-Zähler `searchSeriesRequestSeq`, pro Aufruf `const seq = ++searchSeriesRequestSeq`; `let didTimeout = false`; `const deadlineId = setTimeout(() => { didTimeout = true; localController.abort(); }, SERIES_SEARCH_TIMEOUT_MS)` — der Callback rendert nichts und wirft nicht; fetch mit `localController.signal`; im `catch`: AbortError-Zweig zeichnet die Fristmeldung (UI-Text-Tabelle) NUR bei `didTimeout && seq === searchSeriesRequestSeq` (identischer Query-Text zweimal hintereinander würde den alten String-Guard :3114/:3211 austricksen — Seq-Guard schließt die Lücke, [advocatus] F3.3/F3.4), sonst still wie heute (:3210); bestehende String-Guards :3114/:3211 bleiben UNVERÄNDERT (keine Regression); `finally { clearTimeout(deadlineId); }` räumt den eigenen Timer, ohne fremde zu löschen. Harness (E3-AK5): Fake-Timer-Queue mit Delay-Schwelle — `setTimeout(fn, delay)`: `delay >= 30000` → registrieren (id-basiert, `clearTimeout` entfernt), sonst wie bisher sofort ausführen; Testseite löst Frist-Timer gezielt aus.
- **Alternativen:** Watchdog außerhalb von `searchSeries` (ROADMAP-Alternative) — verworfen: Alex wählte S4; Verlassen auf `abort(reason)`/`signal.reason` — verworfen (P4 bindend); „alle Timer in die Queue" — verworfen ([advocatus] F4.2: bräche implizite Sofortausführungs-Erwartungen, z. B. scrollIntoView-Timer; Bestands-Tests müssten mitschwingen); reiner Query-Guard ohne Seq — verworfen (Lücke F3.3).
- **Begründung:** 30 s ≈ 3-Fache typischer Laufzeiten (Kickoff F2-Plausibilisierung: `search_all_db` sequenziell, typisch < 10 s); Timeout im Kern wirkt automatisch auf alle sechs Aufrufer (:2989/:3017/:3069/:7564/:7566/:13185, B7-korrigiert).
- **Konsequenzen:** Hängt die Suche, wird nach 30 s abgebrochen, die Meldung erscheint im Suchbereich, die Sperre wird frei (Caller-`await` löst aus). Trade-off (Alex mit FP1 akzeptiert): ein legitimer Retry-Storm-Lauf kann bei ~30 s gekappt werden — erneut starten ist der Weg. Bestehende Tests bleiben grün, weil der Queue-Zweig nie automatisch feuert.

## 6. Dissens & Risiken

**Beleg-IOU (Präzedenz #75, Abschnitt 6):** Die wörtlichen Rohoutputs der Akt-2-Konsultation ([produktberater], [grafiker], [advocatus]) werden auf Anweisung des Akt-2-Auftrags NICHT vom Orchestrator abgeschrieben, sondern von Claude Code mechanisch per `opencode export` in diesen Session-Ordner archiviert (`docs/sessions/2026-10-18-roadmap74-staffel-kette/`). Alle Rollen-Zitate und -Nummern (F1.1–F9.3, Optionen A/B, MVP-Veto) in diesem Briefing sind wörtlich den Rollenantworten entnommen und der Archivierung vor Freigabepunkt 2 vorbehalten; die archivierten Originale ermöglichen Alex so die Stichprobe der Dissens-Punkte gegen die wörtlichen Rollen-Aussagen.

**Dokumentierter Dissens (Pflicht, alle Rollen mit Tag; verworfene Alternativen in ADRs/§4 begründet):**

1. **[produktberater] vs. [grafiker]/Plan — Banner-Hinweis:** [produktberater] hält den Hinweis für entbehrlich („Knopftext ist jetzt akkurat, MVP ohne Erklärung"); [grafiker] liefert Option B als Hinweis. Auflösung: Hinweis bleibt (FP1-Antwort verlangt Verständlichkeit ausdrücklich); [produktberater]s MVP-Veto als verworfene Alternative dokumentiert (ADR-K-1a). Restdissens: keiner — beide Seiten akzeptieren die Bindung.
2. **[produktberater] vs. Alex-Bindung — Staffel-Label:** „Staffel 1 (12 Folgen)" vs. bindendes Muster „Staffel N (k)" — Bindung gewinnt (ADR-K-2b).
3. **[produktberater] vs. Alex-FP1 — Bulk-Fehlerform:** [produktberater] schlug `alert()` vor; FP1-Antwort E2-F4 schreibt Inline-div vor — FP1 gewinnt (ADR-K-5).
4. **[grafiker] vs. [produktberater] — Alle-Knopf:** [grafiker] „Alle Staffeln (n)" neu rechts in der Staffel-Leiste + Header-Knopf „Starten"; [produktberater] „Alle starten". Auflösung: EIN Knopf am bestehenden Platz, Label „Alle verarbeiten" (Begründungen ADR-K-2c/d); [grafiker]s Doppel-Knopf-Variante verworfen (zwei Start-Orte für dieselbe Aktion, Label bei Einzelstaffel-Gruppen falsch).
5. **[grafiker] vs. Minimalismus — Fristmeldung zwei Zeilen mit Provider-Diagnose:** verworfen (Abschnitt 4); eine Zeile im Muster :3212.
6. **[advocatus] REVISE gegen den Vorgabetext — eingearbeitet:** F1.1 (Knopf-Disabled wirkungslos gegen 6-s-Neubau), F1.2 (atomares Prüfen+Setzen), F3.1 (Ablöse-Registry darf nicht verschwinden), F3.2 (Timeout abortiert nur den eigenen Controller), F3.3/F3.4 (Seq-Guard), F4.2 (Delay-Schwelle der Queue), F9.3 (`finally` vor Button-Restore) — alle in ADR-K-4/K-6 und den AKs operationalisiert. Verbleibender Dissens: [advocatus] F5.3 (`seasons`-Struktur) bewusst abgelehnt (Abschnitt 4) — dokumentiert, nicht ausgeräumt durch Setzung, sondern durch Begründung; kein Blocker.
7. **[advocatus] F6.2 (Map-Löschung am Banner-Rollback) vs. Analyse:** nach Durchdringung nicht nötig (Rollback trifft nie Gruppen mit Zeile) — als verworfen dokumentiert (Abschnitt 4).

**Verbleibende Risiken (nicht eliminierbar, nur behandelbar):**

- **R-A (Rest von #83):** Ein werfender `finally`-Block oder ein synchroner Wurf VOR der try-Struktur (z. B. :3080 fehlender DOM-Knoten) lässt die Sperre theoretisch offen — der Fall ist aber ohne hängenden fetch nie dauerhaft (Neuaufbau/Neuladen hilft) und E2 fängt die vier Startstellen konsistent ab. Akzeptiert.
- **R-B (30 s kappt legitime Langsuche):** von Alex mit FP1 bewusst gewählt; Meldung sagt „erneut versuchen".
- **R-C (6-s-Neuaufbau visuell):** Knopf-„wird gestartet…" kann durch Neuaufbau optisch verschwinden, während der Lauf läuft — rein kosmetisch, Sperre wirkt weiter (ADR-K-4). Nicht behoben (würde Render-Unterdrückung erfordern, Scope-Fremd).
- **R-D (E3-Harness als größter Eingriff ins Test-Setup):** Restrisiko, dass ein Bestandstest doch an Sofortausführung hängt; Gegenmaßnahme ist die Delay-Schwelle + Pflicht „keine Abschwächung" (E3-AK5) + Rot-/Grün-Beleg je Etappe.
- **R-E (Klassennamen-Irritation):** `.smart-inbox-group-banner-error` heißt „banner" und steht in Zeile/Leiste — bewusst hingenommen (Wiederverwendung > Namensreinheit; Umbenennen wäre Scope-Bruch).
- **Stichproben-pflichtige Themen (Geld, Aussenwirkung, Recht/Registrierung, Kaufentscheidungen):** KEINE berührt — reine lokale Frontend-Änderung, keine neuen Abhängigkeiten, keine Außenwirkung, keine Lizenzänderungen (siehe Abschnitt 7).

## 7. Quellen, Referenzen & Lizenzen

- **Kein neuer Third-Party-Code, keine neuen Assets, Fonts oder Icons.** Verwendet werden ausschließlich bereits im Projekt vorhandene Lucide-Inline-SVGs (ISC-Lizenz; das zap-SVG :13302 bleibt am Alle-Knopf, keine neuen Icons — [grafiker]-Ikonomie).
- **Referenzen nur als Muster, keine Kopiervorlagen:** `inbox_group_banner.test.js:55–93` (`validateSelector`) und `:1100` (Injektionsweg) — eigener Projekt-Code aus #75; `escapeHTML` :245; `bannerApplyErrors`-Muster :12477/:12844/:12852. Externe Apps (Plex/Staffel-Row, macOS Finder-Chips, Gmail-Inline-Fehler, [grafiker]) dienen ONLY als Layout-/Pattern-Idee; kein Code, kein Asset, kein Screenshot übernommen.
- **Serverseitig nur lesende Kontextprüfung:** `gui/mw_metadata.py:323`/:122–150 (Timeout-Kaskade) — unverändert, nicht Teil der Änderung.
- Unklare Lizenzen: keine.

## 8. Offene Fragen an Alex

Keine blockierenden Fragen. Mit FP2 sind ausschließlich die Wortlaute der UI-Text-Tabelle (ADR-K-2) freizugeben oder zu ändern — insbesondere (a) „Alle verarbeiten" und (b) der Banner-Hinweis; beide werden in der `ALEX_ZUSAMMENFASSUNG.md` ausdrücklich genannt (diese Datei wird nach dem plan-reviewer-APPROVE und VOR FP2 erstellt — kein toter Verweis, sondern geplante Reihenfolge). [produktberater]s MVP-Veto gegen den Hinweis (Dissens 1) ist die einzige Stelle, an der Alex gegen eine Rollen-Empfehlung explizit bestätigen möge. Stichproben-pflichtige Themen: keine (Abschnitt 6 R-Hinweis).

## 9. Aufwand (KI-Ausführung vs. menschlicher Engpass — strikt getrennt)

- **KI-Seite (Gate-A2-Läufe, schnell):** E1 ≈ 60–120 Worker-Minuten (Render + Handler + neue Testdatei mit strengem Mock); E2 ≈ 30–60 (drei catch/finally + zwei Meldungsstellen + Tests); E3 ≈ 60–120 (Timeout-Logik klein, aber Harness-Ersatz in vier Dateien + neue Frist-Testdatei). Je Etappe ein Lauf; Nachbesserung = nächster Lauf auf committetem Stand (Präzedenz #75: drei Läufe waren der Realitätsfall — Puffer einplanen).
- **Menschlicher Engpass (Alex + Claude Code):** je Etappe Ampel-Prüfung durch Claude Code (Rot-Probe, volle Suite im Worker-Image, Hintertür-Suche, Dateiliste, `git diff --check`) ≈ 30–60 min; echte Browser-Probe; EIN Rückkanal über den Gesamt-Diff (Alex-Review); EIN Handtest (≈ 20–30 min, Abschnitt 12); EIN PR/Merge. Gesamtdauer dominiert von Alex' Review-Zeit, nicht von der Implementierung.

## 10. Git-Zustand

Von Claude Code im Kickoff ausgeführt und offengelegt (diese Session hat kein `bash`): Branch `feat/roadmap-74-staffel-schnellauswahl` auf Stand `origin/main` (`d011499`), clean. Feature-Branch — kein harter main-Stop. Vor jedem Gate-A2-Lauf legt Claude Code den aktuellen `git status --short --branch` + `git log --oneline -5` erneut offen (Etappenbasis = committeter Stand der Vor-Etappe; docs-only Session-Commits sind nicht Teil der Worker-Basis, Präzedenz Abschnitt „Etappen"/Schritt 0).

## 11. Worker-Auftrag (Gate-A2-Pipeline, drei Läufe — je Etappe einer)

**Kontext:** Briefing-Abschnitte 3–7 sind verbindlich; AKs sind Testfälle, keine Wünsche. Aufruf je Etappe: `--task "Setze Etappe En aus dem Briefing um"` (n = 1, 2, 3) auf dem committeten Stand der Vor-Etappe; der Worker bearbeitet NUR die AKs und erlaubten Dateien seiner Etappe. `test_cmd` identisch zu `docs/sessions/2026-10-16-roadmap75-inbox-vorschlaege/briefing.md` Abschnitt 11 (ohne eigenes `timeout`; Pipeline-Limit `test_timeout_s` = 600 wegen der pip-Installation):

```bash
python3 -m pip install -q --user --break-system-packages -r requirements.txt pytest && python3 -m pytest -q -p no:cacheprovider --deselect tests/test_utils.py::TestMediawerkzeugLogic::test_conversion_estimation_test_encode && npm run test:frontend
```

```text
Medienwerkzeug Feature-Kette Etappe E<n>: Staffel-Schnellauswahl (#74) bzw.
sichtbare Start-Fehler (#80-Rest) bzw. 30s-Frist in searchSeries (#83) — nur
Frontend, ein Gate-A2-Lauf pro Etappe.

UI-Texte und Test-Erwartungen exakt nach Tabelle "Verbindliche UI-Texte
(UTF-8, exakt)" in ADR-K-2: echte Umlaute in UTF-8, Gedankenstrich U+2013;
keine ASCII-Umschrift in Oberfläche oder Tests. Übriger Text in diesem Auftrag
ist Umschrift, keine Vorgabe.

Kontext (Stand E1-Basis): gui/static/app.js — Modul-States :12471–12482
(bannerApplyErrors :12477, groupWorkflowRunning :12478), Banner-Apply-Handler
:12834–12857 (einziger appliedInboxGroups-Schreiber :12845, Ruecknahme :12850,
finally :12855), updateGroupBannerUI-Zeichnung :12679–12700 mit
Fehlerblock-Muster :12683/:12709, Bulk-Handler :12928–12998 (still
catch :12992–12997, alert() nur :12970/:12982–12984 — NICHT anfassen),
Gruppenzeile :13271–13379 (Knopf :13301–13303, Handler :13357–13375,
Mitglieder sortiert Staffel/Folge :12567–12570, items :12581,
inboxFilesEntryForItem :12499–12505), startSeriesGroupWorkflow :13005–13188
(synchron im Top, endet mit return searchSeries() :13184–13185), searchSeries
:3079–3214 (Registry currentSearchSeriesController :3076/:3085–3088,
String-Guards :3114/:3211, AbortError still :3210, Suchfehler-Zeile :3212),
Export-Block :13533–13559 (nur globalThis.X = X), 6-s-Takt :556 →
renderSmartInboxList :13234/:13265. index.html:9 style.css?v=51,
index.html:2760 app.js?v=103, app.js:1–9 neun Importe ?v=103.
style.css:3977 .smart-inbox-group-banner-error unscopiert — NICHT ändern.
tests/frontend/inbox_group.test.js: lockerer Mock (:21–62/:349–352, wirft
NICHT), Sofort-Timer-Stub :536, F2-Labeltest :1407–1448 (Assertion :1447),
Klick-Bestand :1348–1366/:1630–1673. tests/frontend/inbox_group_banner.test.js:
validateSelector :55–93, Injektionsweg :52/:551/:1100, Sofort-Stub :644,
Einzelstaffel-Fixtures :741–748/:1058–1061. tests/frontend/inbox_selection.test.js:
validateSelector :20–58, Sofort-Stub :557, Praeambel-Binding :585.
cache_busting.test.js :13–48 erzwingt app.js-Konsistenz, :50–64 nur
Nicht-Leere fuer style/utilities.

NUR diese Aenderungen je Etappe (Details/AKs im Briefing, Abschnitte 3 und
"Etappen"):
E1: Banner-Split + Hinweiszeile (ADR-K-1), Staffel-Leiste + Labels
(ADR-K-2/K-3), Sperre an allen vier Startstellen mit finally (ADR-K-4),
Cache-Buster v103→v104 an 10 Stellen, benannte Anpassung F2-Labeltest
:1407–1448, NEUE Datei inbox_group_seasons.test.js (strenger Mock nach
Banner-Muster, Mehrstaffel-Fixtures inkl. single_video_relpath, Harness-Anhang
nur fuer im Basis-Stand existierende Symbole).
E2: groupRowStartErrors-Map + bulkStartError-Variable (Deklaration neben
:12477–12478), catch/finally mit Inline-Meldung + console.error an
Alle-/Staffel-/Bulk-Start (ADR-K-5), Bulk-Template :12909–12917 um
Fehlerblock width:100% erweitern, E2-Tests in inbox_group_seasons.test.js
(Harness um werfenden triggerQualityHintUpdates-Stub nach Banner-Muster
erweitern). appliedInboxGroups in Staffel-/Bulk-Catches NIEMALS aendern.
E3: SERIES_SEARCH_TIMEOUT_MS=30000 + searchSeriesRequestSeq-Zaehler, lokaler
Controller pro Aufruf (Registry :3085–3087 bleibt Ablöse-Mechanismus),
didTimeout-Flag, Callback rendert NICHTS und wirft NICHT, Frist-Meldung im
catch nur bei didTimeout && seq===searchSeriesRequestSeq, clearTimeout im
finally (ADR-K-6); Timer-Stubs in allen vier Testdateien durch steuerbare
Queue mit Delay-Schwelle >= 30000 ersetzen (E3-AK5), NEUE Datei
series_search_timeout.test.js. Bestehende String-Guards :3114/:3211
UNVERAENDERT lassen.

ERLAUBTE DATEIEN gesamt (ausschliesslich): gui/static/app.js,
gui/static/index.html (nur Cache-Buster, nur E1),
tests/frontend/inbox_group.test.js (nur benannte Anpassung :1407–1448 in E1;
nur Timer-Stub-Ersatz in E3), tests/frontend/inbox_group_banner.test.js (nur
Timer-Stub-Ersatz in E3), tests/frontend/inbox_selection.test.js (nur
Timer-Stub-Ersatz in E3), tests/frontend/inbox_group_seasons.test.js (neu in
E1; E2/E3 ergaenzen bzw. Timer-Stub-Ersatz),
tests/frontend/series_search_timeout.test.js (neu in E3),
tests/frontend/cache_busting.test.js (nur falls erforderlich — erwartet:
nicht). Je Etappe hoechstens EINE neue Testdatei unter tests/frontend/.

NICHT ANFASSEN (auch nicht "nebenbei"): gui/api/**, gui/core/**,
gui/workers/**, gui/mw_metadata.py, gui/static/style.css, uebrige
gui/static/** (inkl. gui/static/js/**), uebrige tests/**, ROADMAP.md,
docs/** (inkl. docs/sessions/**), STAND.md, VERLAUF.md, scripts/**,
package.json, pytest.ini, API.md, README.md, data/**, .env (nie lesen).

Verbotenes naeher: keine Test-Weichen im Produktcode (Produktcode liest keine
globalen Variablen, die nur Tests setzen); Export-Block nur um
globalThis.X = X ergaeenzt; kein Loeschen/Abschwaechen bestehender
Assertions; kein Umbenennen von appliedInboxGroups-Pfaden; kein
alert()-Umbau im Bulk-Handler; kein flex-wrap-Refactor bestehender Zeilen —
neues Styling nur inline per cssText an NEUEN Knoten; mutable Modulzustaende
(Sperrflag, Fehler-Maps) NICHT per globalThis in Tests lesen (Wert-Binding
veraltet — Verhalten/DOM pruefen; Getter nur ueber Harness-Anhang ans
eval-Scope, Muster getActiveSeriesGroupName inbox_group.test.js:608).

Erfahrungswerte (verbindlich): keine echten Timer in Tests (Queue mit
Delay-Schwelle, E3); fetch-Spy in E3-Tests browser-treu — bei Abort des
signals mit AbortError REJECTEN (sonst erreichen Frist-Meldung und
Sperre-Frei den Test nie); Trailing Whitespace vermeiden; Diff je Etappe klein
halten (Reviewer-Prompt-Grenze ca. 120 KB); bestehende Muster nutzen:
escapeHTML, try/catch/finally, Handler direkt an den erzeugten Knoten
binden (Closure, kein Selektor-String mit group_key/Staffel);
Injektionsweg fuer E2-Fehler NUR werfender triggerQualityHintUpdates-Stub vor
dem eval (fetch-Stub erreicht den Caller-catch nie — Kickoff B6);
nachtraegliches Ueberschreiben von globalThis.startSeriesGroupWorkflow ist
wirkungslos und verboten (Handler rufen lokales Binding).

Schritt 0 vor dem ersten Code-Diff je Etappe: Etappenbasis verifizieren —
E1: app.js?v=103 an index.html:2760 und allen neun Importen,
groupWorkflowRunning nur :12478/:12835/:12838/:12855, Banner-Handler
:12834–12857, Gruppenzeile :13271–13379, F2-Labeltest :1407 vorhanden;
E2: E1-Endstand committet (v104, Staffel-Leiste vorhanden,
inbox_group_seasons.test.js vorhanden); E3: E2-Endstand committet,
Timer-Stubs :536/:644/:557 vorhanden. Bei Abweichung: STOPP + Rueckmeldung an
Claude Code/Alex — AKs werden NICHT autonom angepasst (Planaenderung =
Freigabepunkt).

Pflicht: feste Liste WOERTLICHER Rohausgaben bei der Uebergabe (keine
rekonstruierten Belege; jede Ausgabe mit Exit-Code), Muster
docs/sessions/2026-10-16-roadmap75-inbox-vorschlaege/briefing.md Abschnitt 11:
git status --short --branch; git log --oneline -5; git diff --stat
<basis>..HEAD; git diff --check <basis>..HEAD; volle Ausgabe + Exit des
pytest-Teils von test_cmd; volle Ausgabe + Exit von npm run test:frontend;
git diff --stat je eigenem Commit; zusaetzlich je Etappe Rot-Probe: die
NEUEN/ANGEPASSTEN Tests dieser Etappe gegen den Etappen-Basis-Stand (Stand der
Vor-Etappe) als ROT nachweisen, ohne neue globale Symbole aus app.js
vorauszusetzen (E1-AK9 inklusive — belegt, dass die Anpassung die Semantik
verschaerft statt nur umbenennt); E3 zusaetzlich: Bestand nach
Queue-Umstellung vollstaendig GRUEN (keine Abschwächung).
```

### Freigabe- und Prüfpfad (nicht Aufgabe des Workers — Claude Code)

1. **AK0** vor E1: volle Suite im Worker-Image, wörtliche Ausgaben → `ak0-ausgangsmessung.md`.
2. **Je Etappe Ampel-Prüfung** durch Claude Code nach Kit-Betriebsanleitung §9: Rot-Probe ohne neue Symbole gegen die Etappenbasis; volle Suite (`test_cmd`) im Worker-Image grün; Suche nach Test-Hintertüren (Produktcode liest keine testseitigen Globalen; Export-Block nur `globalThis.X = X`); Dateiliste exakt gegen die Erlaubnisliste der Etappe; `git diff --check` sauber; Etappendiff klein (≤ ~120 KB Reviewer-Grenze).
3. **Echte Browser-Probe** je Etappe (lokal, OrbStack/Wegwerf-Instanz; S5).
4. Nach Etappe 3: **ein Rückkanal** über den Gesamt-Diff (Kette), **ein Handtest** (Abschnitt 12), **ein PR** — Merge bleibt Klasse C bei Alex.

## 12. Handtest-Liste (lokal, vor Push/PR; Vorbereitung durch Claude Code)

Claude Code bereitet eine lokale Test-Inbox (keine echten NAS-Daten) mit: einer Seriengruppe mit ≥ 3 Staffeln (davon eine Staffel mit ≥ 2 Ordner-Folgen mit `single_video_relpath`), einer Einzelstaffel-Gruppe, einem Gruppennamen mit `&` und einem mit `"`. **Nach jedem Schritt einmal 6 Sekunden warten** (Neuaufbau durch `setInterval(loadStatus, 6000)`), damit Knöpfe frisch gebaut werden.

**E1 — Staffel-Auswahl:**
1. Inbox öffnen → Mehrstaffel-Gruppe im Banner: Hinweiszeile sichtbar; Klick „Als Serie gruppieren" → Banner-Knopf verschwindet, NICHTS startet (Ansicht bleibt), Gruppenzeile erscheint mit `Staffel N (k)`-Knöpfen (aufsteigend, Zahlen plausibel) und „Alle verarbeiten".
2. Einzelstaffel-Gruppe im Banner → Klick startet wie bisher sofort den Serien-Dialog.
3. „Staffel 2 (…)" klicken → Dialog/Dateiliste enthält genau die Folgen dieser Staffel.
4. Nach 6 s: Knöpfe erneut klicken → gleicher Effekt.
5. Doppelklick auf einen Staffel-Knopf / zweiter Knopf anderer Stelle während laufendem Start → passiert nichts (still), kein zweiter Dialog; nach Abschluss wieder normal startbar.
6. Gruppen mit `&` und `"`: Namen lesbar, kein kaputtes Markup, Knöpfe klickbar.

**E2 — Sichtbare Start-Fehler:**
7. Claude Code liefert den Provokationsweg (lokale, NICHT committete gepatchte Kopie mit werfender Stelle — der Fehler ist im echten Browser ohne Code-Eingriff nicht provozierbar, Präzedenz #75 Schritt 8): Fehler aus „Alle verarbeiten" → rote Inline-Meldung in der Gruppenzeile, `console.error` in der Konsole, Knopf wieder benutzbar.
8. Dasselbe für Staffel-Knopf und für „Ausgewählte als Serie verarbeiten" (Bulk-Leiste): Meldung INLINE in der Leiste, Auswahl bleibt gesetzt, kein `alert()`.
9. Meldung über 6 s stehen lassen → bleibt stehen; erfolgreicher Start derselben Stelle → Meldung weg.

**E3 — 30-Sekunden-Frist:**
10. Claude Code liefert den Weg für eine hängende Suche (z. B. Netzwerk-Drosselung/Proxy auf `/api/search`): Workflow-Start → nach ~30 s Meldung „Suchfehler: Zeitüberschreitung nach 30 Sekunden. Bitte erneut versuchen." im Suchbereich; Sperre frei → sofort neuer Start möglich.
11. Manuelle Suche (Knopf „Suchen"/Enter) ebenfalls mit hängender Verbindung → gleiche Meldung.
12. Schnelle normale Suche → Ergebnisse wie bisher, keine Fristmeldung.
13. NAS: erst nach Merge mit eigenem Go (S5) — hier nicht Teil des Handtests.
