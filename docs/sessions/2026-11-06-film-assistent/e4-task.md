# Aufgabe Etappe E4 — Provider-Vergleich + Abruf-Rahmenwerk (ROADMAP #92, #55, #54 Teil 2)

Grundlage: `docs/sessions/2026-11-06-film-assistent/briefing.md` (status approved, FP2 von Alex 2026-11-06: "Damit gebe ich FP2 frei."). Gebaut wird **nur Etappe E4** mit den Akzeptanzkriterien E4-AK1 bis E4-AK3. E1 (`7fb0d92`, PR #168), E2 (`6856990`, PR #170) und E3 (`c94d837`, PR #171) sind gemergt. Ergänzende Entscheidungen von Alex vom 2026-11-10 ("ja das passt; Go ist erteilt; das Gate sollte noch belegt sein; gerne danach starten"):
- **Option 1A (Auswahl in Schritt 1):** 1-Klick auf einen Suchtreffer nimmt automatisch den besten passenden Treffer des jeweils anderen Dienstes (`tmdb` ↔ `ofdb`, gleicher normalisierter Titel + Jahr aus der Suchliste) als Vergleichs-Provider mit nach Schritt 2; zusätzlich optionale Vergleichs-Checkboxen je Trefferzeile in Schritt 1 für manuelle Paarung über „Weiter“.
- **Option 2A (Vorbelegung & Genre-Vereinigung in Schritt 2):** Primär-Provider belegt die Alternativ-Felder (`title`, `year`, `plot`, `fsk`) vor; ist ein Feld beim Primär-Provider leer (z. B. TMDb ohne `fsk` oder OFDb ohne `plot`), springt automatisch der nicht-leere Wert des Zweit-Providers ein und dessen Badge wird als `.selected` markiert. Bei `genres` (Kumulativ-Feld laut ROADMAP #55) startet das Feld mit der deduplizierten Vereinigung aller erfolgreichen Provider; Klick auf ein Genre-Provider-Badge schaltet dessen Genres ein/aus bzw. übernimmt sie.
- **Option 3A (API-Endpunkt):** Rückwärtskompatible Erweiterung von `/api/metadata/fetch` in `gui/api/search_api.py` um einen Multi-Provider-Modus (`providers`-Liste → paralleler Abruf via `fetch_movie_comparison_data` in `gui/mw_metadata.py`).

## Ausgangslage (Stand `main` `c94d837`)
- **`gui/mw_metadata.py`:**
  - `_open_with_retry` (Z. 122), `fetch_json_with_retry` (Z. 148) und `fetch_html_with_retry` (Z. 153) existieren bereits.
  - `generate_ofdb_nfo` (Z. 903) und `fetch_movie_nfo_data` (Z. 1421) nutzen bereits `fetch_html_with_retry`.
  - **Noch ohne Retry (HTML, #54 Teil 2):** `get_fernsehserien_episodes` (Z. 554: direktes `urllib.request.urlopen`), `search_ofdb` (`_do_ofdb_search`, Z. 816: direktes `urllib.request.urlopen`) und `resolve_mediathek_url_topic` (Z. 2644: `opener.open(req, timeout=5)` mit `SmartRedirectHandler`).
  - **Noch ohne Retry & Integritätsprüfung (Binär, #54 Teil 2):** `_download_with_timeout(url, path, timeout=10)` (Z. 9–18) öffnet `open(path, "wb")` vor dem Lesen der Antwort, wiederholt transiente Netzwerkfehler nicht und prüft weder auf 0-Byte-Antworten noch auf `Content-Length`.
- **`gui/api/search_api.py`:**
  - `handle_api_metadata_fetch` (`/api/metadata/fetch`, Z. 879–905) ruft bei `media_type == "movie"` bisher nur einen einzelnen Provider über `mw_metadata.fetch_movie_nfo_data(provider, movie_id)` ab.
- **`gui/static/js/nfo_editor.js` & `gui/static/js/film_wizard.js`:**
  - `nfo_editor.js` rendert die 5 Film-Felder (`title`, `year`, `genres`, `fsk`, `plot`) und unterstützt Text-Quellenlabels (`showSourceBadges` für den NFO-Agenten), aber noch keine klickbaren Multi-Provider-Vergleichs-Badges (`.mw-wizard-provider-badge`).
  - `film_wizard.js` ruft in `loadMovieMetadata` (Z. 1104–1137) bisher nur einen einzelnen Provider ab.
- **`tests/test_metadata_retry.py`:**
  - Importiert auf Top-Level `import pytest` (Z. 7) und nutzt `monkeypatch`-Funktionstests. Im Gate-A2-Worker-Container ist `pytest` nicht installiert (`python3 -m unittest` wird genutzt).

## Bauen

### 1. Abruf-Rahmenwerk & #54 Teil 2 in `gui/mw_metadata.py` (E4-AK3)
1. **Erweiterung von `_open_with_retry` und `fetch_html_with_retry` (`gui/mw_metadata.py` Z. 122–156):**
   - Erweitere `_open_with_retry(build_request, timeout=15, attempts=3, context="", opener=None, backoff_base=1.0, jitter=0.0)` rückwärtskompatibel:
     - Wenn `opener is not None`, wird `opener.open(request, timeout=timeout)` statt `urllib.request.urlopen(request, timeout=timeout)` aufgerufen.
     - Zwischen Fehlversuchen (`attempt < attempts`): Standard bleibt `time.sleep(attempt)` (wenn `backoff_base == 1.0` und `jitter == 0.0`, damit alle bestehenden Tests in `test_metadata_retry.py` exakt gleich laufen); wenn `jitter > 0` oder `backoff_base != 1.0`, berechne die Wartezeit mit `attempt * backoff_base + (random.uniform(0, jitter) if jitter > 0 else 0.0)`.
   - Erweitere `fetch_html_with_retry(build_request, timeout=15, attempts=3, context="", opener=None)` so, dass `opener=opener` an `_open_with_retry` durchgereicht wird.
2. **HTML-Abrufe auf `fetch_html_with_retry` umstellen (`gui/mw_metadata.py`):**
   - `get_fernsehserien_episodes(series_name_or_url, season)` (Z. 543–566): Ersetze `with urllib.request.urlopen(req, timeout=10) as response:` durch `fetch_html_with_retry(lambda: urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}), timeout=10, context=f"fernsehserien.de {series_name_or_url} Staffel {season}")`.
   - `search_ofdb(query)` (`_do_ofdb_search`, Z. 811–820): Ersetze `urllib.request.urlopen(req, timeout=10).read().decode('utf-8', errors='ignore')` durch `fetch_html_with_retry(lambda: urllib.request.Request(url, data=data, headers={'User-Agent': 'Mozilla/5.0'}), timeout=10, context=f"OFDb Suche '{q_str}'")`.
   - `resolve_mediathek_url_topic(url_or_topic)` (Z. 2628–2669): Nutze `opener = urllib.request.build_opener(SmartRedirectHandler)` zusammen mit `fetch_html_with_retry(lambda: urllib.request.Request(val, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"}), timeout=5, context=f"Mediathek URL-Auflösung {val}", opener=opener)`.
3. **Binär-Downloads mit `_download_with_retry` (`gui/mw_metadata.py` Z. 9–18):**
   - Implementiere `_download_with_retry(url, path, timeout=10, attempts=3, context="")`:
     - In jedem Versuch `attempt` (`1..attempts`) wird ein frisches `urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})` erzeugt und mit `urllib.request.urlopen(req, timeout=timeout)` geöffnet.
     - Lies zuerst die Bytes im Speicher (`data = r.read()`).
     - **Byte-Integritätsprüfung:**
       - Ist `not data` (`len(data) == 0`), wirf `OSError("Download lieferte 0 Bytes")`.
       - Prüfe `Content-Length` aus `r.headers.get("Content-Length")` (falls `getattr(r, "headers", None)` vorhanden ist): Ist `Content-Length` vorhanden und eine gültige nicht-negative Ganzzahl `expected_bytes`, muss `len(data) == expected_bytes` gelten; andernfalls wirf `OSError(f"Unvollständiger Download: {len(data)} von {expected_bytes} Bytes empfangen")`.
     - **Frischer File-Handle je Versuch / kein halbgeschriebenes Artefakt:** Erst nach erfolgreichem Lesen und bestandener Integritätsprüfung wird `path` mit einem frischen File-Handle (`with open(path, "wb") as f: f.write(data)`) geschrieben. Schlägt ein Versuch fehl, darf keine 0-Byte- oder Teil-Datei unter `path` zurückbleiben (falls während des Schreibens ein Fehler auftritt, Datei aufräumen).
     - **Fehlerbehandlung & Retry:**
       - `urllib.error.HTTPError` (4xx/5xx) wird **nicht** wiederholt, sondern sofort weitergereicht.
       - Transiente Fehler `(TimeoutError, ConnectionError, urllib.error.URLError, OSError)` werden mit `log_message(f"⚠️ [Download] Versuch {attempt}/{attempts} fehlgeschlagen ({context or url}): {exc}")` geloggt und bis zu `attempts`-mal wiederholt (mit `time.sleep(attempt)` zwischen den Versuchen). Nach Erschöpfung aller Versuche wird der letzte Fehler sichtbar geworfen.
   - `_download_with_timeout(url, path, timeout=10)` delegiert direkt an `_download_with_retry(url, path, timeout=timeout)`, sodass alle bestehenden Aufrufstellen in `gui/mw_metadata.py` automatisch abgesichert sind.

### 2. Multi-Provider-Metadaten-Abruf in Backend & API (E4-AK1, E4-AK2, Option 3A)
1. **Neue Funktion `fetch_movie_comparison_data(providers_spec)` in `gui/mw_metadata.py`:**
   - Nimmt eine Liste von Provider-Spezifikationen entgegen, z. B. `[{"provider": "tmdb", "movie_id": "1200320"}, {"provider": "ofdb", "movie_id": "ofdb_391234_Killing-Faith"}]` (unterstütze auch Dicts mit `"id"` statt `"movie_id"` sowie ein Dict `{"tmdb": "1200320", "ofdb": "ofdb_..."}`).
   - Normalisiert den Provider-Namen (`"tmdb_movie"` → `"tmdb"`, `"tmdb"` → `"tmdb"`, `"ofdb"` → `"ofdb"`).
   - Ruft für jeden angefragten Provider parallel (über `concurrent.futures.ThreadPoolExecutor`) `fetch_movie_nfo_data(prov, movie_id)` ab.
   - Liefert die Ergebnisse **ungemergt je Provider** zurück (E4-AK1), inklusive Teil-Erfolg-Status, wenn ein Provider ausfällt (E4-AK2):
     ```python
     {
         "providers": {
             "tmdb": {
                 "provider": "tmdb",
                 "movie_id": "1200320",
                 "status": "ok",       # oder "error"
                 "error": None,        # oder Fehlermeldung als String
                 "fields": {
                     "title": "...",
                     "year": "...",
                     "plot": "...",
                     "fsk": "...",
                     "genres": ["..."],
                 },
             },
             "ofdb": { ... }
         },
         "provider_order": ["tmdb", "ofdb"],
     }
     ```
   - Wenn `fetch_movie_nfo_data` ein Dict mit `"error"` zurückgibt oder eine Exception wirft, darf der Gesamtabruf **nicht** abbrechen: Für diesen Provider wird `"status": "error"`, `"error": str(err)` und leere `"fields"` (`{"title": "", "year": "", "plot": "", "fsk": "", "genres": []}`) eingetragen, während die anderen Provider normal `"status": "ok"` und ihre Felder liefern (E4-AK2).
2. **Erweiterung von `/api/metadata/fetch` in `gui/api/search_api.py` (Z. 879–905):**
   - `handle_api_metadata_fetch()` akzeptiert `providers` entweder im JSON-Body (`params.get("providers")`) oder als JSON-String in `request.args.get("providers")`.
   - Wenn `providers` übergeben wurde (nicht-leere Liste oder Dict), rufe `mw_metadata.fetch_movie_comparison_data(providers)` auf und gib das Ergebnis als JSON zurück (`200 OK`).
   - Wenn `providers` **nicht** übergeben wurde, bleibt das bisherige Einzel-Provider-Verhalten (`GET/POST /api/metadata/fetch?media_type=movie&provider=...&movie_id=...` liefert direkt `{title, plot, year, fsk, genres}`) **100 % unverändert** erhalten!

### 3. Provider-Badge-Karten in `nfo_editor.js` & Schritt 1/2 in `film_wizard.js` (E4-AK1, E4-AK2, Option 1A & 2A)
1. **Erweiterung von `renderNfoEditor` in `gui/static/js/nfo_editor.js`:**
   - Jedes der 5 Feld-Wrapper-Elemente (`title`, `year`, `genres`, `fsk`, `plot`) erhält unterhalb des Labels/Inputs einen Badge-Container `<div class="mw-wizard-field-badges hidden" data-field-badges="title"></div>` (bzw. `year`, `genres`, `fsk`, `plot`).
   - Ergänze am zurückgegebenen Editor-Controller die Methoden:
     - `setProviderComparison(comparisonData, options = {})`
     - `getProviderComparison()`
     - `clearProviderComparison()`
   - **Verhalten von `setProviderComparison(comparisonData)`:**
     - `comparisonData` hat die Struktur `{ providers: { tmdb: { status, error, fields }, ofdb: { ... } }, provider_order: ["tmdb", "ofdb"] }`.
     - Für jedes der 5 Felder (`title`, `year`, `fsk`, `genres`, `plot`) wird der zugehörige `.mw-wizard-field-badges`-Container eingeblendet (`hidden` entfernt) und pro Provider in `provider_order` ein Badge `<button type="button" class="mw-wizard-provider-badge" data-provider="${prov}" data-field="${fieldKey}">` gerendert:
       - Innerhalb des Badges: `<span class="mw-wizard-provider-name">${providerLabel}</span>` (`"TMDb"` für `tmdb`, `"OFDb"` für `ofdb`) und `<span class="mw-wizard-provider-value">${displayValue}</span>`.
       - **Zustand 1 — Provider-Fehler (`status === "error"`):**
         - Klasse `.mw-wizard-provider-badge.error` (oder `.mw-wizard-badge-error`), `disabled = true`.
         - `displayValue`: `"${providerLabel}: nicht erreichbar"` (z. B. `"OFDb: nicht erreichbar"`).
       - **Zustand 2 — Feld beim Provider leer (`status === "ok"`, aber Wert leer `""` bzw. `[]`):**
         - Klasse `.mw-wizard-provider-badge.empty`, `disabled = true`.
         - `displayValue`: bei `fsk` `"${providerLabel}: keine FSK"` (z. B. `"TMDb: keine FSK"` — ROADMAP #55), bei anderen Feldern `"${providerLabel}: keine Daten"` (bzw. bei `plot` `"${providerLabel}: kein Plot"` oder `"${providerLabel}: keine Daten"`).
       - **Zustand 3 — Wert vorhanden (`status === "ok"` und nicht-leerer Wert):**
         - Klasse `.mw-wizard-provider-badge` (plus `.selected`, wenn dieser Provider für das Feld aktiv gewählt ist).
         - `displayValue`: bei `fsk` `"FSK ${val}"`, bei `genres` `val.join(", ")`, bei `title`/`year`/`plot` der String-Wert.
     - **Automatische Vorbelegung & Lücken-Auffüllung (Option 2A):**
       - Für jedes **Alternativ-Feld (`title`, `year`, `plot`, `fsk`)**: Wähle den ersten Provider in `provider_order` mit `status === "ok"` und nicht-leerem Feldwert. Sofern der Nutzer dieses Feld noch nicht manuell editiert hat (`!touchedFields.has(fieldKey)`), übernimm dessen Wert in das Eingabefeld und markiere genau das Badge dieses Providers mit `.selected`.
       - Für das **Kumulativ-Feld (`genres`, ROADMAP #55)**: Bilde über alle Provider in `provider_order` mit `status === "ok"` und nicht-leeren `genres` die deduplizierte Vereinigung (`parseGenresInput(...)`). Sofern `!touchedFields.has("genres")`, setze das Genre-Eingabefeld auf diese Vereinigung und markiere alle beteiligten Provider-Badges mit nicht-leeren Genres als `.selected`.
       - Aktualisiere `baseline` auf diese initial zusammengeführten Provider-Werte; wenn ein Feld durch einen Zweit-Provider aufgefüllt wurde (oder mehrere Provider verglichen werden), stelle sicher, dass `buildWizardMovieOverrides()` die in Schritt 2 angezeigten nicht-leeren Werte (`title`, `year`, `plot`, `fsk`, `genres`) zuverlässig in `nfo_overrides.movie` aufnimmt!
     - **Klick-Interaktion auf ein `.mw-wizard-provider-badge`:**
       - Ignoriere Klicks auf `.empty`- oder `.error`-Badges.
       - **Alternativ-Feld (`title`, `year`, `plot`, `fsk`):** Klick auf ein Badge setzt den Wert des Eingabefelds auf den Wert dieses Providers, setzt `.selected` exklusiv auf dieses Badge (entfernt `.selected` von den Nachbar-Badges desselben Felds), markiert das Feld als geändert (`touchedFields.add(fieldKey)`) und feuert `onChange`.
       - **Kumulativ-Feld (`genres`):** Klick auf ein Genre-Badge schaltet dessen `.selected`-Status um (Toggle) und berechnet das Genre-Eingabefeld als deduplizierte Vereinigung aller aktuell `.selected` markierten Genre-Badges (falls dadurch keines mehr `.selected` wäre, wird stattdessen genau das geklickte Badge `.selected` gesetzt, damit man auch gezielt auf einen einzelnen Provider wechseln kann).
       - **Manuelle Eingabe (`input`/`change` am Textfeld/Select/Textarea):** Entfernt `.selected` von den Provider-Badges des betroffenen Feldes, da der Wert nun manuell überschrieben wurde.
2. **Erweiterung von `gui/static/js/film_wizard.js` (Option 1A, 2A, 3A & D3.4):**
   - **Schritt 1 — Suche & Provider-Paarung (Option 1A):**
     - Speichere in `performSearch()` die erhaltenen Suchtreffer in `lastSearchResults`.
     - Rendere in jeder `.mw-wizard-search-item`-Zeile neben Titel und Dienst-Label eine optionale Vergleichs-Checkbox `<input type="checkbox" class="mw-wizard-compare-cb" data-provider="${item.provider || 'tmdb'}" data-id="${item.id ?? ''}" title="Zum Provider-Vergleich auswählen">` (Klick auf die Checkbox ruft `e.stopPropagation()` auf, erlaubt max. 1 angehakten Treffer pro Provider `tmdb`/`ofdb` und wechselt noch nicht sofort zu Schritt 2).
     - **1-Klick auf die Trefferzeile (Standard-Alltagspfad):** Wenn der Nutzer direkt auf eine `.mw-wizard-search-item`-Zeile klickt (und nicht auf die Checkbox):
       - Falls bereits Vergleichs-Checkboxen angehakt sind und der geklickte Treffer dazugehört (oder diese ergänzt), nutze die angehakten Provider;
       - Andernfalls suche in `lastSearchResults` automatisch nach dem besten passenden Treffer des jeweils anderen Dienstes (`tmdb` ↔ `ofdb`): Vergleiche den normalisierten Titel (ohne Jahresklammer `(YYYY)`, Kleinschreibung, alphanumerisch) und — falls beide eine Jahreszahl `(YYYY)` im Namen tragen — das gleiche Jahr. Wird ein passender Gegen-Treffer gefunden, übergib beide (`[clickedItem, counterpartItem]`) an `selectMovieInWizard(clickedItem, true, [clickedItem, counterpartItem])`!
     - **Klick auf „Weiter“ (`nextStep()`) in Schritt 1:** Falls der Nutzer in Schritt 1 eine oder mehrere `.mw-wizard-compare-cb`-Checkboxen angehakt hat (ohne auf eine Zeile zu klicken), rufe `selectMovieInWizard(primaryCheckedItem, true, checkedItems)` auf (wobei `tmdb` als `primaryCheckedItem` bevorzugt wird, falls unter den angehakten Treffern vorhanden) und wechsle zu Schritt 2.
   - **Schritt 2 — Multi-Provider-Laden & Fehler-Banner (Option 3A & D3.4):**
     - `selectMovieInWizard(movie, fetchMeta = true, comparisonMovies = null)` speichert die Liste der zu vergleichenden Provider (`selectedProviders`, Default `[selectedMovie]`).
     - Für `buildMovieBasePayload()` gilt (Option 2A): Ist unter den verglichenen und erfolgreichen Providern `tmdb` vorhanden, nutze `tmdb` (und dessen `movie_id`) als `provider`/`movie_id` im Basis-Payload (damit Artwork, Cast, Studios und `<tmdbid>` beim Import erstellt werden), während alle in Schritt 2 gewählten/editierten Felder über `nfo_overrides.movie` mitreisen.
     - In `loadMovieMetadata`:
       - Wenn `selectedProviders` mehrere Provider enthält (oder den Multi-Provider-Abruf nutzt), rufe `/api/metadata/fetch?media_type=movie&provider=${encodeURIComponent(movie.provider)}&movie_id=${encodeURIComponent(movie.id)}` mit `POST` und JSON-Body `{ media_type: "movie", providers: selectedProviders.map(p => ({ provider: p.provider, movie_id: String(p.id) })) }` auf (Hinweis: Behalte den Query-String `?media_type=movie&provider=...&movie_id=...` an der URL bei, damit bestehende Test-Mocks in `film_wizard.test.js`, die `url.startsWith('/api/metadata/fetch')` prüfen, weiterhin matchen!).
       - **Antwort-Verarbeitung (kompatibel mit Multi-Provider-Response UND Legacy-Single-Response):**
         - Liefert der Server/Mock `{ providers: { ... }, provider_order: [...] }`, übergib dies an `nfoEditor.setProviderComparison(data)`.
         - Prüfe auf **Teil-Erfolg / Total-Ausfall (E4-AK2 & D3.4)**:
           - Wenn **mindestens ein** Provider `"status": "ok"` hat, aber mindestens ein anderer Provider `"status": "error"` (Teil-Erfolg): Setze das Kopf-Badge `#mw-wizard-provider-badge` auf z. B. `"TMDb + OFDb (Teil-Erfolg)"` (ohne die ganze Feldansicht zu verwerfen!) und zeige über `showError("Einige Provider sind nicht erreichbar. Du kannst mit den geladenen Daten fortfahren.", () => loadMovieMetadata(movie))` den Hinweis-Banner mit Retry-Button an, während die geladenen Felder und Badges in `nfoEditor` vollständig wählbar bleiben!
           - Wenn **alle** angefragten Provider `"status": "error"` liefern, zeige den Fehler-Banner mit Retry-Button und markiere `#mw-wizard-provider-badge` als `"Nicht erreichbar"`.
           - Wenn **alle** angefragten Provider `"status": "ok"` liefern, blende den Fehler-Banner aus (`hideError()`) und zeige im `#mw-wizard-provider-badge` die aktiven Dienste (z. B. `"TMDb"` bei einem Dienst bzw. `"TMDb + OFDb"` bei zwei Diensten).
         - Liefert ein bestehender Test-Mock in `film_wizard.test.js` noch das flache Einzel-Objekt `{ title, year, plot, fsk, genres }` (ohne `.providers`-Schlüssel), rufe wie bisher `nfoEditor.applyProviderMetadata(...)` auf UND aktualisiere die Badges über `nfoEditor.setProviderComparison(...)` für diesen einen Provider, damit alle bestehenden Tests in `film_wizard.test.js` grün bleiben.
3. **Styling in `gui/static/style.css` (`grafiker.md` Abschnitt 2):**
   - Ergänze die CSS-Klassen `.mw-wizard-field-badges`, `.mw-wizard-provider-badge`, `.mw-wizard-provider-badge.selected`, `.mw-wizard-provider-badge.empty`, `.mw-wizard-provider-badge.error`, `.mw-wizard-provider-name`, `.mw-wizard-provider-value` sowie `.mw-wizard-compare-cb` ausschließlich mit bestehenden CSS-Variablen (`var(--bg-surface)`, `var(--bg-card)`, `var(--border-light)`, `var(--accent)`, `var(--danger)`, `var(--text-main)`, `var(--text-muted)`), damit alle 5 Themes (`dark`, `light`, `midnight`, `slate`, `sand`) sauber unterstützt werden.

### 4. Cache-Buster & Tests
- **Cache-Buster:**
  - Hebe in `gui/static/index.html` `app.js?v=116` auf `app.js?v=117` und `style.css?v=61` auf `style.css?v=62` an.
  - Ziehe alle relativen ES-Modul-Importe in `gui/static/app.js` sowie in `gui/static/js/film_wizard.js` (`nfo_editor.js?v=117`, `format.js?v=117`, `preview_render.js?v=117`) konsistent auf `?v=117` nach (Prüfung durch `tests/frontend/cache_busting.test.js`).
- **Backend-Tests (`unittest`-kompatibel im Container!):**
  - **`tests/test_metadata_retry.py` (E4-AK3):**
    - Baue `tests/test_metadata_retry.py` so um (oder ergänze `unittest.TestCase`-Klassen und mache den `pytest`-Import optional), dass `python3 -m unittest tests/test_metadata_retry.py` im Gate-A2-Container **ohne installiertes `pytest`** vollständig durchläuft und gleichzeitig `pytest tests/test_metadata_retry.py` grün bleibt!
    - Ergänze in `tests/test_metadata_retry.py` Tests für **#54 Teil 2 (E4-AK3)**:
      1. HTML-Retry: `search_ofdb`, `get_fernsehserien_episodes` und `resolve_mediathek_url_topic` erholen sich von einem transienten `TimeoutError`/`URLError` beim ersten Versuch und wiederholen echte HTTP-404-Fehler nicht.
      2. Binär-Download (`_download_with_retry` / `_download_with_timeout`):
         - Erholt sich von einem transienten `TimeoutError` beim ersten Versuch und schreibt die Datei beim zweiten Versuch vollständig.
         - Bricht bei unvollständigem Download (`Content-Length: 100`, aber nur 40 Bytes geliefert) oder 0-Byte-Antwort sichtbar mit Fehler ab, wiederholt den Versuch mit frischem Request/File-Handle und hinterlässt bei endgültigem Scheitern keine kaputte Teildatei auf der Platte.
         - Wiederholt echte HTTP-404-Fehler nicht.
  - **`tests/test_provider_fields.py` (neu, `unittest.TestCase`, E4-AK1 & E4-AK2):**
    - Prüft **E4-AK1**: `fetch_movie_comparison_data` und `POST /api/metadata/fetch` (mit `providers: [{"provider": "tmdb", "movie_id": "1200320"}, {"provider": "ofdb", "movie_id": "ofdb_391234_Killing-Faith"}]`) liefern die Felder **ungemergt je Provider** (z. B. TMDb mit Plot, aber `fsk: ""`; OFDb mit `fsk: "16"`, aber `plot: ""`).
    - Prüft **E4-AK2 (Teil-Erfolg im Backend)**: Fällt ein Provider (z. B. OFDb per Timeout/HTTPError) aus, liefert `providers["ofdb"]` `"status": "error"` mit Fehlermeldung, während `providers["tmdb"]` `"status": "ok"` mit allen TMDb-Feldern liefert.
    - Prüft Rückwärtskompatibilität: `GET /api/metadata/fetch?media_type=movie&provider=tmdb&movie_id=1200320` ohne `providers` liefert weiterhin das flache Dict `{title, plot, year, fsk, genres}`.
- **Frontend-Tests (`node --test tests/frontend/*.test.js`):**
  - **`tests/frontend/provider_badges.test.js` (neu, E4-AK1 & E4-AK2):**
    - Prüft, dass `nfoEditor.setProviderComparison(...)` pro Feld Badges für `tmdb` und `ofdb` rendert, leere Angebote sichtbar als `.empty` („TMDb: keine FSK“, „OFDb: keine Daten“) darstellt, Lücken automatisch aus dem Zweit-Provider auffüllt (TMDb-Plot + OFDb-FSK 16) und Genres kumulativ vereinigt.
    - Prüft, dass ein Klick auf ein Provider-Badge den Feldwert umschaltet und in `buildWizardMovieOverrides()` übernimmt.
    - Prüft **E4-AK2 (Teil-Erfolg im Frontend)**: Wenn OFDb `"status": "error"` meldet, zeigt nur das OFDb-Badge `.error` („OFDb: nicht erreichbar“), der Hinweis-Banner im Wizard wird angezeigt, und alle TMDb-Badges sowie die Eingabefelder bleiben wählbar und editierbar.
    - Prüft Option 1A im Wizard: 1-Klick auf einen TMDb-Suchtreffer in Schritt 1 paart automatisch den passenden OFDb-Treffer aus der Suchliste und lädt beide Provider in Schritt 2.
  - **`tests/frontend/nfo_editor.test.js` & `tests/frontend/film_wizard.test.js`:**
    - Bestehende Tests müssen grün bleiben; gerne um gezielte Assertions für `setProviderComparison` / `clearProviderComparison` ergänzen.
- **Autoritatives Testkommando für den Gate-A2-Lauf:**
  `python3 -m unittest tests/test_metadata_retry.py tests/test_provider_fields.py tests/test_inbox_movie_overrides.py && node --test tests/frontend/*.test.js`

## Nicht bauen
- Keine Artwork-Auswahl in Schritt 3 (das ist Etappe E5).
- Keine Filmreihen-Queue „Film X von N“ (das ist Etappe E6).
- Keine Änderungen am NFO-Agenten (`#modal-nfo-agent`) oder am Serien-/Doku-Ablauf.
- Keine Änderungen außerhalb der "Erlaubten Dateien" von E4 im Briefing.

## Diff-Budget (wichtig)
Das Diff-Budget im Briefing ist eine Orchestrator-Metrik, kein Ziel für dich. Sobald die Akzeptanzkriterien erfüllt und alle Tests grün sind, darfst du den Code NICHT künstlich kürzen, minifizieren oder verdichten, und du stoppst nicht wegen der Größe. Fertig + grün = abgeben.
