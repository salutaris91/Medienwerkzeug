# Rückkanal-Review — Feature-Kette (Pilot) #74 + #80-Rest + #83

**Auftraggeber:** Claude Code (Rolle Reviewer/Vermittler), NICHT Alex.
**Prüfumfang (nur lesend):** abgenommenes Briefing `docs/sessions/2026-10-18-roadmap74-staffel-kette/briefing.md`; Gesamt-Diff `d011499..bcac50c` über die geänderten Dateien direkt gelesen: `gui/static/app.js`, `gui/static/index.html`, `tests/frontend/inbox_group.test.js`, `tests/frontend/inbox_group_banner.test.js`, `tests/frontend/inbox_selection.test.js`, neu `tests/frontend/inbox_group_seasons.test.js`, neu `tests/frontend/series_search_timeout.test.js`.
**Konsultiert (Rohoutputs werden von Claude Code mechanisch archiviert, hier nur mit Rollenzuordnung zitiert):** [produktberater], [advocatus].

**Verifikationsgrenze:** Diese Session hat kein `bash`/`git`. Ich habe Code und Tests **selbst gelesen** und gegen die AKs abgeglichen (Behauptungen nicht übernommen). Die Suite-Zahlen (529 + 219/226/231), die Rot-Proben und `git diff --check` sind **Belege von Claude Code**, die ich nicht erneut ausführen konnte — sie werden als vorgelegt bewertet, nicht als unabhängig nachgemessen. Alex' FP2-Wortlaute sind im Code geprüft (siehe UI-Text-Abschnitt).

**Kurzurteil vorab:** Die Kette setzt alle AKs funktional um; die Tests decken die AKs in ihren Rümpfen tatsächlich ab (nicht nur den Namen nach); die UI-Texte stimmen exakt mit ADR-K-2 inkl. Alex' FP2-Wortlaut und Gedankenstrich U+2013 überein. Beide Rollen und diese Prüfung kommen auf **ABNAHME: JA**. Zwei `[wichtig]`-Punkte sind **vorbestehend und außerhalb dieser Kette** (ROADMAP-Folgepunkte, keine Merge-Blocker).

---

## 1. Etappen-Prüfung gegen die Akzeptanzkriterien

### 1.1 E1 — #74 Staffel-Schnellauswahl + Banner-Split + Umbenennung (Ampel GELB)

| AK | Code (app.js) | Test (inbox_group_seasons.test.js) | Befund |
|---|---|---|---|
| E1-AK1 Staffel-Knöpfe ≥ 2 Staffeln, `Staffel N (k)` aufsteigend; Einzelstaffel keine Reihe; Alle `Alle verarbeiten` | `:13355` `distinctSeasons` aus `item.items` per `Set` + numerisch sortiert; `:13357` nur `>= 2`; `:13367` `Staffel ${seasonNum} (${seasonMembers.length})`; `:13350` `Alle verarbeiten` | `:761–812` prüft 3 Knöpfe `['Staffel 1 (3)','Staffel 2 (1)','Staffel 11 (3)']`, Position zwischen Header/Members, `type=button`/`btn-xs`, Einzelstaffel `=== null`, beide Alle-Labels | **AK erfüllt.** Test prüft Wortlaut, Reihenfolge und Abwesenheit bei Einzelstaffel echt. |
| E1-AK2 Klick übergibt genau die Staffel, Folgenreihenfolge, Ordner-Folge via `single_video_relpath` | `:13362` `seasonMembers = item.items.filter(m => m._se.season === seasonNum)`; `:13382` `seasonMembers.map(inboxFilesEntryForItem)`; `:13383` `startSeriesGroupWorkflow(item.group_key, files)` | `:817–855` erwartet exakt `['…S11E01.mkv','…S11E02.Folder/episode2.mkv','…S11E03.mkv']` (Ordner-Folge als Relpath) + Ansichtswechsel | **AK erfüllt.** Ordner-Folge über Relpath nachgewiesen; Reihenfolge aus vorgelagerter Sortierung. |
| E1-AK3 Alle-Knopf übergibt alle Folgen in Items-Reihenfolge | `:13467` `item.items.map(inboxFilesEntryForItem)` | `:860–900` erwartet alle 7 sortiert S01→S02→S11 | **AK erfüllt.** |
| E1-AK4 Knöpfe nach 6-s-Neuaufbau | `renderSmartInboxList` baut Reihen bei jedem Aufruf neu (`:13355ff`) | `:905–947` zweimaliger Render, danach Staffel-2- und Alle-Klick funktionieren | **AK erfüllt.** |
| E1-AK5 Sonderzeichen im strengen Mock | Handler per Closure ans Element gebunden, **kein** Selektor mit `group_key`/Staffel (`:13368`, `:13453`); `data-group-key` nur Attribut (`:13320`, `:13349`) | `:952–997` `validateSelector`-Mock wirft bei ungültigen Selektoren; Name maskiert (`&quot;`/`&lt;`), Staffel-Klick + Alle-Klick `doesNotReject` | **AK erfüllt.** Der strenge Mock (nicht der lockere `inbox_group`-Mock) macht den Test wertvoll — B11a eingehalten. |
| E1-AK6 Banner-Split + Hinweiszeile | `:12873` `seasonCount = new Set(members.map(m => m._se.season)).size`; `:12874` Start nur `if (seasonCount < 2)`; Hinweis `:12702`/`:12732` | `:1002–1084` Teil A (≥ 2): Hinweis exakt inkl. U+2013, `appliedInboxGroups` gesetzt, Gruppenzeile erscheint, **`searchCalls === 0`**, Ansicht/`activeSeriesGroupFiles` unverändert; Teil B (1 Staffel): kein Hinweis, Sofortstart, Fehlerpfad mit Rollback | **AK erfüllt.** „kein Start" über `searchCalls===0` belegt; Hinweis nur bei ≥ 2. |
| E1-AK7 gemeinsame Sperre, vier Startstellen, still | `if (groupWorkflowRunning) return;` jeweils **erste** Anweisung: Banner `:12861`, Alle `:13454`, Staffel `:13369`, Bulk `:12963` | `:1089–1186` rotiert alle vier Starter; prüft Zweitstart → `searchCalls` bleibt 1, Kandidaten-Knopf **nicht** disabled, Textwechsel aus, `consoleErrors`/`alerts`/Banner-Fehler leer | **AK erfüllt.** „still" (kein Feedback am Zweitstart) ist direkt getestet. |
| E1-AK8 Freigabe in `finally` auch bei Erfolg | `finally { groupWorkflowRunning = false; }` an allen vier Stellen (`:12884`, `:13042`, `:13396`, `:13481`) | `:1191–1259` Staffelfolge nach je erfolgreichem Start frei; nach Re-Render Knöpfe wieder aktiv | **AK erfüllt.** |
| E1-AK9 benannte F2-Bestandstest-Anpassung | — | `inbox_group.test.js:1419` Testname trägt jetzt „Alle verarbeiten"; `:1459` `includes('Alle verarbeiten')`, `:1460` Negativ-Assertion bleibt | **AK erfüllt.** Anpassung verschärft (prüft neuen Label positiv + alten Begriff negativ); Rot gegen Basis (alter Label „Auswählen") ist von Claude Code belegt, hier nicht erneut ausführbar. |

**UI-Text-Tabelle ADR-K-2 (Alex' FP2-Wortlaut) — Abgleich Code ↔ Test:**
- `Alle verarbeiten` → `app.js:13350` / Tests `:803`, `:1459`. **exakt.**
- Banner-Hinweis `Diese Serie hat mehrere Staffeln – nach dem Gruppieren kannst du in der Liste eine einzelne Staffel oder alle Folgen verarbeiten.` → `app.js:12702` und `:12732` (beide Vorkommen identisch, Gedankenstrich **U+2013** echt, keine ASCII-Umschrift) / Test `:1004`/`:1028` vergleicht wörtlich. **exakt** (Präzedenz #75 F2 eingehalten).
- `Staffel N (k)` → `app.js:13367` / Test `:793`. **exakt.**
- E2-Meldung `Serien-Start fehlgeschlagen. Bitte erneut versuchen.` → `app.js:12881`, `:13035`, `:13389`, `:13474` / Tests `:1266`, `:1298`, `:1659`. **exakt.**
- E3-Meldung `Suchfehler: Zeitüberschreitung nach 30 Sekunden. Bitte erneut versuchen.` → `app.js:3221` / Test `:792`, `:838`. **exakt** (siehe Hinweis (b) in Abschnitt 2).

### 1.2 E2 — #80-Rest: sichtbare Start-Fehler (Ampel GRÜN)

| AK | Code | Test | Befund |
|---|---|---|---|
| E2-AK1 Fehler Alle-Knopf → Inline-Meldung Gruppenzeile, `console.error`, Knopf benutzbar, Sperre frei | `:13472–13482` catch setzt `groupRowStartErrors`, `console.error`, render; Zeichnung `:13489–13496` (`div.smart-inbox-group-banner-error`, `role=alert`, `aria-live=polite`, `textContent`) | `:1264–1357` prüft Klasse/`role`/`aria-live`/Text, Platzierung nach Staffel-Leiste bzw. direkt nach Header, andere Zeilen fehlerfrei, `console.error` mit Ursache, zweiter erfolgreicher Start läuft | **AK erfüllt.** Injektion über werfenden `triggerQualityHintUpdates`-Stub (`:524`), kein fetch-Stub — Präambel-Binding korrekt. |
| E2-AK2 Fehler Staffel-Knopf; `appliedInboxGroups` UNVERÄNDERT | `:13387–13394` (kein `appliedInboxGroups`-Zugriff) | `:1362–1423` erwartet Map-Größe 2 unverändert, Meldung in derselben Zeile, Retry erfolgreich | **AK erfüllt.** |
| E2-AK3 Fehler Bulk-Leiste → INLINE (kein `alert()`), `width:100%` | Bulk-Template `:12937–12939` zwischen Info und Buttons; catch `:13033–13040` | `:1428–1478` prüft `alerts.length===0`, Platzierung Info<Error<Buttons, `width: 100%`, Retry | **AK erfüllt.** Bestehende `alert()`-Pfade bleiben unberührt. |
| E2-AK4 Meldung überlebt 6-s-Neuaufbau | Modul-Map `:12494` + Variable `:12495`; Zeichnung bei jedem Render | `:1483–1545` erwartet nach erneutem Render **frisch gezeichnete** Knoten (`notStrictEqual` zu vorher) mit gleichem Text | **AK erfüllt.** Muster `bannerApplyErrors` überlebt nachweislich. |
| E2-AK5 Leeren beim nächsten Erfolg / Deselect / Leiste verschwindet | Erfolg löscht vor Start (`:13380–13381`, `:13465–13466`, `:13023–13024`); Deselect `:12952`; count 0 `:13046` | `:1550–1638` deckt alle vier Löschpfade ab inkl. „Gruppen-Fehler bleibt, bis DIESE Gruppe erfolgreich ist" | **AK erfüllt.** |
| E2-AK6 Bulk-Auswahl bleibt nach Fehler | catch ändert `selectedInboxProjects` nicht | `:1643–1673` prüft Auswahl, Zähler „2 ausgewählt", Checkboxen | **AK erfüllt.** |
| E2-AK7 Bestand `alert()` + `appliedInboxGroups`-Invariante | nur Banner schreibt/löscht die Menge | `:1678–1740` prüft beide `alert()`-Pfade wörtlich + Map unverändert bei allen drei Fehlerpfaden | **AK erfüllt.** (#86 F-C eingehalten.) |

### 1.3 E3 — #83 Frist 30 s in `searchSeries` (Ampel GELB)

| AK | Code | Test | Befund |
|---|---|---|---|
| E3-AK1 Frist bei hängender Suche | `SERIES_SEARCH_TIMEOUT_MS=30000` `:3076`; `deadlineId=setTimeout(...)` `:3095`; fetch mit `localController.signal` `:3112`; AbortError-Zweig zeichnet nur bei `didTimeout && seq===…` `:3220` | `:797–857` browser-treuer Abort-Spy (`installAbortAwareSearchFetch` `:725`, rejectet mit `AbortError`), erwartet exakt `<p class="text-center text-danger">…</p>`, Queue leer, Sperre frei für Anschlussstart | **AK erfüllt.** Spy ist nicht abort-blind — AK-Voraussetzung eingehalten. |
| E3-AK2 Ablösung bleibt still (Seq-Guard) | Registry-Ablösung `:3087–3089` abortiert nur Vorgänger; Timeout abortiert nur `localController` `:3097`; Seq-Guard `:3220` | `:862–972` Teil 1 A→B still; Teil 2 identischer Query „Tatort", A's Timer **nach** B-Start → A still, B bleibt, Callback wirft nicht | **AK erfüllt.** Schließt die von [advocatus] F3.3/F3.4 identifizierte String-Guard-Lücke. |
| E3-AK3 normale Suche unberührt, Timer in `finally` zurück | `finally { clearTimeout(deadlineId); }` `:3228`; String-Guards `:3123`/`:3225` unverändert | `:977–1012` erwartet Ergebnisse, keine Fristmeldung, `clearTimeout`-Id in `clearedTimerIds` | **AK erfüllt.** |
| E3-AK4 Pfadabdeckung manuell + Workflow | manuell `:7582` (Enter) + Button; Workflow `return searchSeries()` `:13232` | `:1017–1118` fährt AK1/AK2/AK3 je über Button-Klick, Enter UND Workflow-Pfad | **AK erfüllt.** |
| E3-AK5 Timer-Harness | Queue mit Schwelle `>= 30000`; kleinere Delays sofort | `:1123–1190` prüft Mechanik (200 ms scrollIntoView sofort, 30000 ms queue) **und liest die vier Bestandsdateien**, dass der alte Sofort-Stub überall ersetzt ist | **AK erfüllt.** Meta-Test sichert die Umstellung in allen Dateien (`inbox_group:539`, `banner:647`, `selection:560`, `seasons:619`). |

### 1.4 ALL-Kriterien
- **ALL-AK1 Cache-Buster:** `index.html:2760` = `app.js?v=104`, alle neun Importe `app.js:1–9` = `?v=104` (10 Stellen), `index.html:9` = `style.css?v=51` unverändert. **erfüllt.** `cache_busting.test.js` ist in der Änderungsmenge nicht enthalten → nicht angepasst (erwartungskonform); Grün-Beleg von Claude Code.
- **ALL-AK2 keine Test-Weichen:** Export-Block `app.js:13652–13667` ausschließlich `globalThis.X = X` (plus bereits vorhandene Getter/Setter-Closures). Produktcode liest **keine** nur testseitig gesetzten Globalen; Tests lesen Modulzustand über Harness-Getter im eval-Scope (`getActiveSeriesGroupFiles` etc.), nicht über `globalThis`-Spiegel. `groupWorkflowRunning`/`groupRowStartErrors`/`bulkStartError`/`SERIES_SEARCH_TIMEOUT_MS` werden **nicht** exportiert. **erfüllt.**
- **ALL-AK3 Hygiene:** keine echten Timer in Tests (Queue); `git diff --check` laut Claude Code sauber (hier nicht ausführbar). **_plausibel, nicht unabhängig gemessen._**

---

## 2. Wechselwirkungen zwischen Etappen (Gesamt-Diff `d011499..bcac50c`)

**Gemeinsame Zustände/Funktionen:** Eine Sperre `groupWorkflowRunning` (`:12496`) steuert nach E1 alle vier Startstellen; E2 speist bei Fehlern `groupRowStartErrors` (Map, `:12494`) und `bulkStartError` (`:12495`) und ruft im `catch` `renderSmartInboxList`/`updateBulkActionsBarUI`; E3 macht `searchSeries` nach 30 s abortbar und **resolved** damit das `await startSeriesGroupWorkflow` der Startstellen → `finally` gibt die Sperre frei. Die Kette ist damit in sich geschlossen: E3 ist der Mechanismus, der die von E1/E2 gehaltene Sperre im Hänge-Fall wieder löst (R6-Plan).

**Bewertung der Hinweise (a)–(g):**

- **(a) Knopf-Restore nur im `catch`, Sperre im `finally`** — **[kosmetisch], akzeptieren.** [advocatus]: Freigabe liegt in jedem Pfad im `finally`, **kein Deadlock**; der hängende Knopf-Text ist exakt das im Briefing dokumentierte R-C. Wichtige Einordnung für Alex: Dies ist **keine Abweichung vom abgenommenen Plan.** Alex' Plan-Go-Punkt P2 („Knopf-Rücksetzen in `finally`") wurde im Briefing **bewusst** in ADR-K-4 operationalisiert als „`finally`-Freigabe hat Vorrang; `btn.disabled`/„wird gestartet…" bleiben Kosmetik, weil der 6-s-Neubau sie ohnehin verwirft". Der Code folgt genau dieser freigegebenen Auslegung. [produktberater] sieht den Rest als „≤ 6 s, nicht blockierend" → ROADMAP. **Kein Nachbesserungslauf nötig.**
- **(b) Fristmeldung fest „30 Sekunden" (unabhängig von `SERIES_SEARCH_TIMEOUT_MS`, `:3221`)** — **[kosmetisch], akzeptieren; bewusst NICHT jetzt ändern.** Hier besteht ein **Rollen-Dissens**, der dokumentiert wird: [produktberater] schlug einen trivialen Einzeiler `${SERIES_SEARCH_TIMEOUT_MS/1000} Sekunden` vor; [advocatus] (K-2) und diese Prüfung halten dagegen, dass ADR-K-2 den Wortlaut „nach 30 Sekunden" **verbindlich** festschreibt und der Test `:792`/`:838` ihn wörtlich verlangt. Eine Dynamisierung wäre heute inhaltlich identisch (Konstante = 30000), würde aber den freigegebenen UI-Text an eine Konstante koppeln, die laut Abschnitt 4 bewusst **nicht** konfigurierbar ist. **Entscheidungsempfehlung an Alex:** jetzt **akzeptieren** (Wortlaut ist durch FP2 gebunden); als ROADMAP-Punkt vormerken, den Text aus der Konstante abzuleiten, **falls** die Dauer je konfigurierbar wird — sonst „lügt" die Meldung nach einer künftigen Konstantenänderung.
- **(c) Banner-Sofortstart übergibt unsortierte `members` (`:12875`)** — **[wichtig], aber VORBESTEHEND → ROADMAP-Folgepunkt, kein Merge-Blocker.** Beide Rollen einig: Die Unsortedness ist nicht von dieser Kette eingeführt (der Sofortstart existierte vorher; E1 hat ihn nur um die `seasonCount < 2`-Verzweigung ergänzt). Die Gruppenzeile nutzt korrekt das sortierte `item.items` (`:13467`), der Banner-Pfad nicht → **Inkonsistenz zwischen zwei Startwegen.** [advocatus] W-1: Auswirkung nur auf **Anzeige-Reihenfolge** der Zuordnungstabelle, nicht auf die S/E-Zuordnung (die ist dateinamenbasiert). [produktberater]: echter, kleiner Nutzerbug. Fix wäre eine Zeile (sortierung wie ADR-K-3). Empfehlung: ROADMAP.
- **(d) Gruppenerkennung entfernt Sonderzeichen (`Law & Order` → `Law  Order`)** — **[wichtig], VORBESTEHEND → ROADMAP-Folgepunkt.** [advocatus] W-2 lokalisiert die Normalisierung in `cleanSeriesName` (serverseitig/`utils.js`), **nicht** in `detectInboxGroups`; die Kette führt keine zusätzliche Normalisierung ein und reicht `group_key` unverändert durch. Folge: theoretische **Kollisionsgefahr** unterschiedlicher Titel auf demselben Schlüssel, der `groupRowStartErrors` und `appliedInboxGroups` teilen → im Kollisionsfall Meldung der falschen Gruppe zugeordnet. E1-AK5 belegt aber, dass `"`,`'`,`<`,`&` im Schlüssel erhalten bleiben und nicht werfen. Kein Effekt auf Staffel-Knöpfe (Closure-Handler). Empfehlung: ROADMAP (Kollisionserkennung), kein Blocker.
- **(e) Wechselwirkung E1×E2 — `render…` im `catch` bei noch gesetzter Sperre** — **[kosmetisch], akzeptieren, unkritisch.** [advocatus] und diese Prüfung: Der Neuaufbau erzeugt **neue** Knoten (`innerHTML=""` zuvor) und bindet Listener nur an diese → **kein Doppel-Binden**, kein Überschreiben (die Meldung wird bewusst aus der im `catch` gesetzten Map gezeichnet). Das Fenster `groupWorkflowRunning===true` zwischen `render` und `finally` ist **synchron ohne `await`** — der Event-Loop kann dort keinen Klick einschieben. Einziger Mangel: der `btn.disabled=false`/`innerHTML`-Restore im `catch` (`:13036`, `:13390`, `:13475`) ist **toter Code**, weil der unmittelbar folgende Render den Knoten ohnehin ersetzt ([advocatus] K-1) — irreführend, aber harmlos. Empfehlung: akzeptieren; „toten Restore bereinigen" optional als ROADMAP.
- **(f) Wechselwirkung E1×E3 — `searchSeries`-Aufrufer und Fristmeldung** — **kein Befund, akzeptieren.** [advocatus]: Kein Aufrufer hält eine **eigene** Sperre; die einzige Sperre ist `groupWorkflowRunning` der vier Startstellen, die korrekt im `finally` frei wird, sobald `searchSeries` durch den Abort resolved (AbortError intern gefangen `:3218–3223`). Die fire-and-forget-Aufrufer `detectExistingSeries` (`:2989`/`:3017`) und Auto-Suche (`:3069`) halten keine Sperre — eine Fristmeldung im geteilten `series-search-results` im Hintergrund ist möglich, aber **gewollt** (S4: Timeout wirkt auf alle Aufrufer) und sichtbar. [produktberater]: an allen Pfaden sinnvoll, da immer im Suchbereich. Ablösung korrekt: `:3087–3089` abortet nur das Vorgänger-Objekt, der Timeout nur den eigenen `localController`. **Kein Aufrufer wird durch die Frist fehlerhaft freigegeben.**
- **(g) E3-Harness — identischer ~14-Zeilen-Timer-Stub in vier Dateien (+ eigene Variante in `series_search_timeout`)** — **[kosmetisch], akzeptieren; optionaler ROADMAP.** [advocatus]: Vor der Kette existierte **kein** Timer ≥ 30000, daher hängt kein Bestandstest an Sofortausführung; die Delay-Schwelle schützt die scrollIntoView-200-ms-Timer. Duplikation ist DRY-Verletzung, aber konsistent mit dem bereits bestehenden Muster, dass jede Frontend-Testdatei ihren kompletten Mock-Harness eigenständig trägt. Empfehlung: gemeinsames Harness **extrahieren** als eigener, bewusster Refactor-Zyklus (würde alle Testdateien anfassen → außerhalb dieser Kette), nicht als Nachbesserung.

**Ergänzende Prüfpunkte (von [advocatus] zusätzlich belegt, hier bestätigt):**
- **(h) „still abweisen":** `if (groupWorkflowRunning) return;` steht an allen vier Stellen als **erste** Anweisung, vor jedem `disabled`/Textwechsel → Zweitstart ohne Nebenwirkung. E1-AK7 testet das direkt. **OK.**
- **(i) Seq-/String-Guards bei identischem Query:** Der String-Guard (`:3123`/`:3225`) greift bei gleichem Query nicht, aber die Ablösung läuft primär über `abort`; der Seq-Guard (`:3220`) fängt den Timeout-Fall. [advocatus] K-4: ein sehr schmales, **vorbestehendes** Race (A resolved, Fortsetzung nach `await` noch nicht gelaufen, während B abortet) bleibt — ohne Korrektheitsauswirkung, nur transienter Anzeigezustand. Optionaler ROADMAP: auch `:3123`/`:3225` auf `seq` absichern. **Kein Blocker.**
- **(j) `appliedInboxGroups`-Invariante:** Staffel-/Alle-/Bulk-`catch` greifen **nicht** auf die Menge zu; einziger Schreiber/Löscher bleibt der Banner (`:12871`/`:12879`). **OK** (E2-AK7, #86 F-C).
- **(k) `groupRowStartErrors`-Wachstum:** wächst höchstens um die Gruppenzahl, Einträge werden beim nächsten Erfolg gelöscht; ein toter Eintrag bleibt bis Sitzungsende — speichertechnisch irrelevant. **OK** (Briefing Abschnitt 4 F6.2).

---

## 3. Zurückgestellte Punkte / ROADMAP-Kandidaten ([produktberater], max. 5, priorisiert)

1. **K2 „Rest der Gruppe auswählen" (#74-verwandt):** Nach dem Verarbeiten einer Staffel direkt die nächste wählen, ohne zurück zur Liste. [produktberater]: **echter Nutzen** (Workflow-Beschleunigung bei 11 Staffeln), schwächt den MVP **nicht** — E1 erlaubt staffelweise Verarbeitung bereits; K2 ist Komfort für den Folgeschritt.
2. **#82 „Ignorierte Vorschläge bei neuen Folgen automatisch zurückholen":** [produktberater]: **echter Nutzen** (Serie „erstmal raushaben", später zurückholen; Alex-Wunsch aus #75), schwächt den MVP nicht.
3. **Banner-Sofortstart sortieren** (Hinweis c, `app.js:12875`): [advocatus] W-1 / [produktberater]: vorbestehender, kleiner Anzeige-Bug — Zuordnungstabelle in korrekter Staffel-/Folgenreihenfolge; 1-Zeilen-Fix. **echter Nutzen.**
4. **`group_key`-Kollisionsschutz** (Hinweis d, `cleanSeriesName`/`utils.js`): [advocatus] W-2: vorbestehend, serverseitig bedingt; Schutz gegen gleichlautend bereinigte Titel, damit Fehlermeldungen nie der falschen Gruppe zugeschrieben werden. **echter Nutzen, aber seltener Fall.**
5. **Test-Harness-DRY + Fristmeldungs-Ableitung + toter Restore** (Hinweise g/b/a): gemeinsames Timer-/Mock-Harness extrahieren; Fristmeldung aus `SERIES_SEARCH_TIMEOUT_MS` ableiten, **sobald** die Dauer konfigurierbar wird; toten `btn`-Restore im Fehler-`catch` bereinigen. **Wartbarkeits-/Komfort-Nutzen, kein Funktionsnutzen.**

> Hinweis zur Vollständigkeit: [produktberater] stuft (a) Knopf-Restore und (b) dynamische Fristmeldung als eigene, niedrige Kandidaten ein; sie sind hier in Kandidat 5 gebündelt. Der **einzige** Punkt mit direktem Nutzerwert aus dieser Kette ist Kandidat 3 (Sortierung) — alle übrigen sind Komfort (K2/#82) oder Wartbarkeit.

---

## 4. Handtest-Prüfliste für Alex (lokal, Testdaten von Claude Code; max. 10, inkl. einmal 6 s warten)

Grundregel aus Briefing Abschnitt 12: **nach jedem Schritt einmal 6 Sekunden warten** (Neuaufbau via `setInterval(loadStatus, 6000)`), damit Knöpfe frisch gebaut werden. Die Fehlerfälle E2/E3 hat Claude Code bereits im Browser belegt; sie sind hier nur dort aufgenommen, wo ein eigener Blick Sinn ergibt.

1. **E1 Hinweis + Gruppieren:** Mehrstaffel-Gruppe im Banner → Hinweiszeile sichtbar (exakter Wortlaut, Gedankenstrich); Klick „Als Serie gruppieren" → **nichts startet**, Ansicht bleibt, Gruppenzeile erscheint mit `Staffel N (k)`-Knöpfen (aufsteigend, Zahlen plausibel) und „Alle verarbeiten".
2. **E1 Einzelstaffel:** Einzelstaffel-Gruppe im Banner → Klick startet wie bisher **sofort** den Serien-Dialog (kein Hinweis).
3. **E1 Staffel-Klick:** „Staffel 2 (…)" klicken → Dialog/Dateiliste enthält **genau** die Folgen dieser Staffel (inkl. einer Ordner-Folge).
4. **E1 6-s-Resilienz:** nach 6 s Warten denselben Staffel-Knopf erneut klicken → gleicher Effekt.
5. **E1 Doppelklick/Sperre:** während eines laufenden Starts einen zweiten Knopf (andere Stelle) klicken → **passiert still nichts**, kein zweiter Dialog; nach Abschluss wieder startbar.
6. **E1 Sonderzeichen:** Gruppen mit `&` und `"` → Namen lesbar maskiert, kein kaputtes Markup, Knöpfe klickbar.
7. **E2 Fehler (nur zum Selbstsehen, wenn gewünscht):** Claude Codes gepatchte Wurf-Kopie nutzen → „Alle verarbeiten"/Staffel/Bulk-Fehler zeigt **rote Inline-Meldung** in der Zeile/Leiste, Auswahl bleibt, kein `alert()`; Browser-Konsole zeigt `console.error`. (Von Claude Code bereits belegt — optional eigener Blick.)
8. **E2 Überleben:** Meldung über 6 s stehen lassen → bleibt stehen; erfolgreicher Start **derselben** Stelle → Meldung weg.
9. **E3 Frist:** hängende `/api/search` (Claude Codes Drossel-Weg) → nach ~30 s Meldung „Suchfehler: Zeitüberschreitung nach 30 Sekunden. Bitte erneut versuchen." im Suchbereich; danach **sofort** neuer Start möglich (Sperre frei).
10. **E3 normale Suche:** schnelle Suche → Ergebnisse wie bisher, **keine** Fristmeldung.

---

## 5. Befunde und Abnahme

**[kritisch]:** keine. (Diese Prüfung + [advocatus] + [produktberater] einvernehmlich.)

**[wichtig]:**
- W-1 Banner-Sofortstart übergibt unsortierte `members` (`app.js:12875`) — **vorbestehend**, nur Anzeige-Reihenfolge der Zuordnungstabelle, nicht von dieser Kette eingeführt → ROADMAP (Kandidat 3). **Kein Merge-Blocker.**
- W-2 `group_key`-Kollisionsgefahr durch `cleanSeriesName`-Normalisierung (`utils.js`) — **vorbestehend**, außerhalb des Scopes, kann im Kollisionsfall Fehlerzuordnung vermissen → ROADMAP (Kandidat 4). **Kein Merge-Blocker.**

**[kosmetisch]:**
- K-1 Knopf-Restore nur im `catch` (Erfolgsfall „wird gestartet…" bis 6-s-Neubau) = dokumentiertes R-C, entspricht ADR-K-4 (kein Plan-Verstoß).
- K-2 Fristmeldung hart „30 Sekunden" — durch ADR-K-2 **verbindlich** so gewollt; Dynamisierung erst bei konfigurierbarer Dauer.
- K-3 Timer-Stub-Duplikation in vier Testdateien — konsistent mit bestehendem Harness-Muster; DRY als eigener Refactor-Zyklus.
- K-4 toter `btn`-Restore im Fehler-`catch` (render ersetzt Knoten ohnehin) — irreführend, harmlos.
- K-5 schmales vorbestehendes Identical-Query-Race im Nicht-Timeout-Pfad — keine Korrektheitsauswirkung.

**Dissens-Dokumentation (Pflicht):** Einziger echter Rollen-Widerspruch ist Hinweis **(b)** — [produktberater] wollte sofort auf die Konstante umstellen; [advocatus] und diese Prüfung behalten den festen Wortlaut bei, weil ADR-K-2/FP2 ihn binden. Auflösung: **jetzt akzeptieren, ROADMAP-Folgepunkt.** Die beiden [wichtig]-Punkte (W-1/W-2) sind zwischen den Rollen **konsensfähig** als vorbestehende ROADMAP-Punkte, nicht als Blocker.

**Verbleibende Restrisiken (nicht eliminierbar, nur behandelbar):** R-A (werfender `finally`/synchroner Wurf vor `try` — im Briefing akzeptiert, Neuaufbau/Neuladen heilt), R-C (Knopf-Optik vs. 6-s-Takt), R-D (Harness-Restrisiko, durch Delay-Schwelle + Grün-Belege als nicht realisiert bewertet). Alle im Briefing Abschnitt 6 bereits benannt und durch diese Prüfung bestätigt.

**Stichproben-pflichtige Themen (Geld/Aussenwirkung/Recht/Registrierung/Kauf):** **keine** — reine lokale Frontend-Änderung, keine neuen Abhängigkeiten, keine Außenwirkung, keine Lizenzänderungen. [produktberater] und diese Prüfung bestätigen das. Rohoutputs der Rollenabstimmung: `docs/sessions/2026-10-18-roadmap74-staffel-kette/` (`produktberater.md`, `advocatus.md`, `grafiker.md`).

**Nicht unabhängig nachgemessen (Transparenz):** Suite-Grün, Rot-Proben und `git diff --check` sind Belege von Claude Code; diese Session hat kein `bash`/`git`. Code- und Test-Lektüre erfolgten selbst und stützen das Urteil.

**ABNAHME: JA** — keine [kritisch]-Befunde; die zwei [wichtig]-Befunde (W-1 Sortierung, W-2 `group_key`-Kollision) sind vorbestehend und außerhalb dieser Kette und als ROADMAP-Folgepunkte zu führen, nicht als Merge-Blocker; die [kosmetisch]-Punkte sind entweder durch ADR-K-2/FP2 bindend gewollt (K-2) oder dokumentierte, freigegebene Restrisiken (K-1/R-C).
