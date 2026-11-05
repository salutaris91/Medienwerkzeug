# Rohoutput — advocatus (Akt 1, Planungs-Session "Ähnliche Titel", 2026-11-05)

> Beitrag ungekürzt archiviert (Transparenz-Pflicht). Eingabe-Brief: identischer
> Kontextbrief (Wunsch von Alex, verifizierter Ist-Zustand, Vorschläge A/B/C) wie in
> `synthese.md` beschrieben; Aufgabe an den advocatus: systematische Risikoprüfung
> (Performance, False Positives, XSS, Architektur-Duplikation, Fehlerpfade,
> media_type-Abdeckung) mit Datei-/Zeilenbelegen. Schreibgeschützter Agent.

---

# Risikoprüfung — Plan "Ähnliche Titel vor finaler Verarbeitung" (Akt 1)

Ich habe die benannten Pfade gelesen und die Behauptungen gegen den Code geprüft. Die Kernbehauptungen stimmen; im Detail weiche ich an zwei Stellen ab (markiert). Findings nach Schwere, dann A/B/C-Urteil, dann offene Fragen.

---

## Findings nach Schwere

### [kritisch] 1. XSS über NAS-Fremdordnernamen — besteht bereits, wird von A/B vererbt und vervielfacht

**Beleg:** `gui/static/app.js:10371` rendert den Namenskonflikt per `innerHTML` mit roher Interpolation:

```js
mText.innerHTML = `Der Zielordner auf dem NAS heißt <strong>"${data.show_name_mismatch.nas_name}"</strong> ...`;
```

`nas_name` kommt aus `find_existing_series_folder_by_id` → `os.listdir(destination_path)` (`gui/core/series_helper.py:9`), also aus einem Ordner, den der Nutzer NICHT selbst erzeugt hat (NAS, ggf. von Fremden befüllt). `escapeHTML` **existiert** (`gui/static/app.js:245-253`) und wird an anderer Stelle im selben Modal sogar verwendet (`app.js:10415-10416` für `createCheckbox`), aber genau hier **nicht**. Das ist ein realer, heute schon offener XSS-Vektor: Ein NAS-Ordner mit dem Namen `<img src=x onerror=…>` oder `<script>…` wird beim Öffnen des Preview-Modals im Browser ausgeführt.

**Bedeutung für den Vorschlag:** Vorschlag A/B liefert `similar_existing:[{name,score}]` — eine Liste von Ordnernamen aus NAS **und Outbox**, also dieselbe Fremddatenquelle, nur breiter (auch `/Filme` statt nur Serien). Wird das Feld nach demselben Muster wie `show_name_mismatch` gerendert (was naheliegt, da der Vorschlag explizit "nach Muster show_name_mismatch" sagt), entsteht derselbe XSS-Pfad an einer zusätzlichen Stelle, mit mehr Einträgen. **Pflicht bei Umsetzung:** `escapeHTML()` für jeden `name` (und `score`), nie `innerHTML` mit Rohwerten. Dies ist kein "kosmetischer" Punkt, sondern der einzige echte Sicherheitsbefund des Plans.

### [kritisch] 2. Hängendes SMB-Mount blockiert den Preview-Request ohne Timeout

**Beleg:** Der Film-Zweig arbeitet direkt mit `os.path.exists(nas_path)` (`queue_api.py:273`) und `os.listdir(nas_path)` (`queue_api.py:355`). Es gibt **keinen** Timeout-Wrapper und **keinen** Hintergrund-Thread. `ensure_nas_mounted` (`gui/core/transfers.py:325-412`) hat zwar begrenzte Timeouts (Tailscale `subprocess timeout=5`, Socket `settimeout(0.5)`, osascript `timeout=10`), aber diese Funktion wird im Film-Zweig **gar nicht** aufgerufen — und sie schützt auch nicht vor dem eigentlichen Problem: Ist das Mount gemountet, aber das Netzwerk getrennt („stale mount"), hängt `os.listdir`/`os.path.exists` im Kernel-D-State (I/O-Wait) **ohne** Python-seitiges Timeout — das kann Minuten dauern und blockiert einen Flask-Worker.

**Bedeutung:** Vorschlag A erweitert `os.listdir` vom einen Zielordner (`nas_path`) auf den **gesamten Kategorieordner** (`/Filme` mit z. B. 5.000 Einträgen) bei **jedem** Lauf. Damit wird aus dem heute seltenen Hänger (nur bei exakter Namenskollision) ein Standardpfad bei jedem „Jetzt final verarbeiten". Es gibt keinen Ausweg außer: (a) Timeout/Thread kapseln, (b) auf den bestehenden asynchronen Scan/Cache zu setzen (siehe Finding 5), oder (c) das Feature gar nicht synchron im Preview-Request zu berechnen.

### [wichtig] 3. Latenz wächst für JEDEN Lauf — auch ohne Treffer

**Beleg Präzedenzfall:** `find_existing_series_folder_by_id` iteriert heute schon **synchron** über alle Serienordner und liest pro Ordner die `tvshow.nfo` (`series_helper.py:9-22`, aufgerufen in `queue_api.py:767`). Das ist bereits im Serien-Zweig ein potenzieller Latenz-/I/O-Brocken über SMB. Der Vorschlag A verlangt Vergleich gegen **alle** Ordnernamen im Ziel (NAS+Outbox) bei jedem Preview; Vorschlag B zusätzlich „Jahr", wofür pro Ordner entweder ein NFO gelesen oder das Jahr aus dem Namen geparst werden muss.

**Bedeutung:** `os.listdir` auf 5.000 Einträge über SMB ist messbar; NFO-Lesen pro Ordner (wie in `series_helper.py`) vervielfacht das. Die Vorschau wird **für jeden Lauf** langsamer, nicht nur bei Treffern. Es existieren bereits Caches, die der Plan nicht nutzt: `health_cache.py` (mtime-basierter Ordner-Cache, `SCAN_VERSION=5` Zeile 10) und `duplicates.py` (`duplicate_scan_cache.json`, Zeile 31) sowie die gemeinsame Enumerations-Grundlage `walk_nas_categories` (`transfers.py:1023`). Ein neuer synchroner Voll-Scan im Preview-Request wäre die **dritte** Enumerations-Logik ohne Cache.

### [wichtig] 4. False Positives: Franchise ≠ Duplikat, und `calculate_match_score` ist dafür nicht gebaut

**Beleg zur Funktion:** `calculate_match_score` (`mw_metadata.py:2551-2611`) ist Wortmengen-Jaccard + Bonus + Jahresstrafe. Es ist erkennbar für **Such-API-Ranking** gebaut: Es entfernt `[Land]`-Klammern (`re.sub(r"\[.*\]", …)`, Zeile 2570) und `(Jahr)` (`re.sub(r"\(\d{4}\)", …)`, Zeile 2571) — beides Muster, die ein *Suchtreffer* trägt, ein *NAS-Ordnername* aber typischerweise nicht (Ordnernamen sind meist schon clean, z. B. `X-Men (2000)`).

**Konkrete False-Positive-Fälle:**
- **„X-Men" vs „X-Men 2"**: Wortmengen `{x, men}` vs `{x, men, 2}` → Jaccard **0.667**. Zwei verschiedene Filme, gleicher Wortstamm → hoher Score, fälschlich „Duplikat"-Verdacht. Genau das Beispiel aus dem Wunsch zeigt, dass der Algorithmus Franchise-Titel als Treffer meldet.
- **„Der Herr der Ringe: Die Gefährten" vs „…: Die zwei Türme"**: große Wortüberlappung → hoher Score, verschiedene Filme.
- **„Der Hobbit" vs „Der Herr der Ringe"**: `{der, hobbit}` vs `{der, herr, ringe}` → Jaccard **0.25** — der verwandte Fall *ohne* gemeinsamen Wortstamm rutscht durch, während der Stammgleiche alarmiert. Die Jahresstrafe −1.5 (`mw_metadata.py:2605-2609`) greift **nur, wenn beide Seiten ein Jahr tragen** (`if q_year and res_year:`). „Film" vs „Film (2001)" bekommt also **keine** Strafe — gut — aber „X-Men (2000)" vs „X-Men 2 (2003)" bekommt sie und fällt auf `max(0.0, 0.667-1.5)=0.0` → derselbe Franchise-Fall wird je nach Jahresangabe mal gemeldet, mal nicht.

**Warn-Müdigkeit / Flackern:** Der Vorschlag nennt **keinen Schwellenwert**. `search_api.py:232` nutzt `> 0.35` für Episoden-Matching — ein Wert, der bei Filmtiteln mit nur 2–4 Wörtern extrem leicht überschritten wird. Da der Score bei jedem Lauf neu aus `calculate_match_score` berechnet wird (float, keine Stabilität garantiert), wandern Grenzfälle knapp über/unter die Schwelle. Erscheint die Box „Du hast schon …" bei jedem zweiten Lauf, wird sie ignoriert — das Feature verfehlt sein Ziel (Alex sieht den echten Doppelten nicht mehr).

### [wichtig] 5. Architektur: dritte Ähnlichkeits-Implementierung, Duplikation bestehender Mechanismen

**Belege für die bereits vorhandenen, sich überlappenden Mechanismen:**
- `calculate_match_score` (Such-Ranking, Jaccard + Boni + Jahresstrafe) — `mw_metadata.py:2551`.
- `duplicates._titles_match` (Jaccard-Schwelle 0.4 für Episodentitel *innerhalb derselben Show*) — `duplicates.py:86-98`.
- `normalize_series_name` / `get_matched_series_name` (exakter normalisierter Namensvergleich) — `helpers.py:236-266`.
- `find_existing_series_folder_by_id` (exakter ID-Abgleich via `mw_showid`/`mw_provider`) — `series_helper.py:5-33`.

**Bedeutung:** A/B führt `calculate_match_score` einem **neuen Zweck** zu (Bibliotheks-Vergleich), für den es nicht konzipiert ist, und schafft damit effektiv eine dritte Semantik von „Ähnlichkeit". `resolve_series_folder_name` (`series_helper.py:35-77`) macht bereits ID-Match → Outbox-Match → Fuzzy-Match; der neue Hinweis dupliziert diese Kette auf Namensebene. **Wartungsfolge:** Zwei Jaccard-Schwellen (0.4 in duplicates, künftig X in A) und zwei Normalisierungen (`normalize_umlauts` in mw_metadata vs. `normalize_series_name` in helpers) driften auseinander; ein Tuning an einer Stelle wirkt nicht an der anderen.

### [wichtig] 6. Abdeckung: doku/anime/YouTube/Mehrfilm fallen durch

**Beleg:** `handle_api_preview_process` kennt nur die Zweige `if media_type == "movie"` (`queue_api.py:125`) und `elif media_type == "tv"` (`queue_api.py:365`). Es gibt aber real die Werte `doku` und `anime`, die `project_api.py` setzt (`project_api.py:1425-1474`). Diese laufen in **keinen** der beiden Zweige → weder heutige Warnungen noch ein künftiger similar-Hinweis greifen. Die YouTube-Route sendet `media_type: "youtube"` und bei Modus „movie" `movie_id`/`movie_name` (`app.js:5125-5151`) — auch das erreicht den Film-Zweig nicht, obwohl dort faktisch ein Film mit Namen verarbeitet wird.

**Bedeutung:** Der Vorschlag muss explizit definieren, welche `media_type`-Werte abgedeckt sind. Sonst entsteht ein Feature, das bei Dokumentationen/Anime/YouTube-Filmen stillschweigend nichts tut — ein „false sense of security". Zusätzlich ist der Film-Zweig auf **ein** Projekt = **ein** Film ausgelegt (`main_video` = größte Datei, Rest → Sample/Junk, `queue_api.py:188-208`); bei Mehrfilm-Projekten ist „der ähnliche Titel" nicht eindeutig definiert.

### [kosmetisch] 7. Fehlerpfade im Detail

- **Unicode-Normalisierung fehlt:** `calculate_match_score` macht nur Umlaut-Ersetzung `ä→ae, ß→ss` (`mw_metadata.py:2575-2579`), **keine** NFC/NFD-Normalisierung. macOS/NAS-Dateisysteme liefern häufig NFD (dekomponiert, `u + combining diaeresis`); dann matcht „ü" nicht → False Negatives. (`read_nfo_metadata` liest mit `errors='ignore'`, `nfo_helper.py:110`, und hat try/except + Regex-Fallback, `nfo_helper.py:157-193` — einzelne kaputte NFOs werden sauber übersprungen; das ist solide.)
- **Payload-Größe:** 5.000 Ordnernamen + Scores + (B:) Jahre ≈ mehrere 100 KB JSON pro Preview — verkraftbar, aber unnötig, wenn es einen Cache gäbe. Kein Cap auf Trefferanzahl; eine leere `similar_existing`-Liste sollte bewusst „kein Hinweis" bedeuten und nicht die Box mit 0 Treffern öffnen.
- **Score-Serialisierung:** `score` als float (z. B. 0.6666667) in der UI anzeigen = unschön; gerundet + mit Bedeutung versehen (sonst wirkt „0.67" beliebig).

---

## A/B/C — Risikourteil

**C (eigener Bestätigungsdialog) — korrekt verworfen.** Ein zusätzlicher blockierender Dialog vor „Jetzt final verarbeiten" erzeugt Reibung, ohne das eigentliche Risiko (falsche *Einschätzung*) zu lösen. Nicht blockierend ist hier fachlich richtig — ein Hinweis darf nicht den Prozess anhalten, weil er definitionsgemäß unscharf ist.

**A (nicht-blockierender Hinweis) — machbar, aber die beiden kritischen Findings (XSS, hängendes Mount) müssen zwingend vorab gelöst werden.** Die Idee ist als *Hinweis* harmlos und fachlich vertretbar. Die Risiken liegen nicht in „blockiert es?", sondern in: (1) ungefiltertes `innerHTML` mit Fremdnamen, (2) synchronem Voll-Scan über SMB ohne Timeout/Thread, (3) False-Positive-Flut durch Jaccard auf Franchise-Titeln. **Das größte inhaltliche Problem:** Namens-Jaccard kann „Franchise" nicht von „Duplikat" unterscheiden — und genau die Unterscheidung ist der Kern des Wunsches („X-Men" vs. „X-Men 2" sind *verschiedene* Filme, die Alex gerade NICHT als Doppelten markiert sehen will, sondern als „schon da, aber anderer Teil"). Mit `calculate_match_score` liefert A also regelmäßig das Signal, das es nicht liefern soll.

**B (A + Jahr + Franchise-Gruppierung) — deutlich höheres Risiko, geringer Zusatznutzen ohne neue Datenquelle.** „Jahr" erfordert NFO-Lesen pro Ordner (Latenz über SMB, siehe Finding 3) oder Jahr-Parsing aus Ordnernamen (unzuverlässig bei Altbestand ohne Jahres-Suffix). „Franchise-Gruppierung" braucht **Collection-/Franchise-Daten**, die lokal nicht vorliegen — `mw_metadata` hat kein Franchise-Feld, `read_nfo_metadata` liefert nur `title/year/mw_provider/mw_showid` (`nfo_helper.py:116-122`). Franchise-Gruppierung würde also Provider-API-Calls erzwingen → neue externe Abhängigkeit, Latenz, Rate-Limits, Fehlerpfade — genau die Klasse Risiko, die der Vorschlag eigentlich vermeiden will. B ist ohne eine zusätzliche Datenquelle (z. B. TMDB-Collection-ID im NFO) nicht sauber umsetzbar.

---

## Bewertung der Alternativ-Ideen (Risiken verringern / neu schaffen)

**ID-Abgleich über NFOs (verringert False Positives massiv, empfohlen als Primärsignal).** Für Serien existiert das bereits (`find_existing_series_folder_by_id`, `series_helper.py:5-33` via `mw_showid`/`mw_provider`). Für Filme wird `read_nfo_metadata` zwar aufgerufen (liefert `mw_provider`/`mw_showid`), aber im Film-Zweig **nicht** zum Abgleich genutzt — hier läge der präzise, billige Gewinn. Ein ID-Match ist *eindeutig* (kein Franchise-Problem) und beantwortet exakt „habe ich das schon?". **Restrisiko:** Altbestand ohne NFO/ID → False Negatives (wird nicht gemeldet, obwohl vorhanden). Namens-Ähnlichkeit taugt dann nur als *weiches Zusatzsignal*, klar getrennt von „echtes Duplikat (ID)".

**Jellyfin-API (verringert False Positives, schafft aber neue Risiken).** Das `media_server`-Setting dient heute **nur** Artwork-Regeln (`queue_api.py:691-693` nutzt `get_validator(server_type)`), es gibt keinen API-Client. Ein echter API-Client brächte exakte Duplikat-/Collection-Daten, aber: Secrets-Handling (API-Key in `.env`), externe Verfügbarkeit (Jellyfin down → Feature weg), Netzwerk-Latenz im Preview-Request, Auth-/Rate-Fragen. Das sprengt den Scope eines „Hinweises" deutlich und verschiebt das Projekt von „lokale Datei-Hinweise" zu „Medienserver-Integration". Nur sinnvoll, wenn Alex ohnehin eine Jellyfin/Emby-Anbindung plant.

**Index/Cache (eliminiert Latenz, schafft Invalidation-Risiko).** Ein Name→Pfad-Index (via `walk_nas_categories`, `transfers.py:1023`) würde die Per-Lauf-Latenz auf ~0 senken. **Neues Risiko = veralteter Cache:** Der bestehende `health_cache.py` zeigt mit `SCAN_VERSION=5` und dem Kommentar „Bump whenever …" (`health_cache.py:8-10`), wie mühsam Cache-Versionierung/Invalidierung hier bereits ist. Ein stale Index liefert False Negatives (gerade hinzugefügter Film wird nicht erkannt) — für einen *Duplikat-Hinweis* ist genau das der ungünstigste Fehlermodus. Wenn Cache, dann mit klarer Invalidierung (mtime des Kategorieordners) und *bewusst* tolerierter Aktualitäts-Lücke, nicht stillschweigend.

---

## Offene Fragen (müssen vor Umsetzung beantwortet sein)

1. **Schwellenwert und Semantik:** Ist der Hinweis als „mögliches Duplikat" oder als „Verwandter/Franchise-Titel" intendiert? Die zwei Ziele brauchen verschiedene Algorithmen (ID-Match vs. Namens-Jaccard). Welcher Score-Wert gilt, und wird er konfigurierbar?
2. **Welche `media_type`-Werte?** doku/anime/youtube/movie/tv — der aktuelle Handler deckt nur movie/tv ab; der Plan muss das explizit festlegen.
3. **Datenquelle für Jahr/Franchise in B:** Woher kommt das Jahr (NFO vs. Ordnername)? Woher die Franchise-Gruppierung (lokal nicht vorhanden)?
4. **Synchron oder Cache?** Live-Scan pro Preview (Latenz, Hänger-Risiko) oder Index/Cache (Invalidierung)? Wer baut/invalidiert den Index?
5. **Kategorien getrennt?** „Filme" und „Serien" gemeinsam oder getrennt vergleichen? Outbox einbeziehen (im Film-Zweig heute ungeprüft, `queue_api.py` Film-Zweig greift nicht auf `outbox_root` zu)?
6. **XSS-Fix-Ownership:** Wird der bestehende `innerHTML`-Fehler in `app.js:10371` im selben Schritt behoben (Pflicht), oder nur das neue Feld?

**Kurz-Empfehlung aus Risikosicht:** Primärsignal über **NFO-ID-Abgleich** (präzise, lokal vorhanden, geringe Latenz bei bestehendem Serien-Mechanismus), Namens-Ähnlichkeit nur als sekundärer, klar beschrifteter „evtl. verwandt"-Hinweis, **und** beides frühestens nach Behebung der zwei kritischen Punkte (XSS-Escaping, Timeout/Thread für NAS-Zugriff). C bleibt verworfen.
