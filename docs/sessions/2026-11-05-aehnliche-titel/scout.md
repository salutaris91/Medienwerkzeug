# Rohoutput — scout (Akt 1, Planungs-Session "Ähnliche Titel", 2026-11-05)

> Beitrag ungekürzt archiviert (Transparenz-Pflicht). Eingabe-Brief: identischer
> Kontextbrief (Wunsch von Alex, verifizierter Ist-Zustand, Vorschläge A/B/C) wie in
> `synthese.md` beschrieben; Aufgabe an den scout: Bewertung A/B/C, eigene Ideen,
> 12-Monats-Visionen. Schreibgeschützter Agent, kein Code, keine Git-Operationen.

---

## 1) Bewertung der Vorschläge A, B, C

**A) Warnbox im Vorschau-Dialog nach Muster show_name_mismatch**
Nutzen: Sofort sichtbar im bestehenden UI, blockiert den Workflow nicht, nutzt das etablierte Muster der gelben Warning-Box (index.html:2569-2579). Risiko: `calculate_match_score` (mw_metadata.py:2551) liefert Jaccard-ähnlichkeit über Wörter — bei kurzen Titeln wie "X-Men" vs. "X-Men: Zukunft" ist der Score hoch, bei "Der Pate" vs. "Der Pate: Teil II" aber auch. False Positives sind wahrscheinlich, wenn der Schwellenwert zu niedrig liegt. Machbarkeit: Hoch, `walk_nas_categories` (transfers.py:1023) liefert alle Ordner, `read_nfo_metadata` (nfo_helper.py:105) liest Titel/Jahr — ein zusätzlicher Loop im preview_process-Endpoint ist trivial.

**B) Wie A plus Jahr und Franchise-Gruppierung**
Nutzen: Jahr als zweites Kriterium erhöht die Trefferqualität massiv (gleicher Name + gleiches Jahr = sehr wahrscheinlich identisch). Franchise-Gruppierung ("Du hast X-Men 1, 2, 3, 5") ist der eigentliche Mehrwert — Alex sieht nicht nur "ähnlich", sondern "gehört zur selben Reihe". Risiko: Franchise-Erkennung erfordert entweder TMDb-API-Calls (Rate Limiting, Latenz) oder ein lokales Mapping (Pflegeaufwand). Machbarkeit: Mittel — Jahr ist trivial (steht schon im NFO), Franchise braucht entweder `belongs_to_collection` aus TMDb oder manuelle Gruppen-Definition in settings.json.

**C) Eigener Bestätigungsdialog vor dem Knopf**
Nutzen: Zwingt zur bewussten Entscheidung, verhindert versehentliche Duplikate. Risiko: Unterbricht jeden Lauf — bei bewussten Duplikaten (z.B. Alex will explizit eine 4K-Remaster-Version neben der 1080p behalten) nervt der Dialog. Machbarkeit: Hoch, aber UX-Problem: Der Dialog müsste "Abbrechen"/"Trotzdem verarbeiten"/"Details zeigen" anbieten, was den Footer (index.html:2618-2624) aufbläht. **Verworfen** — der Hinweis im Preview-Dialog (A/B) reicht, die Entscheidung bleibt bei Alex.

---

## 2) Eigene Ideen

### Idee 1: ID-basierter Abgleich über NFOs statt Namen
**Was:** Statt `calculate_match_score` auf Ordnernamen zu wenden, wird `mw_showid` + `mw_provider` aus allen tvshow.nfo/movie.nfo gelesen und mit der aktuellen `show_id`/`movie_id` abgeglichen (app.js:4542-4543 liefert die ID schon im Payload).
**Besser:** Exakt, keine False Positives durch Namensähnlichkeit. "X-Men (2000)" und "X-Men: Der erste Kontakt" haben unterschiedliche TMDb-IDs — kein Problem.
**Kostet:** Einmaliger Loop über alle NAS-Ordner pro Preview (ähnlich `find_existing_series_folder_by_id`, series_helper.py:5-33). Bei 2000 Filmen ca. 2000 NFO-Lesevorgänge — mit Caching (health_cache.py:16) vertretbar.
**Ersetzt/ergänzt:** Ersetzt A bei ID-verfügbaren Medien (TMDb/TVDb). Ergänzt A bei Mediathek/YT-DLP-Content (keine ID).

### Idee 2: Jellyfin/Emby/Plex-API abfragen
**Was:** Statt NAS-Dateisystem zu scannen, wird die Bibliothek des konfigurierten Media-Servers per API abgefragt. `settings.media_server` existiert schon (health.py:1062), aber es gibt keinen API-Client im Codebase.
**Besser:** Nutzt die tatsächlich indexierte Bibliothek, inkl. Metadaten, Poster, Collections. Jellyfin/Emby haben `/Items?SearchTerm=X-Men` — kein lokaler Scan nötig.
**Kostet:** API-Client implementieren (Auth, Endpoint-Discovery), Media-Server muss erreichbar sein. Fallback auf A/B wenn API nicht verfügbar.
**Ersetzt/ergänzt:** Ersetzt A/B komplett, wenn Media-Server vorhanden. Bibliothek: `jellyfin-apiclient-python` (offiziell), `pyemby` (inaktiv, aber forkbar), Plex `plexapi` (aktiv gepflegt, 1.5k Stars).

### Idee 3: Wiederverwendbarer Bibliotheks-Index aus health_cache
**Was:** Der Health-Scan (health.py) läuft bereits periodisch und baut `media_structure` auf (series + movies mit name, path, nfo_path, fsk, seasons). Dieser Cache wird um `mw_provider`/`mw_showid`/`mw_movieid` erweitert und als zentraler "Bibliotheks-Index" (`data/library_index.json`) bereitgestellt.
**Besser:** Kein erneuter Scan pro Preview — der Index wird beim Health-Scan aufgebaut und invalidiert. Preview-Request wird schneller.
**Kostet:** health_cache.py muss erweitert werden (neues Feld `media_metadata.ids`), Invalidierung bei Ordneränderungen. Ein neuer Endpoint `/api/library/search?q=X-Men` liefert Treffer.
**Ersetzt/ergänzt:** Ergänzt A/B — der Index ist die Datenquelle, A/B sind UI-Schichten darauf.

### Idee 4: Franchise-Erkennung via TMDb collection
**Was:** Wenn `movie_id` bekannt ist, wird bei TMDb `GET /movie/{id}` aufgerufen und `belongs_to.collection.id` extrahiert. Dann `GET /collection/{collection_id}` liefert alle Filme der Reihe.
**Besser:** Zeigt ganze Reihen ("Du hast X-Men 1, 2, 3, 5 — fehlt 4?"), nicht nur einzelne Treffer.
**Kostet:** 1-2 API-Calls pro Preview (TMDb Rate Limit: 40 Requests/Sekunde für kostenlose API). Caching in `data/collection_cache.json` (collection_id → [movie_ids]).
**Ersetzt/ergänzt:** Ergänzt B — Franchise-Gruppierung wird automatisch, ohne manuelle Pflege. Bibliothek: `tmdbsimple` (Python, 800 Stars, aktiv).

### Idee 5: "Du hast das schon"-Sammelreport unabhängig vom Vorschaulauf
**Was:** Eigener Hintergrund-Scan (analog duplicates.py:160), der periodisch alle Outbox-Downloads gegen die NAS-Bibliothek prüft und eine "Duplikat-Kandidaten"-Liste in `data/similar_titles_report.json` schreibt. UI zeigt Badge im Sidebar ("3 mögliche Duplikate").
**Besser:** Proaktive Info, nicht reaktiv im Preview. Alex sieht den Report, bevor er überhaupt auf "Verarbeiten" klickt.
**Kostet:** Eigener Hintergrund-Thread (analog health.py:1038), eigener UI-Ort (Sidebar-Badge + Modal).
**Ersetzt/ergänzt:** Ergänzt A/B — der Report ist unabhängig, A/B sind kontextbezogen im Preview.

### Idee 6: Prüfung schon VOR der Zielauswahl im Suchschritt
**Was:** Wenn Alex im Such-Dialog (nicht Preview) eine Serie/Film auswählt, wird sofort geprüft, ob ähnliche Titel in der Bibliothek existieren. UI zeigt unter dem Suchfeld: "Ähnlich: X-Men (2000), X-Men: Zukunft (2014)".
**Besser:** Früher Hinweis, bevor Alex sich festlegt. Verhindert, dass er erst den Preview-Dialog öffnet und dann merkt, dass es Duplikate gibt.
**Kostet:** UI-Änderung im Such-Workflow (app.js, Such-Endpoint), nicht im Preview.
**Ersetzt/ergänzt:** Ergänzt A — Prüfung wandert nach vorne, Preview zeigt nur noch Bestätigung.

### Idee 7: Normalisierung von Jahr/Auflösung/Release-Tags
**Was:** `clean_search_query` (mw_metadata.py:2500) strippt schon Release-Tags (1080p, x264, German, Editionen). Diese Funktion wird konsequent auf NAS-Ordnernamen UND Metadaten-Namen angewendet, bevor `calculate_match_score` läuft.
**Besser:** Sauberer Vergleich, weniger False Positives. "X-Men (2000) [1080p]" wird zu "X-Men", "X-Men: Der erste Kontakt (2011)" wird zu "X-Men: Der erste Kontakt".
**Kostet:** Trivial — `clean_search_query` existiert, muss nur aufgerufen werden.
**Ersetzt/ergänzt:** Ergänzt A — verbessert die Qualität der Namensähnlichkeit.

---

## 3) Visionen: Was könnte das in 12 Monaten sein?

**Vision 1: Intelligente Bibliotheks-Engine**
Zentraler Index aller Medien (NAS + Outbox + Cloud), ID-basiert (TMDb/TVDb/IMDb), mit Franchise-Gruppierung, Query-API für alle Features (Preview, Suche, Health, Duplikate, Similar-Titles). Kein Scan mehr pro Feature — der Index ist die Single Source of Truth. UI zeigt "Deine Bibliothek: 1.247 Filme, 89 Serien, 12 Franchises" mit Drill-Down.

**Vision 2: Proaktive Duplikat-Warnung**
Hintergrund-Scan läuft permanent (fswatch/inotify auf Outbox), warnt sofort beim Download/Import ("Achtung: X-Men (2000) ähnelt 'X-Men: Der erste Kontakt (2011)' — wirklich herunterladen?"). Integration in arrs (Radarr/Sonarr) via Webhook, nicht erst im Preview.

**Vision 3: Media-Server-Integration als Single Source of Truth**
Jellyfin/Emby/Plex als primäre Quelle, Medienwerkzeug nur noch Import/Export. Bibliotheks-Index wird aus Media-Server-API gebaut, nicht aus NAS-Scan. Preview-Request fragt Jellyfin "Hast du X-Men?", nicht das Dateisystem. Medienwerkzeug wird zum "Kurátor", nicht zum "Verwalter".

---

## 4) Was ich am Code überprüft habe / Annahmen

**Überprüft:**
- Preview-Modal-Struktur (index.html:2549-2626): Warning-Boxen für season-warning und show_name_mismatch existieren, Footer mit "Jetzt final verarbeiten" (Zeile 2621).
- Frontend-Logik (app.js:10253-10402): `openPreviewModal()` rendert show_name_mismatch mit `innerHTML` (Zeile 10371), Buttons "NAS-Name übernehmen"/"Metadaten-Name verwenden".
- Backend TV-Zweig (queue_api.py:702-785): Staffel-Warnung (702-763), show_name_mismatch (764-785) über `find_existing_series_folder_by_id` (series_helper.py:5-33) — prüft nur NAS-Ordner via tvshow.nfo mit `mw_showid`/`mw_provider`.
- Backend Film-Zweig (queue_api.py:125-363): Zielordner = NAS-Pfad aus sync_categories (Default /Filme), Kollisionswarnung (272-363) prüft NUR exakte Ordnername-Gleichheit (`os.path.exists(nas_path)`), sonst "Film existiert bereits". Outbox wird NICHT geprüft.
- Movie-Payload enthält `movie_id` + `provider` (app.js:4542-4543) — TMDb/TVDb-ID ist bekannt.
- Namensähnlichkeit: `calculate_match_score` (mw_metadata.py:2551-2611) mit Jaccard, Umlaut-Normalisierung, Jahresbonus/-malus.
- Duplikaterkennung (duplicates.py, search_api.py, nas_api.py) prüft nur SxxExx-Muster, NICHT Titel.
- Health-Scan (health.py) baut `media_structure` auf (series + movies mit name, path, nfo_path, fsk, seasons) — kein ID-Feld.
- NFO-Helper (nfo_helper.py:105-203) liest `title`, `year`, `mw_provider`, `mw_showid` — funktioniert für tvshow.nfo UND movie.nfo.
- `walk_nas_categories` (transfers.py:1023) liefert alle Top-Level-Film-/Serienordner.
- Settings-Feld `media_server` existiert, aber KEIN API-Client im Codebase.

**Annahmen:**
- TMDb-API ist kostenlos und rate-limited (40 Req/s) — für Idee 4 relevant.
- Jellyfin/Emby/Plex haben ähnliche APIs (SearchTerm-Query) — für Idee 2 relevant.
- `health_folder_cache.json` ist groß genug, um IDs aufzunehmen — für Idee 3 relevant.
- Outbox wird im Film-Zweig nicht geprüft (queue_api.py:125-363) — das ist ein Gap, den A/B schließen müssten.
