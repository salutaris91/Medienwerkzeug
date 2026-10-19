<!-- Mechanisch aus `opencode export ses_eace2793fffe8SebFlL3N2iRPS` extrahiert (Claude Code, 2026-10-19): alle Assistant-Textteile in Reihenfolge, ungekürzt, unverändert (nur Trailing Whitespace entfernt). Rohdatei: Kit-Worktree clever-mclaren-94c19f scripts/gate-a2/logs/2026-10-18-roadmap74-kette/rueckkanal/export-advocatus-eace2793fffe.json -->

[advocatus] — Rückkanal-Review, nur lesend. Ich habe das Briefing (Abschnitte 3/ADR-K-1..6/R-A..R-E), `app.js` (searchSeries, Modul-States, Banner-Apply, Gruppenzeile, Bulk, Export-Block, alle `searchSeries`-Aufrufer) und die Timer-Stubs gelesen. Keine `.env`-Lektüre, keine Git-/Datei-Schreiboperation.

---

## (1) Befunde nach Schwere sortiert

### [kritisch]
**Keine.**

### [wichtig]
- **W-1 — Unsichere Einzelstaffel-Reihenfolge im Banner-Sofortstart** — `app.js:12875` (`members.map(m => inboxFilesEntryForItem(m))`). Vorbestehend, nicht durch die Kette eingeführt. `members` stammt aus `detectInboxGroups` (`:12553`) in Eingabe-Reihenfolge der `suggestions`; die Sortierung nach Staffel/Folge existiert nur als `sortedMembers` in `buildGroupedInboxSuggestions` (`:12585–12588`) und damit nur für die Gruppenzeile. Bei einer Einzelstaffel-Gruppe (Sofortstart, `seasonCount < 2`) wird die Dateiliste potenziell unsortiert an `startSeriesGroupWorkflow` übergeben. **Folge für die Zuordnungstabelle:** nur Anzeige-/Reihenfolge-Risiko, keine funktionale S/E-Fehlorientierung (die Extraktion ist dateinamenbasiert, `mw_metadata`). → ROADMAP-Folgepunkt, kein Blocker.
- **W-2 — `group_key`-Kollision über `cleanSeriesName` (serverseitig bedingt)** — `utils.js:11–23` (Underscores→Leerzeichen, Kanal-Tag-Abtrennung `[...]`) kann zwei unterschiedliche Titel auf denselben `group_key` mappen (z. B. `Show [ARTE]` vs. `Show`, `Show_A` vs. `Show A`). Da `groupRowStartErrors` (`app.js:12494`, Schlüssel `group_key`) und `appliedInboxGroups` (`:12490`) diesen Schlüssel teilen, würde im Kollisionsfall eine Fehlermeldung der falschen Gruppe zugeschrieben. **Aber:** Die Kette normalisiert den `group_key` nicht zusätzlich — E1-AK5 testet sogar explizit `"`, `'`, `<`, `&` als im Schlüssel erhalten (kein Wurf). Die Kollision ist vorbestehend und liegt außerhalb des Scopes. → ROADMAP-Folgepunkt, kein Blocker.

### [kosmetisch]
- **K-1** — Toter `btn.disabled=false`/`innerHTML`-Restore in allen drei Fehler-Catches (`:13036–13039`, `:13390–13393`, `:13475–13478`): Der unmittelbar folgende `renderSmartInboxList`/`updateBulkActionsBarUI` ersetzt den Knoten, der gerade „wiederhergestellt" wurde. Irreführend, aber harmlos.
- **K-2** — Fristmeldung hart `"30 Sekunden"` (`:3221`) unabhängig von `SERIES_SEARCH_TIMEOUT_MS` (`:3076`). Konsistent, solange die Konstante nicht konfigurierbar ist (bewusst verworfen, Abschnitt 4).
- **K-3** — Timer-Stub ~14 Zeilen in 4+1 Testdateien dupliziert. DRY-Verletzung, kein Restrisiko realisiert.
- **K-4** — Verbleibendes identische-Query-Race im Nicht-Timeout-Pfad (siehe (i)).

---

## (2) Bewertung der Hinweise (a)–(g) und (h)–(k)

**(a) Sperre-Freigabe/Deadlock** — `[kosmetisch]`, akzeptieren.
Die Freigabe liegt in `finally` (`:13395–13397`, `:13480–13482`, `:13041–13043`, Banner `:12883–12885`) und läuft in jedem Pfad (Erfolg, Fehler, Abort). **Kein Deadlock.** Der Knopf-Text „wird gestartet…" bleibt im Erfolgsfall bis zum 6-s-Neuaufbau stehen — exakt R-C, bereits als „nicht behoben (Scope-Fremd)" dokumentiert. Der einzige theoretische Offen-Pfad ist R-A (werfender `finally`/synchroner Wurf vor der try-Struktur), im Briefing als akzeptiert ausgewiesen. Kein Befund, der einen Nachbesserungslauf rechtfertigt.

**(b) harte „30 Sekunden"** — `[kosmetisch]`, akzeptieren + ROADMAP-Folgepunkt.
Konstante `30000` und Meldung stimmen überein; Timeout ist nicht konfigurierbar (bewusst verworfen). Folgepunkt: Meldungstext aus der Konstante ableiten, falls die Dauer je dynamisch wird — sonst lügt die Meldung nach einer künftigen Konstantenänderung.

**(c) unsortierte `members` im Banner-Sofortstart** — `[wichtig]` als Folgepunkt, **kein** Blocker.
Vorbestehend (Struktur war vor der Kette identisch; nur die `seasonCount`-Verzweigung ist neu). Die Unsortedness wirkt nur bei Einzelstaffel-Gruppen und nur auf die Anzeige-Reihenfolge, nicht auf die Korrektheit der S/E-Zuordnung. Empfehlung: ROADMAP-Folgepunkt — `members` im Sofortstart mit derselben Sortierung versehen wie ADR-K-3, um Konsistenz herzustellen.

**(d) Sonderzeichen-Entfernung → Kollision** — `[wichtig]` als Folgepunkt, **kein** Blocker.
Die Entfernung liegt in `cleanSeriesName` (`utils.js`), nicht in `detectInboxGroups`; die Kette führt keine zusätzliche Normalisierung ein und reicht den `group_key` unverändert durch. Folgen für `groupRowStartErrors`/`appliedInboxGroups` (gleicher Schlüssel) existieren nur im serverseitig erzeugten Kollisionsfall — außerhalb dieser Kette. ROADMAP-Folgepunkt: Kollisionserkennung beim `group_key`-Aufbau.

**(e) `render`/`updateBulkActionsBarUI` im catch bei noch gesetzter Sperre** — `[kosmetisch]`, akzeptieren.
Der Neuaufbau erzeugt neue Knoten und bindet Listener ausschließlich an diese (`innerHTML = ""` vorher), liest `groupWorkflowRunning` selbst nicht (nur die Handler beim Klick). **Kein Doppel-Binden** (alte Knoten werden verworfen), **kein Überschreiben** der wiederhergestellten Werte (die Meldung wird bewusst aus der im catch gesetzten `groupRowStartErrors` gezeichnet). Das Zeitfenster `groupWorkflowRunning === true` zwischen render und `finally` ist synchron und ohne `await` — der Event-Loop kann dort keinen Klick einschieben. Die doppelte Wiederherstellung (`btn.disabled=false` + render) ist **tot Code, nicht schädlich**: der render ersetzt den gerade restaurierten Knoten. Harmlos, aber irreführend (siehe K-1).

**(f) `searchSeries`-Aufrufer und 30-s-Abbruch** — kein Befund.
Kein Aufrufer hält eine eigene Sperre; die einzige Sperre ist `groupWorkflowRunning`, gesetzt von den vier Startstellen und im `finally` freigegeben, sobald `searchSeries` durch den Abort resolved (der AbortError wird intern gefangen, `:3218–3223`). `detectExistingSeries`/`triggerSeriesMatchingFromFolder`/Enter-Handler sind fire-and-forget ohne Sperre — eine Fristmeldung im `series-search-results` im Hintergrund ist möglich, aber gewollt und sichtbar. Seq-Guard ohne neuere Suche → Meldung erscheint (E3-AK1, gewollt). Ablösung ist korrekt: `:3087–3089` abortet nur das Vorgänger-Objekt, der Timeout (`:3095–3098`) abortet ausschließlich den eigenen `localController` (Closure). ADR-K-6 F3.1/F3.2 korrekt umgesetzt.

**(g) Timer-Stub-Duplikat** — `[kosmetisch]`, akzeptieren + ROADMAP-Folgepunkt.
Identische Logik mit Delay-Schwelle `>= 30000`; die einzigen Timer in dieser Größenordnung sind die **neuen** Frist-Timer — vor der Kette existierte kein 30-s-Timer, daher hängt kein Bestandstest an Sofortausführung. In Bestandstests, die `searchSeries` via `startSeriesGroupWorkflow` durchlaufen, resolved der fetch-Spy sofort → `finally { clearTimeout }` räumt den Frist-Timer. Grün-Belege (219/219, 226/226, 231/231) bestätigen kein realisiertes Restrisiko. Folgepunkt: gemeinsames Harness extrahieren.

**(h) E1-AK7 „still abweisen"** — kein Befund.
`if (groupWorkflowRunning) return;` steht als **erste** Anweisung (`:12861`, `:12963`, `:13369`, `:13454`), vor jedem `disabled`/Textwechsel. Zweitstart vom selben Knopf scheitert zusätzlich am `disabled`-Attribut (disabled buttons feuern keinen click). Nach 6-s-Neuaufbau sind die frischen Knöpfe aktiv, aber der Klick wird über das Modul-Flag still abgewiesen — konsistent zu ADR-K-4. Keine Nebenwirkung an anderen Knöpfen.

**(i) seq-Guard + String-Guards, „identischer Query zweimal"** — `[kosmetisch]`, akzeptieren.
Der String-Guard (`:3123`, `:3225`) greift bei identischem Query nicht, aber die Ablöse erfolgt primär über den `abort` (`:3087–3089`): eine neue Suche abortet die alte → AbortError → still (`:3223`). Der Seq-Guard (`:3220`) schließt die Lücke für den Timeout-Fall. Verbleibendes, sehr schmales Race: A und B mit identischem Query, A's `fetch` bereits resolved, aber die Fortsetzung nach `await` noch nicht gelaufen, wenn B abortet — dann rendert A einmalig über B's Spinner. Vorbestehend, extrem unwahrscheinlich, durch die Kette nicht verschlimmert. Optionaler ROADMAP-Folgepunkt: auch `:3123`/`:3225` auf `seq` absichern statt nur auf den Query-String.

**(j) `appliedInboxGroups`-Invariante** — kein Befund.
Staffel-catch (`:13387–13394`), Alle-catch (`:13472–13479`) und Bulk-catch (`:13033–13040`) greifen nicht auf `appliedInboxGroups` zu. Einziger Schreiber/Löscher bleibt der Banner-Handler (`:12871` add, `:12879` delete). Invariante hält; E2-AK7/#86-F-C erfüllt.

**(k) `groupRowStartErrors`-Wachstum** — `[kosmetisch]`, akzeptieren.
Wächst höchstens um die Gruppenzahl (im Briefing Abschnitt 4 F6.2 als „kein Leck" dokumentiert); Einträge werden beim nächsten erfolgreichen Start derselben Gruppe gelöscht (`:13381`, `:13466`). Ein toter Eintrag bei nie wieder erfolgreich gestarteter Gruppe bleibt bis Sitzungsende — speichertechnisch irrelevant.

---

## (3) Verbleibende Restrisiken

1. **R-A** (werfender `finally`/synchroner Wurf vor der try-Struktur): theoretisch offene Sperre, im Briefing akzeptiert; Neuaufbau/Neuladen heilt. Nicht neu, nicht verschärft.
2. **R-C** (kosmetischer Knopf-Zustand vs. 6-s-Neuaufbau): weiterhin vorhanden, rein visuell, Sperre wirkt über Modul-Flag.
3. **R-D** (Harness): durch Delay-Schwelle + Grün-Belege als nicht realisiert anzusehen; Restrisiko nur, falls künftig ein Test einen `setTimeout` mit `>= 30000` und Sofortausführungs-Erwartung hinzufügt.
4. **Identische-Query-Race** (i): vorbestehend, sehr schmal, keine Auswirkung auf Korrektheit, nur auf transienten Anzeigezustand.
5. **`group_key`-Kollision** (d): vorbestehend, serverseitig bedingt; kann bei gleichlautend bereinigten Titeln zu falscher Fehlerzuordnung führen. Außerhalb dieser Kette.

---

## (4) Gesamturteil

**Abnahme: JA.**

Keine `[kritisch]`- oder `[wichtig]`-Punkte, die **vor dem Merge** geklärt werden müssten. Die beiden `[wichtig]`-Befunde (W-1 unsortierte `members`, W-2 `group_key`-Kollision) sind **vorbestehende, serverseitig/architektonisch bedingte** Punkte, die diese Kette weder einführt noch verschlimmert — sie sind als ROADMAP-Folgepunkte zu führen, nicht als Merge-Blocker.

**Vor Merge zu klären: keine.**

**Empfohlene ROADMAP-Folgepunkte** (nicht blockierend):
1. `members` im Banner-Sofortstart sortieren (Konsistenz zu ADR-K-3).
2. `group_key`-Kollisionserkennung/–Vermeidung bei `cleanSeriesName`-basierten Schlüsseln.
3. Fristmeldungstext aus `SERIES_SEARCH_TIMEOUT_MS` ableiten (statt hart „30 Sekunden").
4. Doppelten `btn`-Restore im Fehlerpfad entfernen bzw. konsistent machen (toter Code, K-1).
5. Gemeinsames Timer-Harness extrahieren (Test-DRY, K-3).

**Restrisiko-Hinweis für den Merge:** Der Erfolgsfall lässt den Startknopf bis zum 6-s-Neuaufbau auf „wird gestartet…" stehen (R-C) — rein kosmetisch und bereits freigegeben, aber für den Handtest relevant (Schritt „nach jedem Schritt 6 Sekunden warten" in Abschnitt 12 deckt es ab).
