# Aufgabe Etappe E6 — Filmreihen-Vorab-Queue (ROADMAP #92, #69)

Grundlage: `docs/sessions/2026-11-06-film-assistent/briefing.md` (FP1+FP2 freigegeben durch Alex am 2026-11-06: „Damit gebe ich FP2 frei.“; Ansatz A + E6-Scope-Erweiterung freigegeben durch Alex am 2026-11-11: „ja sehr gerne“). Gebaut wird **nur Etappe E6** mit den Akzeptanzkriterien **E6-AK1**, **E6-AK2** und **E6-AK3**. E1 (`7fb0d92`), E2 (`6856990`), E3 (`c94d837`), E4 (`dda283d`) und E5+E5b (`5816bf1`) sind gemergt.

## Akzeptanzkriterien (aus `briefing.md`)
- **E6-AK1:** Handtest + jsdom: Mehrfachauswahl in der Inbox → „Als Filme einreihen“ → Wizard arbeitet die Vorab-Queue Film für Film ab, Kopf zeigt „Film X von N“.
- **E6-AK2:** Es prüft, dass beim Abbruch der Queue bei Film `k` bereits fertige Filme `1..k-1` nicht verloren gehen und die restliche Queue `k..N` unangetastet in der Inbox bleibt.
- **E6-AK3:** Es prüft, dass ein Provider-Fehler bei Film `k` die Queue nicht blockiert (Teil-Erfolg / manuell / Überspringen auf `k+1`, Fehler am Kopf sichtbar).

## Ausgangslage & Kritische Invarianten (Stand `main` `5816bf1`)
1. **Kein Backend-Endpunkt nötig:**
   - `POST /api/process` (`gui/api/queue_api.py:823–900`) reiht jeden bestätigten Film (`media_type: "movie"`, `project_name: "<Projekt>"`) sofort asynchron in die `job_queue` ein und antwortet in Millisekunden.
   - `files[]` wird in `/api/process` für `media_type !== "tv"` mit HTTP 400 abgelehnt (`queue_api.py:836`). Jeder eingereihte Film nutzt deshalb exakt denselben Einzel-Payload (`project_name`, `media_type: "movie"`, `movie_name`, `provider`, `movie_id`, `nfo_overrides`, optional `artwork_overrides`, `explicit_renames`, `explicit_subs`, `explicit_junk`, Konvertierungs- und Zieloptionen) wie ein Einzelfilm!
   - Bestätigt der Nutzer in Schritt 4 Film `1..k-1`, liegen diese Jobs bereits sicher in der `job_queue`. Bricht der Nutzer bei Film `k` ab (oder überspringt `k`), wird für `k..N` kein `/api/process` gesendet — `k..N` bleiben unangetastet in der Inbox (E6-AK2).
2. **Unantastbare `#65`-/`#77`-Serien-Sperre in `gui/static/app.js` (Ansatz A):**
   - Bestehende Tests (`tests/frontend/inbox_group.test.js` Z. 938–955, Z. 2085 und `tests/frontend/inbox_selection.test.js` Z. 938–965) prüfen strikt, dass gesperrte Filme (`media_type === "movie"` ohne `unlockedMovieProjects`) **keine** `.smart-inbox-cb`-Checkbox rendern und nicht in `selectedInboxProjects` landen!
   - Außerdem liegen Filme in der Inbox sowohl als **Film-Ordner** (`media_type === "movie", is_dir === true`) als auch als **lose Film-Dateien** (`media_type === "movie", is_dir === false`) vor.
   - **Lösung (Ansatz A):** Führe ein eigenes `let selectedInboxMovieProjects = new Set();` und eine eigene Checkbox-Klasse `.smart-inbox-movie-cb` ein! `.smart-inbox-cb` und `selectedInboxProjects` bleiben 100 % exklusiv für Serien / als Serie entsperrte Dateien.
3. **STRIKTE REGEL — KEINE TEST-BACKDOORS IM PRODUKTIVCODE (`Testinfrastruktur-Regel`):**
   - Füge in `gui/static/app.js` oder `gui/static/js/film_wizard.js` **keine** `if (process.env...)`, **keine** neuen `globalThis.__test*` und **keine** neuen `globalThis.*`-Test-Backdoors am Ende von `app.js` hinzu!
   - Wie `tests/frontend/inbox_selection.test.js` (Z. 588–645) zeigt, liest der Frontend-Test `app.js` als Text ein, entfernt ES-Imports im Test-Harness und hängt die gewünschten `globalThis.*`-Bindings **ausschließlich im Testskript (`tests/frontend/film_queue.test.js`)** an `cleanAppJs` an. In `film_wizard.js` werden saubere öffentliche Instanzmethoden (`open`, `getQueueState`, `skipQueueMovie`) am regulären `createFilmWizard`-Rückgabeobjekt exponiert.
4. **Synchrones Wizard-DOM & Mock-DOM-Kompatibilität:**
   - Änderungen am statischen `#modal-film-wizard` in `gui/static/index.html` (um Z. 3322–3330) und am Fallback `buildWizardDom(doc, modalOverlay)` in `gui/static/js/film_wizard.js` (um Z. 326–336) müssen **1:1 synchron** gehalten werden.
   - `createWizardMockDom()` in `tests/frontend/film_wizard.test.js` unterstützt `doc.createElement`, `.innerHTML`, `.setAttribute`, `.querySelectorAll`, aber **kein** `doc.createElementNS`! Verwende für SVGs `.innerHTML` auf einem `<span>` oder reine Text-/Unicode-Symbole, niemals `doc.createElementNS`.

---

## Bauen

### 1. Inbox-Mehrfachauswahl für Filme & Sammelaktions-Leiste in `gui/static/app.js` (E6-AK1)

1. **Zustand & Hilfsfunktionen (um Z. 12516–12560):**
   - Lege neben `let selectedInboxProjects = new Set();` an:
     ```js
     let selectedInboxMovieProjects = new Set();
     ```
   - `isInboxProjectEligibleForSelection(item)` bleibt **unverändert** (nur TV + `unlockedMovieProjects`).
   - Ergänze `isInboxProjectEligibleForMovieQueue(item)`:
     ```js
     function isInboxProjectEligibleForMovieQueue(item) {
         if (!item || item.is_group === true) return false;
         if (item.media_type !== "movie") return false;
         if (item.is_dir === false && unlockedMovieProjects.has(item.project)) return false;
         return true;
     }
     ```
     Damit sind sowohl Film-Ordner (`is_dir: true, media_type: "movie"`) als auch nicht als Serie entsperrte lose Film-Dateien (`is_dir: false, media_type: "movie"`) für die Film-Vorab-Queue wählbar, während Dokus (`media_type: "doku"`), Serien (`media_type: "tv"`), Gruppenzeilen (`is_group: true`) und als Serie freigegebene Dateien ausgeschlossen sind.
   - Ergänze eine kleine Hilfsfunktion `buildMovieQueryFromInboxItem(item)` (analog zur Einzelfilm-Logik in `app.js` Z. 1821–1825):
     - Nimmt `let q = String((item && item.suggested_query) || (item && item.project) || "").trim();`
     - Falls `!item?.suggested_query && item?.is_dir === false`, entferne eine führende/abschließende Video-Dateiendung (`q = q.replace(/\.[a-z0-9]{2,4}$/i, "");`).
     - Ersetze `[._\-]` durch Leerzeichen und entferne `(YYYY)`-Jahresklammern (`q = q.replace(/[._\-]/g, " ").trim().replace(/\([0-9]{4}\)/g, "").trim();`).
     - Fallback: falls danach leer, `String(item?.project || "").trim()`.

2. **Bereinigung & Checkbox-Rendering in `renderSmartInboxList(rawSuggestions, processingSet)` (um Z. 13319–13665):**
   - **Pruning beim Neuzeichnen (analog `#77`):** Direkt neben der Bereinigungsschleife für `selectedInboxProjects` (Z. 13319–13324) bereinige auch `selectedInboxMovieProjects`:
     ```js
     for (const proj of Array.from(selectedInboxMovieProjects)) {
         const item = suggestions.find(s => s && s.project === proj);
         if (!item || currentProcessing.has(proj) || !isInboxProjectEligibleForMovieQueue(item)) {
             selectedInboxMovieProjects.delete(proj);
         }
     }
     ```
   - **Checkbox im Item-Slot (um Z. 13565–13578):**
     - Wenn `isEligible` (`isInboxProjectEligibleForSelection(item)`): unverändert `.smart-inbox-cb` rendern.
     - `else if (isInboxProjectEligibleForMovieQueue(item))`:
       Rendere an derselben Stelle:
       ```js
       const isMovieChecked = selectedInboxMovieProjects.has(item.project);
       const disabledAttr = isProcessing ? 'disabled style="cursor: not-allowed; opacity: 0.5;"' : 'style="cursor: pointer;"';
       checkboxHtml = `<input type="checkbox" class="smart-inbox-movie-cb" data-project="${escapeHTML(item.project)}" ${isMovieChecked ? 'checked' : ''} ${disabledAttr} aria-label="Film für Vorab-Queue auswählen">`;
       ```
   - **Event-Binding nach `itemDiv.innerHTML` (um Z. 13639–13658):**
     - Binde `change` auf `.smart-inbox-movie-cb`: fügt `item.project` zu `selectedInboxMovieProjects` hinzu bzw. löscht es daraus und ruft `updateBulkActionsBarUI()` auf.
     - Beim Klick auf `.btn-unlock-movie-series` (Z. 13653): rufe **vor** `unlockedMovieProjects.add(item.project)` explizit `selectedInboxMovieProjects.delete(item.project);` auf, damit ein zuvor als Film angehakter loser Film beim Wechsel auf „Als Serie / Folge behandeln“ sauber aus der Film-Auswahl entfernt wird!

3. **Sammelaktions-Leiste `updateBulkActionsBarUI()` & Queue-Start (um Z. 12960–13078):**
   - Lies `const seriesCount = selectedInboxProjects.size;` und `const movieCount = selectedInboxMovieProjects.size;`, `const totalCount = seriesCount + movieCount;`.
   - Wenn `totalCount >= 1`:
     - `bulkBar.style.display = "flex";`
     - `countLabel`:
       - Nur Serien gewählt (`seriesCount >= 1 && movieCount === 0`): `${seriesCount} ausgewählt` (100 % abwärtskompatibel zu allen bestehenden `#smart-inbox-bulk-count`-Assertions!).
       - Nur Filme gewählt (`movieCount >= 1 && seriesCount === 0`): `${movieCount} ${movieCount === 1 ? "Film" : "Filme"} ausgewählt`.
       - Beide gewählt (`seriesCount >= 1 && movieCount >= 1`): `${movieCount} ${movieCount === 1 ? "Film" : "Filme"} · ${seriesCount} Serien-Einträge ausgewählt`.
     - Buttons in `.smart-inbox-bulk-buttons`:
       - Immer: `<button type="button" class="btn btn-secondary btn-xs" id="btn-bulk-deselect">Auswahl aufheben</button>`
       - Wenn `movieCount >= 1`: `<button type="button" class="btn btn-primary btn-xs" id="btn-bulk-queue-movies">${seriesCount >= 1 ? `Filme einreihen (${movieCount})` : "Als Filme einreihen"}</button>`
       - Wenn `seriesCount >= 1`: `<button type="button" class="btn btn-primary btn-xs" id="btn-bulk-group-series">Ausgewählte als Serie verarbeiten</button>`
     - `#btn-bulk-deselect` leert `bulkStartError = null;`, `selectedInboxProjects.clear();`, `selectedInboxMovieProjects.clear();`, ruft `updateBulkActionsBarUI()` auf und setzt sowohl `.smart-inbox-cb` als auch `.smart-inbox-movie-cb` in `#smart-inbox-list` auf `checked = false`.
     - **Klick-Handler für `#btn-bulk-queue-movies` (analog zur gehärteten `#77`/`#80`-Logik von `#btn-bulk-group-series`):**
       - Guard gegen Doppelklick (`groupWorkflowRunning`), `try / catch / finally`.
       - Prüfe alle `Array.from(selectedInboxMovieProjects)` in Reihenfolge gegen `currentSmartInboxRawSuggestions` und `activeProjectsProcessing`:
         - Noch vorhanden, nicht in `processing` und `isInboxProjectEligibleForMovieQueue(match)` → `validMovies.push(match)`.
         - Sonst → `skippedProjects.push(proj)` (aus `selectedInboxMovieProjects` löschen und zugehörige `.smart-inbox-movie-cb` per `cb.dataset?.project === proj` ohne ungeescapten Attribut-Selektor abwählen!).
       - Falls `validMovies.length === 0`: `alert("Keiner der ausgewählten Filme ist noch verfügbar in der Inbox – nichts gestartet.");`, `updateBulkActionsBarUI()`, sauber beenden.
       - Falls `skippedProjects.length > 0`: Hinweis per `alert(...)` analog `#77` (`1 Eintrag ist nicht mehr in der Inbox und wurde übersprungen.` bzw. `${skippedCount} Einträge ...`).
       - Setze `bulkStartError = null;`.
       - Baue `const queueItems = validMovies.map(item => ({ projectName: item.project, query: buildMovieQueryFromInboxItem(item) }));`.
       - Setze Standard-Zielkategorie `/Filme` auf den versteckten Kontext-Selects (wie beim Einzelfilm in Z. 1845–1848):
         ```js
         if (typeof getCatIdBySub === "function") {
             const nasDest = document.getElementById("movie-nas-destination");
             if (nasDest) nasDest.value = getCatIdBySub("/Filme", "1");
             const pcloudDest = document.getElementById("movie-pcloud-destination");
             if (pcloudDest) pcloudDest.value = getCatIdBySub("/Filme", "1");
         }
         ```
       - Prüfe `if (typeof openFilmWizard !== "function" || !document.getElementById("modal-film-wizard")) { throw new Error("Film-Assistent ist nicht verfügbar."); }`.
       - Leere nach erfolgreichem Start die Film-Auswahl (`selectedInboxMovieProjects.clear()`, `.smart-inbox-movie-cb` auf `checked = false`, `updateBulkActionsBarUI()`), damit nach Abschluss oder Abbruch keine veralteten Häkchen stehen bleiben, während die nicht verarbeiteten Filme selbst natürlich weiter als normale Karten in der Inbox stehen!
       - Rufe `openFilmWizard` im Queue-Modus auf:
         ```js
         openFilmWizard({
             queue: queueItems,
             onProcessSuccess: () => {
                 if (typeof connectLogStream === "function") connectLogStream();
             },
             onPersistOptions: typeof saveConversionSettings === "function" ? saveConversionSettings : undefined,
             onClosed: () => {
                 if (typeof window !== "undefined" && typeof window.goHome === "function") window.goHome();
             },
             onLog: typeof appendConsoleLog === "function" ? appendConsoleLog : undefined,
         });
         ```
       - Im `catch (err)`: `console.error("Film-Queue-Start fehlgeschlagen:", err);`, `bulkStartError = "Start der Film-Queue fehlgeschlagen. Bitte erneut versuchen.";`, Button wieder aktivieren, `updateBulkActionsBarUI()`.

---

### 2. Vorab-Queue-Modus im Film-Assistenten (`gui/static/index.html`, `gui/static/js/film_wizard.js`, `gui/static/style.css`)

1. **Synchrones Kopf-Markup `#mw-wizard-series-context` (`index.html` & `buildWizardDom` in `film_wizard.js`):**
   - Direkt zwischen `.mw-wizard-header` und `#mw-wizard-stepper` einfügen (standardmäßig mit Klasse `hidden`!):
     ```html
     <div id="mw-wizard-series-context" class="mw-wizard-series-context hidden" role="region" aria-label="Filmreihen-Fortschritt">
         <div class="mw-wizard-queue-main">
             <span class="mw-wizard-queue-icon" aria-hidden="true">&#127916;</span>
             <span id="mw-wizard-queue-label" class="mw-wizard-queue-label"></span>
         </div>
         <div class="mw-wizard-queue-actions">
             <div id="mw-wizard-queue-status" class="mw-wizard-queue-status" aria-live="polite"></div>
             <button type="button" id="mw-wizard-queue-skip-btn" class="btn btn-secondary btn-sm mw-wizard-queue-skip-btn">Film überspringen &rarr;</button>
         </div>
     </div>
     ```
     *(Hinweis: In `buildWizardDom` via `mkEl(doc, ...)` exakt dieselben IDs, Klassen, `role`/`aria-*` und Kind-Elemente anlegen — ohne `createElementNS`!)*

2. **Queue-Zustandsmaschine in `createFilmWizard` (`gui/static/js/film_wizard.js`):**
   - Halte folgende Queue-State-Variablen innerhalb von `createFilmWizard`:
     - `let queueActive = false;`
     - `let queueItems = [];` — Array normalisierter Einträge `{ projectName: string, query: string, status: "pending" | "queued" | "skipped", hadError: boolean }`
     - `let queueIndex = 0;`
     - `let queueCurrentError = "";` — sichtbarer Fehler-/Warnhinweis für den aktuellen Film am Kopf (E6-AK3)
   - **Einzelfilm vs. Vorab-Queue beim Öffnen (`open(openOptions = {})`):**
     - Wenn `Array.isArray(openOptions.queue) && openOptions.queue.length > 0`:
       - Normalisiere alle gültigen Einträge (`projectName` nicht leer; falls `query` fehlt, bereinigter `projectName`).
       - Setze `queueActive = true`, `queueItems = normalized`, `queueIndex = 0`, `queueCurrentError = ""`.
       - Synchronisiere Optionen einmalig beim Öffnen über `syncWizardOptionsFromContext(openOptions)`.
       - Lade Film `0` über eine interne Hilfsfunktion `loadQueueItemAt(0, { autoSearch: openOptions.autoSearch !== false })`.
     - Wenn **kein** `openOptions.queue` übergeben wurde (Einzelfilm-Aufruf):
       - Setze `queueActive = false`, `queueItems = []`, `queueIndex = 0`, `queueCurrentError = ""`.
       - Blende `#mw-wizard-series-context` strikt aus (`classList.add("hidden")`).
       - Einzelfilm-Verhalten bleibt zu 100 % identisch zu E5!

3. **Kopf-Anzeige `renderQueueHeader()` (E6-AK1 & E6-AK3):**
   - Wenn `!queueActive || queueItems.length === 0`:
     - `#mw-wizard-series-context` hat `.hidden`, `#mw-wizard-queue-label` und `#mw-wizard-queue-status` sind leer.
   - Wenn `queueActive`:
     - Entferne `.hidden` von `#mw-wizard-series-context`.
     - Setze `#mw-wizard-queue-label` auf:
       `Film ${queueIndex + 1} von ${queueItems.length} · ${currentItem.projectName}`
     - Berechne Status-Chips in `#mw-wizard-queue-status`:
       - Wenn bereits Filme erfolgreich eingereiht wurden (`queuedCount > 0`): rendere Chip `.mw-wizard-queue-chip.ok` mit Text `✓ ${queuedCount} eingereiht`.
       - Wenn Filme übersprungen wurden (`skippedCount > 0`): rendere Chip `.mw-wizard-queue-chip.muted` mit Text `${skippedCount} übersprungen`.
       - **E6-AK3 (Fehler am Kopf sichtbar):** Wenn beim aktuellen Film ein Provider-/Such-/Metadaten-/Vorschau-Fehler oder Teil-Erfolg auftrat (`queueCurrentError !== ""`), rendere in `#mw-wizard-queue-status` sichtbar ein Fehler-/Warn-Badge `.mw-wizard-queue-chip.error` (mit `role="status"` und aussagekräftigem Text, z. B. `⚠ ${queueCurrentError}`), sodass der Fehler auch nach Wechsel in den manuellen Modus oder beim Weiterklicken am Kopf sichtbar dokumentiert ist!
     - Konfiguriere `#mw-wizard-queue-skip-btn`:
       - Deaktiviert während `isExecutingProcess === true`.
       - Beschriftung:
         - Solange weitere Filme folgen (`queueIndex < queueItems.length - 1`): `"Film überspringen →"`
         - Beim letzten Film (`queueIndex === queueItems.length - 1`): `"Film überspringen & schließen"`

4. **Übergang von Film `k` zu Film `k+1` (Bestätigen in Schritt 4 vs. Überspringen vs. Abbrechen):**
   - **Button-Beschriftung in `updateExecuteButtonState()`:**
     - Wenn `!isExecutingProcess`:
       - Falls `queueActive && queueIndex < queueItems.length - 1`:
         `executeBtn.textContent = "Einreihen & nächster Film";`
       - Sonst (Einzelfilm oder letzter Film der Queue):
         `executeBtn.textContent = "Jetzt final verarbeiten";`
   - **Erfolgreiches `POST /api/process` in `executeStep4Process()`:**
     - Im Erfolgszweig (`if (res && res.ok)`):
       - Wenn `procSession === sessionSeq`:
         - Rufe `if (typeof sessionSuccessCb === "function") sessionSuccessCb(finalPayload);` für **jeden** eingereihten Film sofort auf (damit der Log-Stream / Queue-Status sofort anläuft!).
         - Falls `queueActive && queueIndex < queueItems.length - 1`:
           - Markiere `queueItems[queueIndex].status = "queued"`.
           - **Optionen-Mitnahme innerhalb der Reihe:** Rufe **nicht** `syncWizardOptionsFromContext` erneut auf — die vom Nutzer in Schritt 4 eingestellten Verarbeitungsoptionen (`optConvert`, `optQualitySlider`, `optDelete`, `optCopyNas`, `optNasDest`, `optCopyPcloud`, `optPcloudDest`) bleiben für den nächsten Film derselben Reihe erhalten!
           - Setze alle filmspezifischen Zustände zurück (`metadataRequestSeq += 1`, `previewRequestSeq += 1`, `artworkRequestSeq += 1`, `artworkSessionSeq += 1`, `resetSizeEstimate()`, `hasValidPreview = false`, `currentPreviewPayload = null`, `clearPreviewCheckboxState()`, `hideError()`, `artworkSkipped = false`, `resetArtworkState()`, `switchArtworkTab("poster")`, `selectedMovie = null`, `selectedProviders = []`, `successfulProviders.clear()`, `lastSearchResults = []`, `nfoEditor.clearProviderComparison()`) und lade `loadQueueItemAt(queueIndex + 1, { autoSearch: true })` in Schritt 1!
         - Sonst (Einzelfilm oder letzter Film der Queue):
           - Falls `queueActive && queueItems[queueIndex]`: `queueItems[queueIndex].status = "queued"`.
           - Schließe den Wizard regulär per `close({ force: true })`.
   - **Film überspringen (`skipQueueMovie()`, gebunden an `#mw-wizard-queue-skip-btn` — E6-AK3):**
     - Wenn `!queueActive || isExecutingProcess`, gib `false` zurück.
     - Markiere `queueItems[queueIndex].status = "skipped"` (es wird **kein** `/api/process` aufgerufen → Film bleibt unangetastet in der Inbox!).
     - Wenn `queueIndex < queueItems.length - 1`:
       - Setze die filmspezifischen Zustände zurück (Optionen bleiben erhalten!) und lade `loadQueueItemAt(queueIndex + 1, { autoSearch: true })` in Schritt 1.
       - Gib `true` zurück.
     - Wenn es der letzte Film war (`queueIndex === queueItems.length - 1`):
       - Schließe den Wizard per `close({ force: true })` und gib `true` zurück.
   - **Abbruch mitten in der Queue (`close({ force: false })`, `×`-Button oder `ESC` in Schritt 1 — E6-AK2 & D3):**
     - Halte dich an D3 („Abbruch-Dialog nur bei geänderten Eingaben“): `if (!force && nfoEditor.isDirty()) { if (!confirmFn("Änderungen im Film-Assistenten verwerfen?")) return false; }`.
     - Beim Schließen wird der Wizard sauber beendet: Alle zuvor bestätigten Filme `1..k-1` wurden bereits per `POST /api/process` in die Backend-Queue eingereiht; für den abgebrochenen Film `k` und alle verbleibenden Filme `k+1..N` wurde kein `/api/process` gesendet, sodass sie unangetastet in der Inbox verbleiben!

5. **Provider-Fehler-Resilienz in der Queue (E6-AK3):**
   - Erfasse Provider-Fehler in `performSearch()` und `loadMovieMetadata()` zusätzlich im Queue-Kopf:
     - Wenn `performSearch` fehlschlägt (`catch (err)`): setze bei `queueActive` `queueCurrentError = "Provider-Suche fehlgeschlagen"`, markiere `queueItems[queueIndex].hadError = true` und rufe `renderQueueHeader()` auf. Der Nutzer kann sofort „Metadaten manuell eintragen“ wählen, erneut suchen oder per `#mw-wizard-queue-skip-btn` auf `Film k+1` überspringen.
     - Wenn `loadMovieMetadata` kompletten Provider-Ausfall (`okProviders.length === 0` oder `catch (err)`) meldet: setze bei `queueActive` `queueCurrentError = "Metadaten-Abruf fehlgeschlagen"`, `queueItems[queueIndex].hadError = true`, `renderQueueHeader()`. Der Editor in Schritt 2 bleibt voll manuell editierbar, Weiter zu Schritt 3/4 und `#mw-wizard-queue-skip-btn` bleiben aktiv!
     - Wenn `loadMovieMetadata` einen Teil-Erfolg (`errProviders.length > 0 && okProviders.length > 0`, E4-Rahmenwerk) meldet: setze bei `queueActive` `queueCurrentError = `Teil-Erfolg (${errProviders.map(formatProviderLabel).join(", ")} nicht erreichbar)``, `queueItems[queueIndex].hadError = true`, `renderQueueHeader()`. Die geladenen Felder des funktionierenden Providers stehen bereit und die Queue läuft ohne Blockade weiter!
     - Wenn eine erneute Suche oder ein Metadaten-Retry für denselben Film vollständig erfolgreich durchläuft, lösche `queueCurrentError = ""` und aktualisiere `renderQueueHeader()`.

6. **Öffentliche Methoden am `instance`-Objekt von `createFilmWizard` (`film_wizard.js` um Z. 2734):**
   - Ergänze am zurückgegebenen `instance`-Objekt:
     - `skipQueueMovie`
     - `getQueueState: () => ({ active: queueActive, index: queueIndex, total: queueItems.length, currentError: queueCurrentError, items: queueItems.map((it) => ({ ...it })) })`

---

### 3. Theme-sicheres Styling in `gui/static/style.css` & Cache-Buster

1. **CSS in `gui/static/style.css` (im `.mw-wizard-*`-Block, alle 5 Themes inkl. `Superfood Light`):**
   - Style `.mw-wizard-series-context` angelehnt an `grafiker.md` §4:
     - Flexbox (`display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;`), dezenter Container (`padding: 9px 14px; margin-bottom: 12px; border-radius: 8px; background: var(--bg-surface); border: 1px solid var(--border-light); border-left: 3px solid var(--accent);`).
     - `.mw-wizard-series-context.hidden { display: none !important; }`
     - `.mw-wizard-queue-main` (`display: inline-flex; align-items: center; gap: 8px; min-width: 0;`), `.mw-wizard-queue-label` (`font-size: 0.88rem; font-weight: 600; color: var(--text-main); overflow-wrap: anywhere;`).
     - `.mw-wizard-queue-actions` (`display: inline-flex; align-items: center; gap: 8px; flex-wrap: wrap;`), `.mw-wizard-queue-status` (`display: inline-flex; align-items: center; gap: 6px; flex-wrap: wrap;`).
     - `.mw-wizard-queue-chip` (`font-size: 0.76rem; font-weight: 600; padding: 2px 8px; border-radius: 999px; border: 1px solid var(--border-light); background: var(--bg-hover); color: var(--text-main);`), `.mw-wizard-queue-chip.ok` (`border-color: var(--accent); color: var(--accent);`), `.mw-wizard-queue-chip.muted` (`color: var(--text-muted);`), `.mw-wizard-queue-chip.error` (`border-color: var(--danger); color: var(--danger);`).
   - **Pflicht:** Verwende **ausschließlich** bestehende CSS-Custom-Properties (`var(--...)`), **keine** rohen Hex-/RGB-Farben, damit alle 5 Themes (insbesondere das helle `Superfood Light`) sauberen Kontrast behalten!

2. **Cache-Buster konsistent anheben (`tests/frontend/cache_busting.test.js`):**
   - `gui/static/index.html`: `style.css?v=65` → `style.css?v=66` und `app.js?v=121` → `app.js?v=122`.
   - `gui/static/app.js`: alle 12 relativen ES-Modul-Importe (Z. 1–12) von `?v=121` → `?v=122`.
   - `gui/static/js/film_wizard.js`: alle 3 relativen ES-Modul-Importe (Z. 1–6) von `?v=121` → `?v=122`.

---

### 4. Automatisierte Tests (`tests/frontend/film_queue.test.js` + `tests/frontend/film_wizard.test.js`)

1. **Neue Testdatei `tests/frontend/film_queue.test.js` (`node:test`):**
   - Prüfe das Zusammenspiel aus Inbox-Film-Mehrfachauswahl (`app.js`) und Vorab-Queue im `Film-Assistent` (`film_wizard.js`):
     1. **E6-AK1 (Inbox-Mehrfachauswahl → „Als Filme einreihen“ → Sequentielle Abarbeitung „Film X von N“):**
        - Es prüft, dass sowohl Film-Ordner (`is_dir: true, media_type: "movie"`) als auch lose Film-Dateien (`is_dir: false, media_type: "movie"`) `.smart-inbox-movie-cb` rendern, während `.smart-inbox-cb` für gesperrte Filme `null` bleibt (`#65`-Sperre intakt) und ein Klick auf `.btn-unlock-movie-series` eine lose Film-Datei sauber aus `selectedInboxMovieProjects` nach `.smart-inbox-cb` überführt.
        - Es prüft, dass nach Auswahl von 3 Filmen (z. B. `Herr der Ringe 1`, `Herr der Ringe 2`, `Herr der Ringe 3`) die Bulk-Bar `#btn-bulk-queue-movies` („Als Filme einreihen“) zeigt, beim Klick die Vorab-Queue im `Film-Assistent` öffnet, der Kopf nacheinander `"Film 1 von 3"`, `"Film 2 von 3"` und `"Film 3 von 3"` zeigt, in Schritt 4 gesetzte Optionen (z. B. H.265 aus / geänderte Qualität) von Film 1 auf Film 2 und 3 übernommen werden, beim ersten und zweiten Film `"Einreihen & nächster Film"` und beim dritten `"Jetzt final verarbeiten"` steht und am Ende exakt 3 `POST /api/process`-Aufrufe mit den jeweiligen `project_name`-Werten abgesetzt wurden und das Modal schließt.
     2. **E6-AK2 (Abbruch bei Film `k` bewahrt `1..k-1` und lässt `k..N` unangetastet):**
        - Es prüft bei einer 3er-Queue, dass nach erfolgreichem Abschließen von Film 1 (`POST /api/process` für Film 1 gesendet, `onProcessSuccess` aufgerufen) ein Abbruch während Film 2 (`close()` bzw. `ESC` in Schritt 1 oder Bestätigung bei Dirty-State) den bereits eingereihten Job für Film 1 unangetastet bestehen lässt, für Film 2 und Film 3 **kein** `POST /api/process` auslöst und Film 2 sowie Film 3 unangetastet in der Inbox-Liste verbleiben.
     3. **E6-AK3 (Provider-Fehler bei Film `k` blockiert Queue nicht — Teil-Erfolg, Manuell & Überspringen, Fehler am Kopf sichtbar):**
        - Es prüft bei einer 3er-Queue:
          - **(a) Kompletter Such-/Metadaten-Ausfall bei Film 1 + Überspringen:** `/api/search` schlägt bei Film 1 fehl → Fehler-Chip ist sichtbar in `#mw-wizard-series-context` (`#mw-wizard-queue-status`), Klick auf `#mw-wizard-queue-skip-btn` („Film überspringen →“) springt ohne `/api/process` direkt zu `"Film 2 von 3"`.
          - **(b) Teil-Erfolg (E4 Multi-Provider: OFDb down, TMDb ok) bei Film 2:** Fehler-/Teil-Erfolg-Hinweis ist am Kopf sichtbar, geladene TMDb-Daten sind editierbar, Film 2 lässt sich regulär über Schritt 4 einreihen und schaltet weiter zu `"Film 3 von 3"`.
          - **(c) Kompletter Metadaten-Ausfall bei Film 3 + manuelle Eingabe:** Fehler am Kopf sichtbar, Nutzer trägt Titel/Jahr manuell in Schritt 2 ein und verarbeitet Film 3 regulär über Schritt 4.
     4. **Inbox-Randfälle & Theme-Check:**
        - Es prüft, dass beim Klick auf `#btn-bulk-queue-movies` inzwischen verschwundene oder in Verarbeitung befindliche Filme analog `#77` übersprungen und gemeldet werden.
        - Es prüft, dass `gui/static/index.html` und `buildWizardDom` synchron `#mw-wizard-series-context` mit `.hidden` enthalten und der neue `.mw-wizard-series-context`-Block in `gui/static/style.css` ausschließlich CSS-Variablen (`var(--...)`) ohne hartcodierte Hex-Farben verwendet.
2. **Ergänzung in `tests/frontend/film_wizard.test.js`:**
   - Ergänze einen kompakten Regressionstest, dass ein regulärer Einzelfilm-Aufruf `wizard.open({ projectName: "Matrix (1999)", query: "Matrix" })` den `#mw-wizard-series-context`-Balken verborgen lässt (`classList.contains("hidden") === true`) und `wizard.getQueueState().active === false` liefert.

3. **Autoritatives Testkommando für den Gate-A2-Lauf:**
   `node --test tests/frontend/*.test.js`

## Nicht bauen
- Keine neuen Backend-Routen unter `gui/api/` (`POST /api/process` deckt das Einreihen jedes Films bereits vollständig ab).
- Keine Dialog-Schleife („Noch einen Film?“ am Ende eines Einzelfilms — in FP1 bewusst verworfen).
- Kein Aufweichen der `#65`-Serien-Sperre auf `.smart-inbox-cb`.
- Keine `localStorage`-Persistenz abgebrochener Queue-Läufe (in `briefing.md` Abschnitt 4 bewusst verworfen).
- Keine Änderungen außerhalb der 6 erlaubten Dateien (`gui/static/app.js`, `gui/static/js/film_wizard.js`, `gui/static/index.html`, `gui/static/style.css`, `tests/frontend/film_wizard.test.js`, `tests/frontend/film_queue.test.js`).
