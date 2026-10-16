ABNAHME: JA

Rückkanal-Review ROADMAP #77 (Inbox-Auswahl) — Gesamtänderung `git diff 5c72af2` im Arbeitsbaum
(Commit `7d95496` Lauf 1 + uncommitteter Lauf-2-Patch), geprüft als Arbeitsbaum-Stand am 2026-10-16.
Auftraggeber: Claude Code (Reviewer/Vermittler), nicht Alex. Geprüft: `gui/static/app.js`,
`gui/static/index.html`, `tests/frontend/inbox_selection.test.js`, `tests/frontend/cache_busting.test.js`,
`tests/frontend/inbox_group.test.js` (Regression), `package.json`.

## Methodik und Grenzen

- Reines Code-Review im Arbeitsbaum; kein `bash` verfügbar → **Suite (529/1 + 196/196) und
  `git diff --check` wurden nicht selbst nachausgeführt**; die Belege stammen von Claude Code
  (Worker-Image) und sind hier ungeprüft übernommen. Die statischen AKs (AK7, AK10) und alle
  Testinhalte habe ich selbst gelesen und verifiziert.
- Kein Git-Zustand nötig, da keine Commit/PR-Empfehlung ausgesprochen wird; Freigabe-Pfad
  (Handtest → approved-head → `kit-push-approved-head`) bleibt wie im Briefing.

## 1. Umsetzung R1–R5, F1–F3

| Regel | Status | Beleg (Datei:Zeile, Code = Arbeitsbaum) |
|---|---|---|
| R1 (a) nicht in `rawSuggestions` | ✅ | `app.js:13029-13033` — Cleanup gegen das **übergebene** `suggestions` (13025-13026), nicht gegen alten Global-Stand |
| R1 (b) in Verarbeitung | ✅ | `app.js:13031` (`currentProcessing.has(proj)`) |
| R1 (c) nicht auswählbar, identische Regel wie Kästchen | ✅ | gemeinsame Hilfsfunktion `isInboxProjectEligibleForSelection` (`app.js:12502-12507`), benutzt in Cleanup (`13031`) **und** Kästchen-Rendering (`13204`) — keine zweite Kopie |
| R1 Zähler-Update nach Cleanup | ✅ | `app.js:13035` `updateBulkActionsBarUI()` direkt nach der Bereinigung, vor dem Zeichnen |
| R2 kein `{ project: proj }`-Fallback | ✅ | `app.js:12729-12736` — nur `match` aus `currentSmartInboxRawSuggestions` landet in `validItems`; grep über die ganze Datei: kein `\{ project: proj` mehr, kein unmaskierter Selektor `smart-inbox-cb[data-project=` |
| R3 Meldung + Entfernen + Zähler | ✅ | `app.js:12738-12752` (Delete + `cb.checked=false` + countEl), `12765-12770` (Alert Singular/Plural) |
| R3 nichts übrig → kein Start + Meldung + Knopf frei | ✅ | `app.js:12754-12763`; exakter Meldungstext wie im Briefing |
| R4 unverändert | ✅ (soweit ohne Diff prüfbar) | `inboxFilesEntryForItem` (`12494-12500`), Gruppen-Banner-Apply (`12643-12663`), Gruppenzeilen-„Auswählen“ (`13142-13160`), `startSeriesGroupWorkflow` (`12790+`) ohne Selektor-/Auswahl-Änderungen |
| R5 Cache-Buster v102 | ✅ | `app.js:1-9` alle 9 Imports `?v=102`, `index.html:2760` `app.js?v=102`; `cache_busting.test.js` ist konsistenzbasiert → grün, wenn beide gleich |
| F1 Selektor-Maskierung | ✅ | `app.js:12739-12746` — bevorzugte Variante: `querySelectorAll(".smart-inbox-cb")` + `cb.dataset?.project === proj`, keine `CSS`-Abhängigkeit, kein interpolierter Selektor |
| F2 Test-Hintertüren raus | ✅ | grep `app.js`: `setCurrentSmartInboxRawSuggestions`/`getCurrentSmartInboxRawSuggestions` nicht vorhanden; Harness definiert sie selbst (`inbox_selection.test.js:640-641`); AK10-Test liest den rohen Dateiinhalt (`1037-1049`) |
| F3 `await Promise.resolve()` weg | ✅ | kein `await Promise.resolve` in der Datei; „nichts gestartet“-Pfad nutzt Alert + `queueMicrotask` (siehe Hinweis a) |

## 2. Testabdeckung AK1–AK10 (Tests gelesen, nicht nur Namen)

- **AK1** (`inbox_selection.test.js:675-695`): prüft Set-Inhalt **und** `countEl.textContent === "1 ausgewählt"` — echt.
- **AK2** (`700-732`): B in `processingSet` → entfernt; B's Kästchen `checked === false` **und** `disabled === true`; A bleibt `checked` — deckt die Briefing-Formulierung vollständig ab.
- **AK3** (`737-758`): zwei Varianten (leere Liste / andere Liste), jeweils Auswahl leer + `bulkBar.style.display === "none"` — echt.
- **AK4** (`763-807`): Stale-Fall ohne Neuzeichnen; `deepStrictEqual(activeSeriesGroupFiles, ['ShowA.S01E01.mkv'])` beweist „nur A, kein nackter Ordner“; Alert „1 Eintrag … übersprungen“; X abgewählt; Zähler „1 ausgewählt“ — voll.
- **AK5** (`812-871`): zwei Varianten (ohne Treffer / in Verarbeitung). Wachtumfeld korrekt: `getActiveProjectsProcessing()` liefert dasselbe reale Set, das der Handler liest (`app.js:12724`). Assertionen: kein Workflow-Aufruf (Sentinel `activeSeriesGroupFiles === null`), exakter Meldungstext, Knopf wieder aktiv + Text restauriert, Auswahl leer — voll.
- **AK6** (`876-920`): TV-Einzeldatei + Einzelvideo-Ordner → `files` exakt `['Show.S01E01.mkv', 'Show.Folder.S01E02/video.mkv']` (relpath via `inboxFilesEntryForItem`), **kein** Alert — voll.
- **AK7**: durch `cache_busting.test.js` (konsistent v102) + R5-Prüfung oben abgedeckt.
- **AK8**: nicht selbst ausgeführt (siehe Grenzen). Plausibilitätsprüfung per Lesen: `inbox_group.test.js:946/1002-1031/1033-1067` (Unlock-Bulk, Persistenz über Re-Render/Sort, Deselect) ist mit R1/R2 vereinbar — gültige Einträge bleiben erhalten, verarbeitete werden nur im AK5-Szenario entfernt; keine der Tests enthält Stale-Einträge mit erwartetem Fallback. Kein Regressionsrisiko erkennbar.
- **AK9** (`957-1032`): Name mit `"` im Spiel; prüft Workflow nur mit A, Alert „1 Eintrag“, X abgewählt, **X's Kästchen `checked === false`** (Dataset-Vergleich, HTML-Entities werden im Mock korrekt dekodiert, `test:196-202`), Zähler. **Rot-Nachweis gegen alten Code:** der Mock-Validator wirft für `.smart-inbox-cb[data-project="Show "X".mkv"]` (unbalancierte Quotes im Attributwert, `test:37/43`) einen `SyntaxError` → alter `catch` → kein Workflow-Aufruf → Assertion `startSeriesGroupWorkflow must be called` (1009) schlägt fehl. Passt exakt zur geschilderten Rot-Probe.
- **AK10** (`1037-1049`): roher Dateiinhalt beider Kennungen absent — echt.

**Selektor-Validator (`test:20-58`) plausibel?** Ja für den Einsatzzweck: wirft bei unausgeglichenen/unkorrekt gequoteten Attributwerten (wie der Browser) und akzeptiert alle im Code tatsächlich vorkommenden Selektoren (bestätigt durch grüne Suite; Klammer-/Parenthese-Namen wie `The Rock (1996).mkv` bestehen die Prüfung). Escapes (`\"`) werden korrekt als gültig erkannt (`37/43`).

## 3. Hinweise (a)–d) von Claude Code — Bewertung

**(a) F3-Umbau (Alert zuerst, Knopf-Freigabe in `queueMicrotask`, `app.js:12754-12763`): vertretbar, kein Risiko.**
Im Browser ist `alert` modal — während es offen ist, kann niemand den Knopf klicken; die Microtask-Freigabe läuft garantiert vor dem nächsten User-Event. Im Test ist es deterministisch: `queueMicrotask` wird vor der `await`-Fortsetzung von `click()` eingereiht, die AK5-Assertionen (833-834) laufen erst danach. Gegenüber dem nackten Streichen des `await Promise.resolve()` ist der Zustand während des Alerts sogar konsequenter (Knopf bleibt bis Handler-Ende deaktiviert). Verhaltensgleich im Browser: ja.

**(b) Doppelter `updateBulkActionsBarUI()`-Aufruf pro Render (`app.js:13035` neu + `13301` alt): keine funktionalen Nebenwirkungen.**
Der Bar-Aufbau ersetzt `bulkBar.innerHTML` komplett (`12694`) — alte Button-Knoten samt Listener sterben dabei, **keine doppelten Listener** (echtes DOM wie Mock). Fokusverlust auf Bulk-Buttons bei Re-Render gab es durch den End-Aufruf schon vorher; der neue Aufruf adds nur einen weiteren Churn pro Render ([kosmetisch]). Zähler-Konsistenz: beide Aufrufe rechnen mit derselben bereinigten Auswahl.

**(c) Weitere Leser von `selectedInboxProjects` / `{ project }`-Fallbacks: keine problematischen gefunden.**
Alle Leser: `app.js:12691` (Zähler), `12704` (Deselect), `12729` (Bulk), `13029` (Cleanup), `13208`/`13281-13283` (Kästchen) — alle im bereinigten Pfad. Gruppen-Banner (`12655`) und Gruppenzeile (`13152`) bauen `files` aus **frischen** `members`/`item.items` der aktuellen Suggestions, lesen nie die Auswahl und hatten nie den Fallback. Die restlichen `{ project: ... }`-Literale (`6371`, `6476`, `10766`) sind API-Payloads des allgemeinen Verarbeiten-Pfads (R4, bewusst unverändert). Einzige Rest-Beobachtung: Mitglieder einer **angewendeten** Gruppe können nach dem Banner-Apply kurzzeitig in der Auswahl bleiben, ohne sichtbares Kästchen (`12653-12656`: Render läuft vor Workflow-Start, also noch nicht in `processingSet`) — selbstheilend beim nächsten Render, Dateien sind gültig, kein Server-Ablehnungsrisiko. [kosmetisch], notizwürdig.

**(d) Stiller `catch` im Bulk-Weg (`app.js:12777-12782`): ROADMAP-Notiz ist angemessen, kein Blocker dieser Kette.**
Der catch ist vorbestehend (Briefing F1 nennt ihn „vorhanden“) und außerhalb von R1–R5/F1–F3. Nach F1 verbirgt er keine Selektor-Syntaxfehler mehr, aber weiterhin Workflow-Fehler ohne Meldung — verstößt gegen die Hausregel „Fehler müssen sichtbar sein“. Gleiches Muster an zwei weiteren Stellen: Banner-Apply `12657-12662`, Gruppenzeile `13154-13159`. Empfehlung: ein ROADMAP-Eintrag, der alle drei Stellen nennt (Meldung via `alert`/Toast + `console.error(err)`).

## Findings

- **[wichtig]** (außerhalb des Freigabe-Umfangs, nicht blockierend) Stille `catch`-Blöcke im Bulk-Weg, Banner-Apply und Gruppenzeile (`app.js:12777-12782`, `12657-12662`, `13154-13159`): Fehler werden verschluckt, nur der Knopf wird freigegeben. **Empfehlung:** als ROADMAP-Notiz aufnehmen (Hinweis d).
- **[kosmetisch]** Nach „alle Einträge übersprungen“ bleibt die Bulk-Leiste mit „0 ausgewählt“ sichtbar, bis der nächste Render sie ausblendet (`app.js:12748-12751` aktualisiert nur den Text, statt die Leiste neu aufzubauen — der Klick-Handler hält mitten im Durchlauf an dem Button-Knoten fest). R3 verlangt das Verstecken nicht; selbstheilend. **Empfehlung:** nicht ändern, nur kennen.
- **[kosmetisch]** Doppeltes Bar-Rebuilding pro `renderSmartInboxList` (`app.js:13035` + `13301`) — unnötiger DOM-Churn, keine Funktionsauswirkung. **Empfehlung:** optional beim nächsten Touch zusammenfassen; jetzt nicht anfassen (Scope).
- **[kosmetisch]** Mock-Validator wirft theoretisch bei `]` **innerhalb** eines gequoteten Attributwerts (z. B. Projektname `Film ]X`), wo ein Browser akzeptieren würde (`test:31` regex `\[[^\]]*\]`). Im aktuellen Code wird kein solcher Selektor mehr gebaut (F1 hat die Interpolation entfernt). **Empfehlung:** keine.
- **[kosmetisch]** Abweichung vom Buchstaben des Worker-Auftrags („`startSeriesGroupWorkflow` als Spion“): die Tests nutzen die reale Funktion und beobachten `globalThis.activeSeriesGroupFiles` (`test:788/828/913/1009`). Das folgt dem Muster von `inbox_group.test.js:946/1060` und beweist die `files`-Übergabe gleichwertig. **Empfehlung:** akzeptieren.

## Handtest-Prüfliste für Alex (OrbStack, ≤ 8 Punkte)

1. App öffnen, DevTools → Network: `app.js?v=102` wird geladen (Cache-Buster wirksam, kein harter Reload nötig).
2. Inbox: mehrere Einzelvideo-Ordner anhaken → Bulk-Leiste erscheint, Zähler stimmt mit der Zahl der Häkchen überein.
3. Einen Eintrag extern verschwinden lassen (z. B. Ordner auf dem NAS löschen) und **ohne Seitenreload** den nächsten Hintergrund-Update/Sortier-Klick abwarten → Eintrag verschwindet aus Auswahl und Zähler automatisch; kein Eintrag „N ausgewählt“ ohne sichtbares Häkchen.
4. Verarbeiteten Eintrag anhaken, Verarbeitung starten, Neuzeichnen abwarten → Kästchen leer/deaktiviert, nicht mehr im Zähler (AK2-Gegenstück live).
5. Bulk-Auftrag 1: zwei Einzelvideo-Ordner auswählen → „Ausgewählte als Serie verarbeiten“ → Workflow startet; im Network-Tab die `files` des Auftrags prüfen: relative Pfade aus `single_video_relpath`, **kein nackter Ordnername**.
6. Direkt danach Bulk-Auftrag 2 mit weiteren Ordnern → läuft ebenfalls durch; Server antwortet ohne „Ordner sind im files-Parameter nicht erlaubt“.
7. Veralteter Fall live: Eintrag anticken, dann ohne Neuzeichnen verschwinden lassen, Bulk klicken → Meldung „… 1 Eintrag … übersprungen.“, kein Server-Ablehnung, Häkchen weg.
8. Browser-Konsole die ganze Zeit über: keine `SyntaxError`, keine uncaught rejections (besonders bei Ordnernamen mit `"` im Namen, falls vorhanden).

## Ergebnis

Die Gesamtänderung setzt R1–R5 und F1–F3 korrekt und eng begrenzt um; AK1–AK10 sind durch gelesene, echte Assertionen abgedeckt; der Selektor-Validator ist für den Testzweck browser-plausibel. Die verbleibenden Findings sind [wichtig] nur als ROADMAP-Nachricht (stille catches) bzw. [kosmetisch]. Unter Vorbehalt der nicht selbst nachausgeführten Testläufe (Punkt AK8/Suite-Evidenz stammt von Claude Code): **ABNAHME: JA** — Handtest (Punkte 1–8) ist wie im Briefing der nächste Freigabeschritt durch Alex.
