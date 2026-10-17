---
kind: plan
status: approved
approved_by: alex
approved_on: 2026-10-17
approval_quote: "Briefing freigegeben, miss AK0 und starte den Gate-A2-Lauf."
source: roadmap#75
---

# Feature Briefing: #75 — Inbox-Gruppen: alle Vorschläge sichtbar, „Ignorieren" umkehrbar (plus Banner-Stelle aus #80)

**Quelle präzise:** `roadmap#75` (`ROADMAP.md:2068–2089`) in vollem Umfang **plus** ausschließlich die Banner-Stelle aus `roadmap#80` (`ROADMAP.md:2168–2179`: sichtbare Fehlermeldung + `console.error` beim Start aus dem Banner). Die zusätzlich verlangte Rücknahme von `appliedInboxGroups` im Fehlerfall stammt aus Alex' bindender Kickoff-Vorgabe 1 (`00-kickoff.md:29`), nicht aus dem #80-Text. Nicht enthalten: Bulk-Weg und Gruppenzeile aus #80, #74 (Staffel-Schnellauswahl — eigene Kette, das Banner darf sie nicht verbauen).

**Bindende Alex-Vorgaben (Kickoff `00-kickoff.md`, Vorgaben 1–6; nicht neu verhandelt):** (1) Scope wie oben, #74-Kompatibilität; (2) erster offener Vorschlag bleibt prominent, darunter aufklappbarer Bereich „Weitere Vorschläge (n)" mit je „Als Serie gruppieren" und „Ignorieren", Liste höhenbegrenzt/scrollbar; (3) Ignorier-Zustand in `localStorage`, Zähler/Rückweg nur für aktuell erkannte Gruppen, verwaiste Schlüssel stören nicht; (4) Rückweg „Ausgeblendete Vorschläge (n) – wieder anzeigen", einzeln und „alle", Rückweg bleibt sichtbar wenn nichts mehr offen, Banner darf nur bei null erkannten Gruppen leer/ausgeblendet sein; (5) Prüfstrategie (Sonderzeichen, keine Selektoren mit Gruppennamen ohne `CSS.escape`/besser Elementreferenzen, keine Test-Weichen, Export-Block nur `globalThis.X = X`, Testabdeckung, danach Browser-Probe + volle Suite im Worker-Image); (6) EIN Gate-A2-Lauf, Nachbesserung = Lauf 2 auf committetem Stand.

**Freigabepunkt 1 beantwortet (Alex, wörtlich 2026-10-17):** „Q1 C, Q2 A, Q3 A, Q4 A – starte Akt 2." → **Q1=C:** nur manuelles Wiederanzeigen; automatisches Zurückholen bei neuen Folgen = eigener ROADMAP-Punkt (Eintrag schreibt Claude Code); Speicherformat darf die Erweiterung nicht verbauen, diese Kette speichert/wertet nichts dafür. **Q2=A:** alte `sessionStorage`-Schlüssel `smart-inbox-ignore-group-*` werden ignoriert, kein Migrationscode. **Q3=A:** Fehler als Inline-Meldung im Banner + `console.error`, kein `alert`, keine neue Bibliothek. **Q4=A:** `gui/static/style.css` eng begrenzt erlaubt (Banner-Liste, Max-Höhe/Scroll, Aufklapp-Optik, Inline-Fehlerstil); bei Änderung `style.css?v=50` → `v=51`.

**Akt-2b-Freigabe (Alex, wörtlich 2026-10-17):** „Ja, Akt 2b mit F1–F3 wie empfohlen starten; Apply-Sperre und Bestandstest-Anpassung nehme ich an." → Damit sind die Apply-Sperre `groupWorkflowRunning` (Abschnitt 6 Dissens 5 / Abschnitt 8 Frage 2a) und die benannte Bestandstest-Anpassung `inbox_group.test.js:838–866` (Dissens 6 / Frage 2b) **angenommen** — keine offenen Fragen mehr, nur noch Festlegungen. Die Befunde F1–F3 der Plausibilitätsprüfung sind eingearbeitet (Übersicht: Abschnitt „Änderungen in Akt 2b" am Ende).

## 1. Problemstellung

Alex' Anlass (sinngemäß geglättet; das wörtliche Zitat inkl. Füllwörter steht in `ROADMAP.md:2070`): alle Zusammenziehvorschläge darstellbar machen und nach „Ignorieren" — etwa weil noch nicht alle Folgen da sind — einen Weg zurück geben. Verifiziert im Kickoff (B1–B3, gegen den Code bestätigt):

- **Das Banner zeigt immer nur einen Vorschlag.** `updateGroupBannerUI` (`gui/static/app.js:12594–12664`) sucht über `Object.entries(validGroups)` und bricht beim ersten offenen Kandidaten ab (`:12599–12610` mit `break`). Weitere Vorschläge sind erst sichtbar, wenn der aktuelle ignoriert oder angewendet wurde.
- **„Ignorieren" ist eine Sackgasse.** Der Klick schreibt `sessionStorage['smart-inbox-ignore-group-' + groupKey] = 'true'` (`:12634–12641`), gelesen in `:12601–12605`. Es existiert kein `removeItem` und kein UI-Weg zurück (nur neuer Tab oder Entwicklerwerkzeuge).
- **Der Fehlerfall ist stumm und hinterlässt Schmutz.** Im Apply-Handler wird `appliedInboxGroups.add(groupKey)` VOR dem Re-Render (`:12653–12654`) und vor `await startSeriesGroupWorkflow(...)` (`:12656`) gesetzt; der `catch` (`:12657–12662`) gibt nur den Button wieder frei — ohne Rücknahme der Markierung, ohne Meldung, ohne Log. Verschärfend (Kickoff B3-Nuance): durch das frühe Re-Render ist der referenzierte Button danach ein abgehängter DOM-Knoten — die Reaktivierung verpufft im Browser, während das Banner längst den nächsten Kandidaten zeigt. Das ist genau das in `ROADMAP #80` dokumentierte Muster „stiller `catch`-Block" (Befund aus #77, wo dieses Muster einen Selektor-Fehler bei `"` im Namen verbarg).

## 2. Zielnutzer

Alex, Einzelnutzer der lokalen Instanz und des NAS. Reale Situation: in der Inbox liegen mehrere Serien-Gruppen (z. B. drei Serien à mehrere Folgen); eine Serie soll „erstmal raushaben", weil noch Folgen fehlen, und später zurückgeholt werden. Der Live-Bestand (173 Ordner einer Serie) bildet EINE Gruppe — mehrere gleichzeitige Vorschläge entstehen, wenn mehrere Serien parallel in der Inbox liegen (Faustzahl [produktberater]: realistisch 1–3, selten mehr; Höhenbegrenzung/Scroll ist für Ausreißer da). Kein externer Nutzer, keine Server-/API-/Worker-Betroffenheit: reine Frontend-Änderung (`app.js`, eng begrenzt `style.css`, `index.html` nur Cache-Buster, Frontend-Tests).

## 3. Akzeptanzkriterien

AK0 ist Aufgabe von Claude Code (nicht des Workers). AK1–AK12 sind ausführbare Frontend-Tests; sie entstehen überwiegend in der NEUEN Datei `tests/frontend/inbox_group_banner.test.js` (ADR-75-6); AK11/AK12 betreffen Bestehendes. AK13/AK14 sind Review-/Hygiene-Kriterien (kein eigener Testlauf). Bestehende Tests bleiben grün, mit einer explizit benannten Ausnahme: der Banner-Ignorier-Bestandstest in `inbox_group.test.js:838–866` (Testname „AK3: …" aus der #65-Kette, nicht zu verwechseln mit dem neuen AK3 hier) wird an die neue Spezifikation angepasst (siehe AK11 — Anpassung, keine Abschwächung; von Alex angenommen, Zitat im Kopf dieses Briefings). Alle in AK1–AK11 genannten UI-Texte sind wörtlich durch die Tabelle „Verbindliche UI-Texte (UTF-8, exakt)" in ADR-75-1 gebunden (F2): echte Umlaute in UTF-8, Gedankenstrich U+2013; die Tests prüfen jeden Text der Tabelle mindestens einmal exakt — ASCII-Umschrift ist in Oberfläche und Tests verboten.

- [ ] **AK0 — Ausgangsmessung:** **Claude Code** misst VOR dem scharfen Gate-A2-Lauf im Worker-Image (kein Testlauf auf dem Host) die volle Suite mit dem Befehl aus Abschnitt 11 (`test_cmd`) und schreibt die wörtlichen Ausgaben mit Exit-Codes in `docs/sessions/2026-10-16-roadmap75-inbox-vorschlaege/ak0-ausgangsmessung.md`.
- [ ] **AK1 — mehrere Gruppen: alle offenen Vorschläge erreichbar:** Es prüft, dass bei drei erkannten Gruppen A, B, C die erste (A) prominent im Banner steht (Text + beide Buttons wie heute) und B, C im Bereich „Weitere Vorschläge (2)" (Text exakt nach UI-Text-Tabelle, F2) mit korrektem Zähler n erreichbar sind (je „Als Serie gruppieren" + „Ignorieren"); ist nur EINE Gruppe offen, existiert kein „Weitere Vorschläge"-Bereich.
- [ ] **AK2 — Ignorieren eines beliebigen Vorschlags:** Es prüft, dass „Ignorieren" bei einem NICHT-prominenten Vorschlag (B) den Schlüssel `smart-inbox-ignore-group-B` in `localStorage` schreibt und B aus den offenen Vorschlägen entfernt (A prominent, nur C in „Weitere Vorschläge (1)"), und dass der Zähler „Ausgeblendete Vorschläge (1)" erscheint (Zone-3-Label exakt nach UI-Text-Tabelle, F2).
- [ ] **AK3 — Persistenz über frischen Modulzustand:** Es prüft, dass ein Vorschlag nach erneutem Rendern mit FRISCHEM Modulzustand (zweiter `eval`-Durchlauf des Harness) bei gleichem `localStorage`-Inhalt ausgeblendet bleibt (funktionales `localStorage`-Mock mit Store außerhalb des evalten Codes, ADR-75-6; kein Auto-Clear zwischen den Durchläufen).
- [ ] **AK4 — Wiederanzeigen einzeln und „alle":** Es prüft, dass „Wieder anzeigen" den `localStorage`-Schlüssel der Gruppe entfernt und der Vorschlag wieder unter den offenen erscheint (Zähler sinkt); dass „Alle wieder anzeigen" die Schlüssel ALLER aktuell erkannten, ignorierten Gruppen entfernt und alle Vorschläge wieder offen sind (beide Knopftexte exakt nach UI-Text-Tabelle, F2).
- [ ] **AK5 — verwaiste Schlüssel zählen und stören nicht:** Es prüft, dass ein `localStorage`-Schlüssel `smart-inbox-ignore-group-GHOST` ohne aktuell erkannte Gruppe den Zähler „Ausgeblendete Vorschläge (n)" nicht erhöht, nicht in der Rückweg-Liste erscheint und von „Alle wieder anzeigen" NICHT entfernt wird (bleibt unangetastet liegen).
- [ ] **AK6 — Rückweg bleibt sichtbar / Banner leer bei null Gruppen:** Es prüft, dass nach Ignorieren ALLER aktuell erkannten Vorschläge das Banner sichtbar bleibt und nur die Rückweg-Zone zeigt (Zone-3-Label exakt nach UI-Text-Tabelle, F2); werden gar keine Gruppen erkannt (z. B. nur Einzelfolgen/Sperrfälle), ist das Banner ausgeblendet (`display: none`) und leer.
- [ ] **AK7 — alte `sessionStorage`-Schlüssel wirken nicht mehr (Q2=A):** Es prüft, dass ein vorab gesetzter `sessionStorage`-Schlüssel `smart-inbox-ignore-group-A = 'true'` den Vorschlag A NICHT ausblendet, und dass der Ignorier-Pfad kein `sessionStorage` mehr liest oder schreibt. Voraussetzung: funktionales `sessionStorage`-Mock in der neuen Testdatei (ADR-75-6c — mit einem No-op-Mock wäre der Nachweis trivial grün); der „liest/schreibt nicht"-Teil wird per Zähler/Spy am Mock ODER Store-Inhalts-Check geprüft (Wahl beim Worker, vgl. ADR-75-6c).
- [ ] **AK8 — Sonderzeichen im Gruppennamen:** Es prüft mit einem Gruppennamen, der `"`, `'`, `<` und `&` enthält (z. B. `Show "Special" <'Cut' & Co>`), in einer Testdatei mit SELEKTOR-STRENGEM Mock (Muster `validateSelector` aus `tests/frontend/inbox_selection.test.js:20–58`, wirft bei ungültigen Selektoren `SyntaxError`): Anzeige escaped (kein rohes `<`/`"` im gerenderten Textknoten), und Apply, Ignorieren, Zähler und einzelnes Wiederanzeigen funktionieren ohne Wurf.
- [ ] **AK9 — Fehlerfall beim Start aus dem Banner (F1-geändert):** Es prüft, dass wenn der Workflow-Start wirft, dann (a) `appliedInboxGroups` die Gruppe NICHT mehr enthält, (b) im neu gerenderten, sichtbaren Banner die Inline-Meldung mit festem Wortlaut „Serien-Start fehlgeschlagen. Bitte erneut versuchen." steht (exakt nach UI-Text-Tabelle, F2), (c) `console.error` mit der Fehlerursache aufgerufen wurde, und (d) die Gruppe wieder als offener Vorschlag erscheint. **Einziger Injektionsweg (F1):** ein werfender `triggerQualityHintUpdates`-Stub, gesetzt im TEST vor dem `eval` (Präambel-Binding-Muster `inbox_group.test.js:564`; synchroner Aufruf in `startSeriesGroupWorkflow`, `app.js:12887–12889`); der Stub wirft nur, solange eine **testseitige** Variable gesetzt ist, damit Setup-Pfade (u. a. `initEventListeners`, `app.js:2789`) nicht mitkippen — diese Weiche liegt ausschließlich im Testcode, der Produktivcode liest dafür nichts (AK13). Die `fetch`-Variante (`{ok:false}` für `/api/search`) ist als Injektionsweg **gestrichen**: `searchSeries` fängt ihre HTTP-/Formatwürfe intern (`app.js:3093`/`:3209–3213`), ihr Promise wird dadurch nie abgelehnt und der Banner-`catch` würde sie nie erreichen (Details ADR-75-4). Das nachträgliche Überschreiben von `globalThis.startSeriesGroupWorkflow` bleibt wirkungslos und verboten. Erfolgsfall unverändert: Gruppe bleibt angewendet, keine Meldung. **Zusätzlicher Test (F1):** Suchfehler nach Apply (`fetch`-Stub `{ok:false}` für `/api/search`) → die Gruppe **bleibt angewendet** und es erscheint **keine** Banner-Fehlermeldung; der Fehler steht als „Suchfehler" im Suchbereich (dokumentiert das tatsächliche vorbestehende Verhalten). Zusätzlich: es prüft, dass ein zweiter Apply-Klick während eines noch laufenden Starts keinen zweiten Workflow auslöst (Apply-Sperre `groupWorkflowRunning`, ADR-75-4 — von Alex angenommen, Zitat im Kopf dieses Briefings).
- [ ] **AK10 — Speicher verweigert:** Es prüft, dass der Banner bei werfendem `localStorage` (`getItem`, `setItem`, `removeItem` werfen) nicht crasht, normal rendert, ein „Ignorieren" die Gruppe für die Sitzung trotzdem ausblendet (In-Memory-Fallback) und der Speicherfehler per `console.warn` oder `console.error` protokolliert wird.
- [ ] **AK11 — Regressionen ausgeschlossen + benannte Bestandstest-Anpassung:** Es prüft, dass die Sortierung der Inbox-Liste unverändert bleibt (bestehende Sortier-Tests grün), der Bulk-Weg (`updateBulkActionsBarUI`) und die Gruppenzeile unverändert bleiben (bestehende Tests grün). Der Banner-Ignorier-Bestandstest `inbox_group.test.js:838–866` (Testname „AK3: …" aus der #65-Kette) wird NUR innerhalb seines Testblocks auf die neue Spezifikation umgestellt — der No-op-`localStorage`-Mock des Harness bei `:452–456` bleibt UNANGETASTET, stattdessen ersetzt der Testblock `globalThis.localStorage` nach `setupTestEnvironment()` durch ein funktionales Inline-Speicher-Objekt (wirkt, weil der Produktcode `localStorage` erst zum Aufrufzeitpunkt dynamisch liest). Ziel-Assertions wörtlich: (a) nach Klick auf „Ignorieren" liefert `localStorage.getItem('smart-inbox-ignore-group-Show')` exakt `'{"ignored":true}'`; (b) die Gruppe ist nicht mehr offener Vorschlag (kein `.btn-banner-apply-group`/„Als Serie gruppieren"-Knopf für „Show" im Banner); (c) das Banner bleibt SICHTBAR (`display !== 'none'`) mit Rückweg-Zähler „Ausgeblendete Vorschläge (1)" (Text exakt nach UI-Text-Tabelle, F2) — NEUE Spezifikation gemäß AK6/ADR-75-3, die alte „Banner wird ausgeblendet"-Assertion (`:865`) wird dadurch ERSETZT, nicht gestrichen ohne Ersatz; (d) `sessionStorage.getItem('smart-inbox-ignore-group-Show')` liefert `null` (es wird kein sessionStorage mehr geschrieben). Der Testname wird entsprechend angepasst (er darf nicht „saves to sessionStorage" behaupten). Das ist eine Anpassung an die geänderte Spezifikation auf gleicher Assertions-Ebene — kein Löschen, kein Abschwächen. Alle übrigen Tests in `inbox_group.test.js` bleiben unverändert grün.
- [ ] **AK12 — Cache-Buster:** `app.js?v=102` → `?v=103` in `gui/static/index.html:2760` UND allen neun ES-Modul-Importen `app.js:1–9`; falls `style.css` geändert wird (Q4=A): `style.css?v=50` → `?v=51` in `index.html:9`. `tests/frontend/cache_busting.test.js` bleibt grün — erzwingt aber nur die Konsistenz, nicht den Bump; der Bump ist über diesen AK + Abschnitt 11 + Review abgesichert ([advocatus] W3).
- [ ] **AK13 — keine Test-Weichen (Review-Kriterium, kein automatisierter Test):** Der Produktivcode liest keine globalen Variablen, die nur Tests setzen; der Export-Block `app.js:13318–13344` darf nur um `globalThis.X = X`-Zuweisungen ergänzt werden (idealerweise gar nicht — das Test-Harness exportiert selbst, Muster `inbox_group.test.js:583–618`). Verifikation: Reviewer liest den `app.js`-Diff; [produktberater]/[advocatus]-Versuchungen (Fehlerinjektions-Flag, `bannerDebugState`) sind ausgeschlossen.
- [ ] **AK14 — Hygiene:** `git diff --check` sauber (keine Trailing Whitespace); keine echten Timer in Tests (app.js-Timer stubben/abräumen — Erfahrungswert #65 Lauf B; das Harness stubbt `setInterval`/`setTimeout` bereits, `inbox_group.test.js:536–538`); keine Secrets; `.env` wird nie gelesen.

## 4. Bewusst verworfen (Scope-Eingrenzung)

- **Automatisches Zurückholen ignorierter Vorschläge bei neuen Folgen:** **verworfen für diese Kette** (Alex, wörtlich 2026-10-17: „Q1 C"). Wird eigener ROADMAP-Punkt; den Eintrag schreibt Claude Code, nicht dieser Lauf. Diese Kette speichert und wertet nichts dafür — nur das Format bleibt erweiterbar (ADR-75-2).
- **Migration alter `sessionStorage`-Schlüssel:** **verworfen** (Alex, wörtlich: „Q2 A"). Alte Markierungen verpuffen; AK7 hält das fest.
- **`alert` oder Toast-Bibliothek für den Fehlerfall:** **verworfen** (Alex, wörtlich: „Q3 A"; Kickoff-O3-Befund: keine allgemeine Toast-Funktion vorhanden, `showFskBatchError` `app.js:18056ff.` ist an `#fsk-batch-error-inline` gebunden und nicht übertragbar).
- **Zeitstempel/Zusatzwerte im Ignorier-Eintrag:** **verworfen** — [produktberater] Finding 10 schlug `{ignored, timestamp}` vor; ein Timestamp WÄRE „mehr speichern für später" und widerspricht Alex' Vorgabe Q1=C („diese Kette speichert nichts dafür"). Angenommen wird nur die reine JSON-Hülle `{"ignored": true}` (ADR-75-2).
- **Merkender Aufklapp-Zustand (über Render/Reload):** **verworfen** — [grafiker] Punkt 4: Aufwand ohne Nutzen; Banner wird bei jeder Aktion neu gezeichnet, beide Zonen starten eingeklappt.
- **Auto-Aufklappen ab n ≥ 3:** **verworfen** — [produktberater] Finding 2 nannte das als Option; Sonderfall-Logik im Diff für marginalen Gewinn. Immer eingeklappt, der Nutzer entscheidet.
- **Multi-Select, Filter, Suchfeld, Drag-and-drop, Animationen im Banner:** **verworfen** ([produktberater] Finding 7, Fallen-Liste) — der Worker baut nichts davon.
- **Bulk-Weg und Gruppenzeile aus #80:** bleiben unverändert (bindende Vorgabe 1); nur die Banner-Stelle wird angefasst.
- **#74 Staffel-Schnellauswahl:** eigene Kette; dieses Briefing verbaut sie nicht (Banner und `.smart-inbox-group-row` bleiben getrennt, keine ID-/Klassen-Kollisionen — [grafiker] Punkt 6).
- **Aufräumen verwaister `localStorage`-Schlüssel:** **verworfen** — unsichtbar, harmlos, kein Nutzer-Schaden ([produktberater] Finding 6: „Feature, kein Bug").
- **Server-seitiger Ignorier-Zustand / neue Endpunkte / Payload-Änderungen:** nichts davon; reine Client-Änderung.
- **Explizite „bereits angewendet"-Prüfung beim „Wieder anzeigen" ([produktberater] Finding 5, dort [wichtig]):** **verworfen, weil durch die Design-Semantik erledigt** — der Edge-Fall „ignoriert, später über anderen Weg (z. B. Bulk) angewendet, dann wieder angezeigt" kann nicht zur Doppelanzeige führen: Zonen 1/2 zeigen nur Kandidaten „nicht angewendet && nicht ignoriert" (ADR-75-1), und „Wieder anzeigen" ist reines `removeItem` + Fallback-Set-Löschung (ADR-75-3) — die Gruppe taucht nach dem Wiederanzeigen gerade NICHT als offener Vorschlag auf, es tritt also genau das vom [produktberater] angestrebte „still entfernen" automatisch ein; kein zusätzlicher Code (plan-reviewer Akt 2b, Einwand 1).

## 5. ADR-Blöcke

### ADR-75-1: Banner = prominenter erster Vorschlag + aufklappbare „Weitere Vorschläge (n)" (max-height/Scroll)
- **Entscheidung:** `updateGroupBannerUI` wird umgebaut: Zone 1 zeigt den ersten offenen Vorschlag in heutiger Optik (Wrapper `.smart-inbox-group-banner-primary`; Inhalt `.smart-inbox-group-banner-content` + `.smart-inbox-group-banner-actions` strukturell/textlich wie heute); Zone 2 „Weitere Vorschläge (n)" (aufklappbarer Button nach dem bestehenden Chevron-Muster mit `aria-expanded`, Standard: eingeklappt) listiert alle übrigen offenen Vorschläge mit je „Als Serie gruppieren" und „Ignorieren"; Zone 3 ist die Rückweg-Zone (ADR-75-3). Wird der prominente Vorschlag ignoriert oder angewendet, erscheint automatisch der nächste offene Kandidat auf Position 1 (kein „Nachrücken"-Zustand — einfach der erste offene Kandidat). Banner-Root wechselt auf `flex-direction: column`; bei genau einem offenen Vorschlag ohne ignorierte Gruppen ist der Zustand optisch wie heute.

**Verbindliche UI-Texte (UTF-8, exakt — F2, von Alex freizugeben als Teil dieses Briefings):** Alle Oberflächen-Texte und Test-Erwartungen verwenden exakt diese Schreibweisen — echte Umlaute in UTF-8, Gedankenstrich U+2013 wie in Alex' bindender Vorgabe 4 und `ROADMAP.md:2077`. ASCII-Umschrift („ae/oe/ue/ss", Bindestrich statt Gedankenstrich) ist in Oberfläche UND Tests verboten. Weicht eine Formulierung an anderer Stelle dieses Briefings davon ab, gilt ausschließlich diese Tabelle; die Tests in AK1/AK2/AK4/AK6/AK11 prüfen jeden Text mindestens einmal exakt.

| Stelle | Text (exakt) |
|---|---|
| Zone-2-Toggle | „Weitere Vorschläge (n)" |
| Zone-3-Toggle (Rückweg, complete Label) | „Ausgeblendete Vorschläge (n) – wieder anzeigen" |
| Zone-3-Kopf (nur falls Kopf und Toggle getrennt umgesetzt werden) | „Ausgeblendete Vorschläge (n)" |
| Einzel-Knopf (Zone 3) | „Wieder anzeigen" |
| Sammel-Knopf (Zone 3) | „Alle wieder anzeigen" |
| Apply-Knopf (Zonen 1 und 2) | „Als Serie gruppieren" |
| Ignore-Knopf (Zonen 1 und 2) | „Ignorieren" |
| Banner-Fehlermeldung (Zone mit betroffener Gruppe) | „Serien-Start fehlgeschlagen. Bitte erneut versuchen." |

(n = aktueller Zähler. Der in AK2/AK5/AK11 genannte Zähler-Text „Ausgeblendete Vorschläge (1)" ist der Präfix des Zone-3-Labels bzw. -Kopfs; Umlaute und Ziffer müssen exakt übereinstimmen.)

- **Alternativen:** flache Liste aller Vorschläge ohne prominente Erste ([produktberater] Position 1: einfacher — **abgelehnt**, weil Alex' Vorgabe 2 die prominente Erste Zone bindend verlangt); ein Banner pro Gruppe gestapelt (**abgelehnt** — visueller Lärm, Diff-Fläche, #74-Kollisionsgefahr).
- **Begründung:** Setzt die bindende Vorgabe 2 und den [grafiker]-Zustandsplan (a–e) 1:1 um; Höhenbegrenzung + Scroll fängt den Ausreißer-Fall ab, ohne die Inbox zu verdecken.
- **Konsequenzen:** `updateGroupBannerUI` wird deutlich größer (ein Umbau, kein Flickwerk); die Aufrufstelle `renderSmartInboxList` (`app.js:13045–13049`) und `detectInboxGroups` bleiben unverändert; der Leer-Zweig `:13302–13315` (keine Vorschläge → Banner aus) bleibt gültig.

### ADR-75-2: Ignorier-Zustand in localStorage, Schlüssel wie bisher, Wert JSON `{"ignored": true}`
- **Entscheidung:** Lesen/Schreiben über `localStorage`, Schlüssel `smart-inbox-ignore-group-<groupKey>` (Naming wie bisher). Geschriebener Wert: `JSON.stringify({ ignored: true })`. Lesung: `try/catch` — `getItem` liefert `null` oder wirft ⇒ nicht ignoriert; `JSON.parse`-Fehler ⇒ wie nicht ignoriert behandeln. Schreiben: `try/catch`; wirft `setItem`, wird die Gruppe zusätzlich in ein Modul-`Set` (In-Memory-Fallback, deklariert bei `appliedInboxGroups`, `app.js:12471–12477`) eingetragen und für die Sitzung ausgeblendet, plus `console.warn` — kein stilles Scheitern (Lektion #77/#80). `removeItem` (Wiederanzeigen) ebenfalls `try/catch` + konsistente Set-Pflege. „Ist ignoriert" = localStorage-Treffer ODER Fallback-Set.
- **Alternativen:** reiner String `'true'` wie heute (**abgelehnt** — [advocatus] W1 + [produktberater] 10: die spätere Q1-Erweiterung müsste String- und Objektformate im Lesepfad unterscheiden; JSON kostet heute nichts, und Q2=A macht den Anfang frei); JSON mit `timestamp` (**abgelehnt**, Abschnitt 4); Session-/Tab-Scope (**abgelehnt** — Persistenz über Reload ist genau der Nutzen).
- **Begründung:** Vorgabe 3 (bindend) + Q1=C: Format erweiterbar (später z. B. `episodeCount` als Zusatzfeld), ohne dass diese Kette mehr speichert oder auswertet als `ignored`.
- **Konsequenzen:** Der Wert ist kein `'true'`-String mehr; AK2/AK3/AK4 prüfen das JSON-Format. Kein Migrationspfad (Q2=A).

### ADR-75-3: Rückweg-Zone „Ausgeblendete Vorschläge (n) – wieder anzeigen" — berechnet aus validGroups, nie aus dem Storage
- **Entscheidung:** Zone 3 erscheint, wenn ≥1 AKTUELL erkannte Gruppe (Schlüssel aus `validGroups` = `detectInboxGroups`-Ergebnis) ignoriert ist. Zähler n und Liste entstehen durch Iteration über `validGroups` + Ignorier-Prüfung (ADR-75-2), NIE durch `Object.keys(localStorage)`/Präfix-Scan. „Wieder anzeigen" je Gruppe = `removeItem` + Fallback-Set-Löschung; „Alle wieder anzeigen" = `removeItem` für alle aktuell erkannten, ignorierten Gruppen (idempotent). Verwaiste Schlüssel bleiben liegen, zählen nicht, erscheinen nicht, werden nicht entfernt. Die Zone bleibt sichtbar, wenn keine offenen Vorschläge mehr da sind (Banner dann nur mit Zone 3); Banner komplett ausgeblendet nur bei null erkannten Gruppen.
- **Alternativen:** Storage-Scan über `localStorage.key(i)` mit Präfix-Splitting (**abgelehnt** — [advocatus] K6: Parserei, Sonderzeichen in Keys, Schlüssel anderer Tabs/Zwecke, widerspricht Vorgabe 3); nur ein globaler „Alle"-Knopf ohne Einzel-Wiederanzeigen (**abgelehnt** — Vorgabe 4 verlangt beides).
- **Begründung:** Vorgabe 3/4 (bindend) sind exakt diese Semantik; `validGroups` ist die einzige Quelle für „aktuell erkannt".
- **Konsequenzen:** Eine ignorierte Gruppe, die nicht mehr in der Inbox auftaucht (längst verarbeitet o. ä.), fällt automatisch aus Zähler und Liste — ohne Aufräumcode.

### ADR-75-4: Fehlerfall — Rücknahme + Re-Render + Inline-Meldung über Modul-State; Apply-Sperre während laufendem Start
- **Entscheidung:** Apply-Handler: `appliedInboxGroups.add(groupKey)` → `renderSmartInboxList(...)` (sofortiges Feedback wie heute) → `await startSeriesGroupWorkflow(groupKey, files)`; im `catch`: `appliedInboxGroups.delete(groupKey)` (Rücknahme, bindende Vorgabe 1), `console.error` mit der Fehlerursache, erneutes `renderSmartInboxList(...)` (Banner/Liste auf korrekten Stand), danach Setzen der Modul-State-Meldung `bannerApplyErrors` (Map `groupKey → Text`, deklariert bei `appliedInboxGroups`), die `updateGroupBannerUI` bei JEDEM Render in der betroffenen Zone als Inline-Block `.smart-inbox-group-banner-error` (`role="alert"`, `aria-live="polite"`) mit festem Wortlaut „Serien-Start fehlgeschlagen. Bitte erneut versuchen." zeichnet; die Meldung wird beim nächsten Apply-Versuch derselben Gruppe gelöscht (vor dem `add`). Ein Modul-Flag `groupWorkflowRunning` blockiert bannerseitig weitere Apply-Klicks, solange ein Start läuft (`finally`-Reset). **Reale Wurfquellen (F1-Korrektur, selbst verifiziert gegen `app.js`):** `searchSeries` (`:3079`) wirft bei HTTP-/Formatfehlern (`:3107`, `:3111`) innerhalb seines eigenen `try` ab `:3093`, das der `catch` `:3209–3213` vollständig abfängt (`AbortError`/veraltete Abfrage → `return`, sonst „Suchfehler: …" im Suchbereich `:3212`) — ihr Promise wird durch **diese Würfe** nie abgelehnt (theoretische synchrone Würfe *vor* dem internen `try`, `:3080–3091`, z. B. fehlendes Suchfeld-Element, wären Ausnahmen und würden über das `await` den Banner-`catch` erreichen — für das Testdesign folgenlos, weil der Stub-Wurf bei `:12887–12889` vor `:12969` liegt und `searchSeries` dann nie erreicht wird). `startSeriesGroupWorkflow` (`:12790`) ist synchron und gibt am Ende genau dieses Promise zurück (`:12969–12971`). Den Banner-`catch` erreichen daher praktisch ausschließlich **synchrone Würfe** in `startSeriesGroupWorkflow` (z. B. `triggerQualityHintUpdates` `:12887–12889`, DOM-/Selektorfehler der #77-Klasse) oder im Handler selbst (Programmierfehler) — NICHT Such-/Netzwerkfehler; die meldet `searchSeries` weiterhin selbst als „Suchfehler" im Suchbereich (vorbestehendes Verhalten, außerhalb Scope — Abschnitt 6). Der Handler-`try` muss den **Aufruf UND das `await`** von `startSeriesGroupWorkflow` umschließen (Bestandsstruktur `:12652–12656` beibehalten; der Aufruf darf nicht aus dem `try` wandern), damit ein synchroner Wurf gefangen wird.
- **Alternativen:** (a) `add → await → render bei Erfolg` (**abgelehnt** — [advocatus] K4: verlöre das sofortige „gruppiert"-Feedback und änderte mehr am Erfolgsverhalten); (b) Meldung direkt vor dem letzten Re-Render ins DOM schreiben (**abgelehnt** — `updateGroupBannerUI` ersetzt das Banner per `innerHTML` (`:12623`), die Meldung würde überschrieben); (c) `alert` (Q3=A verworfen); (d) nur Button-Reaktivierung wie heute (**abgelehnt** — B3-Nuance: abgehängter Knoten, verpufft).
- **Begründung:** „Fehler müssen sichtbar sein" (Hausregeln) + bindende Vorgabe 1. Der State-Ansatz überlebt jedes Re-Rendering und ist im Test deterministisch prüfbar (kein Timer — [advocatus] W5: das Harness führt `setTimeout` sofort aus, verzögerte Meldungen wären nicht testbar; die Meldung wird synchron zum Render gezeichnet).
- **Konsequenzen:** Neue Modul-Variablen (`bannerApplyErrors`, `groupWorkflowRunning`, Ignorier-Fallback-`Set`) im Deklarationsblock `app.js:12471–12477` ([advocatus] C1). Die Apply-Sperre ist eine NEUE, aus dem Multi-Button-Design abgeleitete Verhaltensregel (Abschnitt 6, Dissens 5) — **von Alex angenommen** (Zitat im Kopf dieses Briefings) — bewusst minimal: nur Banner-Apply-Pfad; Bulk-Weg bleibt unangetastet.

### ADR-75-5: Selektorsicherheit — Handler-Closures beim Rendern, keine dynamischen Selektor-Strings mit Gruppennamen
- **Entscheidung:** Alle Buttons (Apply/Ignore je Zone, „Wieder anzeigen" je Gruppe, „Alle wieder anzeigen") bekommen ihre `click`-Handler beim Rendern per `addEventListener` auf dem Elementknoten mit Closure über `groupKey`/`members` (Muster wie heute `:12634`/`:12643`, nur mehrfach). `querySelector` im Banner-Kode bleibt auf STATISCHEN Klassen-Selektoren beschränkt. Der Banner-Kode baut NIEMALS einen Selektor-String mit eingesetztem Gruppennamen. Anzeigewerte laufen über `escapeHTML` (`app.js:245`). `data-group-key`-Attribute dürfen für Debugbarkeit bleiben, werden aber nicht selektiert; alternativ numerische `data-group-index`-Attribute ([grafiker] Muster) — Wahl beim Worker, Bedingung: kein Selektor mit Namen.
- **Alternativen:** `CSS.escape` vor jeder Selektor-Interpolation (**abgelehnt als Primärmuster** — funktioniert, ist aber fehleranfällig und im Test-Mock nicht vorhanden, [advocatus] K1); Event-Delegation über `closest()` (**abgelehnt** — `closest` fehlt im Test-Mock, zusätzliche Mock-Arbeit, gleicher Effekt wie Closures).
- **Begründung:** Genau die #77/#80-Fehlerklasse (Sonderzeichen-Selektor-Wurf, stumm weggecatcht) wird an der Wurzel verhindert: es gibt keinen angreifbaren Selektor. Vorgabe 5 (bindend): „besser Elementreferenzen statt Selektoren".
- **Konsequenzen:** AK8 muss im strengen Selektor-Mock laufen (ADR-75-6), sonst ist er wertlos; der strenge Mock wirft bei `[data-group-key="A"B"]`-artigen Selektoren `SyntaxError`.

### ADR-75-6: Testarchitektur — neue Datei `inbox_group_banner.test.js` mit strengem Selektor-Mock + funktionalem localStorage-Mock; Bestand nur an einer benannten Stelle angepasst
- **Entscheidung:** Alle neuen Tests (AK1–AK10) entstehen in `tests/frontend/inbox_group_banner.test.js`: eigenes Harness (Muster `inbox_group.test.js:240–646`) mit (a) STRENGEM Selektor-Mock — `validateSelector`-Muster aus `inbox_selection.test.js:20–58`, validierte Element-/Dokument-`querySelector(All)` nach Muster `:368–378`/`:492–519`; (b) FUNKTIONALEM `localStorage`-Mock: `getItem`/`setItem`/`removeItem` auf einem Store-Objekt im TEST-Modulscope (außerhalb des `eval`ten Codes, analog `sessionStore` `inbox_group.test.js:12–19`), das den zweiten `eval`-Durchlauf überlebt und NICHT pro Setup automatisch geleert wird (AK3 braucht zwei frische Modulzustände bei gleichem Storage); (c) FUNKTIONALEM `sessionStorage`-Mock nach Muster `inbox_group.test.js:12–19` — ohne ihn wäre der AK7-Nachweis trivial grün; optional mit Schreib-Leser-Zähler am Mock, um „Ignorier-Pfad nutzt kein sessionStorage" automatisch zu belegen. `inbox_group.test.js` wird nur an EINER Stelle geändert: der Ignorier-Test `:838–866` wird innerhalb seines Testblocks auf die neuen Ziel-Assertions umgestellt (wörtlich in AK11 definiert; funktionaler `localStorage`-Mock als Inline-Swap nach `setupTestEnvironment()`, Harness-Mock `:452–456` bleibt unangetastet; Testname angepasst). Der laxere Bestand-Mock wird NICHT auf streng umgebaut.
- **Alternativen:** alles in `inbox_group.test.js` ergänzen (**abgelehnt** — [advocatus] K3: der Umbau des laxen Mocks auf streng lässt in 2221 Zeilen bisher still durchlaufene Templates werfen (Sub-Regression); Mock-Duplikation ist im Projekt bereits etablierter Zustand — `inbox_group` und `inbox_selection` duplizieren den Harness ebenfalls); No-op-`localStorage`-Mock belassen (**abgelehnt** — Persistenz-AK wäre nicht testbar, Kickoff B5).
- **Begründung:** Der strenge Mock ist die einzige Möglichkeit, die Browser-`SyntaxError`-Klasse automatisiert sichtbar zu machen (Vorgabe 5); der funktionale Mock ist Pflicht für Vorgabe 3.
- **Konsequenzen:** Fehlerfall-Injektion (AK9, F1-korrigiert) läuft **ausschließlich** über einen werfenden `globalThis.triggerQualityHintUpdates`-Stub VOR dem `eval` (die Harness-Präambel bindet ihn als `const`, Muster `inbox_group.test.js:564`; `startSeriesGroupWorkflow` ruft ihn synchron, `app.js:12887–12889`, ein synchroner Wurf erreicht so den Handler-`catch`). Der Stub wirft nur, solange eine **testseitige** Variable gesetzt ist — `triggerQualityHintUpdates` hat viele weitere Aufrufstellen in `app.js` (u. a. `:2789`, `initEventListeners`-Pfade), ein bedingungsloser Stub würde Setup-Pfade mitkippen lassen. Die Weiche liegt ausschließlich im Testcode, der Produktivcode liest nichts dafür (AK13). Ein `fetch`-Stub (`{ok:false}` für `/api/search`) erreicht den Banner-`catch` nie (`searchSeries` fängt intern, `app.js:3209–3213`) und ist als Injektionsweg gestrichen; als **Pending**-Promise bleibt ein `fetch`-Stub für den Apply-Sperre-Test zulässig (offener Start ohne Fehler, Abschnitt 6). NIE: `globalThis.startSeriesGroupWorkflow` nach dem `eval` überschreiben — der Apply-Handler ruft den lokalen Binding (`:12656`), die Überschreibung verpufft ([advocatus] K2, selbst verifiziert). Kein neuer globaler Lese-Punkt im Produktivcode (AK13).

### ADR-75-7: Cache-Buster + Style-Scope + ein Lauf
- **Entscheidung:** `app.js?v=102` → `?v=103` in `index.html:2760` und allen neun Importen `app.js:1–9`; `style.css` nur für die vier erlaubten Themen (Zonen-Layout/Max-Höhe/Scroll, Aufklapp-Optik, Inline-Fehlerstil; neue Klassen `.smart-inbox-group-banner-primary/-more/-ignored/-error/-toggle` nach [grafiker]-Skizze; nur bestehende Theme-Variablen `--text-main`, `--text-muted`, `--danger`, `--radius-md`; keine neuen Icons — vorhandene Lucide-Inline-SVGs genügen); bei `style.css`-Änderung `style.css?v=50` → `?v=51` in `index.html:9`. EIN Gate-A2-Lauf mit `test_cmd` aus Abschnitt 11 (bindende Vorgabe 6).
- **Alternativen:** Optik per Inline-Styles im JS (**abgelehnt** — Q4=A entschieden, schlechter wartbar); Bump dem `cache_busting.test.js` überlassen (**abgelehnt** — der Test prüft nur Konsistenz, nicht den Bump, `cache_busting.test.js:13–56`, [advocatus] W3).
- **Begründung:** Browser-Cache-Invalidierung ist bei `app.js`/`style.css`-Änderung Pflicht; der enge Style-Scope hält den Diff klein.
- **Konsequenzen:** Zwei Dateien mit Zeilen-Scope in Abschnitt 11; keine weiteren Cache-Buster-Fälle.

## 6. Dissens & Risiken

**Dissens 1 — Wortlaut „Ausgeblendete" vs. „Ignorierte" (entchieden gegen [produktberater]):** [produktberater] Finding 1 forderte durchgehend „Ignorieren/Ignorierte Vorschläge" und sah die Mischung mit „Ausgeblendete Vorschläge (n)" als inkonsistent an. **Verworfen:** Die Rückweg-Bezeichnung „Ausgeblendete Vorschläge (n) – wieder anzeigen" ist wörtlich in Alex' bindender Vorgabe 4 und in `ROADMAP.md:2077` festgeschrieben — Agenten dürfen bindenden Wortlaut nicht umbenennen. Der Button bleibt „Ignorieren" (wie heute), die Zone heißt „Ausgeblendete Vorschläge (n)". Konsistenz-Problem damit bewusst akzeptiert und Alex in der Zusammenfassung vorgelegt.

**Dissens 2 — Speicherformat (entchieden mit [advocatus]/[produktberater], gegen reinem String):** [advocatus] W1 und [produktberater] 10 empfehlen JSON statt `'true'`. Übernommen: `{"ignored": true}`. Nicht übernommen: der [produktberater]-Zusatz `timestamp` — das wäre für die Zukunft gespeicherter Mehrwert, den Q1=C („diese Kette speichert nichts dafür") ausschließt (Abschnitt 4).

**Dissens 3 — „Nachrücken" des prominenten Vorschlags (entchieden, eigentlich kein echter Widerspruch):** [produktberater] Finding 3 formuliert „kein Springen", [grafiker] Punkt 4 „der nächste rückt nach". In der Sache gleich: Es gibt keinen separaten „Prominenten-Platz"-Zustand — Zone 1 zeigt immer den ersten offenen Kandidaten, ohne Animation. Als Verhalten in ADR-75-1 festgeschrieben und in AK2/AK9d getestet.

**Dissens 4 — Aufklapp-Standardzustand (entchieden zugunsten der einfacheren Variante):** [produktberater] Finding 2 bot „eingeklappt, ab n ≥ 3 automatisch auf" oder „immer eingeklappt"; [grafiker] wollte immer eingeklappt. Übernommen: immer eingeklappt (keine Sonderfall-Logik, Abschnitt 4).

**Dissens 5 — Apply-Sperre während laufendem Start (neu aufgenommen nach [advocatus] K4 — von Alex angenommen, wörtlich 2026-10-17: „Ja, Akt 2b mit F1–F3 wie empfohlen starten; Apply-Sperre und Bestandstest-Anpassung nehme ich an."):** [advocatus] wies nach, dass das neue Design mehrere Apply-Buttons gleichzeitig sichtbar macht und der abgehängte-Button-Schutz (`btn.disabled`, `app.js:12645/12648`) nach dem Re-Render nicht greift — ein zweiter Klick auf eine andere Gruppe könnte parallel einen zweiten `startSeriesGroupWorkflow` starten und globale Zustände (`activeSeriesGroupFiles`, `currentProject`, `:12792–12799`) überschreiben. **Übernommen als ADR-75-4-Regel** (`groupWorkflowRunning`), weil die Gefahr erst durch die Mehr-Button-Sichtbarkeit dieser Kette entsteht und der Schutz ~5 Zeilen kostet. **Trade-off:** minimales, zusätzliches Verhalten über Alex' Fehlerfall-Vorgabe hinaus; Bulk-Weg bleibt ungesperrt (bewusst außerhalb Scope #80-Rest). **Status Akt 2b:** angenommen, keine offene Frage mehr.

**Dissens 6 — Testort und Mock-Strategie (entschieden nach [advocatus] K3 gegen „alles ergänzen"):** Die Aufgabe erlaubte „Ergänzung `inbox_group.test.js` ODER neue Datei". Gewählt: neue Datei `inbox_group_banner.test.js` (strenger Selektor-Mock + funktionale `localStorage`-/`sessionStorage`-Mocks), weil der Umbau des laxen Bestand-Mocks in 2221 Zeilen ein Sub-Regressionsrisiko ist. **Konflikt zur Aufgaberandbedingung „`inbox_group.test.js` nur ergänzen":** Der Bestandstest `:838–866` prüft `sessionStorage`-Verhalten, das es nach Q2=A/ADR-75-2 nicht mehr gibt, und seine Banner-Versteck-Assertion (`:865`) widerspricht der neuen Spezifikation (AK6: Rückweg bleibt sichtbar) — er muss an der benannten Stelle angepasst werden, sonst ist die Suite nicht grün, ohne dass der Worker „nur ergänzt" hätte. Das Briefing ordnet genau diese eine, namentlich benannte Anpassung an — **begrenzt auf den Testblock selbst** (funktionaler `localStorage`-Mock als Inline-Swap nach `setupTestEnvironment()`, damit der Harness-Mock `:452–456` unangetastet bleibt; Ziel-Assertions wörtlich in AK11 vorgegeben; Testname mit angepasst) — kein Löschen, kein Abschwächen. Das wurde Alex als bewusste, eng definierte Abweichung vorgelegt und ist **von Alex angenommen** (wörtlich 2026-10-17: „Ja, Akt 2b mit F1–F3 wie empfohlen starten; Apply-Sperre und Bestandstest-Anpassung nehme ich an."; Abschnitt 8, Frage 2b) — keine offene Frage mehr.

**Verbleibende Risiken (dokumentiert, nicht blockierend):**
- **Mock ≠ Browser:** Der strenge Selektor-Mock simuliert `SyntaxError`, aber echtes `querySelector`/`CSS.escape`/`dataset`-Verhalten, echte `localStorage`-Verweigerung (Privacy-Modus) und echter Reload sind nur im Handtest (Abschnitt 12) prüfbar ([advocatus] Frage 8).
- **Strenger Mock als Kopie:** Die neue Datei dupliziert ~500 Zeilen Harness — etabliertes Muster im Projekt, aber Wartungskosten; künftige Harness-Fixes müssen beide (drei) Dateien erwischen.
- **`triggerQualityHintUpdates`-Vor-`eval`-Stub ist der EINZIGE Injektionsweg (F1-korrigiert):** Der Stub muss testseitig variablen-gesteuert werfen — `triggerQualityHintUpdates` hat viele weitere Aufrufstellen in `app.js` (u. a. `:2789`, `initEventListeners`-Pfade); ein bedingungsloser Wurf ließe Setup-Pfade mitkippen (`DOMContentLoaded`/`initEventListeners` laufen im Harness zwar in `try/catch`, `inbox_group.test.js:622–627`, ein Mitkippen wäre trotzdem ein Test-Artefakt). Die Weiche liegt ausschließlich im Testcode (AK13). Ein `fetch`-Stub ist als Fehler-Injektionsweg ungeeignet und gestrichen — er erreicht den Banner-`catch` nie, weil `searchSeries` intern fängt (`app.js:3209–3213`, ADR-75-4/F1).
- **Suchfehler nach dem Gruppieren (F1, neu gefasst):** Schlägt die Suche nach erfolgreichem Gruppieren fehl (Backend/Netzwerk), bleibt die Gruppe als angewendet markiert; der Fehler erscheint als „Suchfehler: …" im Suchbereich (`app.js:3212`) — vorbestehendes Verhalten, außerhalb dieses Scopes; Kandidat für spätere Prüfung. AK9 enthält dazu einen dokumentierenden Test (Gruppe bleibt angewendet, KEINE Banner-Meldung).
- **Banner-Höhe bei vielen Gruppen:** max-height + Scroll ([grafiker] 220px, [produktberater] 300–400px) — Zahl nicht bindend, Worker wählt im Rahmen „höhenbegrenzt/scrollbar"; Sichtprüfung im Handtest.
- **#74-Kompatibilität ist nicht automatisierbar:** Kein Test kann die kommende #74 prüfen; Absicherung = keine IDs/Klassen-Kollisionen (nur `.smart-inbox-group-banner-*`-Klassen, `#smart-inbox-group-banner` bleibt die einzige Banner-ID) + Review.
- **Cache-Buster nicht test-erzwungen:** Der Bump `v=102→103` (+ ggf. `v=50→51`) steht nur in AK12/Abschnitt 11 und wird im Review am Diff geprüft ([advocatus] W3, ROADMAP #61 bekannt).
- **Zustand `groupWorkflowRunning` und Tests:** Der Harness führt `setTimeout` sofort aus; der Test muss den Start „offen" halten (Pending-`fetch`-Promise — zulässig: hier zählt das offene Promise von `searchSeries`, nicht die Fehlerinjektion, F1), um die Sperre zu prüfen — Umsetzungshinweis, kein Blocker.
- **Kein E2E gegen echten Server:** Frontend-Tests mocken `fetch` (Präzedenz #65/#71) — Abhilfe ist der Pflicht-Handtest (Abschnitt 12).

**Dissens-Dokumentation Rohoutputs:** Die ungekürzten Antworten von [produktberater], [grafiker] und [advocatus] archiviert Claude Code mechanisch per `opencode export` in diesen Ordner (Rollen-Dateien). Alle Rollenzitate dieses Briefings sind erst mit den archivierten Rohoutputs voll belegbar (IOU wie in `docs/sessions/2026-10-12-inbox-ordnerfolgen/briefing.md`, Abschnitt 6).

## 7. Quellen, Referenzen & Lizenzen

- **Kein Third-Party-Code, keine neuen Assets/Fonts/Icons/Bibliotheken.** Verwendete Lucide-Inline-SVGs (Layers, Chevron — ISC-lizenziert) sind bereits im Projekt vorhanden (`app.js:12625`, `:13079`); es werden keine neuen Icon-Sets eingeführt.
- **Referenz-Apps nur als Muster, nicht kopiert:** Gmail („alle anzeigen/weniger anzeigen"), Slack („X weitere Antworten", höhenbegrenzte Liste), Apple Mail (kontextnahe Inline-Fehlermeldung) — [grafiker]-Akt-2-Konsultation; übernommen werden nur Layout-Pattern, kein Code, keine Assets.
- **Interne Referenzen:** `ROADMAP.md:2068–2089` (#75), `ROADMAP.md:2168–2179` (#80, nur Banner-Stelle), `ROADMAP.md:2045–2065` (#74, nicht im Scope, Kompatibilität), `docs/sessions/2026-10-16-roadmap75-inbox-vorschlaege/00-kickoff.md` (B1–B7, O3, Q1–Q4), `docs/sessions/2026-10-12-inbox-ordnerfolgen/briefing.md` (Gate-A2-Format Abschnitt 11, `test_cmd`, Erfahrungswerte), `docs/sessions/2026-10-08-roadmap64-65-inbox/briefing-65.md` (Präzedenz Rückkanal/Handtest-Pfad).

## 8. Offene Fragen

1. **Alex-Go für den scharfen Gate-A2-Lauf** (Klasse B je Kette) nach Freigabe dieses Briefings. Verbindliche Reihenfolge (bindende Vorgabe 6): Freigabe (Freigabepunkt 2) → AK0-Ausgangsmessung durch Claude Code (`ak0-ausgangsmessung.md`) → Gate-A2-Lauf → Plausibilitätsprüfung (Claude Code) → Rückkanal-Abnahme → Patch-Übernahme/Commit → **Handtest lokal (Abschnitt 12) vor Push/PR** → Push/PR → Merge durch Alex (Klasse C) → kurzer NAS-Blick nach grüner Main-CI. Eine Nachbesserung wäre Lauf 2 auf dem committeten Stand von Lauf 1.
2. **Zwei bewusste Abweichungen/Neuigkeiten — von Alex angenommen (wörtlich 2026-10-17: „Ja, Akt 2b mit F1–F3 wie empfohlen starten; Apply-Sperre und Bestandstest-Anpassung nehme ich an."):** (a) Apply-Sperre `groupWorkflowRunning` (Dissens 5) — **angenommen**, bleibt in ADR-75-4/AK9; (b) die namentlich benannte Anpassung des Bestandstests `inbox_group.test.js:838–866` (Dissens 6) — **angenommen**; Anpassung begrenzt auf den Testblock, Ziel-Assertions wörtlich in AK11 (Texte verbindlich nach UI-Text-Tabelle, F2), Harness-Mocks bleiben unangetastet. Beide Punkte sind Festlegungen, keine offenen Fragen mehr.
3. **ROADMAP-Folgepunkt „automatisches Zurückholen" (Q1=C):** schreibt Claude Code nach der Freigabe, nicht dieser Lauf (`ROADMAP.md` ist im Worker-Lauf unerlaubt).
4. **Fehler-Provokation (F1-korrigiert):** Der Banner-Fehlerfall ist im echten Browser ohne Code-Eingriff **nicht provozierbar** — Backend stoppen oder `/api/search` blockieren ergibt „Suchfehler" im Suchbereich, nicht die Banner-Meldung (`searchSeries` fängt intern, `app.js:3209–3213`); ES-Module-Funktionen sind aus der DevTools-Konsole nicht austauschbar. Daher ist die Banner-Fehlermeldung **kein Handtest-Schritt für Alex**: Claude Code belegt sie in seiner Browser-Probe mit einer **lokal gepatchten Kopie** (nicht committet) und legt Screenshot + Konsolenausgabe vor. Optionaler Handtest-Sichtprüfungsschritt für Alex: Backend kurz stoppen → nach „Als Serie gruppieren" erscheint „Suchfehler" im Suchbereich (vorbestehendes Verhalten, außerhalb Scope).

Keine inhaltlichen Blocker offen; `design-frage`- und `sicherheits-frage`-Eskalationen sind durch die bindenden Vorgaben 1–6 und die Freigabepunkt-1-Antworten („Q1 C, Q2 A, Q3 A, Q4 A") beantwortet. Die Apply-Sperre (Frage 2a) und die Bestandstest-Anpassung (Frage 2b) sind von Alex angenommen (Zitat bei Frage 2); offen ist nur noch Freigabepunkt 2 auf dieses überarbeitete Briefing.

## 9. Aufwand (KI-Implementierung vs. menschlicher Engpass)

- **KI/Pipeline (schnell):** ein Gate-A2-Lauf; realistisch 1–2 Runden. Diff-Schätzung: `app.js` ~150–250 Zeilen (Umbau `updateGroupBannerUI` + Handlers + State), `style.css` ~40–80 Zeilen, `index.html` 2 Zeilen (Buster), neue Testdatei ~400–600 Zeilen (größtenteils Harness-Kopie), `inbox_group.test.js` ~10 Zeilen. Unter der Reviewer-Grenze (~120 KB).
- **Menschlicher Engpass (Alex, der Takt):** Briefing-Review + Freigabepunkt 2 (~10–15 min); nach dem Lauf: Plausibilitätsprüfung und Rückkanal (nicht Alex' Zeit, können aber Lauf 2 auslösen); **Handtest lokal ~15–20 min** mit von Claude Code vorbereiteten Testdaten (drei Serien-Gruppen inkl. Sonderzeichen-Namen); Merge (Klasse C); nach CI-Grün kurzer NAS-Blick (~2 min). Grob 30–40 min Menschenzeit, nicht Laufzeit.

## 10. Git-Zustand

Geliefert im Kickoff-Prompt (wörtlich übernommen; ich habe `bash: deny` und habe in dieser Session keinen Git-Befehl ausgeführt — und keine Git-Schreiboperation vorgenommen; Quelle: `00-kickoff.md`, Abschnitt „Git-Zustand"):

```text
$ git status --short --branch
## feat/roadmap-75-inbox-gruppen...origin/main
$ git log --oneline -3
34d621e fix(inbox): keep selection limited to current selectable entries (ROADMAP #77) (#154)
5c72af2 fix(search): match spelled-out season/episode names (ROADMAP #78) (#153)
b2adc8c fix(search): match episodes by season before episode number (ROADMAP #76) (#152)
```

Feature-Branch `feat/roadmap-75-inbox-gruppen`, kein main-Stop. Arbeitsverzeichnis: `/Users/alex/Documents/Medienwerkzeug/.worktrees/feat-roadmap-75-inbox-gruppen`. Diese Session schreibt ausschließlich unter `docs/sessions/2026-10-16-roadmap75-inbox-vorschlaege/`. Der Gate-A2-Lauf läuft in eigener Clone/Workspace der Kit-Pipeline; Patch-Übernahme/Commits/Push/PR bleiben bei Claude Code nach Alex-Go.

## 11. Worker-Auftrag (Gate-A2-Pipeline, ein Lauf)

**Kontext:** Briefing-Abschnitte 3–7 sind verbindlich; AKs sind Testfälle, keine Wünsche. `test_cmd` identisch zu `docs/sessions/2026-10-12-inbox-ordnerfolgen/briefing.md` Abschnitt 11 (ohne eigenes `timeout`; Pipeline-Limit `test_timeout_s` = 600 wegen der pip-Installation):

```bash
python3 -m pip install -q --user --break-system-packages -r requirements.txt pytest && python3 -m pytest -q -p no:cacheprovider --deselect tests/test_utils.py::TestMediawerkzeugLogic::test_conversion_estimation_test_encode && npm run test:frontend
```

```text
Smart-Inbox-Gruppenbanner: alle offenen Vorschlaege sichtbar, Ignorieren umkehrbar
(localStorage), Fehlerfall mit Ruecknahme + Inline-Meldung — ROADMAP #75 plus
Banner-Stelle aus #80 (ein Gate-A2-Lauf, nur Frontend).

UI-Texte und Test-Erwartungen exakt nach Tabelle „Verbindliche UI-Texte (UTF-8, exakt)"
(ADR-75-1): echte Umlaute in UTF-8, Gedankenstrich U+2013; keine ASCII-Umschrift in
Oberfläche oder Tests. Übriger Text in diesem Auftrag ist Umschrift, keine Vorgabe.

Kontext: gui/static/app.js: updateGroupBannerUI (:12594-12664, innerHTML-Template
:12623-12632, sessionStorage-Lesung :12601-12605, Ignore-Handler :12634-12641,
Apply-Handler :12643-12663 mit appliedInboxGroups.add VOR Re-Render VOR await,
catch nur Button-Freigabe), detectInboxGroups (:12509-12540, liefert validGroups
in Erkennungsreihenfolge), Renderstelle renderSmartInboxList (:13045-13049),
Leer-Zweig ohne Vorschlaege (:13302-13315, Banner display:none), Modul-States
currentSmartInboxRawSuggestions/appliedInboxGroups (:12471-12477), escapeHTML
(:245), startSeriesGroupWorkflow (:12790ff., SYNCHRON, gibt am Ende searchSeries() zurueck
:12969-12971; ruft triggerQualityHintUpdates synchron :12887-12889), searchSeries (:3079ff.,
async; fangt HTTP-/Formatwuerfe :3107/:3111 im internen try ab :3093 per catch :3209-3213 ab
('Suchfehler' im Suchbereich :3212) — ihr Promise wird dadurch NIE abgelehnt; den
Banner-catch erreichen praktisch nur synchrone Wuerfe (Details ADR-75-4), F1), Export-Block
(:13318-13344, darf nur um globalThis.X = X-Zuweisungen ergaenzt werden).
gui/static/index.html: style.css?v=50 (:9), app.js?v=102 (:2760); neun Importe
app.js:1-9 mit ?v=102. gui/static/style.css: #smart-inbox-group-banner +
.smart-inbox-group-banner-content/-actions (:3866-3894), Responsive ~:4067.
Theme-Variablen: --text-main, --text-muted, --danger, --radius-md.
tests/frontend/inbox_selection.test.js: validateSelector (:20-58, wirft
SyntaxError), validierende Element-/Dokument-querySelector (:368-378, :492-519).
tests/frontend/inbox_group.test.js: sessionStorage-Mock funktional (:12-19),
localStorage-Mock NO-OP (:452-456), Harness evalt app.js frisch pro
setupTestEnvironment (:554-620, eval :620), Praeambel-Stubs via globalThis
(:560-581), eigener Export-Block des Harness (:583-618), Ignorier-Bestandstest
(:838-866), Timer-Stubbing (:536-538).

NUR diese Aenderungen:
1. app.js updateGroupBannerUI umbauen (ADR-75-1/3/5): Zone 1 = erster offener
   Vorschlag (Optik/Wortlaut wie heute), Zone 2 = aufklappbarer Bereich
   "Weitere Vorschläge (n)" (Standard eingeklappt, aria-expanded, Chevron-
   Muster, max-height + overflow-y:auto) mit je "Als Serie gruppieren" +
   "Ignorieren", Zone 3 = "Ausgeblendete Vorschläge (n) – wieder anzeigen"
   mit "Wieder anzeigen" je ignorierte, aktuell erkannte Gruppe + "Alle wieder
    anzeigen". n in Zone 2 = Anzahl der offenen Vorschlaege minus 1 (Zone entfaellt
   bei 0); Zone 3 entfaellt bei 0 ignorierten, aktuell erkannten Gruppen;
   Banner bleibt sichtbar, wenn nur Zone 3 existiert; Banner display:none +
   innerHTML="" nur wenn validGroups leer ist. Kein separater
   "Prominent-Nachruecken"-Zustand: Zone 1 zeigt immer den ersten offenen
   Kandidaten.
2. app.js Ignorier-Zustand auf localStorage umstellen (ADR-75-2/3): Schluessel
   'smart-inbox-ignore-group-' + groupKey, Wert
   JSON.stringify({ignored:true}); Lesung try/catch (null/Wurf/Parse-Fehler =
   nicht ignoriert); Zaehler und Rueckweg NUR ueber validGroups, niemals
   Object.keys(localStorage) oder key(i)-Scan; removeItem einzeln und "alle"
   ueber die aktuell erkannten, ignorierten Gruppen (idempotent); kein
   sessionStorage-Lesen/-Schreiben mehr an dieser Stelle, keine Migration.
   sessionStorage-Kode in updateGroupBannerUI ersatzlos entfernen.
3. app.js Fehlerfall + Sperre (ADR-75-4; Sperre von Alex angenommen 2026-10-17):
   Apply-Handler: try umschliesst Aufruf UND await von startSeriesGroupWorkflow
   (Bestandsstruktur :12652-12656 beibehalten — nur synchrone Wuerfe aus
   startSeriesGroupWorkflow/Handler erreichen den catch; searchSeries nicht
   aendern, Suchfehler meldet es selbst im Suchbereich, F1). Apply-Handler
   catch fuehrt aus:
   appliedInboxGroups.delete(groupKey); console.error mit Fehler;
   renderSmartInboxList(...); danach bannerApplyErrors.set(groupKey,
   'Serien-Start fehlgeschlagen. Bitte erneut versuchen.') — die Meldung wird
   von updateGroupBannerUI bei jedem Render in der betroffenen Zone als Block
   .smart-inbox-group-banner-error (role="alert", aria-live="polite")
   gezeichnet und beim naechsten Apply-Versuch derselben Gruppe vor dem add
   geloescht. Modul-Flag groupWorkflowRunning: waehrend eines laufenden
   Banner-Starts ignorieren weitere Apply-Klicks im Banner (finally-Reset);
   Ignorier-/Wiederanzeigen-Klicks bleiben moeglich. Erfolgsfall unveraendert.
   Neue Modul-Variablen (bannerApplyErrors, groupWorkflowRunning,
   Ignorier-Fallback-Set) im Deklarationsblock :12471-12477 deklarieren.
4. app.js Speicher-verweigert-Fallback (ADR-75-2): wirft localStorage.setItem,
   Gruppe in In-Memory-Set eintragen (fuer die Sitzung ausgeblendet) +
   console.warn; wirft getItem/removeItem: wie nicht ignoriert bzw.
   idempotent behandeln; kein leerer catch ohne Log; Banner rendert weiter.
5. Selektorsicherheit (ADR-75-5): alle Klick-Handler per addEventListener mit
   Closure auf dem gerenderten Elementknoten; KEIN querySelector-String mit
   eingesetztem Gruppennamen (data-group-key-Attribute duerfen bleiben, werden
   nicht selektiert); Anzeige der Gruppennamen weiterhin ueber escapeHTML.
6. Cache-Buster: index.html:2760 und ALLE neun app.js:1-9-Importe v102 -> v103;
   index.html:9 style.css v50 -> v51 (style.css wird geaendert).
7. style.css (nur Banner-Stelle, ADR-75-7): Zonen-Layout (Banner-Root
   flex-direction column), Listen max-height + Scroll, Aufklapp-Toggle-Optik,
   Inline-Fehlerstil (.smart-inbox-group-banner-error). Nur bestehende
   Theme-Variablen, keine neuen Icons, keine anderen Selektoren als
   #smart-inbox-group-banner/.smart-inbox-group-banner-*.

Akzeptanzkriterien (Tests: NEUE Datei tests/frontend/inbox_group_banner.test.js
mit strengem Selektor-Mock (validateSelector-Muster inbox_selection.test.js
:20-58), funktionalem localStorage-Mock (Store im Test-Modulscope, ueberlebt
zweite evals, kein Auto-Clear) UND funktionalem sessionStorage-Mock (Muster
inbox_group.test.js:12-19; ohne ihn ist AK7 trivial gruen; AK7-Nachweis per
Spy oder Store-Inhalts-Check, Wahl beim Worker);
tests/frontend/inbox_group.test.js NUR den Testblock :838-866 anpassen —
Harness-Mocks (:452-456) bleiben unangetastet, stattdessen im Testblock nach
setupTestEnvironment() globalThis.localStorage auf ein funktionales
Inline-Speicher-Objekt setzen (Produktcode liest localStorage erst zum
Aufrufzeitpunkt) und wörtlich diese Ziel-Assertions setzen: (a)
localStorage.getItem('smart-inbox-ignore-group-Show') === '{"ignored":true}',
(b) kein .btn-banner-apply-group fuer 'Show' mehr im Banner, (c) Banner bleibt
sichtbar (display !== 'none') mit "Ausgeblendete Vorschläge (1)", (d)
sessionStorage.getItem('smart-inbox-ignore-group-Show') === null; Testname
mit anpassen (er darf nicht mehr "saves to sessionStorage" behaupten); kein
Loeschen, kein Abschwaechen; alle sonstigen Bestands-Tests unveraendert
gruen):
- Es prueft, dass bei drei Gruppen A/B/C A prominent ist und B, C unter
  "Weitere Vorschläge (2)" (exakt nach UI-Text-Tabelle) mit je beiden Buttons
  erreichbar sind; bei nur einem offenen Vorschlag existiert kein
  "Weitere Vorschläge"-Bereich (AK1).
- Es prueft, dass "Ignorieren" bei B den localStorage-Schluessel
  smart-inbox-ignore-group-B mit JSON-Wert {"ignored":true} schreibt, B aus den
  offenen Vorschlaegen faellt und "Ausgeblendete Vorschläge (1)" erscheint
  (exakt nach UI-Text-Tabelle) (AK2).
- Es prueft, dass nach frischem Modulzustand (zweiter eval) bei gleichem
  localStorage-Inhalt B ausgeblendet bleibt (AK3).
- Es prueft, dass "Wieder anzeigen" den Schluessel entfernt und B wieder offen
  ist; "Alle wieder anzeigen" alle aktuell erkannten Ignorier-Schluessel
  entfernt (AK4).
- Es prueft, dass ein Schluessel smart-inbox-ignore-group-GHOST ohne
  erkannte Gruppe weder gezaehlt noch angezeigt noch von "alle" entfernt wird
  (AK5).
- Es prueft: alle offen ignoriert -> Banner sichtbar, nur Rueckweg-Zone; keine
  Gruppe erkannt -> Banner display:none und leer (AK6).
- Es prueft, dass ein vorab gesetzter sessionStorage-Schluessel
  smart-inbox-ignore-group-A='true' A NICHT ausblendet (AK7).
- Es prueft mit Gruppennamen aus ", ', <, & (z.B. Show "Special" <'Cut' & Co>)
  im STRENGEN Mock: Anzeige escaped, Apply, Ignorieren, Zähler, einzelnes
  Wiederanzeigen ohne SyntaxError (AK8).
- Es prueft den Fehlerfall: EINZIGER Injektionsweg ist ein werfender
  triggerQualityHintUpdates-Stub VOR dem eval (Praeambel-Binding-Muster
  inbox_group.test.js:564; wirft nur bei gesetzter TESTSEITIGER Variable, damit
  Setup-Pfade wie initEventListeners/app.js:2789 nicht mitkippen — Weiche
  ausschliesslich im Testcode, Produktcode liest nichts dafuer, AK13). KEIN
  fetch-Stub als Fehlerquelle: searchSeries fangt eigene Wuerfe intern
  (app.js:3093/:3209-3213), {ok:false} erreicht den Banner-catch nie (F1). KEIN
  ueberschreiben von globalThis.startSeriesGroupWorkflow nach dem eval —
  verpufft, Handler ruft lokalen Binding app.js:12656. Dann: appliedInboxGroups
  ohne Gruppe, Inline-Meldung exakt "Serien-Start fehlgeschlagen. Bitte erneut
  versuchen." im neu gerenderten sichtbaren Banner, console.error aufgerufen,
  Gruppe wieder offener Vorschlag; Erfolgsfall unveraendert; zweiter
  Apply-Klick waehrend laufendem Start loest keinen zweiten Workflow aus
  (AK9, Sperre von Alex angenommen). ZUSAETZLICHER TEST: fetch-Stub {ok:false}
  fuer /api/search NACH Apply -> Gruppe bleibt angewendet, KEINE Banner-
  fehlermeldung, "Suchfehler" im Suchbereich (dokumentiert das reale
  vorbestehende Verhalten).
- Es prueft: localStorage wirft bei getItem/setItem/removeItem -> kein Crash,
  Banner rendert, Ignorieren wirkt per In-Memory-Fallback fuer die Sitzung,
  console.warn/console.error aufgerufen (AK10).
- Es prueft Regression: Sortierung unveraendert, Bulk-Weg und Gruppenzeile
  unveraendert (Bestands-Tests gruen, inkl. angepasster :838-866) (AK11).
- cache_busting.test.js gruen; app.js?v=103 in index.html:2760 UND allen neun
  Importen app.js:1-9; style.css?v=51 in index.html:9 (AK12; der Test erzwingt
  nur Konsistenz — der Bump wird am Diff geprueft).
- Keine Test-Weichen: Produktcode liest keine globalen Variablen, die nur
  Tests setzen; Export-Block :13318ff. nur ggf. um globalThis.X = X-Zuweisungen
  erweitert (AK13, Review-Kriterium).
- git diff --check sauber; keine Trailing Whitespace; keine echten Timer, die
  Tests stehen lassen (Harness-Stubbing :536-538 nutzen); Diff klein halten
  (Reviewer-Prompt-Grenze ca. 120 KB); .env nie lesen.

ERLAUBTE DATEIEN (ausschliesslich):
gui/static/app.js (nur updateGroupBannerUI + neue Modul-States + Handler;
Export-Block nur globalThis.X = X), gui/static/style.css (nur die vier
Banner-Themen Punkt 7), gui/static/index.html (nur Cache-Buster Zeilen :9 und
:2760), tests/frontend/inbox_group_banner.test.js (genau eine neue Datei),
tests/frontend/inbox_group.test.js (NUR Anpassung Test :838-866).

NICHT ANFASSEN (auch nicht "nebenbei"): gui/api/**, gui/core/**,
gui/workers/**, uebrige gui/static/** (inkl. gui/static/js/**, parse.js),
uebrige tests/**, ROADMAP.md, STAND.md, VERLAUF.md, docs/** (inkl.
docs/sessions/**), scripts/**, package.json, pytest.ini, API.md, README.md,
data/**, .env (nie lesen).
```

**Erfahrungswerte (verbindlich):** Frontend-Tests müssen Timer aus `app.js` stubben/abräumen (Bestandsharness tut das bereits — neue Datei übernimmt das Muster); keine echten Timer; Inline-Meldung synchron zum Render (kein `setTimeout`) — das Harness führt `setTimeout` sofort aus, Timing ist nicht testbar; Trailing Whitespace vermeiden; Diff klein halten (~120 KB Reviewer-Grenze); bestehende Muster nutzen: `escapeHTML`, `try/catch` um Storage-Zugriffe (Vorbild `:12601–12605`, aber NICHT der leere catch — Log Pflicht).

**Schritt 0 vor dem ersten Code-Diff:** Basis ist `origin/main` @ `34d621e` (Stand des Kickoff-Git-Zustands, Abschnitt 10); ein etwaiger Session-Head mit docs-only-Commits im Worktree-Branch (diese Briefing-Dateien) ist NICHT Teil der Worker-Basis — Präzedenz `docs/sessions/2026-10-12-inbox-ordnerfolgen/briefing.md` AK0. Verifikation: `app.js?v=102` an `index.html:2760` und allen neun Importen `app.js:1–9`; `style.css?v=50` an `index.html:9`; `updateGroupBannerUI` mit `break`-Kandidatensuche um `:12599–12610`; `sessionStorage`-Schlüssel nur noch `:12603`/`:12637`; Ignorier-Bestandstest `inbox_group.test.js:838–866`; `validateSelector` `inbox_selection.test.js:20–58` vorhanden. Bei Abweichung: STOPP + Rückmeldung an Claude Code/Alex — AKs werden NICHT autonom angepasst (Planänderung = Freigabepunkt).

**Pflicht: feste Liste WÖRTLICHER Rohausgaben bei der Übergabe** (keine rekonstruierten Belege; jede Ausgabe mit Exit-Code), Muster `docs/sessions/2026-10-12-inbox-ordnerfolgen/briefing.md` Abschnitt 11: `git status --short --branch`; `git log --oneline -5`; `git diff --stat <basis>..HEAD`; `git diff --check <basis>..HEAD`; volle Ausgabe + Exit des pytest-Teils von `test_cmd`; volle Ausgabe + Exit von `npm run test:frontend`; `git diff --stat` je eigenem Commit; zusätzlich Rot-Proben: (1) die neuen Banner-Tests gegen den ALTEN Stand (vor dem Fix) als ROT nachweisen; (2) auch der ANGEPASSTE Bestandstest `:838–866` muss gegen den alten `app.js`-Stand ROT sein (belegt, dass die Anpassung die Semantik verschärft statt nur umbenennt).

## 12. Handtest-Liste (lokal, vor Push/PR)

Vorbereitung durch **Claude Code**: lokale Test-Inbox mit künstlichen Serien-Dateien (keine echten NAS-Daten), mindestens **drei Seriengruppen**, davon eine mit `\"` (Anführungszeichen) und eine mit `'` (Apostroph) im Gruppennamen, dazu ein Fall mit `<`/`&`. Die Banner-Fehlermeldung ist **kein Handtest-Schritt für Alex** (F1/Abschnitt 8, Frage 4): Sie ist im echten Browser ohne Code-Eingriff nicht provozierbar; Claude Code belegt sie in seiner Browser-Probe mit einer lokal gepatchten Kopie (nicht committet) und legt Screenshot + Konsolenausgabe vor.

Schritte (Alex führt aus, ~15–20 min):

1. **Alle Vorschläge sehen:** Inbox öffnen → Gruppe 1 prominent im Banner, Gruppen 2+3 unter „Weitere Vorschläge (2)" — aufklappen, beide Zeilen mit je „Als Serie gruppieren" + „Ignorieren" sichtbar.
2. **Mittleren ignorieren:** „Ignorieren" bei Gruppe 2 → sie verschwindet aus den offenen Vorschlägen; „Ausgeblendete Vorschläge (1)" erscheint.
3. **Persistenz:** Seite neu laden (F5) → Gruppe 2 bleibt ausgeblendet, Zähler steht noch auf 1.
4. **Zähler/Rückweg einzeln:** „Ausgeblendete Vorschläge (1)" aufklappen → „Wieder anzeigen" → Gruppe 2 ist wieder offen, Zähler 0, Zone verschwindet.
5. **Alle:** Gruppe 2 und 3 ignorieren → „Alle wieder anzeigen" → beide wieder offen.
6. **Rückweg bleibt:** alle drei Gruppen ignorieren → Banner bleibt sichtbar und zeigt nur die Rückweg-Zone mit (3); nichts ist „weg".
7. **Sonderzeichen:** Gruppen mit `"`, `'`, `<`/`&` ansehen (Namen korrekt lesbar, kein kaputtes Markup), eine davon ignorieren und wieder anzeigen, eine davon mit „Als Serie gruppieren" starten (Arbeitsansicht öffnet sich wie bisher).
8. **Suchfehler-Sichtprüfung (optional, kein Abnahmekriterium — F1):** Backend-Dienst kurz stoppen → nach „Als Serie gruppieren" erscheint „Suchfehler" im Suchbereich; die Gruppe bleibt als angewendet markiert (vorbestehendes Verhalten, außerhalb Scope). Die Banner-Fehlermeldung „Serien-Start fehlgeschlagen. Bitte erneut versuchen." ist ohne Code-Eingriff nicht provozierbar und wird von Claude Code mit lokal gepatchter Kopie belegt (Screenshot + Konsolenausgabe, nicht committet).
9. **Sortierung:** Inbox-Liste über Sortierleiste umsortieren → Reihenfolge der Listeneinträge verhält sich wie vorher (Banner-Zonen sind davon unabhängig, Gruppenzeilen unverändert).
10. **NAS (nach Merge, Klasse-C-Update):** nur kurzer Blick — Banner zeigt wie gewohnt, Ignorieren/Wiederanzeigen funktioniert (Abschnitt 12 ist lokal getestet; NAS nur Smoke-Check).

## Änderungen in Akt 2b (Korrekturrunde, 2026-10-17)

Alex' Entscheidung (wörtlich, 2026-10-17): „Ja, Akt 2b mit F1–F3 wie empfohlen starten; Apply-Sperre und Bestandstest-Anpassung nehme ich an."

- **F1 [kritisch] — Fehlerfall neu gefasst (selbst verifiziert gegen `app.js`):** `searchSeries` (`:3079`) fängt eigene HTTP-/Formatwürfe (`:3107`, `:3111`) im internen `try` (`:3093`) per `catch` (`:3209–3213`) ab und meldet „Suchfehler" im Suchbereich (`:3212`); ihr Promise wird durch diese Würfe nie abgelehnt. Den Banner-`catch` erreichen praktisch nur synchrone Würfe aus `startSeriesGroupWorkflow` (`:12790`, synchron; `:12969–12971`) oder dem Handler. Einarbeitung: ADR-75-4 (Wurfquellen-Korrektur, `try` umschließt Aufruf UND `await`), ADR-75-6-Konsequenzen (einziger Injektionsweg: testseitig gesteuerter werfender `triggerQualityHintUpdates`-Stub vor dem `eval`, Präambel-Binding `inbox_group.test.js:564`; `fetch`-Variante als Fehlerquelle gestrichen, als Pending-Promise für den Sperre-Test zulässig), AK9 (inkl. neuem dokumentierenden Test „Suchfehler nach Apply → Gruppe bleibt angewendet, keine Banner-Meldung"), Abschnitt 6 (neuer Risikopunkt „Suchfehler nach dem Gruppieren", alter Stub-Risikopunkt ersetzt), Abschnitt 8 Frage 4 und Abschnitt 12 Schritt 8 (kein Alex-Handtest-Schritt mehr; Claude Code belegt mit lokal gepatchter Kopie + Screenshot/Konsole; optional nur die „Suchfehler"-Sichtprüfung), Abschnitt 11 (Kontext, Punkt 3, AK9-Text). Die alten Aussagen „reale Wurfquelle `searchSeries`" ([advocatus] C3/K2, plan-reviewer R1) sind damit widerlegt und korrigiert.
- **F2 [wichtig] — Verbindliche UI-Texte:** neue Tabelle „Verbindliche UI-Texte (UTF-8, exakt)" in ADR-75-1 (echte Umlaute, Gedankenstrich U+2013 gemäß `ROADMAP.md:2077`); Abschnitt 11 Codeblock auf echte Umlaute umgestellt + Bindungssatz „keine ASCII-Umschrift in Oberfläche oder Tests"; AK1/AK2/AK4/AK6/AK11 verweisen auf die Tabelle (Fehlerklasse #78: Briefing-Muster ≠ AK-Beispiel).
- **F3 [kosmetisch]:** Tippfehler „Zaeler" → „Zähler" (Abschnitt 11, AK8-Zeile) korrigiert. Plan-reviewer-R2-Optionalpunkt (Spy-Formulierung) geprüft: AK7, ADR-75-6c und Worker-Text sind bereits angeglichen („per Zähler/Spy am Mock ODER Store-Inhalts-Check, Wahl beim Worker") — keine weitere Änderung nötig.
- **Angenommen nach Alex-Zitat (oben), keine offenen Fragen mehr:** (a) Apply-Sperre `groupWorkflowRunning` (Dissens 5 / Frage 2a); (b) benannte Anpassung des Bestandstests `inbox_group.test.js:838–866` (Dissens 6 / Frage 2b) — Ziel-Assertions jetzt verbindlich nach UI-Text-Tabelle.

## Nachtrag Lauf 2 (Alex, wörtlich, 2026-10-17: „Ja, Nachtrag F-A, F-G und F-H wie empfohlen und Gate-A2-Lauf 2 auf af261ac; F-B bis F-F und Q1=C in die ROADMAP.“)

Quelle: Rückkanal `rueckkanal.md` (ABNAHME: JA mit Auflage F-A), Befunde von Claude Code am Code verifiziert. Ausgangsstand: Commit `af261ac` (Lauf 1, AK1–AK14 umgesetzt). Lauf 2 ändert **nur** Folgendes:

- **F-A [wichtig] veraltete Banner-Fehlermeldung:** `bannerApplyErrors` wird heute nur beim nächsten Apply derselben Gruppe gelöscht (`app.js:12829`). Ablauf Fehler: Start scheitert → Meldung gesetzt (`:12837`) → „Ignorieren“ → „Wieder anzeigen“ → die alte Meldung erscheint wieder. Fix: Die Meldung der Gruppe wird beim Ignorieren UND beim Wiederanzeigen (einzeln und „Alle wieder anzeigen“) gelöscht (`bannerApplyErrors.delete(groupKey)`; Stelle frei wählbar, z. B. in `setInboxGroupIgnored` und `clearInboxGroupIgnored`).
- **F-G [kosmetisch] Fallback ohne Log:** In `setInboxGroupIgnored` (`:12614–12625`) landet die Gruppe bei fehlendem `localStorage` (else-Zweig `:12618–12620`) still im Fallback-Set. Fix: dort zusätzlich `console.warn` mit kurzer Beschreibung (kein stilles Scheitern).
- **F-H [kosmetisch] toter Code im Fehlerpfad:** Im `catch` des Banner-Apply-Handlers stellt `targetBtn.disabled = false` / `targetBtn.innerHTML = originalContent` (`:12839–12842`) einen Knopf wieder her, der nach dem Re-Render (`:12831`, `:12838`) nicht mehr im DOM hängt. Fix: diese Wiederherstellung entfernen und `originalContent` (`:12822`, `:12825`) entfernen, falls danach unbenutzt. Das Sperren und Beschriften des Knopfs vor dem Start (`:12824`, `:12826`) bleibt. Verhalten im Fehlerfall sonst unverändert (AK9 bleibt grün).

Zusätzliche Akzeptanzkriterien (in `tests/frontend/inbox_group_banner.test.js`):
- **AK15:** Es prüft, dass nach gescheitertem Start (gleicher Injektionsweg wie AK9: testseitig gesteuerter werfender `triggerQualityHintUpdates`-Stub vor dem `eval`), anschließendem „Ignorieren“ dieser Gruppe und „Wieder anzeigen“ KEINE „Serien-Start fehlgeschlagen. Bitte erneut versuchen.“-Meldung mehr im Banner steht; ebenso über „Alle wieder anzeigen“. Der Test muss gegen den Lauf-1-Code (`af261ac`) rot sein und darf dafür keine neuen globalen Symbole aus `app.js` voraussetzen.
- **AK16:** Es prüft, dass bei `localStorage === undefined` „Ignorieren“ die Gruppe für die Sitzung ausblendet UND `console.warn` aufgerufen wird.
- AK1–AK14 bleiben grün; AK13 (keine Test-Weichen) gilt unverändert.

Schreibgrenzen Lauf 2: nur `gui/static/app.js` (nur `setInboxGroupIgnored`, `clearInboxGroupIgnored`, die Banner-Handler in `updateGroupBannerUI` und der Banner-Apply-Handler) und `tests/frontend/inbox_group_banner.test.js` (AK15/AK16 ergänzen; Harness darf angepasst werden, bestehende Testfälle inhaltlich unverändert). Cache-Buster bleibt `app.js?v=103` / `style.css?v=51` (noch nicht ausgeliefert). Alles andere wie oben.

## Nachtrag Lauf 3 (Alex, wörtlich, 2026-10-17: „ja gerne gkattziehen; der Rest des Handtests sah gut aus“)

Quelle: Handtest Alex (2026-10-17) auf Stand `4785da5`: „Weitere Vorschläge“ klappt nach kurzer Zeit von selbst wieder zu. Ursache (von Claude Code im Code belegt): `setInterval(loadStatus, 6000)` (`app.js:556`) → `updateHomepageData` (`:2275`) → `renderSmartInboxList` (`:12372`) → `updateGroupBannerUI` baut das Banner per `innerHTML` neu und setzt beide Bereiche auf eingeklappt (`:12727`, `:12759` `aria-expanded="false"`; `:12780`, `:12794` `display = "none"`). Die Annahme in Abschnitt 4 („Banner wird bei jeder Aktion neu gezeichnet“) übersah diesen 6-Sekunden-Takt; der dort verworfene „merkende Aufklapp-Zustand“ wird hiermit für die Dauer der Seite eingeführt (ROADMAP #85 wird damit in dieser Kette erledigt). Ausgangsstand: Commit `4785da5`. Lauf 3 ändert **nur** Folgendes:

- **F-I [wichtig] Aufklapp-Zustand halten:** Der Aufklapp-Zustand von „Weitere Vorschläge“ und „Ausgeblendete Vorschläge“ wird in zwei Modul-Variablen gehalten (deklariert neben `groupWorkflowRunning`, `:12478`), beim Klick auf den jeweiligen Toggle umgeschaltet und bei JEDEM Rendern von `updateGroupBannerUI` angewendet (`aria-expanded` und `display` der Liste passend). Standard beim Laden der Seite: beide eingeklappt. Kein Speichern über Neuladen (kein `localStorage`/`sessionStorage`). Der 6-Sekunden-Takt und `renderSmartInboxList` bleiben unverändert.

Zusätzliches Akzeptanzkriterium (in `tests/frontend/inbox_group_banner.test.js`):
- **AK17:** Es prüft, dass „Weitere Vorschläge“ nach dem Aufklappen und einem erneuten `renderSmartInboxList`-Aufruf mit denselben Vorschlägen (wie der 6-Sekunden-Takt) aufgeklappt bleibt (`aria-expanded="true"`, Liste sichtbar), ebenso „Ausgeblendete Vorschläge“; dass Zuklappen ebenfalls erhalten bleibt; und dass bei frischem Modulzustand (zweiter `eval`) beide eingeklappt sind. Der Test muss gegen `4785da5` rot sein und darf keine neuen globalen Symbole aus `app.js` voraussetzen.
- AK1–AK16 bleiben grün (AK1 „Standard eingeklappt“ gilt weiter für den ersten Aufbau).

Schreibgrenzen Lauf 3: nur `gui/static/app.js` (nur die Modul-Deklarationen bei `:12474–12478` und `updateGroupBannerUI`) und `tests/frontend/inbox_group_banner.test.js` (AK17 ergänzen; bestehende Testfälle inhaltlich unverändert). Cache-Buster bleibt `app.js?v=103` / `style.css?v=51`. Alles andere wie oben.
