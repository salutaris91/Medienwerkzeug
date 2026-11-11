# Aufgabe Etappe E5b (Handtest-Nachzug) — Logo-Grid-Fix, Label „Hintergrundbild (16:9)“ & Mehrfachauswahl für Hintergrundbilder (ROADMAP #92, #51)

Grundlage: `docs/sessions/2026-11-06-film-assistent/briefing.md` (Etappe E5) und der bereits auf Branch `feat/film-wizard-e5` (HEAD `e209951`) umgesetzte E5-Stand.
Explizite Handtest-Entscheidung von Alex vom 2026-11-11:
`Alex: „Lass uns das mit dem Logo und dem Poster genauso machen, wie du jetzt vorgeschlagen hast, und das jetzt auch gleich glattziehen.“`

## Ziel (3 klar abgegrenzte Punkte auf dem bestehenden E5-Stand)

### 1. CSS-Fix für das überlappende `Logo`-Grid & Doppel-Scrollbar (`gui/static/style.css`)
- **Ursache im Handtest-Screenshot:** `.mw-wizard-artwork-tile` hatte `min-height: 140px;`. Zusammen mit `.mw-wizard-artwork-grid-logo .mw-wizard-artwork-tile { aspect-ratio: 16 / 7; }` erzwang das eine Mindestbreite von `140 * 16 / 7 = 320px` je `<button>` innerhalb einer `~185px` breiten Grid-Spalte, sodass die Logo-Kacheln horizontal überliefen und sich überlappten.
- **Umsetzung in `gui/static/style.css`:**
  1. Setze auf `.mw-wizard-artwork-tile`: `width: 100%; min-width: 0; min-height: 0; box-sizing: border-box;` (behalte `min-height: 110px;` gezielt auf `.mw-wizard-artwork-tile.empty`, `.mw-wizard-artwork-tile.error` und `.mw-wizard-artwork-tile.loading`, sofern keine `aspect-ratio` greift; für `.mw-wizard-artwork-grid-poster .mw-wizard-artwork-tile`, `.mw-wizard-artwork-grid-backdrop .mw-wizard-artwork-tile` und `.mw-wizard-artwork-grid-logo .mw-wizard-artwork-tile` bestimmt allein `aspect-ratio` + Spaltenbreite die Höhe, `min-height: 0;`).
  2. Stelle sicher, dass `.mw-wizard-artwork-image` `max-width: 100%; max-height: 100%; min-width: 0; min-height: 0;` hat, sodass breite Transparent-Logos (`object-fit: contain`) strikt innerhalb der Kachel bleiben.
  3. Setze in `Superfood Light` auf `body.theme-superfood-light .mw-wizard-artwork-grid-logo .mw-wizard-artwork-tile` einen voll deckenden Hintergrund `background: var(--primary);` (statt halbtransparentem `rgba(var(--primary-rgb), 0.78)`), ausschließlich mit bestehenden CSS-Variablen.
  4. Setze auf `.mw-wizard-artwork-grid`: `overflow-x: hidden; max-height: 290px;` (statt `360px`), damit `#mw-wizard-tmdb-attribution` im Modal ohne doppelten Scrollbalken direkt sichtbar bleibt.
  5. Passe `.mw-wizard-artwork-check` für mehrstellige Reihenfolge-Badges (`✓`, `✓ 1`, `✓ 2`) an: `min-width: 24px; height: 24px; padding: 0 6px; border-radius: 999px;` (statt fixer `width: 24px; border-radius: 50%;`).

### 2. Deutsche Bezeichnung `Hintergrundbild (16:9)` statt `Fanart (16:9)` (`gui/static/index.html` & `gui/static/js/film_wizard.js`)
- Ändere den sichtbaren Tab-Text von `#mw-wizard-tab-fanart` sowohl in `gui/static/index.html` als auch in `buildWizardDom()` (`gui/static/js/film_wizard.js`) von `Fanart (16:9)` auf `Hintergrundbild (16:9)`.
- **Wichtig:** Alle bestehenden DOM-IDs (`#mw-wizard-tab-fanart`, `#mw-wizard-artwork-fanart`), `data-artwork-tab="fanart"`, `switchArtworkTab("fanart")` und der Rollen-Schlüssel `"backdrop"` bleiben intern unverändert!
- Ändere `artworkRoleLabel(role)` und die Schritt-4-Zusammenfassung (`formatArtworkSummaryLine()`) in `gui/static/js/film_wizard.js` so, dass für `"backdrop"` durchgängig `"Hintergrundbild"` ausgegeben wird (z. B. `"Kein Hintergrundbild bei TMDb verfügbar."`, Placeholder `"Automatischer Hintergrundbild-Download (TMDb) ist aktiv. Dieser Schritt kann übersprungen werden."`, Schritt-4-Label `"Hintergrundbild: ..."`).

### 3. Geordnete Mehrfachauswahl NUR für `Hintergrundbild (16:9)` (`backdrop`), Einzelauswahl bleibt für `Poster (2:3)` & `Logo`

#### A. Frontend (`gui/static/js/film_wizard.js`)
- **`poster` und `logo` bleiben strikt bei 1-Klick-Einzelauswahl:**
  - Höchstens 1 ausgewählte Kachel je Rolle; Klick auf eine andere Kachel wählt diese direkt aus und hebt die vorherige auf; Klick auf die bereits aktive Kachel oder `#mw-wizard-artwork-deselect-btn` setzt `mode = "none"`.
- **`backdrop` (`Hintergrundbild (16:9)`) unterstützt geordnete Mehrfachauswahl (bis max. `MAX_BACKDROP_SELECTION = 10` Bilder):**
  - Verwalte im `backdrop`-State eine geordnete Liste ausgewählter Einträge `selectedItems` (jeder Eintrag `{ mode: "url", url, thumbUrl }` oder `{ mode: "upload", dataUrl, fileName }`).
  - **Initialzustand nach Kandidaten-Abruf (solange `!st.explicit`):** Wenn `backdrops.length > 0`, ist wie bisher `backdrops[0]` als einziges Element vorausgewählt (`selectedItems = [{ mode: "url", url: backdrops[0].url, thumbUrl: ... }]`, `mode = "url"`, `selectedUrl = backdrops[0].url`, `explicit = false`).
  - **Klick auf eine TMDb-Kachel im Tab `Hintergrundbild (16:9)` (`selectArtworkCandidate("backdrop", idxOrUrl)`):**
    - Ist diese URL bereits in `selectedItems` enthalten → entferne genau diesen Eintrag aus `selectedItems` (`explicit = true`). Ist `selectedItems` danach leer, setze `st.mode = "none"`, `st.selectedUrl = ""`, `st.selectedDataUrl = ""`.
    - Ist diese URL noch **nicht** in `selectedItems` enthalten → hänge `{ mode: "url", url: cand.url, thumbUrl: ... }` ans Ende von `selectedItems` an (`explicit = true`; falls `selectedItems.length >= MAX_BACKDROP_SELECTION`, zeige einen kurzen sichtbaren Hinweis wie `"Maximal 10 Hintergrundbilder auswählbar."` im Panel/Log und füge kein 11. hinzu).
  - **Eigenes Bild hochladen im Tab `Hintergrundbild (16:9)` (`setCustomArtworkUpload("backdrop", dataUrl, fileName)`):**
    - Speichert `st.customUpload = { dataUrl, fileName }` (Kachel erscheint ganz vorn im Grid).
    - Falls in `selectedItems` bereits ein `"upload"`-Eintrag liegt, aktualisiere ihn an seiner Position; andernfalls füge `{ mode: "upload", dataUrl, fileName }` zu `selectedItems` hinzu (falls `< MAX_BACKDROP_SELECTION`, sonst ersetze den letzten bzw. melde das Limit), **ohne** bereits gewählte TMDb-Hintergrundbilder aus `selectedItems` zu löschen (`explicit = true`).
    - Klick auf die eigene Upload-Kachel im `backdrop`-Grid toggelt den `"upload"`-Eintrag in `selectedItems` genauso wie eine TMDb-Kachel an/aus!
  - **Klick auf `#mw-wizard-artwork-deselect-btn` (`deselectArtworkRole("backdrop")`):**
    - Leert `selectedItems = []`, setzt `st.mode = "none"`, `st.selectedUrl = ""`, `st.selectedDataUrl = ""`, `st.explicit = true`.
  - **Visuelle Darstellung im `backdrop`-Grid:**
    - Jede in `selectedItems` enthaltene Kachel erhält `.selected` und `aria-pressed="true"`.
    - Badge `.mw-wizard-artwork-check`: Ist genau **1** Hintergrundbild ausgewählt (`selectedItems.length === 1`), zeige `"✓"` (damit Einzelauswahl-Optik und bestehende Tests konsistent bleiben); sind **`>= 2`** Hintergrundbilder ausgewählt, zeige die 1-basierte Reihenfolge `"✓ 1"`, `"✓ 2"`, `"✓ 3"`, … (Index `1` = Haupt-Hintergrundbild `fanart.*`/`backdrop.*`, ab `2` = Zusatz-Hintergrundbilder `fanart-1.*`, `fanart-2.*`).
  - **Payload in `buildArtworkOverridesPayload()` für `backdrop`:**
    - `0` gewählte Bilder (`mode === "none"`): `{ mode: "none" }`.
    - Nicht explizit geändert bei TMDb-Provider: `{ mode: "auto" }` (und falls keine der 3 Rollen explizit geändert wurde, bleibt `artwork_overrides` auf dem Gesamt-Payload wie bisher `undefined`!).
    - Genau **`1`** gewähltes Bild in `selectedItems`: serialisiere **unverändert** als `{ mode: "url", url: item.url }` bzw. `{ mode: "upload", data_url: item.dataUrl }` (100 % rückwärtskompatibel!).
    - **`>= 2`** gewählte Bilder in `selectedItems`: serialisiere als:
      ```js
      {
          mode: "multi",
          items: selectedItems.map((it) =>
              it.mode === "upload"
                  ? { mode: "upload", data_url: it.dataUrl }
                  : { mode: "url", url: it.url }
          ),
      }
      ```
  - **Schritt-4-Zusammenfassung (`formatArtworkSummaryLine()`):**
    - Hat `backdrop` `>= 2` ausgewählte Bilder: zeige `"Hintergrundbild: N Bilder"` (z. B. `"Hintergrundbild: 3 Bilder"`). Bei 1 Bild weiterhin `"TMDb-Auswahl"` bzw. `"Eigenes Bild"`, bei Abwahl `"Kein Bild"`.
  - **`getArtworkState()`:**
    - Ergänze im zurückgegebenen Snapshot je Rolle `selectedCount` (`number`) und `selectedItems` (flache Kopie der aktiven Elemente), während `mode` (`"multi"` bei `>= 2` Bildern, sonst `"url" | "upload" | "none" | "auto"`), `selectedUrl` und `selectedDataUrl` erhalten bleiben.

#### B. Backend (`gui/mw_metadata.py`)
- **`_normalize_role_override(raw_spec)` & `_explicit_artwork_roles(artwork_overrides)`:**
  - Unterstütze `mode == "multi"` mit `"items": [...]` (Liste von Einzel-Specs `"url"` / `"upload"`, max. `10` Elemente; mehr als `10` Elemente wirft `ValueError("Maximal 10 Hintergrundbilder erlaubt.")`).
  - Eine leere `items`-Liste bei `mode == "multi"` wird wie `{"mode": "none"}` behandelt; eine 1-elementige `items`-Liste kann direkt oder über denselben Multi-Pfad verarbeitet werden.
  - `"multi"` zählt in `_explicit_artwork_roles()` als explizite Steuerung (`needs_fanart = False` in `generate_movie_nfo`, damit kein ungewollter Auto-Download dazwischenläuft).
  - Wird `mode == "multi"` für `"poster"` oder `"logo"` übergeben, wirf `ValueError("Mehrfachauswahl wird nur für Hintergrundbilder (backdrop) unterstützt.")`.
- **`apply_movie_artwork_overrides(folder_path, filename_base, artwork_overrides, settings=None)`:**
  - Bestimme für `"backdrop"` die bevorzugte Server-Basis über `validator.get_preferred_movie_backdrop_name(f"{filename_base}.mkv")` (`pref_base` ist `"fanart"` für Emby/Plex und `"backdrop"` für Jellyfin).
  - Für `mode == "multi"` mit `items`:
    - Speichere Element `idx == 0` als `{pref_base}{ext}` (z. B. `fanart.jpg` / `backdrop.jpg`) und jedes weitere Element `idx >= 1` als `{pref_base}-{idx}{ext}` (z. B. `fanart-1.jpg`, `fanart-2.jpg` bzw. `backdrop-1.jpg`, `backdrop-2.jpg`).
      *(Bindestrich `-{idx}` ist gemäß `ArtworkValidator.matches_artwork_name` in `gui/core/artwork_validators.py` Z. 25–31 mit Emby, Jellyfin UND Plex kompatibel!)*
    - Nutze für jedes Element exakt dieselben Sicherheits- und Integritätsprüfungen wie bei Einzelbildern: `validate_tmdb_image_url(url)` + `_download_with_retry(...)` in eine `.part`-Datei + atomares `os.replace(...)` bzw. `decode_and_validate_uploaded_image(data_url)` + `.part` + `os.replace(...)`, sowie Entfernen abweichender Dateiendungen derselben Zielbasis erst nach erfolgreichem Write.
    - Bereinige nach erfolgreichem Speichern im `folder_path` veraltete überzählige nummerierte Backdrop-Dateien `{b}-{n}.{e}` (`b in ("fanart", "backdrop")`, `e in (".jpg", ".jpeg", ".png", ".webp")`, `n > anzahl_zusatzbilder`), auch bei Wechsel von `multi` zurück auf Einzel-`url`/`upload` (`anzahl_zusatzbilder = 0`), damit keine alten `fanart-2.jpg` liegen bleiben.
    - Schlägt bei `multi` ein einzelnes Bild fehl, logge den Fehler sichtbar über `log_message(...)`, räume dessen `.part`-Datei auf und setze für die übrigen Elemente fort; `results["backdrop"]` enthält `{"ok": len(saved_paths) > 0 and len(errors) == 0, "mode": "multi", "path": saved_paths[0] if saved_paths else None, "paths": saved_paths, "error": "; ".join(errors) if errors else None}` (und `generate_movie_nfo` setzt `result["fanart"] = bool(saved_paths)`).

### 4. Cache-Buster & Tests
- **Cache-Buster:**
  - Hebe in `gui/static/index.html` `app.js?v=120` → `app.js?v=121` und `style.css?v=64` → `style.css?v=65` an.
  - Ziehe alle relativen ES-Modul-Importe in `gui/static/app.js` sowie in `gui/static/js/film_wizard.js` konsistent auf `?v=121` nach (`tests/frontend/cache_busting.test.js` prüft dies!).
- **Tests anpassen & ergänzen:**
  1. `tests/test_artwork_download.py`:
     - Testet `mode: "multi"` für `backdrop` (Kombination aus 2 TMDb-URLs + 1 lokalem PNG-Upload → erzeugt `fanart.jpg`, `fanart-1.jpg`, `fanart-2.png` für Emby bzw. `backdrop.jpg`, `backdrop-1.jpg`, `backdrop-2.png` für Jellyfin, und prüft auch, dass `processor.process_worker` alle Dateien bis in den finalen Outbox-Filmordner übernimmt!).
     - Testet, dass `mode: "multi"` bei `poster` / `logo` sowie `> 10` Einträge mit Fehler abgewiesen werden und überzählige Alt-Dateien (`fanart-3.jpg`) beim Überschreiben bereinigt werden.
  2. `tests/frontend/film_wizard_artwork.test.js`:
     - Prüft das neue Tab-Label `Hintergrundbild (16:9)` (statisch & dynamisch) und die Schritt-4-Zusammenfassung (`Hintergrundbild: 2 Bilder`).
     - Prüft, dass im Tab `Hintergrundbild (16:9)` mehrere Kacheln gleichzeitig ausgewählt werden können (`✓ 1`, `✓ 2`), erneuter Klick einzelne Kacheln wieder entfernt, `buildMovieBasePayload().artwork_overrides.backdrop` bei 2+ Bildern `{ mode: "multi", items: [...] }` (inkl. Kombination mit eigenem Upload) liefert und bei 1 Bild weiterhin `{ mode: "url", url: ... }`, während `Poster (2:3)` und `Logo` strikt bei maximal 1 ausgewählter Kachel bleiben.
     - Prüft die CSS-Regeln in `gui/static/style.css` (`.mw-wizard-artwork-tile` hat `min-width: 0` und `min-height: 0` ohne `140px`-Zwang auf den Aspect-Ratio-Kacheln, `Superfood Light` Logo-Tile nutzt `var(--primary)`).
- **Autoritatives Testkommando:**
  `python3 -m unittest tests/test_artwork_download.py tests/test_metadata_retry.py tests/test_provider_fields.py tests/test_inbox_movie_overrides.py && node --test tests/frontend/*.test.js`

## Nicht bauen
- Keine Mehrfachauswahl für `Poster` oder `Logo`.
- Keine Änderung an `fetch_tmdb_images()` oder am Serien-/Doku-Pfad.
- Keine hartcodierten Hex-Farben in `gui/static/style.css`.
