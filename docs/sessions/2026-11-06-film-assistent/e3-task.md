# Aufgabe Etappe E3 — NFO-Agent-Filmpfad andocken + Altcode-Rückbau (ROADMAP #92, #50, #52)

Grundlage: `docs/sessions/2026-11-06-film-assistent/briefing.md` (status approved, FP2 von Alex 2026-11-06: "Damit gebe ich FP2 frei."). Gebaut wird **nur Etappe E3** mit den Akzeptanzkriterien E3-AK1 bis E3-AK3. E1 (`7fb0d92`, PR #168) und E2 (`6856990`, PR #170) sind gemergt. Ergänzende Entscheidungen von Alex vom 2026-11-10 ("super, dann go mit den empfehlungen"): Option 1A (dynamischer Film-Editor-Container im NFO-Agenten mit Quellen-Badges und Patch-Semantik), Option 2A (Vollständiger Rückbau des Film-spezifischen Alt-Einstiegs inkl. `#btn-open-film-wizard`, `wizardMovieOverrides` und `triggerHandover`/`getHandoverPayload`, Erhalt von `#context-movie` rein für Doku), Option 3A (Verarbeitungsoptionen in Wizard und `#context-movie` bewusst getrennt belassen).

## Ausgangslage (Stand `main` `6856990`)
- **`#modal-nfo-agent` (`gui/static/index.html` Z. 3161–3325, `gui/static/app.js` Z. 16940–18035):**
  - Besitzt heute in `#nfo-agent-details-container` (index.html Z. 3250–3289) statische Input-Felder (`#nfo-agent-show-title`, `#nfo-agent-show-year`, `#nfo-agent-show-fsk`, `#nfo-agent-show-genres`, `#nfo-agent-show-plot` samt `#nfo-agent-source-*`-Spans), die sowohl für `tvshow` als auch für `movie` genutzt werden.
  - Enthält außerdem hartcodierte Dark-Theme-Farben (`background: #141923` auf Z. 3166; `background: #161b22` auf Z. 3192, 3196, 3221; `background: #0d1117` auf Z. 3203, 3230), die auf hellen Themes (`light`, `sand`) brechen (`[grafiker]` Mitwander, `briefing.md` Z. 81).
- **Altcode Film-Einstieg & Handover (`gui/static/index.html` Z. 763–769, `gui/static/app.js`, `gui/static/js/film_wizard.js`):**
  - In `index.html` Z. 764–768 sitzt noch `.mw-wizard-context-bar` mit `#btn-open-film-wizard` („Geführten Film-Assistenten öffnen“).
  - In `app.js` Z. 1818–1861 blendet der Klick auf `#mode-movie` auch bei normalen Filmen (`!isDoku`) im Hintergrund `#context-movie` ein, startet `searchMovie()`, `updateSizeEstimation("movie")` und `triggerQualityHintUpdates()` auf dem Alt-Panel und öffnet parallel `openFilmWizard(...)`. Analog ruft `scanProject()` (`app.js` Z. 2925–2944) bei `mediaType === "movie"` noch unkonditional `selectMovie(metaObj)` auf.
  - In `app.js` existieren noch `let wizardMovieOverrides = null;` (Z. 230), der Reset in `selectMovie()` (Z. 4315), die Auswertung in `executeMovieWorkflow()` (Z. 4598–4610) sowie die Handler für `#btn-open-film-wizard` (Z. 1834–1846, 1875–1890).
  - In `gui/static/js/film_wizard.js` existieren noch der seit E2 tote Übergabe-Altpfad `onHandoverCallback` (Z. 53, 862), `handoverBtn` (Z. 68, 725–728, 742), `getHandoverPayload()` (Z. 429–441) und `triggerHandover()` (Z. 443–453).

## Bauen

### 1. NFO-Agent-Filmpfad an `nfo_editor.js` andocken (E3-AK1, E3-AK2, Option 1A)
- **HTML-Struktur in `#modal-nfo-agent` (`gui/static/index.html` Z. 3250–3289):**
  - Innerhalb von `#nfo-agent-details-container` werden die bestehenden statischen Serien-Felder (`#nfo-agent-show-title`, `#nfo-agent-show-year`, `#nfo-agent-show-fsk`, `#nfo-agent-show-genres`, `#nfo-agent-show-plot` inkl. `#nfo-agent-title-label-text` und `#nfo-agent-source-*`) in einen eigenen Serien-Wrapper (z. B. `<div id="nfo-agent-series-fields">...</div>`) gelegt. Alle bestehenden IDs der Serien-Felder bleiben **unverändert** erhalten!
  - Direkt daneben in `#nfo-agent-details-container` wird ein neuer Container `<div id="nfo-agent-movie-editor" class="hidden"></div>` ergänzt.
- **Erweiterung von `renderNfoEditor` in `gui/static/js/nfo_editor.js` (rückwärtskompatibel):**
  - `renderNfoEditor(container, initialValues = {}, onChange = null, options = {})` unterstützt optional `options.showSourceBadges === true` (Default `false`, sodass Schritt 2 im Film-Assistenten unverändert bleibt) und optional `options.titleLabel` (z. B. `"Filmtitel (movie.nfo):"`).
  - Wenn `showSourceBadges: true` gesetzt ist, rendert `renderNfoEditor` im Label jedes der 5 Felder (`title`, `year`, `fsk`, `genre`, `plot`) ein Quellen-Badge-Element (`<span class="nfo-agent-source-badge" data-source-field="title"></span>` usw.), analog zu den bisherigen `#nfo-agent-source-*`-Spans.
  - Der zurückgegebene Editor-Controller erhält zusätzlich die Methode `setFieldSource(field, labelText)` (setzt `textContent` des jeweiligen Badges für `title | year | fsk | genre | plot`, bzw. `genres` als Alias auf `genre`) sowie `clearFieldSources()`.
  - Bei einer Benutzereingabe in einem Feld des Editors (`input`/`change`) setzt der Editor (sofern `showSourceBadges: true` oder ein Callback übergeben wird) die Quelle dieses Feldes auf `"manuell"` bzw. informiert `onChange(values, changedField)`.
- **Einbindung in `gui/static/app.js` (Region 16975–18035):**
  - Im `movie`-Modus (`mediaType === "movie"`) wird `#nfo-agent-series-fields` ausgeblendet (`hidden`) und `#nfo-agent-movie-editor` eingeblendet; darin wird genau eine `nfo_editor.js`-Instanz (`renderNfoEditor` mit `showSourceBadges: true`) gemountet bzw. aktualisiert (kein doppeltes statisches Feld-Markup für Titel/Jahr/Plot/FSK/Genre im Film-Modus — E3-AK1).
  - Im `tvshow`-Modus (`mediaType === "tvshow"`) wird `#nfo-agent-movie-editor` ausgeblendet (`hidden`) und `#nfo-agent-series-fields` eingeblendet. Serien-Modus (`nfo-agent-edit-mode-bar`, `series`/`season`/`episode`/`full`, Episoden-Mapping `#nfo-agent-episodes-section`) und der Einstieg aus dem Health-Check (`fixWithNfoAgent`) bleiben **komplett unverändert** (E3-AK2).
- **Wichtige Leitplanken für den NFO-Agenten (zwingend einhalten):**
  1. **Quellen-Herkunftsanzeige (`setNfoAgentSource`, `app.js` Z. 16955):** Wenn `mediaType === "movie"`, delegiert `setNfoAgentSource(field, sourceType)` (mit Mapping `"genres" -> "genre"`) zusätzlich an `nfoAgentMovieEditor.setFieldSource(...)`, sodass Herkunfts-Hinweise (`aus vorhandener NFO`, `vom Metadatendienst`, `manuell`, `Metadatensuche liefert keine Angabe`) im Film-Modus sichtbar bleiben.
  2. **Patch-Semantik beim Speichern (`submitNfoAgentJob`, `app.js` Z. 17886–17915) — Handtest N-1:** Im Film-Modus liest `submitNfoAgentJob()` die bereinigten Werte über `nfoAgentMovieEditor.getValues()` (`title`, `year`, `plot`, `fsk`, `genre` -> `genres`), **filtert sie aber weiterhin strikt durch `if (val && includeMainField(val, original))`**! Leere Felder im NFO-Agenten dürfen bestehende NFO-Tags **niemals** löschen (anders als `buildWizardMovieOverrides` beim Neu-Import).
  3. **MediathekViewWeb-Übernahme (`applyNfoAgentMediathekSelection`, `app.js` Z. 17467):** Setzt im Film-Modus den übernommenen Titel auch in `nfoAgentMovieEditor` (und Quelle auf `"manuell"`) und ruft `updateNfoAgentCompletenessWarning()` auf.
  4. **Vollständigkeits-Warnung (`updateNfoAgentCompletenessWarning`, `app.js` Z. 16984):** Prüft im Film-Modus die Werte aus `nfoAgentMovieEditor.getValues()` (Titel, Jahr, Plot, FSK, Genre) und aktualisiert den Warnbanner `#nfo-agent-completeness-warning` bei `onChange` des Editors sofort.
  5. **Kompatibilität mit minimalen DOM-Mocks in bestehenden Unit-Tests (`app_warning.test.js` & `fsk_batch_dom.test.js`):**
     - `app_warning.test.js` (Z. 586) ruft `triggerNfoAgentMediaTypeChange()` mit einem minimalen Mock-DOM auf und prüft `elements["nfo-agent-title-label-text"].textContent === "Filmtitel (movie.nfo):"`. Setze `#nfo-agent-title-label-text` daher in `triggerNfoAgentMediaTypeChange()` weiterhin auch im `movie`-Modus und sichere das Mounten in `#nfo-agent-movie-editor` sauber ab, falls `#nfo-agent-movie-editor` im Mock-DOM nicht existiert oder keine echten DOM-Methoden (`appendChild`/`querySelector`) besitzt.
     - `fsk_batch_dom.test.js` (Z. 1826–1870) setzt in seinen Tests `"nfo-agent-media-type": "movie"` und schreibt Testwerte direkt in `elements["nfo-agent-show-title"]` / `elements["nfo-agent-show-fsk"]`, ohne vorher `openNfoAgentModal()` oder `triggerNfoAgentMediaTypeChange()` aufzurufen. Deshalb muss das Auslesen der Film-Felder in `submitNfoAgentJob()` und `updateNfoAgentCompletenessWarning()` über einen kleinen Helfer laufen: Wenn `nfoAgentMovieEditor` gemountet ist und mindestens einen nicht-leeren Wert enthält (oder alle `#nfo-agent-show-*`-Felder leer sind), nimm `nfoAgentMovieEditor.getValues()`; falls `nfoAgentMovieEditor` nicht gemountet oder komplett leer ist, während `#nfo-agent-show-*` Werte enthält (Legacy-Test-Mock), lies als Fallback aus `#nfo-agent-show-*`.

### 2. Hartcodierte NFO-Agent-Farben in CSS-Variablen migrieren (`[grafiker]` Mitwander, `briefing.md` Z. 81)
- In `gui/static/index.html` innerhalb von `#modal-nfo-agent` (aktuell Z. 3166, 3192, 3196, 3203, 3221, 3230):
  - Ersetze `background: #141923;` (Z. 3166) und `background: #161b22;` (Z. 3192, 3196, 3221) durch `background: var(--bg-card);` (oder entsprechende CSS-Klassen in `style.css` mit `var(--bg-card)`).
  - Ersetze `background: #0d1117;` (Z. 3203, 3230) durch `background: var(--bg-input);`.
  - Dadurch funktioniert `#modal-nfo-agent` sauber in allen 5 Themes (`dark`, `light`, `midnight`, `slate`, `sand`).

### 3. Altcode-Rückbau für Filme bei vollem Erhalt des Doku-Pfads (E3-AK3, Option 2A, Option 3A)
- **`gui/static/js/film_wizard.js`:**
  - Entferne den seit E2 ungenutzten Übergabe-Altpfad: `onHandoverCallback` (inkl. `options.onHandover`), `handoverBtn` (`#mw-wizard-btn-handover`-Binding), `getHandoverPayload()` und `triggerHandover()`.
  - `buildMovieBasePayload()` bleibt bestehen (wird von Schritt 4 und den Payload-Paritätstests genutzt).
- **`gui/static/index.html` (`#context-movie`, Z. 763–769):**
  - Entferne `#btn-open-film-wizard` (und den nun unnötigen `.mw-wizard-context-bar`-Wrapper darum), behalte aber `<h3 id="context-movie-header" class="mt-0">Doku verarbeiten</h3>` sowie den gesamten restlichen Inhalt von `#context-movie` (`#movie-search-input`, `#movie-results`, Optionen-Block `#movie-option-*`, `#btn-execute-movie`), da dieser den Doku-Pfad bedient!
- **`gui/static/app.js`:**
  - Entferne `let wizardMovieOverrides = null;` (Z. 230), das Zurücksetzen `wizardMovieOverrides = null;` in `selectMovie()` (Z. 4315) und den `if (wizardMovieOverrides)`-Block in `executeMovieWorkflow()` (Z. 4598–4610).
  - Entferne die Event-Listener/ Referenzen auf `#btn-open-film-wizard` (`openWizardBtn` in Z. 1834–1846 und Z. 1875–1890).
  - **Modus-Klick `#mode-movie` (`app.js` Z. 1818–1861):**
    - Wenn `!isDoku` (regulärer Film): `#context-movie` bleibt `.hidden`! Rufe **nicht** `searchMovie()`, `updateSizeEstimation("movie")` oder `triggerQualityHintUpdates()` für das versteckte Alt-Panel auf, sondern öffne direkt `openFilmWizard(currentProject, initialQuery)`.
    - Wenn `isDoku` (`currentProjectIsDoku === true`): Blende `#context-movie` ein (`classList.remove("hidden")`), setze `#context-movie-header` auf `"Doku verarbeiten"` und führe wie bisher `searchMovie()`, `updateSizeEstimation("movie")` und `triggerQualityHintUpdates()` aus.
  - **`scanProject()` (`app.js` Z. 2925–2944):**
    - Im Zweig `else if (mediaType === "movie")` darf `selectMovie(metaObj)` nur noch aufgerufen werden, wenn `currentProjectIsDoku` wahr ist (für normale Filme hat `modeCard.click()` bereits den Film-Wizard geöffnet).
  - **`searchSeries()` Doku-Film-Treffer (`app.js` Z. 3178 und Z. 3233):**
    - Wenn innerhalb einer Doku-Suche auf einen Film-Treffer gewechselt wird (`contextMovie.classList.remove("hidden")`), stelle sicher, dass `#context-movie-header` auf `"Doku verarbeiten"` steht.
- **Verarbeitungsoptionen (Option 3A):**
  - Die Options-Blöcke in Wizard Schritt 4 (`mw-wizard-*`) und `#context-movie` (`movie-option-*` für Doku) bleiben bewusst getrennt.

### 4. Cache-Buster & Tests
- **Cache-Buster:**
  - Hebe in `gui/static/index.html` `app.js?v=113` auf `app.js?v=114` an, und ziehe alle ES-Modul-Importe in `gui/static/app.js` (`nfo_ui.js`, `nfo_editor.js`, `film_wizard.js`, `preview_render.js`) sowie in `gui/static/js/film_wizard.js` (`nfo_editor.js`, `preview_render.js`) konsistent auf `?v=114` nach.
  - Falls `gui/static/style.css` geändert wird, hebe `style.css?v=57` in `gui/static/index.html` auf `style.css?v=58` an (Prüfung durch `tests/frontend/cache_busting.test.js`).
- **Tests (`node --test tests/frontend/*.test.js`):**
  - `tests/frontend/nfo_editor.test.js`: Ergänze Tests für `showSourceBadges: true` + `setFieldSource()` / `clearFieldSources()` sowie das Setzen auf `"manuell"` bei Benutzereingabe.
  - `tests/frontend/film_wizard.test.js`: Aktualisiere die 4 Stellen, die noch `getHandoverPayload()` / `triggerHandover()` / `wizardMovieOverrides` testen (Z. 385, 515–543, 665, 915), auf `wizard.buildMovieBasePayload()` und prüfe, dass `triggerHandover`/`getHandoverPayload` nicht mehr exportiert bzw. am Controller vorhanden sind.
  - `tests/frontend/app_warning.test.js` & `tests/frontend/fsk_batch_dom.test.js`: Stelle in der `eval(app.js)`-Umgebung die Exporte aus `nfo_editor.js` (`renderNfoEditor`, `buildWizardMovieOverrides`, `normalizeFsk`, `parseGenres`) bereit; ergänze in `fsk_batch_dom.test.js` (oder `nfo_editor.test.js`) einen Test für E3-AK1/E3-AK2 (NFO-Agent mountet im `movie`-Modus den `nfo_editor.js`-Editor in `#nfo-agent-movie-editor`, liest dessen Werte in `submitNfoAgentJob` mit Patch-Semantik aus und lässt den `tvshow`-Modus unverändert).
  - Testkommando des Laufs: `python3 -m unittest tests/test_inbox_movie_overrides.py && node --test tests/frontend/*.test.js`. Alle Frontend- und Backend-Tests müssen grün sein.

## Nicht bauen
- Keine Änderungen am Serien-Modus von `#modal-nfo-agent` (Episoden-Mapping, Staffel-/Episoden-Felder, `nfo-agent-edit-mode-bar`, `fixWithNfoAgent`).
- Keine Änderungen an `gui/static/js/nfo_ui.js` (Signatur und Verhalten von `updateNfoAgentModeUI` bleiben unverändert).
- Keine Änderungen am Doku-Ablauf in `#context-movie` (`searchMovie`, `selectMovie`, `executeMovieWorkflow` bleiben für Doku vollständig funktionsfähig).
- Keine Backend-Änderungen (`gui/**/*.py`).
- Kein Provider-Vergleich (E4), keine Artwork-Auswahl (E5), keine Filmreihen-Queue (E6).
- Keine Änderungen außerhalb der "Erlaubten Dateien" von E3 im Briefing.

## Diff-Budget (wichtig)
Das Diff-Budget im Briefing ist eine Orchestrator-Metrik, kein Ziel für dich. Sobald die Akzeptanzkriterien erfüllt und alle Tests grün sind, darfst du den Code NICHT künstlich kürzen, minifizieren oder verdichten, und du stoppst nicht wegen der Größe. Fertig + grün = abgeben.
