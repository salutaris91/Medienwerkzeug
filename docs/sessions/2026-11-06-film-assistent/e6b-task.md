# Aufgabe Etappe E6b — Handtest-Nachzug Smart-Inbox & Filmreihe (ROADMAP #92, #69)

Grundlage: `docs/sessions/2026-11-06-film-assistent/briefing.md` (Etappe E6) und Alex' Handtest-Freigaben vom 2026-11-11 und 2026-11-12 auf PR #174 (`feat/film-wizard-e6`):
> Alex: „Ja, ich folge all deinen Empfehlungen zu 1, 2 und 3. Da folge ich deinem Ansatz. Macht ja auch Sinn, dass man da keine Mischung zulässt, weil man verarbeitet ja nicht alles immer gleichzeitig, sondern eins nach dem anderen. Deswegen passt das aus meiner Sicht. Und gerne bei der Notiz am Rande, gerne das mit fixen, ja.“
> Alex: „ja gerne ansatz 1“

## Ziel & Umfang

Nachbesserung aus dem OrbStack-Handtest (E6b) mit sechs klar abgegrenzten Punkten:
1. **Beidseitiges Überschreiben des erkannten Medientyps (`Film ↔ Serie`) direkt in der Smart-Inbox — für Ordner UND lose Dateien:**
   - Alle Film-Einträge (`media_type === "movie"`, sowohl `is_dir: false` als auch `is_dir: true`) zeigen den Link **`Als Serie / Folge behandeln`** (ohne den alten Zusatztext `Film (für Serie gesperrt)`). Nach Klick wechselt der Eintrag auf Serie (`Als Serie freigegeben` + Rücksetz-Link **`Auf Film zurücksetzen`**).
   - Alle Serien-Einträge (`media_type === "tv"`, `!item.is_group`, sowohl `is_dir: false` als auch `is_dir: true`) zeigen den Link **`Als Film behandeln`**. Nach Klick wechselt der Eintrag auf Film (`Als Film freigegeben` + Rücksetz-Link **`Auf Serie zurücksetzen`**).
   - Der effektive Typ steuert konsistent: das Typ-Badge (`Film` vs. `Serie`), den Einzelklick-Button `Auswählen` (`data-media-type`), die Checkbox-Klasse (`.smart-inbox-movie-cb` vs. `.smart-inbox-cb`), sowie `scanProject` (damit ein expliziter Override selbst bei vorhandener `.nfo` nicht zurückspringt).
2. **Hover-Fix für die Umschalt-/Rücksetz-Links in `Superfood Light` (`gui/static/style.css`):**
   - Kein hartcodiertes `color: #fff;` beim `:hover` / `:focus-visible` (auf weißem Kartenhintergrund unsichtbar), sondern Theme-Variablen (`color: var(--text-main); background: var(--bg-hover);`).
3. **Kein vertikales Springen beim Anhaken (`0 px` Layout-Shift):**
   - `#smart-inbox-bulk-actions` wandert in `gui/static/index.html` rechtsbündig (`margin-left: auto`) direkt **in** die ohnehin sichtbare Zeile `#smart-inbox-sort-bar` (`min-height: 38px`). Beim An-/Abhaken des ersten Eintrags wird keine zusätzliche Zeile über `#smart-inbox-list` eingeschoben.
4. **Typ-reine Checkbox-Auswahl & neue Button-Beschriftungen (Ansatz 1):**
   - Sobald mindestens ein Film angehakt ist (`selectedInboxMovieProjects.size >= 1`), sind Serien-Checkboxen `.smart-inbox-cb` deaktiviert (`disabled`, Tooltip: `Erst Filmreihe starten oder Auswahl aufheben`) — und umgekehrt sind bei `selectedInboxProjects.size >= 1` alle Film-Checkboxen `.smart-inbox-movie-cb` deaktiviert (`disabled`, Tooltip: `Erst Serien-Auswahl starten oder Auswahl aufheben`).
   - Button `#btn-bulk-queue-movies`: **`Als Filmreihe verarbeiten`** (bei 1 Film) bzw. **`Als Filmreihe verarbeiten (${movieCount})`** (ab 2 Filmen).
   - Button `#btn-bulk-group-series`: **`Ausgewählte Folgen als Serie verarbeiten`** (bei 1 Folge) bzw. **`Ausgewählte Folgen als Serie verarbeiten (${seriesCount})`** (ab 2 Folgen).
5. **Schriftkontrast auf `.btn-primary` in `Superfood Light` (`gui/static/style.css`):**
   - `.btn-primary` (und `.btn-accent`) setzen `color: var(--text-on-primary, #ffffff);` mit `--text-on-primary: #ffffff;` in `:root`, damit Buttons wie `Auswählen` und `Als Filmreihe verarbeiten` in `Superfood Light` nicht dunkelblauen Text `#1b3456` auf dunkelblauem Verlauf `#1b3456 → #f08aa0` rendern.
6. **Ungekürzte Dateinamen + Dateityp-Badge bei Junk-Dateien & Vorschau-Zeilen (`gui/static/js/preview_render.js` & `gui/static/style.css`, Ansatz 1):**
   - Bisher schnitt `.mw-wizard-result-item-old` lange `Ordner/Datei.ext`-Pfade rechts per `text-overflow: ellipsis` ab, sodass Dateiname und Dateiendung (`.nfo`, `.jpg`, `.txt`, `-sample.mkv`) komplett unsichtbar waren.
   - `data-old` und `data-new` auf der Checkbox bleiben 1:1 unverändert (Backend-Payload unangetastet).
   - Für die Darstellung zerlegt `preview_render.js` den Pfad in den reinen **Dateinamen** (umbrechend mit `overflow-wrap: anywhere`, niemals mit `...` abgeschnitten; bei Junk-Einträgen ohne `line-through`), den optionalen **Unterordnerpfad** klein/gedimmt darunter (`dirPath + "/"`) + `title`-Tooltip mit dem vollen Pfad, sowie rechts am Zeilenrand ein schrumpffestes **Dateityp-Badge** (`NFO`, `JPG`, `TXT`, `MKV`, `SRT` …).

## Kritische Invarianten

1. **STRIKTE REGEL — KEINE TEST-BACKDOORS IM PRODUKTIVCODE (`Testinfrastruktur-Regel`):**
   - Füge in `gui/static/app.js` oder `gui/static/js/film_wizard.js` **keine** `if (process.env...)`, **keine** `__test*`-Hooks und **keine** neuen `globalThis.*`-Zuweisungen am Dateiende hinzu! Bestehende Zuweisungen (`globalThis.unlockedMovieProjects = unlockedMovieProjects;` etc.) bleiben unverändert; neue Zustandsvariablen wie `unlockedSeriesAsMovieProjects` werden in Tests ausschließlich im Test-Harness an `cleanAppJs` angehängt.
2. **Backend liefert `single_video_relpath` bereits für Film-Ordner:**
   - `get_inbox_suggestions()` (`gui/api/project_api.py:1525–1539`) befüllt `single_video_relpath` bereits für **jeden** Ordner mit genau 1 Nicht-Sample-Videodatei unabhängig von `media_type`. Es sind **keine** Backend-Änderungen nötig.
3. **Bestehende DOM-IDs & Fehler-Reihenfolge bewahren:**
   - `#smart-inbox-sort-bar`, `#smart-inbox-bulk-actions`, `#smart-inbox-bulk-count`, `#btn-bulk-deselect`, `#btn-bulk-queue-movies` und `#btn-bulk-group-series` behalten exakt ihre IDs.
   - Innerhalb von `#smart-inbox-bulk-actions` bleibt die Kind-Reihenfolge `.smart-inbox-bulk-info` → optional `.smart-inbox-group-banner-error` (`role="alert" aria-live="polite" style="width: 100%;"`) → `.smart-inbox-bulk-buttons` erhalten (`tests/frontend/inbox_group_seasons.test.js` Z. 1448–1459 prüft das exakt!).

---

## Detaillierte Umsetzung

### 1. Beidseitiger Typ-Override (`Film ↔ Serie`) in `gui/static/app.js`

1. **Zustand & effektiver Medientyp (um Z. 12515–12570):**
   - Ergänze direkt unter `let unlockedMovieProjects = new Set();`:
     ```js
     let unlockedSeriesAsMovieProjects = new Set();
     ```
   - Ergänze eine kleine Hilfsfunktion `getEffectiveInboxMediaType(item)`:
     ```js
     function getEffectiveInboxMediaType(item) {
         if (!item) return "";
         if (item.media_type === "movie" && unlockedMovieProjects.has(item.project)) {
             return "tv";
         }
         if (item.media_type === "tv" && unlockedSeriesAsMovieProjects.has(item.project)) {
             return "movie";
         }
         return item.media_type || "";
     }
     ```
   - Aktualisiere `isInboxProjectEligibleForSelection(item)` (Serien-Checkbox `.smart-inbox-cb`):
     ```js
     function isInboxProjectEligibleForSelection(item) {
         if (!item || item.is_group === true) return false;
         const effectiveType = getEffectiveInboxMediaType(item);
         if (effectiveType !== "tv") return false;
         return item.is_dir === false || (item.is_dir === true && Boolean(item.single_video_relpath));
     }
     ```
     *Wirkung:*
     - Ein nativer `tv`-Eintrag, der per `Als Film behandeln` überschrieben wurde (`effectiveType === "movie"`), ist **nicht** mehr in `selectedInboxProjects` wählbar, sondern wechselt zu `.smart-inbox-movie-cb`.
     - Ein `movie`-Eintrag, der per `Als Serie / Folge behandeln` entsperrt wurde (`unlockedMovieProjects.has(item.project)`), erhält `.smart-inbox-cb` sowohl als lose Datei (`is_dir === false`) **als auch** als Einzelvideo-Ordner (`is_dir === true && Boolean(item.single_video_relpath)`, z. B. `Zurück in die Zukunft (1985)`!). Ein Multi-Video-Filmordner ohne `single_video_relpath` bekommt wie Multi-Video-Serienordner keine projektübergreifende Folgen-Checkbox, öffnet aber über `Auswählen` sauber den Serien-Modus.
   - Aktualisiere `isInboxProjectEligibleForMovieQueue(item)` (Filmreihen-Checkbox `.smart-inbox-movie-cb`):
     ```js
     function isInboxProjectEligibleForMovieQueue(item) {
         if (!item || item.is_group === true) return false;
         return getEffectiveInboxMediaType(item) === "movie";
     }
     ```
     *Wirkung:* Sowohl reguläre Filme (Ordner & lose Dateien, solange nicht als Serie entsperrt) als auch per `Als Film behandeln` umgeschaltete `tv`-Einträge (Ordner & lose Dateien) erhalten `.smart-inbox-movie-cb`.
   - **Auto-Gruppierungs-Schutz (`detectInboxGroups`, um Z. 12585):**
     - `detectInboxGroups(suggestions)` prüft weiterhin `if (item.media_type !== "tv") return;` **und zusätzlich** `if (unlockedSeriesAsMovieProjects.has(item.project)) return;`.
     - Dadurch bleibt die `#65`-Regel gewahrt (entsperrte Filme `media_type === "movie"` triggern kein automatisches Serien-Gruppenbanner) **und** eine explizit als Film behandelte `tv`-Datei wird ebenfalls nicht mehr automatisch in ein Serien-Gruppenbanner gezogen!

2. **Rendering von Badge, Umschalt-/Rücksetz-Links & `Auswählen`-Typ in `renderSmartInboxList` (um Z. 13690–13840):**
   - Berechne `const effectiveMediaType = getEffectiveInboxMediaType(item);` und verwende `effectiveMediaType` für:
     - `typeBadge` und `badgeColor` (`effectiveMediaType === "movie"` → `Film`-Badge, `effectiveMediaType === "tv"` → `Serie`-Badge, `doku` → `Doku`, `anime` → `Anime`).
     - `data-media-type="${escapeHTML(effectiveMediaType)}"` auf `.btn-select-smart` (damit `Auswählen` den umgeschalteten Modus öffnet!).
   - **Umschalt- und Rücksetz-UI (`typeOverrideHtml`, ersetzt `movieLockHtml` um Z. 13744–13751):**
     - Wenn `item.media_type === "movie"` (gilt für `is_dir === false` **und** `is_dir === true`!):
       - Falls `unlockedMovieProjects.has(item.project)`:
         ```js
         typeOverrideHtml = `<span class="badge-movie-unlocked">Als Serie freigegeben</span><a href="#" class="btn-reset-movie-series" data-project="${escapeHTML(item.project)}">Auf Film zurücksetzen</a>`;
         ```
       - Sonst:
         ```js
         typeOverrideHtml = `<a href="#" class="btn-unlock-movie-series" data-project="${escapeHTML(item.project)}">Als Serie / Folge behandeln</a>`;
         ```
         *(Kein `Film (für Serie gesperrt)`-Span mehr!)*
     - `else if (item.media_type === "tv")`:
       - Falls `unlockedSeriesAsMovieProjects.has(item.project)`:
         ```js
         typeOverrideHtml = `<span class="badge-movie-unlocked">Als Film freigegeben</span><a href="#" class="btn-reset-series-movie" data-project="${escapeHTML(item.project)}">Auf Serie zurücksetzen</a>`;
         ```
       - Sonst:
         ```js
         typeOverrideHtml = `<a href="#" class="btn-unlock-series-movie" data-project="${escapeHTML(item.project)}">Als Film behandeln</a>`;
         ```
     - Für `doku` und `anime` bleibt `typeOverrideHtml = ""` (unverändert, `Dokus must not have unlock link`).
   - **Click-Handler für alle 4 Links nach `itemDiv.innerHTML`:**
     - `.btn-unlock-movie-series`: `e.preventDefault(); selectedInboxMovieProjects.delete(item.project); unlockedMovieProjects.add(item.project); renderSmartInboxList(...);`
     - `.btn-reset-movie-series`: `e.preventDefault(); selectedInboxProjects.delete(item.project); unlockedMovieProjects.delete(item.project); renderSmartInboxList(...);`
     - `.btn-unlock-series-movie`: `e.preventDefault(); selectedInboxProjects.delete(item.project); unlockedSeriesAsMovieProjects.add(item.project); renderSmartInboxList(...);`
     - `.btn-reset-series-movie`: `e.preventDefault(); selectedInboxMovieProjects.delete(item.project); unlockedSeriesAsMovieProjects.delete(item.project); renderSmartInboxList(...);`
   - **`scanProject(project)` Absicherung bei vorhandener `.nfo` (um Z. 2905–2910):**
     - Wenn `unlockedMovieProjects.has(project)` gilt, erzwinge `mediaType = "series";`.
     - Wenn `unlockedSeriesAsMovieProjects.has(project)` gilt, erzwinge `mediaType = "movie";`.

---

### 2. Typ-reine Auswahl & klare Beschriftungen in `gui/static/app.js`

1. **Gegenseitige Exklusivität zwischen Film- und Serien-Auswahl:**
   - Schreibe eine Hilfsfunktion `syncExclusiveCheckboxLocks()` und rufe sie am Ende von `updateBulkActionsBarUI()` auf:
     - Lies `const hasSeriesSelection = selectedInboxProjects.size >= 1;` und `const hasMovieSelection = selectedInboxMovieProjects.size >= 1;`.
     - Lies `const processingSet = (typeof activeProjectsProcessing !== "undefined" && activeProjectsProcessing) ? activeProjectsProcessing : new Set();`.
     - Falls `hasSeriesSelection && hasMovieSelection` jemals programmatisch gleichzeitig befüllt sein sollte (defensiver Guard in `renderSmartInboxList` vor dem Zeichnen): wenn `selectedInboxMovieProjects.size > 0 && selectedInboxProjects.size > 0`, gewinnt die bestehende Auswahl bzw. leere die jüngere/inkompatible Menge nicht still, sondern verhindere im UI das gleichzeitige Anhaken:
       - In `renderSmartInboxList` beim Erzeugen von `.smart-inbox-cb`: `const isLockedByMovies = selectedInboxMovieProjects.size >= 1 && !isChecked; const isDisabled = Boolean(isProcessing || isLockedByMovies);` (mit `title="Erst Filmreihe starten oder Auswahl aufheben"`, falls `isLockedByMovies`).
       - In `renderSmartInboxList` beim Erzeugen von `.smart-inbox-movie-cb`: `const isLockedBySeries = selectedInboxProjects.size >= 1 && !isMovieChecked; const isDisabled = Boolean(isProcessing || isLockedBySeries);` (mit `title="Erst Serien-Auswahl starten oder Auswahl aufheben"`, falls `isLockedBySeries`).
       - Im `change`-Handler von `.smart-inbox-cb`: falls `cb.checked && selectedInboxMovieProjects.size >= 1`, setze `cb.checked = false; return;`.
       - Im `change`-Handler von `.smart-inbox-movie-cb`: falls `movieCb.checked && selectedInboxProjects.size >= 1`, setze `movieCb.checked = false; return;`.
       - In `syncExclusiveCheckboxLocks()` (aufgerufen in `updateBulkActionsBarUI()`): aktualisiere live im `#smart-inbox-list` alle `.smart-inbox-cb` und `.smart-inbox-movie-cb`:
         - Für jede `.smart-inbox-cb`: `const proj = cb.dataset?.project || ""; const proc = processingSet.has(proj); const locked = hasMovieSelection && !cb.checked; cb.disabled = Boolean(proc || locked); cb.style.cursor = cb.disabled ? "not-allowed" : "pointer"; cb.style.opacity = cb.disabled ? "0.5" : "";` (und setze bei `locked` `cb.setAttribute("title", "Erst Filmreihe starten oder Auswahl aufheben")`; wenn `!locked`, stelle bei Einzelvideo-Ordnern den ursprünglichen `Verarbeitet wird: ...`-Titel wieder her bzw. entferne den Sperr-Titel).
         - Analog für jede `.smart-inbox-movie-cb`: `const proj = cb.dataset?.project || ""; const proc = processingSet.has(proj); const locked = hasSeriesSelection && !cb.checked; cb.disabled = Boolean(proc || locked); cb.style.cursor = cb.disabled ? "not-allowed" : "pointer"; cb.style.opacity = cb.disabled ? "0.5" : "";` (mit `title="Erst Serien-Auswahl starten oder Auswahl aufheben"` bei `locked`, sonst Titel entfernen).

2. **Neue Beschriftungen in `updateBulkActionsBarUI()` & `formatBulkCountLabel()` (um Z. 12982–13025):**
   - `formatBulkCountLabel(seriesCount, movieCount)`:
     - `seriesCount === 0 && movieCount === 0` → `"0 ausgewählt"`
     - `seriesCount >= 1 && movieCount === 0` → `${seriesCount} ausgewählt` *(unverändert für bestehende `#smart-inbox-bulk-count`-Tests!)*
     - `movieCount >= 1 && seriesCount === 0` → `${movieCount} ${movieCount === 1 ? "Film" : "Filme"} ausgewählt`
     - Fallback falls beide `>= 1`: `${movieCount} ${movieCount === 1 ? "Film" : "Filme"} · ${seriesCount} Folgen ausgewählt`
   - Button `#btn-bulk-queue-movies`:
     - Beschriftung: `movieCount >= 2 ? \`Als Filmreihe verarbeiten (${movieCount})\` : "Als Filmreihe verarbeiten"`
   - Button `#btn-bulk-group-series`:
     - Beschriftung: `seriesCount >= 2 ? \`Ausgewählte Folgen als Serie verarbeiten (${seriesCount})\` : "Ausgewählte Folgen als Serie verarbeiten"`

---

### 3. Zero-Jump Toolbar-Integration (`gui/static/index.html` & `gui/static/style.css`) + Kontrast-Fixes

1. **`gui/static/index.html` (um Z. 462–469):**
   - Integriere `#smart-inbox-bulk-actions` rechtsbündig direkt in `#smart-inbox-sort-bar`:
     ```html
     <div id="smart-inbox-sort-bar" role="toolbar" style="display: none;">
         <div class="smart-inbox-sort-controls">
             <span style="font-size: 0.8em; color: var(--text-muted); font-weight: 500;">Sortieren:</span>
             <button class="btn btn-secondary btn-xs smart-inbox-sort-btn" data-field="name" aria-pressed="false">Name</button>
             <button class="btn btn-secondary btn-xs smart-inbox-sort-btn" data-field="date" aria-pressed="false">Datum</button>
             <button class="btn btn-secondary btn-xs smart-inbox-sort-btn" data-field="size" aria-pressed="false">Größe</button>
         </div>
         <div id="smart-inbox-bulk-actions" role="toolbar" style="display: none;"></div>
     </div>
     ```

2. **`gui/static/style.css`:**
   - **`:root` & `.btn-primary` / `.btn-accent` Kontrast-Fix (um Z. 22–25 und Z. 599–614):**
     - Ergänze in `:root`: `--text-on-primary: #ffffff;`
     - Setze in `.btn-primary` und `.btn-accent`: `color: var(--text-on-primary);` (damit primäre Buttons wie `Auswählen` und `Als Filmreihe verarbeiten` auch im hellen Theme `Superfood Light` klaren weißen Text auf dem dunklen Farbverlauf haben!).
   - **`#smart-inbox-sort-bar` & `#smart-inbox-bulk-actions` ohne Höhen-Sprung (um Z. 4002–4010 und Z. 4152–4181):**
     - `#smart-inbox-sort-bar`:
       ```css
       #smart-inbox-sort-bar {
           display: flex;
           align-items: center;
           justify-content: space-between;
           gap: 12px;
           min-height: 38px;
           margin-bottom: 12px;
           flex-wrap: wrap;
       }

       .smart-inbox-sort-controls {
           display: inline-flex;
           align-items: center;
           gap: 8px;
           flex-wrap: wrap;
       }
       ```
     - `#smart-inbox-bulk-actions`:
       ```css
       #smart-inbox-bulk-actions {
           display: none;
           margin-left: auto;
           align-items: center;
           justify-content: flex-end;
           gap: 10px;
           padding: 3px 10px;
           min-height: 32px;
           margin-bottom: 0;
           flex-wrap: wrap;
           background: rgba(var(--accent-rgb), 0.12);
           border: 1px solid var(--border-light);
           border-radius: var(--radius-md, 8px);
           font-size: 0.82rem;
       }
       ```
     - `.smart-inbox-bulk-buttons .btn-xs`:
       ```css
       .smart-inbox-bulk-buttons .btn-xs {
           min-height: 26px;
           padding: 3px 10px;
           font-size: 11px;
           line-height: 1.2;
       }
       ```
       *(Dadurch hat `#smart-inbox-bulk-actions` im normalen Zustand exakt ~34 px Gesamthöhe und passt komplett in die `min-height: 38px` von `#smart-inbox-sort-bar` — vertikaler Versatz beim An-/Abhaken = `0 px`!)*
   - **Theme-sicherer Hover für Umschalt- und Rücksetz-Links (um Z. 4297–4322):**
     - Gemeinsame Regel für `.btn-unlock-movie-series, .btn-unlock-series-movie, .btn-reset-movie-series, .btn-reset-series-movie`:
       ```css
       .btn-unlock-movie-series,
       .btn-unlock-series-movie,
       .btn-reset-movie-series,
       .btn-reset-series-movie {
           font-size: 0.75em;
           color: var(--accent);
           text-decoration: underline;
           text-underline-offset: 2px;
           cursor: pointer;
           background: none;
           border: none;
           padding: 2px 6px;
           border-radius: var(--radius-sm, 4px);
           transition: color 0.15s ease, background-color 0.15s ease;
       }

       .btn-unlock-movie-series:hover,
       .btn-unlock-movie-series:focus-visible,
       .btn-unlock-series-movie:hover,
       .btn-unlock-series-movie:focus-visible,
       .btn-reset-movie-series:hover,
       .btn-reset-movie-series:focus-visible,
       .btn-reset-series-movie:hover,
       .btn-reset-series-movie:focus-visible {
           color: var(--text-main);
           background: var(--bg-hover);
           outline: none;
       }
       ```
       *(Kein `#fff` mehr — in `Superfood Light` wird der Text beim Hover dunkelblau `#1b3456` auf warmem `#f4e6da`, in dunklen Themes hell `var(--text-main)` auf `var(--bg-hover)`!)*

3. **Ungekürzte Dateinamen & Dateityp-Badge in `gui/static/js/preview_render.js` und `gui/static/style.css` (Ansatz 1):**
   - Ergänze in `gui/static/js/preview_render.js` eine kleine reine Hilfsfunktion `splitPreviewPath(rawPath)` (und exportiere sie optional mit):
     ```js
     export function splitPreviewPath(rawPath) {
         const str = String(rawPath ?? "");
         const lastSep = Math.max(str.lastIndexOf("/"), str.lastIndexOf("\\"));
         const fileName = lastSep >= 0 ? str.slice(lastSep + 1) : str;
         const dirPath = lastSep > 0 ? str.slice(0, lastSep) : "";
         const dotIdx = fileName.lastIndexOf(".");
         const extLabel = (dotIdx > 0 && dotIdx < fileName.length - 1)
             ? fileName.slice(dotIdx + 1).toUpperCase()
             : "DATEI";
         return { fileName: fileName || str, dirPath, extLabel };
     }
     ```
   - Aktualisiere `createPreviewCheckbox(item, checked = true, groupName = "renames")`:
     - `data-old="${safeOld}"` und `data-new="${safeNew}"` auf `<input type="checkbox" class="preview-cb-${safeGroup}" ...>` bleiben **100 % unverändert**!
     - Zerlege `rawOld` über `const { fileName, dirPath, extLabel } = splitPreviewPath(rawOld);`.
     - Wenn **kein** `rawNew` vorliegt (insbesondere `groupName === "junk"`):
       - Rendere `<label class="mw-wizard-result-item mw-wizard-result-item-junk" title="${safeOld}">` mit:
         - der Checkbox `<input type="checkbox" class="preview-cb-${safeGroup}" data-old="${safeOld}" data-new="${safeNew}" ${checked ? "checked" : ""}>`
         - `<div class="mw-wizard-result-item-body">` mit:
           - `<div class="mw-wizard-result-item-filename">${escapeHTML(fileName)}</div>` (prominent, kein `line-through`, bricht um per `overflow-wrap: anywhere`!)
           - optional `${dirPath ? `<div class="mw-wizard-result-item-dir">${escapeHTML(dirPath)}/</div>` : ""}` (klein & gedimmt darunter)
         - rechts außerhalb des `.mw-wizard-result-item-body` ein schrumpffestes Badge `<span class="mw-wizard-result-item-ext">${escapeHTML(extLabel)}</span>` (z. B. `NFO`, `JPG`, `TXT`, `MKV`).
     - Wenn `rawNew` vorhanden ist (`renames` / `subs`):
       - Rendere `<label class="mw-wizard-result-item" title="${safeOld}">` mit Checkbox, `<div class="mw-wizard-result-item-body">` (`<div class="mw-wizard-result-item-old">${escapeHTML(fileName)}</div>` + optional `<div class="mw-wizard-result-item-dir">${escapeHTML(dirPath)}/</div>` + `<div class="mw-wizard-result-item-new">${safeNew}</div>`) sowie rechts `<span class="mw-wizard-result-item-ext">${escapeHTML(extLabel)}</span>`.
   - Ergänze/aktualisiere das CSS in `gui/static/style.css` (um Z. 4459–4464, **ausschließlich mit CSS-Variablen**, keine Hex-Farben!):
     ```css
     .mw-wizard-result-item { display: flex; align-items: flex-start; gap: 10px; background: var(--bg-input); padding: 8px 12px; border-radius: var(--radius-sm); border: 1px solid var(--border-glass); cursor: pointer; }
     .mw-wizard-result-item input[type="checkbox"] { accent-color: var(--accent); flex-shrink: 0; margin-top: 2px; }
     .mw-wizard-result-item-body { flex: 1 1 auto; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
     .mw-wizard-result-item-filename { font-size: 0.84rem; font-weight: 500; color: var(--text-main); white-space: normal; overflow-wrap: anywhere; word-break: break-word; }
     .mw-wizard-result-item-dir { font-size: 0.72rem; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
     .mw-wizard-result-item-old { font-size: 0.76rem; color: var(--text-muted); text-decoration: line-through; white-space: normal; overflow-wrap: anywhere; word-break: break-word; }
     .mw-wizard-result-item-new { font-size: 0.85rem; font-weight: 500; color: var(--text-main); white-space: normal; overflow-wrap: anywhere; word-break: break-word; }
     .mw-wizard-result-item-ext { flex-shrink: 0; align-self: center; font-size: 0.7rem; font-weight: 700; font-family: var(--font-mono); letter-spacing: 0.03em; padding: 2px 7px; border-radius: var(--radius-sm); background: var(--bg-surface); color: var(--accent); border: 1px solid var(--border-light); }
     ```

4. **Cache-Buster konsistent erhöhen (`tests/frontend/cache_busting.test.js`):**
   - `gui/static/index.html`: `style.css?v=66` → `style.css?v=67` und `app.js?v=122` → `app.js?v=123`.
   - `gui/static/app.js`: alle 12 relativen ES-Modul-Importe (Z. 1–12) von `?v=122` → `?v=123`.
   - `gui/static/js/film_wizard.js`: alle 3 relativen ES-Modul-Importe (Z. 1–6) von `?v=122` → `?v=123`.

---

### 4. Tests anpassen & erweitern (`tests/frontend/`)

1. **`tests/frontend/preview_render.test.js`:**
   - Ergänze Tests für **Ansatz 1 bei langen Scene-Pfaden (`Junk-Dateien` & Vorschau)**:
     - Es prüft mit einem langen Pfad wie `"The.Piano.Tuner.2026.German.DL.1080p.DV.HDR.WEBRip.AV1-WOTT/The.Piano.Tuner.2026.German.DL.1080p.DV.HDR.WEBRip.AV1-WOTT.nfo"` und `"...WOTT.jpg"`, dass:
       1. `data-old` weiterhin exakt den vollen relativen Pfad hält (`collectPreviewSelection` liefert in `explicit_junk` unverändert den kompletten Pfad!).
       2. `.mw-wizard-result-item-filename` den vollständigen Dateinamen inkl. Endung enthält (nicht abgeschnitten), `.mw-wizard-result-item-dir` den Ordnerpfad `The.Piano.Tuner.2026.../` separat darstellt, `title` den vollen Pfad trägt und `.mw-wizard-result-item-ext` sichtbar `NFO` bzw. `JPG` ausgibt (XSS-sicher geescaped!).
       3. In `style.css` `.mw-wizard-result-item-filename` **kein** `text-overflow: ellipsis` und **kein** `line-through` verwendet, sondern `overflow-wrap: anywhere`.

2. **`tests/frontend/film_queue.test.js`:**
   - Aktualisiere die Button-Assertions auf `"Als Filmreihe verarbeiten"` (bei 1 Film) und `"Als Filmreihe verarbeiten (3)"` (bei 3 Filmen).
   - Erweitere die Inbox-Tests um alle E6b-Akzeptanzfälle:
     - **Beidseitiges Überschreiben (Ordner & lose Dateien):**
       - Es prüft, dass **sowohl** ein Film-Ordner (`Zurück in die Zukunft (1985)`, `is_dir: true, single_video_relpath: "Zurück in die Zukunft (1985)/back1.mkv"`) **als auch** eine lose Film-Datei (`is_dir: false`) `.btn-unlock-movie-series` („Als Serie / Folge behandeln“) anzeigen (und kein `Film (für Serie gesperrt)` gerendert wird), beim Klick auf `Serie` wechseln, `.smart-inbox-cb` erhalten, `data-media-type="tv"` am `Auswählen`-Button tragen und über `.btn-reset-movie-series` („Auf Film zurücksetzen“) wieder in den Film-Zustand mit `.smart-inbox-movie-cb` zurückkehren.
       - Es prüft, dass ein Serien-Eintrag (`Breaking.Bad.S01E01.mkv`, `media_type: "tv"`) `.btn-unlock-series-movie` („Als Film behandeln“) zeigt, beim Klick kein Auto-Gruppen-Banner auslöst, `.smart-inbox-movie-cb` sowie `data-media-type="movie"` erhält, zusammen mit regulären Filmen über `#btn-bulk-queue-movies` in die Filmreihen-Queue eingereiht werden kann und über `.btn-reset-series-movie` („Auf Serie zurücksetzen“) wieder auf Serie zurückwechselt.
     - **Typ-reine Auswahl (kein Mischen von Film + Serie):**
       - Es prüft, dass beim Anhaken eines Films alle `.smart-inbox-cb`-Checkboxen deaktiviert (`disabled === true`) werden und beim Aufheben der Auswahl wieder aktiv sind — sowie umgekehrt beim Anhaken einer Serienfolge alle `.smart-inbox-movie-cb`-Checkboxen deaktiviert werden.
     - **Zero-Jump-DOM & `Superfood Light`-CSS-Prüfung:**
       - Es prüft gegen `index.html`, dass `#smart-inbox-bulk-actions` innerhalb von `#smart-inbox-sort-bar` liegt (kein separates Geschwister-Element vor `#smart-inbox-list`).
       - Es prüft gegen `style.css`, dass `.btn-unlock-movie-series:hover` **kein** `#fff` / `#ffffff` verwendet, sondern `var(--text-main)` und `var(--bg-hover)`, und `.btn-primary` `color: var(--text-on-primary)` besitzt.

2. **Bestehende Inbox-Tests gezielt auf die neuen Texte/Regeln nachziehen:**
   - `tests/frontend/inbox_group.test.js`:
     - Um Z. 890–911 (`AK3 & AK13`): Entferne die veraltete Assertion `item.innerHTML.includes('Film (für Serie gesperrt)')` und prüfe stattdessen, dass `Als Serie / Folge behandeln` sowohl auf losen Film-Dateien als auch auf Film-Ordnern erscheint (und `Film (für Serie gesperrt)` nicht mehr angezeigt wird).
     - Um Z. 1463–1470 (`F2`): Aktualisiere den erwarteten Text von `#btn-bulk-group-series` auf `'Ausgewählte Folgen als Serie verarbeiten'`.
   - `tests/frontend/inbox_group_seasons.test.js`:
     - Z. 1154 (1 ausgewählte Folge): `expectedText: 'Ausgewählte Folgen als Serie verarbeiten'`.
     - Z. 1469 (2 ausgewählte Folgen): `'Ausgewählte Folgen als Serie verarbeiten (2)'`.
   - `tests/frontend/inbox_selection.test.js`:
     - Z. 847: `'Ausgewählte Folgen als Serie verarbeiten'`.

## Verifikation im Worker-Container

Führe vor Abschluss das vollständige Frontend-Testkommando aus:
```bash
npm run test:frontend
```
Alle Tests müssen grün durchlaufen (`0 failed`). Keine `git commit`- oder `git push`-Befehle im Worker-Container ausführen.
