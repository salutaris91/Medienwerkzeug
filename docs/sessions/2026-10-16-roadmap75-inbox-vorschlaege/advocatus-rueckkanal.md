<!-- Mechanisch aus `opencode export ses_eb48d8d4effeH2taxJRSb1spb7` extrahiert (Claude Code, 2026-10-17, Rückkanal): alle Assistant-Textteile in Reihenfolge, ungekürzt, unverändert (nur Trailing Whitespace entfernt). Rohdatei: Kit scripts/gate-a2/logs/2026-10-16-roadmap75-inbox-vorschlaege/rueckkanal/export-direkt/export-advocatus.json -->

Ich habe die Artefakte vollständig gelesen (app.js 12440–12899, 3079–3214, 12994–13272, 13506–13559; die neue Testdatei komplett 1–1278; den angepassten Bestandstest `inbox_group.test.js:800–919`; das Briefing komplett; zusätzlich die Backend-Quelle von `suggested_query` in `gui/api/project_api.py` und `gui/core/utils.py`). Keine Schreiboperationen, keine Tests ausgeführt, keine `.env` gelesen.

# Befunde nach Schwere

## [wichtig] B1 — `bannerApplyErrors`-Leiche: alte Fehlermeldung taucht nach „Ignorieren → Wieder anzeigen" wieder auf
**Prüfauftrag 8 (sonstige Fehlerpfade).** Pfad:
1. Gruppe A „Als Serie gruppieren" → Start wirft → `catch` setzt `bannerApplyErrors.set(A, …)` (`app.js:12837`), Re-Render zeichnet die Inline-Meldung nur in den **offenen** Zonen (`app.js:12677–12678`, `12703–12704`).
2. Nutzer klickt „Ignorieren" für A → Ignorier-Handler (`app.js:12806–12809`) ruft `setInboxGroupIgnored`, **löscht aber `bannerApplyErrors` nicht**. A wandert nach Zone 3, die Meldung wird dort nicht gezeichnet (`app.js:12735–12750` rendert keine Fehlermeldung) — sie bleibt still in der Map liegen.
3. Nutzer klickt „Wieder anzeigen" → `clearInboxGroupIgnored` (`app.js:12627–12636`) löscht den localStorage-Schlüssel und das Fallback-Set, **nicht aber `bannerApplyErrors`**. A erscheint wieder in den offenen Zonen → `updateGroupBannerUI` zeichnet die **alte** Fehlermeldung erneut (`app.js:12677–12678`).

Der Eintrag wird nur bei `bannerApplyErrors.delete(groupKey)` unmittelbar vor einem erneuten Apply derselben Gruppe gelöscht (`app.js:12829`). Es ist ein klarer, reproduzierbarer Zustands-Leak (veraltete Fehlermeldung), aber ohne Datenverlust/Crash.

**Empfehlung: jetzt beheben (Gate-A2-Lauf 2).** Ein-Zeilen-Fix: `bannerApplyErrors.delete(groupKey)` in `clearInboxGroupIgnored` (oder im Ignorier-Handler) ergänzen.

## [wichtig] B2 — Hängende Suche lässt `groupWorkflowRunning` dauerhaft `true`
**Prüfauftrag 2 (Hinweis b).** Belegt:
- `searchSeries` hat einen `AbortController` (`app.js:3088`, Signal am fetch `:3103`), aber **keinen Timeout**. Der Abort wird nur bei einem *neuen* `searchSeries`-Aufruf ausgelöst (`app.js:3085–3087`).
- `startSeriesGroupWorkflow` ist synchron und gibt am Ende `searchSeries()` zurück (`app.js:13173–13174`); der Apply-Handler `await`et genau das (`app.js:12833`).
- `groupWorkflowRunning` wird ausschließlich im `finally` zurückgesetzt (`app.js:12843–12845`), das erst läuft, wenn das `await` beendet ist. Die Sperre greift bei `app.js:12818`.

Hängt `/api/search` (Backend blockiert, Netzwerkpartition ohne Socket-Close), bleibt das Promise pending → `groupWorkflowRunning` bleibt `true` → **alle weiteren Banner-Apply-Klicks sind bis zum Reload blockiert**. Ignorieren/Wiederanzeigen und die Inbox-Liste bleiben nutzbar; kein Datenverlust. Das fehlende Timeout ist vorbestehendes `searchSeries`-Verhalten, aber die Sperre ist neu und verstärkt die Folge.

**Empfehlung: ROADMAP-Folgepunkt** (Timeout-/Abort-Guard entweder in `searchSeries` oder ein Timeout um den `await` im Apply-Handler). Kein Blocker für diese Kette, da kein Datenverlust und im Lokalbetrieb (localhost/NAS) selten.

## [kosmetisch] B3 — Hinweis (a): „ignoriert vor angewendet" ist nicht erreichbar
**Prüfauftrag 1.** Die Prüfreihenfolge in `app.js:12657–12664` (ignoriert vor angewendet) wäre nur dann falsch, wenn eine Gruppe *gleichzeitig* ignoriert **und** angewendet wäre. Der einzige Schreiber von `appliedInboxGroups` ist `appliedInboxGroups.add(groupKey)` im Banner-Apply (`app.js:12830`) — bestätigt per grep (keine weiteren `add`-Stellen; `delete` nur im catch `:12835`). Die dort angewendete Gruppe ist zuvor zwingend **offen** (nicht ignoriert), da `openGroups` nur `!isInboxGroupIgnored && !appliedInboxGroups.has` enthält (`app.js:12657–12663`). Nach `add` + Re-Render verschwindet sie aus dem Banner (weder offen noch ignoriert). Es gibt keinen Codepfad, der beide Zustände gleichzeitig herstellt.

**Empfehlung: akzeptieren.** ROADMAP-Notiz, dass die Prüfreihenfolge umzudrehen ist („angewendet" zuerst → gar nicht ins Banner), sobald künftig #80-Bulk-Weg oder die Q1-Erweiterung `appliedInboxGroups` befüllt.

## [kosmetisch] B4 — Hinweis (f): `setInboxGroupIgnored`-Fallback ohne Log bei fehlendem `localStorage`
**Prüfauftrag 5.** Der `else`-Zweig („localStorage undefined/null") trägt die Gruppe ins Fallback-Set **ohne** Log ein (`app.js:12618–12620`), während der `catch`-Zweig (`setItem` wirft) korrekt `console.warn` loggt (`app.js:12622–12623`). Das entspricht wörtlich dem Briefing (ADR-75-2 verlangt den Log nur für den Wurf-Fall), berührt aber die Hausregel „kein stilles Scheitern" marginal: Der Zustand wird für die Sitzung korrekt ausgeblendet, aber die fehlende Persistenz bleibt stumm. Im Browser ist der Pfad praktisch unerreichbar (localStorage existiert fast immer).

**Empfehlung: akzeptieren** oder **ROADMAP-Folgepunkt** (ein `console.warn` im `else`-Zweig ergänzen).

## [kosmetisch] B5 — Abgehängter Button im Fehlerpfad (toter Code, harmlos)
**Prüfauftrag 8.** Im `catch` wird `targetBtn.disabled = false; targetBtn.innerHTML = originalContent` gesetzt (`app.js:12839–12842`), obwohl `targetBtn` nach dem Re-Render (`app.js:12831` bzw. `:12838`) bereits ein abgehängter DOM-Knoten ist (das Banner wird per `innerHTML` ersetzt, `app.js:12772`). Wirkungslos, aber unschädlich — der frische Render zeichnet den Button ohnehin neu und nicht-disabled. Genau das im Briefing (ADR-75-4) beschriebene „verpufft"-Muster; die Sichtbarkeit übernimmt korrekt `bannerApplyErrors` + Re-Render.

**Empfehlung: akzeptieren** (optional im Lauf 2 die beiden Zeilen streichen).

## [kosmetisch] B6 — Hinweis (c): Index-Bindung aktuell korrekt, aber implizite Kopplung
**Prüfauftrag 3.** Die DOM-Reihenfolge ist deterministisch identisch mit `openGroups`/`ignoredGroups`: primary-Zone (`app.js:12681–12695`) = `openGroups[0]`, more-Zone (`:12698–12733`) = `openGroups.slice(1)`, ignored-Zone (`:12735–12769`) = `ignoredGroups`. `querySelectorAll(".btn-banner-ignore-group"/"-apply-group")` (`:12802`, `:12812`) liefern in DOM-Reihenfolge genau `openGroups[0..n-1]`; `".btn-banner-unignore-group"` (`:12849`) genau `ignoredGroups[0..n-1]`. Die Zonen werden erst zusammengesetzt und dann per `banner.innerHTML = html` (`:12772`) gesetzt, danach werden die Handler gebunden — es gibt keine Zone, die „0 Buttons rendert" und die Indizes verschiebt, solange die Zonen-Reihenfolge primary → more → ignored bleibt. `data-group-key` wird nur gesetzt (`:12689/12690/12713/12714/12746`), **nie** für Selektion benutzt — die Handler laufen über Closure-`groupKey` (ADR-75-5 erfüllt; kein `[data-group-key=…]`-Selektor im Produktcode, grep bestätigt).

**Empfehlung: akzeptieren.** ROADMAP-Notiz: die Kopplung „DOM-Reihenfolge ↔ Array-Reihenfolge" ist fragil bei künftigen Zonen-Umbauten; sauberer wäre, beim Rendern pro Button direkt `addEventListener` auf dem erzeugten Knoten zu binden (Closure), statt nachträglich über `querySelectorAll` + Index.

## [kosmetisch] B7 — Hinweis (e): Sonderzeichen-Verlust ist vorbestehend und Backend-seitig
**Prüfauftrag 4.** Der `groupKey` kommt aus `item.suggested_query` bzw. `single_video_query` (`app.js:12518`), nicht aus dem rohen Dateinamen. Das Backend bereinigt `suggested_query` über `clean_show_name` (`gui/core/utils.py:27`: `re.sub(r"[^a-zA-Z0-9\s._-]", "", show_name)`), angewendet in `gui/api/project_api.py:1441–1443`. `<`, `&`, `"`, `'`, `>` werden **entfernt** (nicht ersetzt) → „Delta <&> Show" wird zu „Delta  Show" (Doppel-Leerzeichen, weil die umgebenden Leerzeichen stehen bleiben). Konsequenz: AK8 testet Sonderzeichen, die nach Backend-Bereinigung real **nicht** im `groupKey` auftauchen — der Test ist defensiv (schützt gegen künftige Backend-Änderungen), nicht falsch. Der Frontend-Code selbst geht mit beliebigen `groupKey`s korrekt um (escapeHTML `app.js:12686/12710/12743`, `encodeURIComponent` in `searchSeries:3102`).

**Empfehlung: ROADMAP-Folgepunkt** (Backend: legitime Sonderzeichen in Seriennamen — z. B. „Law & Order", „Wall·E" — sollten erhalten bleiben; Doppel-Leerzeichen nach Entfernung kollabieren). Kein Fehler dieser Kette.

# Antworten auf die übrigen Prüfaufträge

## Prüfauftrag 6 (Testqualität) — keine trivial grünen Tests gefunden
- **AK7:** Der `sessionStorage`-Mock ist funktional (Store `sessionStore` im Modulscope, `mockSessionStorage` `:21–50`) und zählt Reads **nur** für Keys mit Präfix `smart-inbox-ignore-group-` (`:26–28`), Writes bei `setItem`/`removeItem` (`:31–38`). Die Asserts `getReads()===0` (`:1036`, `:1042`) und `getWrites()===0` (`:1043`) sind damit ein echter Nachweis — kein No-op-Mock. Der vorab gesetzte `sessionStorage`-Schlüssel (`:1027`) würde bei noch vorhandenem sessionStorage-Lesepfad den Test rot machen. Präzise.
- **AK8:** `validateSelector` ist streng (unbalancierte Quotes `:58–64`, unerwartete Tokens in Attribut-Selektoren `:66–85`, unbalancierte Klammern `:86–92`, wirft `SyntaxError`). Der Produktcode baut keinen dynamischen Selektor → kein Wurf, aber genau das belegt der Test. Zusätzlich escaped-HTML-Assert (`:1067`) und funktionaler localStorage-Schlüssel mit Sonderzeichen (`:1074`). Nicht trivial.
- **AK9:** Die Fehlerinjektion ist **testseitig** gesteuert (`shouldThrowInQualityHint` `:52–53`, Stub `:551–555`), der Produktcode liest dafür nichts (AK13 erfüllt — siehe Prüfauftrag 7). Der Stub-Wurf erreicht den Banner-`catch`, weil `startSeriesGroupWorkflow` `triggerQualityHintUpdates()` synchron **vor** `return searchSeries()` aufruft (`app.js:13091–13093` → `return` erst `:13174`); der Wurf propagiert über das `await` (`:12833`) in den `try` (`:12828`). Der Test prüft Rollback (`:1115`), Inline-Meldung mit exaktem Wortlaut (`:1119–1123`), `console.error` mit Ursache (`:1126–1130`) und „wieder offen" (`:1133–1135`); dazu Retry-löscht-Meldung (`:1138–1143`), F1-Suchfehler-Test (`:1146–1170`) und Apply-Sperre-Test (`:1172–1219`). Solide.
- **AK10:** Ersetzt `globalThis.localStorage` nach `setupTestEnvironment` (`:1230–1234`), `assert.doesNotThrow` für Render (`:1239–1241`), Log-Nachweis (`:1255–1258`), Fallback-Set wirkt (`:1260–1269`), Restore crasht nicht (`:1272–1276`). Der Produktcode liest `localStorage` erst zur Aufrufzeit dynamisch — der Inline-Swap greift. Nicht trivial.
- **Bestandstest-Anpassung (`inbox_group.test.js:838–875`):** erfüllt die vier Ziel-Assertions wörtlich — `'{"ignored":true}'` (`:870`), kein `.btn-banner-apply-group` (`:871`), Banner sichtbar + „Ausgeblendete Vorschläge (1)" (`:872–873`), `sessionStorage`-Wert `null` (`:874`). Testname korrekt umbenannt (`:838`). Einzige Nuance: `:871` prüft `querySelector('.btn-banner-apply-group') === null` **global** statt „für Show" — im Ein-Gruppen-Kontext dieses Tests gleichwertig, daher kein Fehler, nur etwas globaler als im Briefing formuliert.

## Prüfauftrag 7 (Export-Block / AK13)
Der Export-Block `app.js:13522–13548` enthält ausschließlich `globalThis.X = X`-Zuweisungen (plus vorbestehende Setter/Getter-Closures `:13537–13539`, `:13542–13547`, die nicht aus dieser Kette stammen). Die Zeilen `globalThis.activeSeriesGroupFiles = null; activeSeriesGroupName = ""` (`:13554–13555`) liegen **nicht** im Export-Block, sondern in `handleSmartInboxClick` (`:13550`). Der Produktivcode liest kein Test-only-globales (kein `shouldThrowInQualityHint`, kein `__currentElementsById`); der einzige `globalThis`-Lese-Punkt ist `globalThis.currentQueueJobs` (`:4318`), vorbestehend und nicht test-spezifisch. **AK13 erfüllt.**

## Prüfauftrag 8 (übrige Fehlerpfade)
- **Double-click „Alle wieder anzeigen":** idempotent — `clearInboxGroupIgnored` (`:12627–12636`) fängt Fehler und `removeItem` auf fehlendem Key ist harmlos. Kein Problem.
- **Ignorieren während laufendem Apply:** bewusst erlaubt (ADR-75-4: nur Apply-Klicks gesperrt). Der `catch`-Re-Render (`:12838`) re-rendert mit den aktuellen States konsistent nach. Kein Problem.
- **localStorage-Manipulation durch dritte Hand:** `isInboxGroupIgnored` parsed JSON und prüft strikt `parsed.ignored === true` (`:12602–12605`); ungültiges JSON → `catch` → „nicht ignoriert" (`:12608–12611`). Robust.
- **Race `renderSmartInboxList` während `await`:** alle Handler übergeben `currentSmartInboxRawSuggestions` (`:12808/12831/12838/12855/12865`); der State liegt in Modul-Variablen (`:12471`, `:13229`) — keine Inkonsistenz erkennbar.
- **Leere Inbox:** der `else`-Zweig versteckt und leert das Banner korrekt (`:13508–13512`) — kein Stale-Banner.

# Gesamturteil

**Abnahme aus Risikosicht: ja, mit Auflage.**

Begründung: Kein [kritisch]-Befund, kein Datenverlust, kein Sicherheitsproblem, kein Crash. Die Kernmechanik (Zonen-Aufbau, localStorage-Persistenz, Rückweg, Selektorsicherheit, Fehler-Rollback) ist korrekt umgesetzt und die Tests sind substantiell (keine trivial grünen Mocks, AK13 sauber). Zwei [wichtig]-Befunde: **B1** (`bannerApplyErrors`-Leiche, reproduzierbarer UX-Glitch, Ein-Zeilen-Fix) sollte im **Gate-A2-Lauf 2** behoben werden; **B2** (hängende Suche klemmt `groupWorkflowRunning`) ist als **ROADMAP-Folgepunkt** zu dokumentieren, da vorbestehendes `searchSeries`-Verhalten ohne neuen Datenverlust. Die [kosmetisch]-Befunde B3–B7 sind akzeptabel bzw. ROADMAP-Notizen. Für ein „Nein" sehe ich keine Grundlage — die Auflage B1 ist kein Abnahmehindernis, sollte aber vor dem Merge nicht unbehandelt bleiben.
