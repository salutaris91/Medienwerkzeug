<!-- Mechanisch aus `opencode export ses_eb73aeb5bffe9aWLAai8tJnxSR` extrahiert (Claude Code, 2026-10-17, Akt 2b): alle Assistant-Textteile in Reihenfolge, ungekürzt, unverändert (nur Trailing Whitespace entfernt). Rohdatei: Kit scripts/gate-a2/logs/2026-10-16-roadmap75-inbox-vorschlaege/akt2b/export-direkt/export-plan-reviewer.json -->

Ich beginne mit dem vollständigen Lesen der zu prüfenden Artefakte und der Kontextdateien.

---

Das Briefing ist länger als 252 Zeilen — ich lese den Rest, parallel dazu die ROADMAP-Stellen für den verbindlichen Wortlaut.

---

Jetzt verifiziere ich F1 selbst gegen `gui/static/app.js` — alle relevanten Codeabschnitte.

---

F1-Kernverifikation gegen `app.js` ist weitgehend bestätigt. Jetzt prüfe ich die zitierten Test-Harness-Stellen und die übrigen app.js-Referenzen.

---

Die Harness-Zitate (:12–19, :452–456, :536–538, :554–620, :560–581, :564, :583–618, :622–627, :838–866) sind alle verifiziert korrekt. Jetzt die restlichen app.js-Referenzen und die Selektor-Mock-Datei.

---

Zitate :2789, :12471–12477, :13318–13344, Importe :1–9 alle bestätigt. Jetzt die restlichen Referenzen (escapeHTML, Renderstelle, Leer-Zweig, index.html) und den strengen Selektor-Mock.

---

Alle Code-Referenzen bestätigt. Jetzt index.html und die Session-Rohoutputs (Rollen-Dateien) für die Dissens-Vollständigkeitsprüfung.

---

Jetzt die vier Rollen-Rohoutputs, um zu prüfen, ob wesentliche Einwände oder Varianten im finalen Briefing verloren gingen oder verfälscht wurden.

---

Advocatus-Rohoutput vollständig ausgewertet. Jetzt produktberater.md und grafiker.md.

---

Produktberater ausgewertet. Jetzt grafiker.md und plan-reviewer.md.

---

Grafiker ausgewertet. Jetzt plan-reviewer.md (Runde-1-Rohoutput).

---

Rollen-Rohoutputs vollständig gelesen. Jetzt verifiziere ich die verbleibenden technischen Kernbehauptungen selbst: den Gedankenstrich U+2013, die Swap-Wirksamkeit von `localStorage` (keine Top-Level-Binding), die zitierten SVG-/CSS-Stellen und `test_cmd` gegen das Referenz-Briefing.

---

Gedankenstrich U+2013 in der Tabelle bestätigt, keine `localStorage`-Top-Level-Binding (Swap-Wirksamkeit plausibel). Jetzt die letzten Verifikationen: Chevron-SVG, style.css-Zitate, cache_busting-Test, `test_cmd`-Referenz und ein Negativ-Grep auf die Hyphen-Variante des Rückweg-Labels.

---

Letzte Verifikation: `test_cmd` gegen das Referenz-Briefing von 2026-10-12 und die Responsive-CSS-Stelle.

---

# Plan-Review Akt 2b (Korrekturrunde), Runde 1 von max. 2: `briefing.md`

**Prüfumfang:** F1–F3-Einarbeitung gegen den Code selbst verifiziert, Konsistenz aller betroffenen Briefing-Stellen, Kickoff-Bindungen, Alex-Zitat-Gleichheit, AK-Ausführbarkeit, Test-Weichen-Freiheit, Dissens-/Transparenzpflicht gegen alle vier Rollen-Rohoutputs, ALEX_ZUSAMMENFASSUNG, Formales (Frontmatter, Struktur, Lizenzen, Dateiscope). Read-only; kein bash, keine `.env`, nichts außerhalb des Worktrees.

## 1. Selbst verifizierte Code-Belege (alle F1-Kernthesen bestätigt)

- **`searchSeries` (app.js:3079–3214):** `async`; Würfe `:3107`/`:3111` liegen **innerhalb** des internen `try` ab `:3093`; `catch` `:3209–3213` fängt vollständig (`AbortError` → `return` `:3210`, veraltete Abfrage → `return` `:3211`, sonst „Suchfehler: …" `:3212`). HTTP-/Formatfehler erreichen den Banner-`catch` nie — die F1-Korrektur ist technisch richtig.
- **`startSeriesGroupWorkflow` (app.js:12790–12973):** synchron (nicht `async`); ruft `triggerQualityHintUpdates()` synchron bei `:12887–12889` (typeof-guarded — ein Stub ist eine Funktion, wird also aufgerufen); gibt am Ende `searchSeries()` zurück (`:12969–12971`) bzw. `Promise.resolve()` (`:12972`). `:12887–12889` liegt vor `:12969` — der Injektionsweg ist **technisch erfüllbar**: Stub vor dem `eval` via `globalThis` gesetzt → Präambel-Binding als `const` (inbox_group.test.js:564, verifiziert: `const triggerQualityHintUpdates = globalThis.triggerQualityHintUpdates || (() => {})`) → synchroner Wurf propagiert durch die synchrone Funktion zum Handler-`catch` (`:12657`).
- **Apply-Handler (app.js:12643–12663):** `add` `:12653` → Re-Render `:12654` → `await` `:12656`; `catch` `:12657–12662` nur Button-Freigabe. Abschnitt 1 des Briefings beschreibt das korrekt.
- **Swap-Wirksamkeit (AK11):** grep `^(const|let|var)\s+localStorage` in app.js → leer; `:459` und `:10473` binden nur `getItem`-**Ergebnisse** in Funktionen. „Produktcode liest `localStorage` erst zum Aufrufzeitpunkt dynamisch" stimmt.
- **Übrige Zitate:** Präambel/Export-Block/Eval `inbox_group.test.js:560–581`/`:583–618`/`:620` ✓; Bestandstest `:838–866` (Assertion `'true'` `:864`, „Banner must be hidden" `:865`) ✓; Timer-Stubs `:536–538` ✓; Setup-try/catch `:622–627` ✓; `validateSelector` `inbox_selection.test.js:20–58` (wirft `SyntaxError`) ✓; `cache_busting.test.js:13–48` nur Konsistenz, `:50–56` style.css nur nicht-leer ✓; `escapeHTML` `:245` ✓; Modul-States `:12471–12477` ✓; Export-Block `:13318–13344` nur `globalThis.X = X` ✓; neun Importe `?v=102` `:1–9` ✓; `index.html:9`/`:2760` ✓; `triggerQualityHintUpdates`-Zweitaufruf `:2789` ✓; Chevron-SVG `:13079` (lucide-chevron-right) ✓; `style.css:3866–3894` + Responsive `:4067` ✓; `test_cmd` token-weise identisch mit dem Referenz-Briefing (2026-10-12:182) ✓.

## 2. F1–F3-Einarbeitung (alle geforderten Stellen geprüft)

- **F1:** ADR-75-4 (`:103`: Wurfquellen-Korrektur + „try umschließt Aufruf UND await"), ADR-75-6-Konsequenzen (`:118`: einziger Injektionsweg, Präambel-Binding `:564`, testseitige Weiche, fetch als Fehlerquelle gestrichen / als Pending-Promise für den Sperre-Test zulässig), AK9 (`:45` inkl. Zusatztest „Suchfehler nach Apply → Gruppe bleibt angewendet, KEINE Banner-Meldung" + Sperre), Abschnitt 6 (`:143–144`: neuer Risikopunkt „Suchfehler nach dem Gruppieren", Stub-Punkt F1-korrigiert ersetzt), Abschnitt 8 Frage 4 (`:164`), Abschnitt 12 (`:379`, `:390`: kein Alex-Handtest-Schritt mehr; lokal gepatchte, nicht committete Kopie + Screenshot/Konsole; optional nur Suchfehler-Sichtprüfung), Abschnitt 11 (Kontext `:212–216`, Punkt 3 `:251–267`, AK9-Text `:325–341`) — **überall konsistent, keine Restspur der widerlegten alten Lesart**. Pending-fetch für den Sperre-Test technisch sauber (startSeriesGroupWorkflow läuft synchron durch bis `:12969`, `await fetch` `:3102` hält offen).
- **F2:** Tabelle „Verbindliche UI-Texte (UTF-8, exakt)" in ADR-75-1 (`:71–84`) mit allen acht geforderten Texten; Gedankenstrich U+2013 per grep bestätigt (`:76`), Negativ-grep auf die Hyphen-Variante des Rückweg-Labels → leer; ROADMAP.md:2077 und Kickoff-Vorgabe 4 (`:37`) deckungsgleich; Worker-Codeblock nutzt echte Umlaute für alle UI-Texte/Test-Erwartungen plus Bindungssatz „keine ASCII-Umschrift in Oberfläche oder Tests" mit klarer Abgrenzung des übrigen Umschrift-Texts (`:201–203`); AK1/AK2/AK4/AK6/AK11 (und AK9) verweisen auf die Tabelle; keine Widersprüche zu ADR-75-3-Überschrift (`:96`) und Dissens 1 (`:128`); Kollisionsregel „gilt ausschließlich diese Tabelle" (`:71`) vorhanden.
- **F3:** „Zähler" korrigiert (`:44`, `:323`); Spy-Formulierung konsistent angeglichen (AK7 `:43` „per Zähler/Spy am Mock ODER Store-Inhalts-Check, Wahl beim Worker" ↔ ADR-75-6c `:115` „optional" ↔ Worker `:288–289`) — Nachweis Pflicht, Weg Wahl, kein scheinbarer AK/ADR-Widerspruch.

## 3. Weitere Prüfpflichten

- **Alex-Zitat:** voll wörtlich identisch an Kopf (`:18`), Dissens 5 (`:136`), Abschnitt 8 Frage 2 (`:162`), Änderungen (`:396`), ALEX_ZUSAMMENFASSUNG (`:15`); AK9/Worker als Verweis. Apply-Sperre und Bestandstest-Anpassung firmieren nirgends mehr als offene/streichbare Frage (Dissens 5/6 „keine offene Frage mehr", Frage 2 „Festlegungen", Abschluss `:166` „offen ist nur noch Freigabepunkt 2").
- **AKs ausführbar:** AK0–AK14 in sich konsistent; Harness-Muster (Präambel-Binding, setTimeout-sofort-Ausführung, funktionale Storage-Mocks, strenger Selektor-Mock) durchgängig korrekt beschrieben; Bestandstest-Anpassung `:838–866` unverändert korrekt (Inline-Swap nach `setupTestEnvironment()`, Harness-Mock `:452–456` unangetastet, Ziel-Assertions wörtlich, nur (c) mit Tabellen-Verweis).
- **Keine Test-Weiche im Produktivcode:** die Wurf-Variable ist an vier Stellen (`:45`, `:118`, `:143`, `:327–329`) ausdrücklich Testcode-only; AK13 deckt ab.
- **Transparenz:** Änderungen-Abschnitt (`:398`) dokumentiert die Widerlegung der älteren Rollenaussagen ([advocatus] C3/K2, plan-reviewer R1) korrekt als Korrektur.
- **Rollen-Rohoutputs:** Alle vier Dateien vorhanden und ausgewertet. Kein wesentlicher Einwand ignoriert, verfälscht oder verloren: advocatus K1–K6/W1–W6/C1–C3 (C3 widerlegt + dokumentiert), produktberater Findings 1/2/3/6/7/8/9/10, grafiker Empfehlungen 1–6 + Präzedenzfälle — alles im Briefing abgebildet oder begründet verworfen. Eine kleine Dokumentationslücke siehe Einwand 1.
- **ALEX_ZUSAMMENFASSUNG:** konsistent zum Briefing, F1-Risiko in Klartext (`:12`), Sonderpunkte mit vollem Zitat (`:15`), Handtest ohne Fehlerfall-Schritt (`:18`), nicht-technisch, 23 Zeilen (≤ 1 Seite).
- **Formales:** Frontmatter `status: draft` + Platzhalter-`approval_quote` (keine erfundene Freigabe); 12 Abschnitte + Änderungen-Abschnitt; 7 ADR-Blöcke; Lizenzabschnitt vorhanden und gepflegt (kein neuer Third-Party-Code, Lucide ISC korrekt, Referenz-Apps nur Muster) → **kein Lizenz-Blocker**; Dateiscope des Worker-Auftrags unverändert eng (`:357–368`).

## 4. Findings

**Blocker:** keine.

**Sollte behoben werden:** keine.

**Optional:**

1. **Produktberater Finding 5 ohne Dissens-Dokumentation.** Der als `[wichtig]` markierte Edge-Fall „Wieder anzeigen einer bereits angewendeten Gruppe" (produktberater.md:42–46) erscheint im Briefing weder im Dissens-Block noch in Abschnitt 4. Inhaltlich ist der Einwand durch das Design erschöpft — offene Vorschläge sind per Semantik „nicht angewendet && nicht ignoriert", und „Wieder anzeigen" ist ein reines `removeItem` (ADR-75-3, briefing.md:97), sodass genau das vom produktberater empfohlene „still entfernen" eintritt und die befürchtete Doppelanzeige nicht entstehen kann. Für den Worker entsteht kein Handlungsbedarf — aber die Dissens-Dokumentation ist gegenüber dem Rohoutput unvollständig. Empfehlung: eine Zeile nachtragen (Dissens-Block oder Abschnitt 4).
2. **Absolute Aussage „ihr Promise lehnt nie ab" hat eine theoretische Randzone.** briefing.md:103 (ADR-75-4), :45 (AK9) und :212–216 (Worker-Kontext) behaupten das kategorisch. Strikt gilt es nur für die zitierte Wurfklasse (HTTP-/Formatwürfe app.js:3107/:3111 innerhalb des try ab :3093); synchrone Würfe **vor** dem internen try (app.js:3080–3091, z. B. `document.getElementById("series-search-query").value` bei fehlendem Element) würden das async-Promise doch ablehnen und über `await` (app.js:12656) den Banner-catch erreichen. Für das Testdesign ist das folgenlos (der Stub-Wurf bei :12887–12889 liegt vor :12969, `searchSeries` wird nie erreicht; im Browser und im getOrCreateElement-Harness existiert das Element), aber die Formulierung „ausschließlich synchrone Würfe" ist so nicht wasserdicht. Empfehlung: auf die Wurfklasse einengen („HTTP-/Format-/Netzwerkfehler").
3. **Alex-Zitat in Dissens 6 nur als Auszug.** briefing.md:138 zitiert gekennzeichnet „… Apply-Sperre und Bestandstest-Anpassung nehme ich an." statt des vollständigen Wortlauts wie an den fünf anderen Stellen (:18, :136, :162, :396, ALEX_ZUSAMMENFASSUNG.md:15). Nicht verfälschend, aber die Prüfpflicht „wörtlich gleich an allen betroffenen Stellen" wäre mit dem Vollzitat überall erfüllt. Triviale Angleichung.

## 5. Restrisiken / nicht ausgeführte Prüfungen

- **Zeilenende von briefing.md:103** (ADR-75-4-Entscheidung, >2000 Zeichen) war in meinen Lesungen toolbedingt gekappt („der Aufruf …"); der sichtbare Teil deckt alle F1-Forderungen, und der Worker-Text (:253–255) formuliert dieselbe Regel konsistent — ein Widerspruch im verdeckten Rest ist unwahrscheinlich, aber von mir nicht vollständig gelesen worden.
- **Keine Testausführung** durch mich (Review-Modus, read-only) — Ausführbarkeit der AKs nur formal und gegen den Code geprüft.
- **Git-Ausgaben (Abschnitt 10)** ungeprüft übernommen (kein bash); `test_cmd`-Identität nur token-weise visuell gegen das Referenz-Briefing verifiziert.
- ALEX_ZUSAMMENFASSUNG.md:19 („Rohoutputs … liegen ungekürzt im Session-Ordner") — verifiziert: alle vier Rollen-Dateien vorhanden; die Bedingung aus plan-reviewer Runde 1/2 (Archivierung vor Freigabepunkt 2) ist erfüllt.

## 6. Potenziale-Block (optional, keine Bedingungen)

- **Dissens-Notiz zu produktberater Finding 5** nachtragen (siehe Einwand 1) — erhöht die Dissens-Vollständigkeit gegenüber dem archivierten Rohoutput.
- **Abschnitt 6 (briefing.md:151)** formuliert die Rollen-Archivierung noch als IOU („erst mit den archivierten Rohoutputs voll belegbar"); die Archivierung ist inzwischen erfolgt — der Satz könnte den Ist-Zustand spiegeln.
- **Apply-Sperre im Handtest:** Abschnitt 12 prüft die Sperre nicht (nur automatisiert via AK9); ein optionaler Sichtprüfungsschritt (langsames Backend + zweiter Klick) wäre denkbar, ist aber wegen der fehlenden Provokierbarkeit bewusst verzichtbar — nur als Idee für die Freigabe-Entscheidung.

---

**Zusammenfassung:** F1 ist technisch korrekt neu gefasst und an allen elf geforderten Stellen konsistent eingearbeitet (selbst gegen app.js verifiziert, inkl. Injektionsweg-Erfüllbarkeit und testseitiger Weiche); F2 ist vollständig umgesetzt (Tabelle, U+2013, Umlaute, Bindungssatz, AK-Verweise, keine Widersprüche); F3 ist erledigt. Das Alex-Zitat ist wörtlich und gleich an allen Stellen, Sperre und Bestandstest-Anpassung sind durchgängig Festlegungen. Kein wesentlicher Subagent-Einwand ging verloren oder wurde verfälscht; Lizenz- und Referenzpflicht ist erfüllt. Keine Blocker, keine wichtigen Einwände — drei kosmetische.

VERDICT: APPROVE

1. [kosmetisch] produktberater Finding 5 (Edge-Fall „Wieder anzeigen einer bereits angewendeten Gruppe", produktberater.md:42–46, dort [wichtig]) ist im Briefing weder als Dissens dokumentiert noch als verworfen ausgewiesen — inhaltlich durch die Filter-Semantik (offen = nicht angewendet && nicht ignoriert; „Wieder anzeigen" = reines removeItem, briefing.md:97) bereits erschöpft, aber dokumentatorisch eine Lücke gegenüber dem Rohoutput; eine Zeile in Dissens-Block oder Abschnitt 4 nachtragen.
2. [kosmetisch] Die kategoriale Aussage „ihr Promise wird nie abgelehnt" (briefing.md:103, :45, :212–216) gilt strikt nur für die zitierte Wurfklasse (app.js:3107/:3111 im try ab :3093); Würfe vor dem internen try (app.js:3080–3091, fehlendes DOM) wären Promise-Rejections und erreichten den Banner-catch doch — für das Testdesign folgenlos (Stub-Wurf bei app.js:12887–12889 liegt vor :12969), aber als absolute Behauptung auf die Wurfklasse einengen.
3. [kosmetisch] briefing.md:138 (Dissens 6) zitiert Alex nur als gekennzeichneten Auszug statt des vollständigen wörtlichen Zitats wie an den fünf anderen Stellen (:18, :136, :162, :396, ALEX_ZUSAMMENFASSUNG.md:15) — angleichen für byte-gleiche Zitierbarkeit.
