# Aufgabe Etappe E5 — Artwork-Auswahl (ROADMAP #92, #51)

Grundlage: `docs/sessions/2026-11-06-film-assistent/briefing.md` (status approved, FP2 von Alex 2026-11-06: "Damit gebe ich FP2 frei.", D2 = Option A: nur TMDb-Bilder, kein Fanart.tv). Gebaut wird **nur Etappe E5** mit den Akzeptanzkriterien E5-AK1 bis E5-AK3. E1 (`7fb0d92`, PR #168), E2 (`6856990`, PR #170), E3 (`c94d837`, PR #171) und E4 (`dda283d`, PR #172) sind gemergt.

Ergänzende Entscheidungen von Alex vom 2026-11-11 ("Ja genau, wie von dir vorgeschlagen umsetzen. Ich stimme dir in allen drei Punkten zu."):
- **Option 1A (Lokaler Bild-Upload je Rolle):** Zusätzlich zum TMDb-Grid gibt es je Rolle (`poster`, `backdrop`, `logo`) die Möglichkeit, eine eigene lokale Bilddatei (`.jpg`, `.jpeg`, `.png`, `.webp`) auszuwählen (`<input type="file" accept=".jpg,.jpeg,.png,.webp">`). Das Bild wird in Schritt 3 sofort als Vorschau angezeigt, im Payload als Base64-Data-URL mitgeschickt und erst beim finalen Job-Lauf nach strikter Größen- (max. 15 MB) und Magic-Byte-Prüfung (JPEG/PNG/WebP) gespeichert. **Keine freie Fremd-URL-Eingabe** (SSRF-Schutz).
- **Option 2A (Provider-unabhängige TMDb-Bildsuche in Schritt 3):** Liegt aus Schritt 1 keine numerische `tmdb_id` vor (z. B. nur OFDb oder „Metadaten manuell eintragen“), sucht Schritt 3 automatisch per `Titel (+ Jahr)` aus Schritt 2 über `/api/artwork/candidates` bei TMDb nach dem passenden Film für die Bildkandidaten und zeigt oberhalb der Tabs eine kompakte Quellen-/Nachsuch-Zeile an, mit der die TMDb-Bildquelle unabhängig vom NFO-Provider angepasst werden kann.
- **Option 3A (3 Rollen-Tabs + Abwahl + TMDb-Attribution):** Schritt 3 zeigt drei Rollen-Tabs (`Poster (2:3)`, `Fanart (16:9)`, `Logo`), markiert initial den besten Treffer (`de -> sprachneutral -> en`, identisch zu `fetch_tmdb_images()`) als vorausgewählt und erlaubt die explizite Abwahl („Kein Bild laden“ bzw. erneuter Klick auf die aktive Kachel), wodurch im Backend auch der automatische Fallback-Download dieser Rolle unterdrückt wird. Sichtbare TMDb-Attribution (offizielles TMDb-SVG-Logo + Pflichtsatz) im Fuß von Schritt 3.
- **CSP-Vorabprüfung (E5-AK3, erledigt 2026-11-11):** Weder `gui/main.py` / `gui/core/auth_middleware.py` noch `gui/static/index.html` setzen ein restriktives `Content-Security-Policy` / `img-src`. TMDb-Thumbnails (`https://image.tmdb.org/t/p/w185/...` und `w300/...`) laden direkt im Browser.

## Ausgangslage (Stand `main` `dda283d`)
- **`gui/mw_metadata.py`:**
  - `_download_with_retry(url, path, timeout=10, attempts=3, context="")` (Z. 9–71) und `_download_with_timeout` (Z. 74–75) existieren seit E4 mit frischem Request/File-Handle je Versuch sowie 0-Byte- und `Content-Length`-Integritätsprüfung.
  - `fetch_tmdb_images(media_type, tmdb_id)` (Z. 1094–1139) liefert pro Rolle maximal eine URL (`{'poster': ..., 'backdrop': ..., 'logo': ...}`). **WICHTIG (E5-AK1):** `fetch_tmdb_images()` darf in Signatur und Rückgabe **nicht** verändert werden, weil `generate_movie_nfo()` und `generate_tvshow_nfo()` im Auto-Modus davon abhängen!
  - `search_tmdb_movie(query)` (Z. 726+) sucht Filme bei TMDb per Text, IMDb-ID oder TMDb-ID.
  - `generate_movie_nfo(tmdb_id, folder_path, filename_base, fallback_json=None, nfo_overrides=None, overwrite=False)` (Z. 1141–1425) erzeugt die NFO und lädt im TMDb-Zweig automatisch `poster`, `backdrop` (über `validator.get_preferred_movie_backdrop_name`) und `logo` herunter. Bei `"manual"`, `"url_mediathek:..."` oder `generate_ofdb_nfo` werden keine TMDb-Artworks geladen.
- **`gui/workers/processor.py`:**
  - Im Film-Import-Block (Z. 2103–2186) werden `generate_ofdb_nfo` bzw. `generate_movie_nfo` (inkl. `patch_nfo_fields` bei `has_wizard_movie_overrides`) aufgerufen, danach konvertiert und per `safe_move_recursive` nach `dest_movie_dir_outbox` verschoben, wo Poster/Backdrop/Logo auf Server-Konventionen (`poster.*`, `fanart.*`/`backdrop.*`, `logo.*`) normalisiert werden (Z. 2268–2435).
- **`gui/static/js/film_wizard.js` & `gui/static/index.html`:**
  - Schritt 3 (`#mw-wizard-step-3`) enthält bisher nur 2 Platzhalter-Tabs (`#mw-wizard-tab-poster`, `#mw-wizard-tab-fanart`) und statischen Platzhalter-Text (`#mw-wizard-artwork-poster`, `#mw-wizard-artwork-fanart`).
  - **Achtung Bestandstests (`tests/frontend/film_wizard.test.js`):**
    1. `buildMovieBasePayload()` wird in mehreren Bestandstests mit `assert.deepEqual(basePayload.nfo_overrides, { movie: { ... } })` geprüft! Verändere `nfo_overrides` daher **nicht**, sondern lege Artwork-Auswahlen als eigenes Top-Level-Feld `artwork_overrides` auf dem Payload an (und lasse `artwork_overrides` weg bzw. `undefined`, solange `artworkSkipped === true` oder in Schritt 3 keine explizite Auswahl/Abwahl/Upload getroffen wurde und der Primär-Provider bereits `tmdb` im Auto-Modus ist — bzw. siehe exakte Payload-Spezifikation unten).
    2. `createWizardMockDom()` in `tests/frontend/film_wizard.test.js` unterstützt `doc.createElement`, `.innerHTML` (`parseHtmlInto`), `.setAttribute`, `.querySelectorAll`, aber **kein** `doc.createElementNS`! Verwende für Inline-SVGs (z. B. TMDb-Logo) `.innerHTML` auf einem `<span>`/`<div>`, niemals `doc.createElementNS`.
    3. Lade Artwork-Kandidaten erst **beim Betreten von Schritt 3** (`goToStep(3)`), **nicht** schon in Schritt 2 (`selectMovieInWizard`), damit Bestandstests mit eingeschränkten `mockFetch`-Stubs in Schritt 2 unberührt bleiben. Wenn `fetchFn` für `/api/artwork/candidates` in alten Mocks `undefined` zurückgibt, fange das sauber innerhalb von Schritt 3 ab (Placeholder-Kachel mit Retry in Schritt 3, **ohne** den globalen `#mw-wizard-error-banner` für ungemockte Legacy-Aufrufe zu triggern, bzw. zeige Fehler lokal in der Schritt-3-Kachel gemäß E5-AK2!).

## Bauen

### 1. Backend: TMDb-Kandidaten, Validierung & Artwork-Anwendung in `gui/mw_metadata.py` (E5-AK1, E5-AK2)

1. **`fetch_tmdb_images(media_type, tmdb_id)` unverändert lassen (E5-AK1):**
   - Signatur und Rückgabewert (`dict` mit `'poster'`, `'backdrop'`, `'logo'` als Einzel-Strings) bleiben 100 % unverändert.
2. **Neue Funktion `fetch_tmdb_image_candidates(media_type, tmdb_id, limit_per_role=24)` in `gui/mw_metadata.py` (E5-AK1):**
   - Prüft `TMDB_API_KEY`; falls leer, wirf `MetadataKeyMissing("TMDB_API_KEY ist nicht konfiguriert.")` oder gib `{"tmdb_id": str(tmdb_id or ""), "posters": [], "backdrops": [], "logos": [], "error": "TMDB_API_KEY fehlt"}` zurück (analog zu den anderen Fetch-Helfern; Fehler dürfen nicht still verschluckt werden).
   - Ruft `https://api.themoviedb.org/3/{media_type}/{tmdb_id}/images?api_key={TMDB_API_KEY}&include_image_language=de,en,null` über `fetch_json_with_retry(lambda: make_tmdb_request(url), timeout=10, context=f"TMDb {media_type} Bildkandidaten {tmdb_id}")` ab.
   - Sortiert jede Liste (`posters`, `backdrops`, `logos`) stabil nach Sprachpriorität:
     1. `iso_639_1 == "de"` (Priorität 0)
     2. `not iso_639_1` / sprachneutral (Priorität 1)
     3. `iso_639_1 == "en"` (Priorität 2)
     4. sonstige Sprachen (Priorität 3)
     Innerhalb derselben Sprachgruppe bleibt die TMDb-Originalreihenfolge erhalten — dadurch ist Element `[0]` exakt dasselbe Bild, das `fetch_tmdb_images()` standardmäßig auswählt!
   - Begrenzt jede Rolle auf maximal `limit_per_role` Einträge (Default `24`) und überspringt Einträge ohne gültigen `file_path` (muss mit `"/"` beginnen).
   - Baut pro Eintrag folgendes Dict:
     ```python
     {
         "url": f"https://image.tmdb.org/t/p/original{file_path}",
         "thumb_url": f"https://image.tmdb.org/t/p/{thumb_size}{file_path}",  # "w185" für posters & logos, "w300" für backdrops
         "lang": item.get("iso_639_1") or "",
         "width": int(item.get("width") or 0),
         "height": int(item.get("height") or 0),
     }
     ```
   - Gibt zurück:
     ```python
     {
         "tmdb_id": str(tmdb_id),
         "posters": [...],
         "backdrops": [...],
         "logos": [...],
     }
     ```
3. **Hilfsfunktion `resolve_movie_artwork_candidates(tmdb_id="", query="", year="")` in `gui/mw_metadata.py` (Option 2A):**
   - Wenn `tmdb_id` übergeben wurde und numerisch ist (`str(tmdb_id).strip().isdigit()`, inkl. Strip eines optionalen `"tmdb:"`-Präfixes):
     - Ruft direkt `fetch_tmdb_image_candidates("movie", clean_id)` auf und gibt das Ergebnis ergänzt um `"matched_title": ""` und `"matches": []` zurück.
   - Wenn keine numerische `tmdb_id` vorliegt, aber `query` (nicht-leerer String) übergeben wurde:
     - Ruft `search_tmdb_movie(query)` auf.
     - Ist `results` leer, gib `{"tmdb_id": "", "matched_title": "", "matches": [], "posters": [], "backdrops": [], "logos": []}` zurück.
     - Wählt den besten Treffer: Wenn `year` (4-stellig) angegeben ist, bevorzuge den ersten Treffer aus `results`, dessen `name` `f"({year})"` enthält; sonst `results[0]`.
     - Ruft `fetch_tmdb_image_candidates("movie", str(chosen["id"]))` auf und gibt das Ergebnis zusammen mit `"tmdb_id": str(chosen["id"])`, `"matched_title": chosen.get("name", "")` und `"matches": [{"id": str(r["id"]), "name": r.get("name", "")} for r in results]` zurück.
4. **Sicherheits-Validierung & Speichern gewählter Artworks `apply_movie_artwork_overrides(folder_path, filename_base, artwork_overrides, settings=None)` in `gui/mw_metadata.py` (E5-AK2, Option 1A, Option 3A):**
   - Unterstützte Rollen in `artwork_overrides`: `"poster"`, `"backdrop"` (Akzeptiere synonym auch `"fanart"` falls übergeben), `"logo"`.
   - Jede Rolle in `artwork_overrides` kann sein:
     - `"auto"` oder `None` / nicht enthalten → nichts überschreiben (Standardverhalten).
     - `"none"` oder `{"mode": "none"}` → Rolle wurde bewusst abgewählt! Falls im `folder_path` bereits Standard-Dateien dieser Rolle liegen, die gerade frisch erzeugt worden wären, wird nichts heruntergeladen (bestehende Dateien im Inbox-Ordner müssen bei `"none"` nicht gelöscht werden, aber es darf **kein** Download stattfinden).
     - `{"mode": "url", "url": "https://image.tmdb.org/t/p/..."}` (oder String `"https://image.tmdb.org/t/p/..."`):
       - **Strikter SSRF-Schutz (`validate_tmdb_image_url(url)`):** Erlaube ausschließlich `https://image.tmdb.org/t/p/<size>/<file>` (`scheme == "https"`, `netloc == "image.tmdb.org"`, `path.startswith("/t/p/")`, kein `".."` im Pfad, Dateiendung `.jpg`, `.jpeg`, `.png`, `.webp` case-insensitive). Jede andere Domain, `http://`, IP-Adresse oder `file://` wirft sofort `ValueError`!
       - Entferne vor dem Schreiben etwaige abweichende Erweiterungs-Varianten derselben Ziel-Basisdatei in `folder_path` (z. B. altes `poster.png`, wenn jetzt `poster.jpg` geladen wird — aber erst **nach** erfolgreichem Download in eine `.part`-Datei oder direkt vor dem atomaren `os.replace`, damit bei Download-Fehlern nichts zerstört wird!).
       - Lade das Bild mit `_download_with_retry(url, tmp_part_path, timeout=15, attempts=3, context=f"Artwork {role} {filename_base}")` herunter (nutzt automatisch Retry + 0-Byte- & `Content-Length`-Integritätsprüfung aus E4!) und verschiebe es per `os.replace(tmp_part_path, target_path)` an den Zielpfad:
         - `poster`: `os.path.join(folder_path, f"poster{ext}")` (Standard-Ext `.jpg`, `.jpeg` -> `.jpg`)
         - `backdrop`: `pref_name = validator.get_preferred_movie_backdrop_name(f"{filename_base}.mkv")`, `pref_base, _ = os.path.splitext(pref_name)` → `os.path.join(folder_path, f"{pref_base}{ext}")`
         - `logo`: `os.path.join(folder_path, f"logo{ext}")` (Standard-Ext `.png`)
     - `{"mode": "upload", "data_url": "data:image/...;base64,..."}` (Option 1A — eigenes lokales Bild):
       - **Größen- und Magic-Byte-Validierung (`decode_and_validate_uploaded_image(data_url, max_bytes=15 * 1024 * 1024)`):**
         - Prüft `data:image/(jpeg|jpg|png|webp);base64,<payload>`-Format und prüft schon vor `base64.b64decode`, dass die String-Länge `<= int(max_bytes * 1.38) + 128` ist.
         - Dekodiert mit `base64.b64decode(..., validate=True)`, prüft `0 < len(raw) <= max_bytes`.
         - Prüft die echten **Magic Bytes** des Binärinhalts (vertraue niemals allein dem MIME-Header oder Dateinamen!):
           - `raw.startswith(b"\xff\xd8\xff")` → `ext = ".jpg"`
           - `raw.startswith(b"\x89PNG\r\n\x1a\n")` → `ext = ".png"`
           - `len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP"` → `ext = ".webp"`
           - Alles andere (z. B. SVG, HTML, Text, korrupte Bytes) wirft `ValueError("Ungültiges Bildformat: Nur echte JPEG-, PNG- oder WebP-Dateien sind erlaubt.")`!
         - Schreibt atomar über temporäre `.part`-Datei + `os.replace` nach `poster{ext}` / `{pref_base}{ext}` / `logo{ext}` und räumt abweichende Alt-Endungen derselben Rolle auf.
   - Fehlerbehandlung in `apply_movie_artwork_overrides`: Jede Rolle wird einzeln in `try/except Exception as exc:` ausgeführt, Fehler werden sichtbar über `log_message(f"⚠️ [Artwork] {role} konnte nicht gespeichert werden: {exc}")` geloggt, temporäre `.part`-Dateien werden im Fehlerfall entfernt, und die Funktion gibt ein Ergebnis-Dict `{"poster": {"ok": bool, "path": ..., "error": ...}, "backdrop": {...}, "logo": {...}}` zurück.
5. **Integration in `generate_movie_nfo` (`gui/mw_metadata.py`) und `processor.py` (`gui/workers/processor.py`):**
   - Erweitere `generate_movie_nfo(tmdb_id, folder_path, filename_base, fallback_json=None, nfo_overrides=None, overwrite=False, artwork_overrides=None)` rückwärtskompatibel:
     - Bestimme vor dem Auto-Download (Z. 1180 / Z. 1369), welche Rollen in `artwork_overrides` explizit gesteuert werden (`mode in ("none", "url", "upload")`):
       - Ist `poster` explizit `"none"`, `"url"` oder `"upload"`, setze `needs_poster = False` (unterdrückt sowohl den `fetch_tmdb_images`-Download als auch den `data.get("poster_path")`-Fallback in Z. 1403!).
       - Ist `backdrop` explizit `"none"`, `"url"` oder `"upload"`, setze `needs_fanart = False` (unterdrückt `fetch_tmdb_images` und `data.get("backdrop_path")`-Fallback in Z. 1413!).
       - Ist `logo` explizit `"none"`, `"url"` oder `"upload"`, setze `needs_logo = False`.
     - Führe am Ende von `generate_movie_nfo` — **auch** in den frühen Return-Zweigen (`manual`, `url_mediathek:`, `http(s)://`, sowie „existiert“-Frühausstieg Z. 1288, falls `artwork_overrides` gesetzt ist!) — `apply_movie_artwork_overrides(folder_path, filename_base, artwork_overrides, settings=settings)` aus und aktualisiere die Rückgabe-Flags `poster`/`fanart`/`logo` entsprechend.
   - In `gui/workers/processor.py` (Film-Import-Block um Z. 2103–2186):
     - Lies `artwork_overrides = params.get("artwork_overrides") if isinstance(params.get("artwork_overrides"), dict) else None`.
     - Übergib `artwork_overrides=artwork_overrides` an `mw_metadata.generate_movie_nfo(...)` (in beiden Zweigen: mit und ohne `has_wizard_movie_overrides`).
     - Im `provider == "ofdb"`-Zweig (`mw_metadata.generate_ofdb_nfo(...)`): Rufe direkt danach `if artwork_overrides: mw_metadata.apply_movie_artwork_overrides(current_dir, clean_movie_name, artwork_overrides, settings=settings)` auf! Damit greift die Artwork-Auswahl und der lokale Bild-Upload aus Schritt 3 auch bei reinen OFDb-Filmen (Option 1A & 2A).

### 2. API-Endpunkt `/api/artwork/candidates` in `gui/api/search_api.py` (E5-AK1, Option 2A)
- Ergänze in `gui/api/search_api.py` die Route `@search_api.route('/artwork/candidates', methods=['GET', 'POST'])`:
  - Liest `tmdb_id` (oder `movie_id`), `query` (oder `title`) und `year` aus `request.args` bzw. `request.get_json(silent=True) or {}`.
  - Ruft `mw_metadata.resolve_movie_artwork_candidates(tmdb_id=tmdb_id, query=query, year=year)` auf und gibt das JSON mit Status `200` zurück.
  - Fängt `mw_metadata.MetadataKeyMissing` (`400` oder `503` mit `{"error": str(e)}`), `mw_metadata.MetadataProviderUnavailable` (`503` mit `{"error": str(e)}`) und allgemeine Exceptions (`502` mit `{"error": str(e)}`) sauber ab.

### 3. Frontend: Schritt 3 Artwork-Auswahl in `index.html`, `film_wizard.js`, `style.css` & `app.js` (E5-AK1, E5-AK2, E5-AK3)

1. **Markup in `gui/static/index.html` (`#mw-wizard-step-3`) UND synchron in `buildWizardDom` (`gui/static/js/film_wizard.js`):**
   - **Quellen- & Nachsuch-Leiste (`#mw-wizard-artwork-source-bar`, Option 2A):**
     - Zeigt links den aktuellen Bildquellen-Status `<span id="mw-wizard-artwork-source-info" class="mw-wizard-artwork-source-info">Bildquelle: TMDb</span>`.
     - Daneben ein optionales Treffer-Dropdown `<select id="mw-wizard-artwork-match-select" class="mw-wizard-select mw-wizard-artwork-match-select hidden" aria-label="TMDb-Film für Artwork wählen"></select>` (sichtbar wenn `matches.length > 1`) sowie ein kompaktes Suchfeld `<input type="text" id="mw-wizard-artwork-search-input" class="mw-wizard-input mw-wizard-artwork-search-input" placeholder="Anderen Filmtitel für TMDb-Bilder suchen..." aria-label="Filmtitel für TMDb-Bilder suchen">` + Button `<button type="button" id="mw-wizard-artwork-search-btn" class="btn btn-secondary btn-sm">Bilder suchen</button>`.
   - **3 Rollen-Tabs (`role="tablist" aria-label="Artwork-Rollen"`, Option 3A & E5-AK1):**
     - `<button type="button" id="mw-wizard-tab-poster" class="mw-wizard-tab active" role="tab" aria-selected="true" data-artwork-tab="poster">Poster (2:3)</button>`
     - `<button type="button" id="mw-wizard-tab-fanart" class="mw-wizard-tab" role="tab" aria-selected="false" data-artwork-tab="fanart">Fanart (16:9)</button>`
     - `<button type="button" id="mw-wizard-tab-logo" class="mw-wizard-tab" role="tab" aria-selected="false" data-artwork-tab="logo">Logo</button>`
   - **Aktionszeile je Rolle / Upload & Abwahl (Option 1A & 3A):**
     - Oberhalb des aktiven Rasters (oder pro Panel) eine kompakte Toolbar mit:
       - Button `<button type="button" id="mw-wizard-artwork-deselect-btn" class="btn btn-secondary btn-sm">Kein Bild für diese Rolle</button>` (schaltet die aktive Rolle explizit auf `"none"` / abgewählt; ist sie bereits `"none"`, zeigt der Button aktiv/hervorgehoben den Zustand an).
       - Verstecktes `<input type="file" id="mw-wizard-artwork-upload-input" class="hidden" accept=".jpg,.jpeg,.png,.webp">` + sichtbarer `<button type="button" id="mw-wizard-artwork-upload-btn" class="btn btn-secondary btn-sm">Eigenes Bild wählen…</button>` (öffnet den Dateidialog für die aktuell aktive Rolle; liest die Datei per `FileReader.readAsDataURL`, prüft Dateigröße `<= 15 MB` und `image/jpeg|png|webp`, fügt eine „Eigenes Bild“-Kachel an erster Stelle des aktiven Rollen-Grids ein und markiert sie als ausgewählt).
   - **3 Rollen-Panels (`role="tabpanel"`):**
     - `<div id="mw-wizard-artwork-poster" class="mw-wizard-artwork-panel active" role="tabpanel" aria-labelledby="mw-wizard-tab-poster"></div>`
     - `<div id="mw-wizard-artwork-fanart" class="mw-wizard-artwork-panel hidden" role="tabpanel" aria-labelledby="mw-wizard-tab-fanart"></div>`
     - `<div id="mw-wizard-artwork-logo" class="mw-wizard-artwork-panel hidden" role="tabpanel" aria-labelledby="mw-wizard-tab-logo"></div>`
   - **Sichtbare TMDb-Attribution im Fuß von `#mw-wizard-step-3` (E5-AK3):**
     - `<div id="mw-wizard-tmdb-attribution" class="mw-wizard-tmdb-attribution">`:
       - Enthält das offizielle kompakte TMDb-Badge als Inline-SVG mit `role="img" aria-label="TMDB"` (via `.innerHTML` in `buildWizardDom` eingefügt, **ohne** `createElementNS`!) und exakt den englischen Pflichttext:
         `This product uses the TMDB API but is not endorsed or certified by TMDB.`

2. **Auswahl-Zustandsmaschine & Lade-/Fehlerverhalten in `gui/static/js/film_wizard.js` (E5-AK1, E5-AK2):**
   - **Exakt ein Auswahl-Zustand je Rolle (`poster`, `backdrop`, `logo` — E5-AK1):**
     - Halte `artworkState` für die 3 Rollen (`poster`, `backdrop`, `logo`), jeweils mit:
       `{ mode: "auto" | "url" | "upload" | "none", url: "", thumbUrl: "", dataUrl: "", fileName: "", explicit: false }`
     - Beim Öffnen des Wizards (`open()`) oder Wechsel des Films in Schritt 1 (`selectMovieInWizard()`) wird `artworkState` auf `"auto"` (`explicit: false`), `artworkCandidatesLoadedForKey = ""` und `artworkSkipped = false` zurückgesetzt.
     - **Beim Betreten von Schritt 3 (`goToStep(3)`):**
       - Setze `artworkSkipped = false`, sobald der Nutzer in Schritt 3 aktiv interagiert oder mit „Weiter“ (`nextStep()`) aus Schritt 3 nach Schritt 4 geht; klickt der Nutzer hingegen in Schritt 3 auf „Überspringen“ (`skipBtn`), setze `artworkSkipped = true` und gehe zu Schritt 4 (bei `artworkSkipped === true` sendet `buildMovieBasePayload()` kein `artwork_overrides`, sodass der Standard-Auto-Download läuft).
       - Wenn für den aktuellen Film noch keine Kandidaten geladen wurden:
         - Bestimme `tmdbId`: Falls `successfulProviders.get("tmdb")` oder `selectedMovie?.provider === "tmdb"` eine numerische ID hat, nutze diese `tmdbId`.
         - Andernfalls (Option 2A: OFDb oder Manuell) nutze `query = nfoEditor.getValues().title || selectedMovie?.name || currentProjectName` und `year = nfoEditor.getValues().year || ""`.
         - Zeige während des Ladens Skeleton-Kacheln (`.mw-wizard-artwork-tile.loading`) im aktiven Panel.
         - Rufe `/api/artwork/candidates?...` über `fetchFn` ab.
         - **Initiale Vorauswahl nach erfolgreichem Abruf:**
           - Für jede Rolle (`poster` ← `data.posters`, `backdrop` ← `data.backdrops`, `logo` ← `data.logos`):
             - Solange der Nutzer für diese Rolle noch keine eigene Entscheidung getroffen hat (`!artworkState[role].explicit`):
               - Hat die Kandidatenliste mindestens 1 Bild, wird `candidates[0]` als vorausgewählt markiert (`mode: "url", url: candidates[0].url, thumbUrl: candidates[0].thumb_url`, Kachel erhält `.selected` + `aria-pressed="true"` + `✓`-Badge).
               - Ist die Kandidatenliste leer, bleibt die Rolle ohne Auswahl und zeigt eine Placeholder-Kachel `.mw-wizard-artwork-tile.empty` („Kein Poster/Fanart/Logo bei TMDb verfügbar“).
     - **Klick-Interaktion auf eine Bild-Kachel (`.mw-wizard-artwork-tile` als `<button type="button">`, E5-AK1):**
       - Klick auf eine **nicht ausgewählte** Kachel: wählt genau diese Kachel für die Rolle aus (`mode: "url"` bzw. `"upload"`, `explicit: true`), entfernt `.selected` / `aria-pressed="true"` von allen anderen Kacheln derselben Rolle → **exakt ein Auswahl-Zustand je Rolle**.
       - Klick auf die **bereits ausgewählte** Kachel (oder Klick auf `#mw-wizard-artwork-deselect-btn`): hebt die Auswahl auf und setzt die Rolle explizit auf Abwahl (`mode: "none", url: "", dataUrl: "", explicit: true`) — keine Kachel dieser Rolle ist mehr `.selected`!
     - **Fehler-Resilienz & Broken-Image-Fallback (E5-AK2):**
       - **API-Fehler beim Laden der Kandidaten:** Bricht Schritt 3 **nicht** ab (Weiter/Überspringen/Eigenes Bild bleiben voll bedienbar!). Rendert im Panel eine Placeholder-Fehlerkachel `.mw-wizard-artwork-tile.error` mit verständlicher Meldung und einem Kachel-eigenen Retry-Button (`.mw-wizard-artwork-retry-btn`, „Erneut laden“), der `loadArtworkCandidates({ force: true })` erneut anstößt. *(Hinweis: Wenn `fetchFn` in einem Legacy-Unit-Test `undefined` liefert, ebenfalls nur diese lokale Placeholder-Kachel in Schritt 3 rendern und nicht werfen.)*
       - **Einzelbild-Ladefehler (`error`-Event am `<img class="mw-wizard-artwork-image" loading="lazy" alt="...">`):** Markiert genau diese Kachel als `.mw-wizard-artwork-tile.error`, blendet einen Inline-Placeholder („Bild nicht ladbar“) + kleinen „Erneut versuchen“-Button in dieser Kachel ein (der `img.src` mit Cache-Bypass/Retry neu lädt), ohne die übrigen Kacheln oder Schritt 3 zu stören!
   - **Payload in `buildMovieBasePayload()` & Zusammenfassung in `renderSummary()` (Schritt 4):**
     - `basePayload.nfo_overrides` bleibt **unverändert** `{ movie: { ... } }`!
     - `basePayload.artwork_overrides`:
       - Wenn `artworkSkipped === true`: `artwork_overrides` **nicht** setzen (`undefined`).
       - Wenn `!artworkSkipped` und entweder (a) mindestens eine Rolle `explicit === true` hat (`"url"`, `"upload"` oder `"none"`) **oder** (b) `resolvedProvider !== "tmdb"` (z. B. OFDb/Manuell mit in Schritt 3 gefundenen TMDb-Kandidaten aus Option 2A):
         Füge `artwork_overrides` zum Rückgabe-Objekt von `buildMovieBasePayload()` hinzu, z. B.:
         ```js
         artwork_overrides: {
             poster: serializeRoleOverride("poster"),     // "auto" | "none" | { mode: "url", url } | { mode: "upload", data_url }
             backdrop: serializeRoleOverride("backdrop"),
             logo: serializeRoleOverride("logo"),
         }
         ```
       - Hat der Nutzer bei einem `tmdb`-Film in Schritt 3 hingegen nichts explizit geändert (oder Schritt 3 gar nicht besucht / übersprungen), lasse `artwork_overrides` weg, damit alle bestehenden Payload-Tests und der TMDb-Standardpfad 100 % unverändert bleiben!
     - Aktualisiere in `renderSummary()` (Schritt 4) die `Artwork:`-Zeile aussagekräftig (z. B. bei `artworkSkipped`: `"Übersprungen (Standard-Artwork)"`, bei individuellen Auswahlen/Abwahlen/Uploads eine kompakte Statuszusammenfassung wie `"Poster: TMDb · Fanart: Kein Bild · Logo: Eigenes Bild"` bzw. `"Standard-Artwork (TMDb)"` im unveränderten Auto-Modus).
     - Stelle für Tests an der Wizard-Instanz Hilfsmethoden bereit: `getArtworkState()`, `selectArtworkCandidate(role, indexOrUrl)`, `deselectArtworkRole(role)`, `setCustomArtworkUpload(role, dataUrl, fileName)` und `loadArtworkCandidates()`.

3. **Styling in `gui/static/style.css` (`grafiker.md` §3, alle 5 Themes):**
   - Ergänze die CSS-Klassen `.mw-wizard-artwork-source-bar`, `.mw-wizard-artwork-toolbar`, `.mw-wizard-artwork-panel`, `.mw-wizard-artwork-grid` (`grid-template-columns: repeat(auto-fill, minmax(150px, 1fr))` für Poster, `minmax(240px, 1fr)` für Fanart `16:9`, `minmax(180px, 1fr)` für Logo), `.mw-wizard-artwork-tile`, `.mw-wizard-artwork-tile.selected` (3px `var(--accent)` Ring + `.mw-wizard-artwork-check` mit `✓`), `.mw-wizard-artwork-tile.loading` (Skeleton-Pulse), `.mw-wizard-artwork-tile.empty`, `.mw-wizard-artwork-tile.error`, `.mw-wizard-artwork-image` (`object-fit: cover`, für Logo `object-fit: contain` auf kontrastierendem Surface-Hintergrund), `.mw-wizard-artwork-meta` (Sprach-Badge `DE`/`EN`/Auflösung) und `.mw-wizard-tmdb-attribution`.
   - Nutze **ausschließlich** bestehende CSS-Variablen (`var(--bg-surface)`, `var(--bg-input)`, `var(--bg-hover)`, `var(--border-glass)`, `var(--border-light)`, `var(--accent)`, `var(--accent-rgb)`, `var(--danger)`, `var(--text-main)`, `var(--text-muted)`, `var(--bg-base)`), keine hartcodierten Hex-Farben außer den offiziellen Markenfarben innerhalb des eingebetteten TMDb-Attribution-SVGs!

### 4. Cache-Buster & Tests
- **Cache-Buster:**
  - Hebe in `gui/static/index.html` `app.js?v=119` auf `app.js?v=120` und `style.css?v=63` auf `style.css?v=64` an.
  - Ziehe alle relativen ES-Modul-Importe in `gui/static/app.js` sowie in `gui/static/js/film_wizard.js` (`nfo_editor.js?v=120`, `format.js?v=120`, `preview_render.js?v=120`) konsistent auf `?v=120` nach (`tests/frontend/cache_busting.test.js` prüft dies!).
- **Backend-Tests (`tests/test_artwork_download.py`, neu, `unittest.TestCase` — OHNE Pflicht-Import von `pytest`, da im Gate-A2-Container nur `unittest` verfügbar ist!):**
  1. **`fetch_tmdb_image_candidates` vs. `fetch_tmdb_images` (E5-AK1):** Prüft, dass `fetch_tmdb_image_candidates("movie", "603")` Listen je Rolle (`posters`, `backdrops`, `logos`) sortiert nach `de -> neutral -> en` mit `url` (`original`) und `thumb_url` (`w185`/`w300`) liefert, während `fetch_tmdb_images("movie", "603")` unverändert Einzel-URL-Strings zurückgibt.
  2. **`resolve_movie_artwork_candidates` & `/api/artwork/candidates` (Option 2A):** Prüft sowohl direkten Abruf mit `tmdb_id` als auch automatische TMDb-Titelsuche (`query="Matrix"`, `year="1999"`), wenn keine `tmdb_id` vorliegt (z. B. OFDb/Manuell).
  3. **Download mit Retry & Integritätsprüfung + Abwahl + SSRF-Schutz (E5-AK2 & Option 3A):**
     - Prüft, dass `apply_movie_artwork_overrides` / `generate_movie_nfo(..., artwork_overrides=...)` ein gewähltes TMDb-Bild über `_download_with_retry` lädt (inkl. Erholung nach transientem Fehler beim 1. Versuch und Ablehnung von korrupten `Content-Length`-Teildownloads ohne verwaiste Zieldatei).
     - Prüft, dass `mode: "none"` bei `generate_movie_nfo` sowohl den Standard-Download als auch den `poster_path`/`backdrop_path`-Fallback zuverlässig unterdrückt.
     - Prüft, dass Nicht-TMDb-URLs (z. B. `http://127.0.0.1/...`, `https://evil.example/poster.jpg`, Pfad-Traversal `..`) strikt mit Fehler abgewiesen werden (SSRF-Schutz).
  4. **Lokaler Bild-Upload (Option 1A):** Prüft, dass gültige JPEG-, PNG- und WebP-Data-URLs anhand ihrer Magic Bytes erkannt und gespeichert werden, während gefälschte Dateien (z. B. HTML/SVG mit `data:image/jpeg;base64,...`) oder übergroße Payloads abgewiesen werden.
  5. **OFDb-Integration in `processor.py`:** Prüft, dass `artwork_overrides` auch beim OFDb-/Manuell-Filmimport angewendet werden.
- **Frontend-Tests (`tests/frontend/film_wizard_artwork.test.js`, neu, `node:test`):**
  1. **E5-AK1:** Prüft, dass Schritt 3 die Kandidatenlisten je Rolle (`Poster`, `Fanart`, `Logo`) rendert, Tab-Wechsel (`aria-selected`, sichtbares Panel) funktioniert, initial pro Rolle maximal 1 Kachel vorausgewählt ist, Klick auf eine andere Kachel exakt 1 Auswahlzustand je Rolle herstellt und erneuter Klick (bzw. „Kein Bild für diese Rolle“) die Rolle auf `"none"` abwählt und in `buildMovieBasePayload().artwork_overrides` übergibt.
  2. **Option 1A (Eigenes Bild):** Prüft `setCustomArtworkUpload` / Datei-Upload-Flow für eine Rolle und Übergabe als `{ mode: "upload", data_url: ... }` in `artwork_overrides`.
  3. **Option 2A (OFDb / Manuell → TMDb-Bildsuche):** Prüft, dass bei einem OFDb- oder manuellen Film beim Wechsel nach Schritt 3 automatisch `/api/artwork/candidates` mit `query` + `year` angefragt wird (ohne `provider`/`movie_id` des NFO-Payloads zu verstellen) und eine manuelle Nachsuche über `#mw-wizard-artwork-search-btn` die Kandidaten aktualisiert.
  4. **E5-AK2 (Fehler-Placeholder + Retry):** Prüft sowohl API-Fehler beim Kandidaten-Abruf als auch `error`-Events einzelner `<img>`-Kacheln: Es erscheint eine Placeholder-Kachel mit funktionierendem Retry-Button, und Schritt 3 bricht nicht ab (Weiter/Überspringen bleibt bedienbar).
  5. **E5-AK3 (TMDb-Attribution):** Prüft sowohl in `gui/static/index.html` als auch im dynamischen Wizard-DOM, dass `#mw-wizard-tmdb-attribution` das TMDb-SVG-Logo (`role="img"`) und den exakten Pflichtsatz `"This product uses the TMDB API but is not endorsed or certified by TMDB."` sichtbar enthält.
- **Autoritatives Testkommando für den Gate-A2-Lauf:**
  `python3 -m unittest tests/test_artwork_download.py tests/test_metadata_retry.py tests/test_provider_fields.py tests/test_inbox_movie_overrides.py && node --test tests/frontend/*.test.js`

## Nicht bauen
- Kein Fanart.tv, kein TVDB-Artwork, kein OFDb-Cover-Scraping (D2 = Option A: nur TMDb + eigener lokaler Datei-Upload).
- Keine freie Eingabe beliebiger externer Bild-URLs (SSRF-Vermeidung).
- Keine Änderung an `fetch_tmdb_images()` (Signatur und Rückgabe bleiben unangetastet).
- Keine Änderung am Serien- oder Doku-Pfad oder am NFO-Agenten (`#modal-nfo-agent`).
- Noch keine Mehrfachauswahl / Filmreihen-Queue (das ist Etappe E6).
