---
kind: feature-briefing
status: approved
approved_by: alex
approved_on: 2026-11-05
approval_quote: "Freigabe: Ja"
source: docs/sessions/2026-11-05-aehnliche-titel/synthese.md
---

# Feature Briefing — Ähnliche-Titel-Hinweis vor finaler Verarbeitung (Medienwerkzeug)

**Datum:** 2026-11-05 · **Akt:** 2 (Ausarbeitung nach FP1-Entscheidungen von Alex)
**Grundlage:** `docs/sessions/2026-11-05-aehnliche-titel/synthese.md` + Alex' FP1-Entscheid im Chat (2026-11-05): „Ja, genau so. Bauen, wie du jetzt empfohlen hast."
**plan-reviewer:** Runde 1 REVISE (8 Einwände, alle eingearbeitet, Archiv `plan-review-r1.md`) → Runde 2 **VERDICT: APPROVE** (3 kosmetische Punkte eingearbeitet, Archiv `plan-review-r2.md`). Status bleibt `draft`: Freigabe (FP2) gibt ausschließlich Alex.

---

## 1. Ziel & Scope

**Problem:** Beim Klick auf „Jetzt final verarbeiten" erkennt das Medienwerkzeug bei Filmen nur die exakte Ordnernamen-Kollision (`gui/api/queue_api.py:272-363`, verifiziert). Hat Alex denselben Film schon unter anderem Ordnernamen auf dem NAS (z. B. „X-Men - Der Film" vs. „X-Men (2000)"), gibt es keinen Hinweis → stiller Doppelt-Bestand.

**Ziel:** Nicht-blockierende Warnbox im Vorschau-Modal (`preview-modal`), nur für `media_type == "movie"`, nur NAS-Zielkategorie, in zwei Stufen:
- **Stufe 1 „Gleicher Film"** (deterministisch, sicher): ID-Abgleich.
- **Stufe 2 „Ähnlich / gehört evtl. dazu"** (großzügige Namens-Heuristik): Alex nimmt bewusst Fehlalarme in Kauf, um keine verpassten Treffer zu riskieren (FP1-Entscheid).

**Scope-Grenze:** Der Hinweis blockiert „Jetzt final verarbeiten" (`index.html:2621`, `btn-preview-execute`, verifiziert) **nie** und lässt die Vorschau **nie** fehlschlagen.

---

## 2. Verifizierte Code-Fakten (gegen den Worktree geprüft) und Korrekturen zur Synthese

Alle Zeilenangaben der Synthese wurden in Akt 2 selbst nachgeprüft und bestätigen sich: Kollisionswarnung `queue_api.py:272-363` ✓, Film-Zweig ab `:125` / TV-Zweig ab `:365` ✓, `show_name_mismatch` nur NAS (`:765-785`, Aufruf `:767` mit `nas_serien`) ✓, Staffelwarnung prüft NAS+Outbox (`:707-714`) ✓, `movie_id`+`provider` im Payload (`app.js:4542-4543`) und bereits im Backend gelesen (`queue_api.py:30-31`) ✓, `escapeHTML` (`app.js:245-253`) ✓, `read_nfo_metadata`-Label-Fehler (`nfo_helper.py:142-145` und Regex-Fallback `:180-183`) ✓, `<tmdbid>` im generierten Film-NFO (`mw_metadata.py:1188`) ✓, `calculate_match_score` (`mw_metadata.py:2551-2611`) ✓, `_is_genre_container` (`film_normalize.py:33`) ✓, YouTube-Route (`app.js:5124-5151`) ✓, Referenztests `tests/test_utils.py:3123/3665` ✓.

**Vier Korrekturen/Ergänzungen gegenüber der Synthese (in diesem Briefing maßgeblich):**

1. **XSS-Zeile 10371 betrifft BEIDE Felder.** Verifiziert: `app.js:10371` interpoliert `show_name_mismatch.nas_name` **und** `show_name_mismatch.metadata_name` unescaped in `innerHTML`. Der Fix muss beide Werte escapen, nicht nur `nas_name` (Synthese nannte nur `nas_name`).
2. **Provider `ofdb` existiert für Filme** (`search_api.py:515`) und wurde in der Synthese nicht als Skip-Provider genannt. Eine OFDB-ID ist **nicht** im TMDb-ID-Raum; ein Abgleich gegen `<tmdbid>` wäre ein Namespace-Fehler mit False-Positive-Risiko. **Stufe 1 nutzt eine Whitelist:** nur `provider in {"tmdb", "tmdb_movie"}` löst den ID-Abgleich aus; alle anderen (`ofdb`, `mediathek`, `ytdlp`, `ytdlp_movie` — real lesbar, `app.js:2887` —, `manual`, fehlend) ⇒ stiller Skip mit `log_message`. Die geschlossene Whitelist (statt Blacklist) fängt auch künftige Provider automatisch ab; `tmdb_movie` ist verifiziert ein realer Wert (`project_api.py:507`, `app.js:17376`).
3. **Film-NFOs auf dem NAS heißen nicht garantiert `movie.nfo`.** Verifiziert: MW-generierte Filmordner bekommen `<ordnername>.nfo` (`queue_api.py:263`), Bestand kann `movie.nfo` oder `<videostem>.nfo` tragen. Der etablierte Mechanismus `health.find_primary_nfo(folder, is_movie=True)` (`gui/core/health.py:~295-333`, Prio `<videostem>.nfo` → `movie.nfo`) löst das. **Pflicht:** Scan nutzt Kandidaten `movie.nfo`, `<ordnername>.nfo`, dann `find_primary_nfo`-Fallback; hartes Hardcoding auf `movie.nfo` ist verboten.
4. **Der `tmdbid`-Label-Fehler und seine bewusste Lösung.** Verifiziert: generierte Film-NFOs enthalten **kein** `<mw_provider>`/`<mw_showid>` (`mw_metadata.py:1172-1201`), also greift der Fallback `nfo_helper.py:142-145`, der `<tmdbid>` fälschlich als Provider `tmdb_tv` labelt. Der Payload-Provider lautet aber `tmdb`. **Lösung (FP1-Auftrag „bewusst lösen"):** Die neue Hilfsfunktion behandelt die ID-Räume `tmdb`/`tmdb_movie`/`tmdb_tv` beim Film-Abgleich als äquivalent (Vergleich nur der ID, Provider-Whitelist auf Payload-Seite). **Zusätzlich gilt NFO-seitig eine Label-Whitelist** (plan-review B4): nur Ordner, deren von `read_nfo_metadata` geliefertes Provider-Label in `{tmdb, tmdb_movie, tmdb_tv}` liegt (Groß-/Kleinschreibung egal), nimmt am ID-Vergleich teil; Ordner mit `tvdb`- oder sonstigem Label werden übersprungen + `log_message` — denn der `<tvdbid>`-Fallback hat Vorrang vor `<tmdbid>` (`nfo_helper.py:136-145`), und ein label-agnostischer Vergleich würde eine TVDB-ID gegen eine TMDb-Film-ID desselben Zahlenwerts matchen (derselbe Namespace-Fehler, den Korrektur 2 bei `ofdb` ausschließt). `read_nfo_metadata` wird **nicht** geändert — der TV-Pfad (`series_helper.py:27`) hängt an dieser Beschriftung; eine Änderung wäre eine ungetestete Regression im Serien-Flow.

**Weitere Akt-2-Verifikationen (Konventionen):**
- Endpoint ist doppelt gemountet: `/api/preview-process` und `/api/preview_process` (`queue_api.py:19-20`) — Tests können beide nutzen, Änderung betrifft nur die Response-Erweiterung.
- Cache-Buster-Konvention (verifiziert gegen `tests/frontend/cache_busting.test.js`): Der `app.js?v=`-Wert in `index.html:2760` (aktuell **104**) muss mit **allen 9** ES-Module-Imports in `app.js:1-9` (aktuell alle `?v=104`) exakt übereinstimmen; `style.css?v=51`/`utilities.css?v=1` (`index.html:9,13`) brauchen nur nicht-leere `?v=`. Regel für dieses Feature: **alle `?v=104` auf `105`** (index.html + 9 Imports); CSS-Versionen nur erhöhen, falls CSS-Dateien angefasst werden (im Plan nicht vorgesehen — die neue Box nutzt Inline-Stile nach Muster `index.html:2569`).

---

## 3. Kern-Features

### 3.1 Backend — neue Hilfsfunktion (`gui/core/similar_titles.py`, neu)

Zwei reine, einzeln testbare Funktionen + eine Konstante:

- `find_movie_folders_by_id(category_root, provider, movie_id, exclude_folder) -> list[dict]`
  - Whitelist-Gate (Fakten-Korrektur 2), rekursiver Scan max. 2 Ebenen (`<Kategorie>/<Film>` und `<Kategorie>/<Genre>/<Film>`), versteckte Ordner (`.`-Präfix) übersprungen, Zielordner selbst ausgeschlossen (Kollisionswarnung soll sich nicht doppeln).
  - NFO-Auflösung nach Fakten-Korrektur 3; ID-Vergleich nach Fakten-Korrektur 4 (Stringvergleich, wie `series_helper.py:21`) **mit NFO-seitiger Label-Whitelist** `{tmdb, tmdb_movie, tmdb_tv}` — `tvdb`/sonstige Labels ⇒ Ordner-Skip + Log (plan-review B4, AK19).
  - Jeder Lese-/Parse-Fehler ⇒ Ordner überspringen + `log_message` (Muster `series_helper.py:29-30`). Fehlendes/leeres `category_root` ⇒ leere Liste.
- `find_similar_movie_folders_by_name(category_root, movie_name, exclude_folders, limit=10) -> list[dict]`
  - **Nur Ordnernamen, keine NFO-Lektüre** (FP1-Entscheid).
  - Bereinigung beider Seiten: NFC-Normalisierung (`unicodedata.normalize("NFC")`, schließt Synthese-R6 günstig ein) → klein → Umlaute `ä→ae, ö→oe, ü→ue, ß→ss` → Klammerinhalte `(…)`, `[…]`, `{…}` komplett weg (trägt meist das Jahr) → Release-Tag-Tokens weg (feste kleine Liste: `1080p/2160p/720p/480p`-Muster, `x264`, `x265`, `bluray`, `dvd`, `remux`, `proper`, `repack`, `extended`, `uncut`, `german`, `multi`, `dual`) → Satzzeichen → Leerzeichen → Füllwort-Tokens weg (`der, die, das, ein, eine, one, the, a, an, und, and, of, &`) → Fortsetzungszahl-Tokens weg (Ziffern-Tokens `2..9` sowie römische Tokens `ii, iii, iv, vi, vii, viii, ix` als eigene Tokens). **Die Einzelbuchstaben `v` und `x` werden bewusst NICHT entfernt** — sie kollidern mit echten Titel-Tokens („X-Men") und würden sonst den Kernfall AK12 zerstören (plan-review B3).
  - **Trefferregel (strukturell, kein Schwellenwert):** mindestens ein **bedeutungstragendes gemeinsames Wort** (beide Tokenmengen enthalten dasselbe Wort, das nicht auf der Allgemeinwort-Liste steht) **ODER** der bereinigte Titel der einen Seite ist **String-Präfix** des bereinigten Titels der anderen Seite (fängt „Hobbit" vs. „Hobbits"). **Leer-Guard, gilt verbindlich für BEIDE Zweige** (plan-review B1): Sind nach der Bereinigung auf einer Seite keine bedeutungstragenden Wörter mehr übrig, gibt es **keinen** Treffer — auch nicht über die Präfixregel (ein leerer Titel wäre sonst Präfix jedes Strings = Total-Matcher; „Night" matcht dadurch „Nightcrawler" **nicht**). **Mehrstellige Zahlen-Tokens (`300`, `1917`, auch zweistellige wie „21") bleiben bedeutungstragend** und sind damit untereinander matchbar — bewusste Wahl für den echten Duplikat-Fall, Alex-Review-Punkt (Abschnitt 12 und `ALEX_ZUSAMMENFASSUNG.md` Entscheidungspunkt 2; plan-review B2).
  - `GENERAL_WORDS`: kleine Modul-Konstante, initial `{man, men, woman, women, love, night, day, big, little, new, world, story, part, teil}` — bewusst leicht änderbar (FP1-Entscheid „kleine, leicht änderbare Liste"). Ein Token zählt als „bedeutungstragend" genau dann, wenn es nicht in `GENERAL_WORDS` steht.
  - Sortierung: absteigend nach `overlap` mit **determinierter Formel** `overlap = max(Anzahl geteilter bedeutungstragender Wörter, 2 bei Präfixtreffer, sonst 0)` (Mischfälle werden nicht addiert; plan-review-r2 Punkt 3); bei Gleichstand alphabetisch. Cap `limit=10`.
- Rückgabeform je Treffer: `{"folder": <Ordnername>, "relative_path": <Pfad relativ zur Kategorie>}` (+ `overlap` nur bei Stufe 2). Nur Treffer, nie die Vollbibliothek.

### 3.2 Backend — Endpoint-Erweiterung (`gui/api/queue_api.py`, Film-Zweig)

- Am **Ende des `media_type == "movie"`-Zweigs, unmittelbar vor `elif media_type == "tv"` (`:365`)** — der Film-Zweig hat kein eigenes Return, das gemeinsame Return bei `:787` liegt hinter dem TV-Zweig und ist die einzige Platzierung, die den TV-Pfad unberührt lässt (plan-review C2). Scan-Basis ist `target_base` (bereits in `:152-155` aufgelöste Ziel-Kategorie, z. B. `NAS/Filme`), ausgeschlossen wird `clean_movie_name` (der geplante Zielordner selbst).
- Neue response-`preview`-Ergänzung, beide Keys immer vorhanden (leere Liste = kein Hinweis):

```json
"similar_existing": {
  "exact":   [{"folder": "X-Men - Der Film", "relative_path": "Action/X-Men - Der Film"}],
  "similar": [{"folder": "X-Men 2", "relative_path": "X-Men 2", "overlap": 2}]
}
```

- `exact` auf max. 5 Treffer gekappt (mehr ⇒ `log_message`), `similar` auf 10 (Cap der Funktion).
- Der gesamte Block läuft in `try/except`; jeder Fehler ⇒ `log_message` + leere Listen. **Bestehende Felder (`renames`/`subs`/`junk`/`destination`/`warning`) und der TV-Zweig bleiben unverändert** (`:365-787` tabu). Die bestehende exakte Kollisionswarnung (`:272-363`) wird nicht angefasst.

### 3.3 Frontend — Warnbox (`gui/static/index.html`, `gui/static/app.js`)

- Neue Box `#preview-similar-existing` zwischen der Mismatch-Box (`index.html:2568-2579`) und dem Zielverzeichnis (`:2581`), hidden per Default, Muster/Styles kopiert von der Mismatch-Box (Inline-Stile, Lucide-Inline-SVG `alert-triangle` — Bestand, ISC).
- **Stufe 1 oben, deutlich hervorgehoben** (z. B. rote/orange Kopfzeile „Diesen Film hast du schon auf dem NAS: …"); darunter Stufe 2 („Ähnliche Titel – gehören evtl. dazu: …"). Ein Ordner, der in Stufe 1 steht, erscheint nie zusätzlich in Stufe 2 (Dedup über `folder`-Name, im Backend: Stufe-2-Aufruf mit `exclude_folders` = Stufe-1-Treffer).
- Stufe 2: erste 5 sichtbar, Rest in eingeklapptem `<details>`/Toggle („Weitere N Treffer anzeigen").
- Rendering **ausschließlich** über `escapeHTML()` bzw. `textContent` (FP1-Sicherheitsvorgabe).
- Box ist rein informativ: kein Button, keine Änderung an `btn-preview-execute` oder am Payload der Ausführung.

### 3.4 Frontend — Bestand-XSS-Fix im selben PR (FP1-Entscheid)

- `app.js:10371`: beide Interpolationen (`nas_name`, `metadata_name`) mit `escapeHTML()` umschließen (Fakten-Korrektur 1). Keine weitere Umstrukturierung der Zeile.

### 3.5 Cache-Buster

- `index.html:2760` `app.js?v=104` → `105`; alle 9 Imports `app.js:1-9` `?v=104` → `105`. `cache_busting.test.js` muss grün bleiben (siehe Konvention in Abschnitt 2).

### 3.6 Doku

- `API.md`: neues Response-Feld `similar_existing` für `/api/preview-process` dokumentieren (Verhaltensänderung → Doku-Pflicht nach Hausregeln).

---

## 4. Akzeptanzkriterien (ausführbare Tests; „es prüft, dass …")

Backend-Tests: neue Datei `tests/test_similar_titles_hint.py` (pytest, Artefakte nur in `tmp_path`, keine Test-Hintertüren im Produktivcode; Endpoint-Muster orientiert an `tests/test_movie_processing_fixes.py` und `tests/test_utils.py:2969ff`). Frontend-Tests: neue Datei `tests/frontend/similar_titles_hint.test.js` (Muster `tests/frontend/inbox_group.test.js`, `npm run test:frontend`).

- **AK1 (Stufe-1-Treffer):** Es prüft, dass bei `movie_id` 3409/Provider `tmdb` und NAS-Ordner „X-Men - Der Film" mit `<tmdbid>3409</tmdbid>` die Response `similar_existing.exact` den Ordner enthält — Ordnernamen egal.
- **AK2 (keine Verdopplung):** Es prüft, dass bei ID-Treffer **und** exakt gleichem Ordnernamen die bestehende Kollisionswarnung (`warning`-Feld) unverändert erscheint und `exact` den Zielordner selbst **nicht** enthält (Ausschluss).
- **AK3 (Regression ohne Treffer):** Es prüft, dass ohne ID-/Namens-Treffer `similar_existing` beide Keys mit leeren Listen enthält und `renames`/`subs`/`junk`/`destination` inhaltlich unverändert sind.
- **AK4 (Skip-Provider):** Es prüft, dass Payloads mit `provider` `manual`/`mediathek`/`ytdlp`/`ofdb` oder fehlender `movie_id` fehlerfrei durchlaufen: keine Stufe 1, HTTP 200, Log-Eintrag; Stufe 2 (Namensregel) läuft trotzdem.
- **AK5 (Genre-Zwischenordner):** Es prüft, dass ein Treffer in `Filme/Action/X-Men (2000)/` (2. Ebene) gefunden wird; ein Treffer in 3. Ebene wird **nicht** gefunden (Tiefen-Cap).
- **AK6 (defekte NFO):** Es prüft, dass eine unlesbare/defekte NFO übersprungen wird (Log), der Restscan weiterläuft und HTTP 200 zurückkommt.
- **AK7 (fehlendes NAS):** Es prüft, dass ein nicht existenter `category_root` ⇒ leere Listen, Vorschau normal, kein HTTP-Fehler.
- **AK8 (Escaping):** Es prüft, dass ein NAS-Ordnername `<img src=x onerror=alert(1)>` in Stufe 1 und Stufe 2 im DOM nur als Text erscheint (Frontend-Test: kein ausgeführtes Element, `textContent` enthält den Rohstring).
- **AK9 (nicht-blockierend):** Es prüft, dass bei gesetztem Hinweis `btn-preview-execute` aktiv bleibt und der Ausführungs-Payload unverändert gesendet wird (Frontend-Test).
- **AK10 (TV-Regression):** Es prüft, dass die TV-Route unverändert ist: die bestehenden Tests `tests/test_utils.py:3123` und `:3665` sowie die Staffelwarnung bleiben grün, `similar_existing` wird bei `media_type == "tv"` **nicht** gesetzt.
- **AK11 (Caps):** Es prüft, dass bei 12 Namens-Treffern max. 10 in der Response stehen (sortiert nach Überlappung) und die Response nur Treffer-Ordner enthält, keine Vollbibliothek.
- **AK12 (Heuristik Treffer):** Es prüft, dass „X-Men (2000)" den Ordner „X-Men 2" in `similar` findet — über die **Wortregel** mit dem gemeinsamen bedeutungstragenden Wort „x" („men" ist Allgemeinwort und zählt allein nicht; „x" bleibt erhalten, weil die Einzelbuchstaben `v`/`x` bewusst nicht als Fortsetzungszahl entfernt werden; die Präfixregel greift hier zusätzlich als Backup) — **und** dass „Hobbit" den Ordner „Hobbits" über die **Präfixregel** findet und „300" den Ordner „300 (2006)" über die Wortregel (mehrstellige Zahl bleibt bedeutungstragend).
- **AK13 (Heuristik Nicht-Treffer):** Es prüft, dass „Die X-Men Origins" den Ordner „Iron Man" **nicht** findet (Füllwort „die" weg; „man" auf Allgemeinwort-Liste; kein gemeinsames bedeutungstragendes Wort, kein Präfix) — und dass „Night" (nur Allgemeinwort übrig) gegen „Nightcrawler" **nicht** matcht (Leer-Guard gilt auch für die Präfixregel) — und dass ein Ordner „Teil 2" (nach Bereinigung leer: „teil" Allgemeinwort, „2" Fortsetzungszahl) gegen **keinen** Titel matcht (kein Total-Matcher).
- **AK14 (Füllwörter/Tags):** Es prüft, dass „Der Hobbit (2012) [1080p][GERMAN]" gegen „Hobbit - Eine unerwartete Reise" trifft (Füllwörter/Jahr/Klammern/Release-Tags weg, gemeinsames Wort „hobbit").
- **AK15 (UI-Kappung):** Es prüft, dass bei 7 Stufe-2-Treffern die ersten 5 sichtbar und die restlichen 2 eingeklappt sind (Frontend-Test).
- **AK16 (Stufen-Trennung):** Es prüft, dass ein Stufe-1-Ordner nicht zusätzlich in Stufe 2 erscheint.
- **AK17 (Cache-Buster):** Es prüft, dass `tests/frontend/cache_busting.test.js` mit einheitlicher Version (105) grün läuft.
- **AK18 (Bestand-XSS):** Es prüft, dass `show_name_mismatch.nas_name` und `.metadata_name` mit HTML-Sonderzeichen nur als Text gerendert werden (Frontend-Test an der bestehenden Box).
- **AK19 (NFO-Label-Whitelist):** Es prüft, dass ein Filmordner, dessen NFO `read_nfo_metadata` als Provider `tvdb` labelt (z. B. `<tvdbid>3409</tvdbid>` + `<tmdbid>3409</tmdbid>`, Payload `provider=tmdb`, `movie_id=3409`), **kein** Stufe-1-Treffer wird (NFO-seitige Label-Whitelist, Fakten-Korrektur 4); der Scan läuft fehlerfrei weiter (Log-Eintrag).

---

## 5. Etappen (Schnitt nach Diff-Größe, Richtwert ≤ 80 KB je Etappe)

### E1 — Backend: Hilfsfunktion + Endpoint-Feld + Backend-Tests + API.md
- **Erlaubte Dateien:** `gui/core/similar_titles.py` (neu), `gui/api/queue_api.py` (nur Film-Zweig, Ergänzungsblock), `tests/test_similar_titles_hint.py` (neu), `API.md` (Abschnitt Preview-Response).
- **Umfang (geschätzt):** ~120 Zeilen Helper, ~40 Zeilen Endpoint, ~220 Zeilen Tests — Diff deutlich unter 80 KB. KI-Umsetzung schnell; Engpass ist Alex' Review der Heuristik-Liste (GENERAL_WORDS, Release-Tags).
- **Done-Kriterium E1:** AK1-AK7, AK11-AK14, AK19 grün; **AK16 im Backend-Anteil** grün (Stufe-2-Response enthält keinen Stufe-1-Ordner — `exclude_folders` wird direkt in `tests/test_similar_titles_hint.py` geprüft, plan-review C3); `pytest` komplett grün; TV-Zweig unangetastet (AK10 als Regressionstest bereits hier).

### E2 — Frontend: Warnbox + XSS-Fix + Cache-Buster + Frontend-Tests
- **Erlaubte Dateien:** `gui/static/index.html` (neue Box + `?v=`), `gui/static/app.js` (Render-Logik in `openPreviewModal`, Imports `?v=`, XSS-Fix `:10371`), `tests/frontend/similar_titles_hint.test.js` (neu), `tests/frontend/cache_busting.test.js` **nur lesend** (Prüfinstanz, nicht ändern).
- **Umfang (geschätzt):** ~40 Zeilen HTML, ~80 Zeilen JS, ~160 Zeilen Tests — unter 80 KB.
- **Done-Kriterium E2:** AK8, AK9, AK15, AK16 (nur noch die UI-Sicht: Stufe-1-Ordner erscheint im Modal nicht doppelt), AK17, AK18 grün; `npm run test:frontend` komplett grün.

### Abbruchkriterien (beide Etappen, sofort Stopp + Rückmeldung statt „kreativer Lösung")
1. Eine Änderung müsste Dateien außerhalb der Erlaubten-Liste der jeweiligen Etappe anfassen.
2. Der Diff einer Etappe überschreitet ~80 KB.
3. Der Test erforderte eine Test-Hintertür (Env-Branch, Sonderpfad) im Produktivcode.
4. Stufe 1 ließe sich nur durch Änderung von `read_nfo_metadata`/`calculate_match_score`/TV-Zweig erreichen — das ist **verboten**; Abbruch und Eskalation an Alex.
5. Ein bestehender, nicht zugeordneter Test wird rot und die Ursache liegt außerhalb des erlaubten Umfangs.

---

## 6. Nicht-Ziele (bewusst ausgeschlossen, FP1-Entscheid)

- Serien (`show_name_mismatch` deckt ID-Treffer bereits ab), Outbox-Abgleich, Doku/Anime/YouTube-Abdeckung.
- Franchise-/Reihenübersicht via TMDb-Collection (V2, eigener ADR-Zyklus + Lizenz-/Terms-Prüfung).
- Jellyfin/Plex/Emby-Anbindung; Bibliotheks-Index/Cache; neue Abhängigkeiten jeglicher Art.
- Änderung an `calculate_match_score` (weder modifiziert noch wiederverwendet — FP1-Vorgabe) oder an `read_nfo_metadata`.
- Bekannte Lücken werden **nicht** gelöst, nur dokumentiert (siehe ROADMAP-Notiz in Abschnitt 9): doku/anime/youtube laufen in keinen Warn-Zweig (`queue_api.py:125/:365`, `project_api.py:1425-1474`, `app.js:5124-5151` — verifiziert); Mount-Hänger-Risiko R1.

---

## 7. Sicherheit & Architektur

- **Escaping-Pflicht:** jedes neue Feld nur über `escapeHTML()`/`textContent` (advocatus Finding 1, verifiziert). Bestand-XSS (`app.js:10371`, beide Felder) wird im selben PR behoben (FP1).
- **Fehler-Contract (ADR-4):** jeder Lese-/NFO-Fehler ⇒ Skip + `log_message`; fehlendes NAS ⇒ kein Hinweis; Vorschau schlägt nie wegen `similar_existing` fehl (try/except um den Gesamtblock). Kein neuer Timeout/Thread im MVP — Restrisiko R1 bleibt bewusst bestehen (Abschnitt 9).
- **Architektur-Contract:** neue Logik gekapselt in `gui/core/similar_titles.py`; keine Wiederverwendung von `calculate_match_score` (bewusste FP1-Entscheidung gegen die Synthese-Empfehlung, Begründung: Alex' Nutzenabwägung „lieber mehr Fehlalarme"; Kapseleffekt: Stufe-2-Treffer sind nie „Duplikat"-Behauptung, sondern klar als „evtl. dazu gehörig" beschriftet). `read_nfo_metadata` bleibt unverändert (TV-Regressionsschutz, Fakten-Korrektur 4).
- **Keine Secrets, keine externen Aufrufe, keine neuen Abhängigkeiten** — rein lokales Dateisystem-Lesen im bestehenden Request. SMB-Latenz bleibt als R1 dokumentiert.
- **Rate Limiting:** entfällt (kein neuer öffentlicher Endpunkt; bestehender interner GUI-Endpunkt).

---

## 8. UX/UI

- Ort: Vorschau-Modal, zwischen Namenskonflikt-Box und Zielverzeichnis (Muster `index.html:2568-2579`, verifiziert).
- Stufe 1 hervorgehoben oben („Diesen Film hast du schon auf dem NAS"); Stufe 2 darunter, kleiner/sekundär („Ähnliche Titel – gehören evtl. dazu"); 5 sichtbar, Rest eingeklappt.
- Ton: Hinweis, nie Sperre; keine Buttons in der neuen Box (anders als die Mismatch-Box — bewusst, weil hier keine Namensübernahme-Aktion existiert).
- Leere Ergebnislisten ⇒ Box bleibt komplett hidden (kein „0 Treffer"-Zustand, advocatus Finding 7).
- Assets: nur bestehende Lucide-Inline-SVGs (ISC, Bestand).

---

## 9. Potenziale, ROADMAP-Notizen & Restrisiken (nicht gelöst, dokumentiert)

- **R1 [kritisch, bleibt]:** Hängender SMB-Mount ohne Timeout kann Preview-Request blockieren (advocatus Finding 2); der begrenzte 2-Ebenen-Kategorie-Scan reduziert, eliminiert nicht. Gegenmaßnahmen (Thread/Timeout-Kapselung) → ROADMAP.
- **R3:** doku/anime/youtube erreichen keinen Warn-Zweig — Feature tut dort stillschweigend nichts. → ROADMAP-Notiz (bewusstes Nicht-Ziel, FP1).
- **R4:** ID-loser Altbestand wird von Stufe 1 nicht erkannt — Stufe 2 (Namensheuristik) fängt genau diese Klasse jetzt bewusst mit ab (FP1-Entscheid gegen den produktberater-Veto, s. Abschnitt 10).
- **V2-Franchise:** TMDb `belongs_to_collection`; vor Umsetzung Lizenz-/API-Terms-Prüfung + Alex-Go (stichproben-pflichtig: Außenwirkung/Registrierung).
- **Index/Cache-Ausbau** (scout Vision 1) als Antwort auf R1/Latenz; Invalidation-Risiko bleibt bedacht (advocatus).
- **Weitere ROADMAP-Kandidaten aus Akt 1 (plan-review C4, Übernahme aus `synthese.md` Abschnitt 4):** „Du hast das schon"-Sammelreport mit Sidebar-Badge (scout Idee 5) und Prüfung bereits im Suchschritt vor der Zielauswahl (scout Idee 6) — von der Synthese als ergänzungsfähig, aber nicht Kern geparkt; bei der ROADMAP.md-Pflege nach Merge ausdrücklich mit übernehmen, damit sie nicht verloren gehen.
- **Architektur-Schuld (Notiz, advocacy außerhalb Scope):** bereits heute driften drei Ähnlichkeits-/Normalisierungssysteme (`mw_metadata`, `duplicates._titles_match`, `normalize_series_name`); mit `similar_titles.py` sind es vier — bewusst in Kauf genommen (FP1: keine Wiederverwendung von `calculate_match_score`), bei nächstem Ähnlichkeits-Feature konsolidieren. → ROADMAP.

---

## 10. Dissens-Dokumentation (Pflicht nach Session-Ritual)

- **produktberater-Veto gegen Namens-Fuzzy** („Fuzzy-Matching ist eine Falle", Rohoutput Warnung 1) und **advocatus' False-Positive-Beleg** (X-Men vs. X-Men 2 → Jaccard 0.667): **von Alex in FP1 bewusst überstimmt** — Stufe 2 wird als großzügige Heuristik gebaut („lieber mehr Fehlalarme als verpasste Treffer"). Abgemildert durch: strukturelle Trefferregel ohne Schwellenwert-Tuning, Allgemeinwort-Liste, Stufen-Trennung mit klarer Beschriftung, Cap 10/5. Verworfen bleibt die Wiederverwendung von `calculate_match_score` (beide Prüfer + FP1-Vorgabe einig).
- **advocatus forderte Timeout/Thread-Kapselung als Vorbedingung:** für das MVP **verworfen** (Begründung: Präzedenzfall — der TV-Zweig macht denselben synchronen NFO-Loop heute schon, `queue_api.py:767` verifiziert; Scope-Reduktion auf Zielkategorie senkt das Risiko). Restrisiko R1 bleibt dokumentiert, nicht bestritten.
- **scout sah Franchise-Übersicht als „eigentlichen Mehrwert":** als Use Case 2 anerkannt, aber **verworfen für MVP** (eigene Datenquelle nötig); als V2 mit Lizenz-Vorbehalt geparkt.
- **Kein Agenten-Konsens-Blindflug:** die drei obigen Punkte sind echte Dissense, hier mit Entscheidungsträger (Alex/FP1) bzw. Verwerfungsgrund.

---

## 11. Quellen, Referenzen & Lizenzen

- **Eigener Code** (lesend verifiziert, keine Lizenzfrage): `gui/api/queue_api.py`, `gui/core/series_helper.py`, `gui/core/nfo_helper.py`, `gui/core/health.py`, `gui/core/film_normalize.py`, `gui/mw_metadata.py`, `gui/static/app.js`, `gui/static/index.html`, `tests/test_utils.py`, `tests/frontend/cache_busting.test.js`, `tests/frontend/inbox_group.test.js`, `API.md`.
- **Drittanbieter-Code/Assets:** nicht verwendet, nichts kopiert. Referenzen dienten nur als Pattern. Neue Assets: keine (bestehende Lucide-Inline-SVGs, ISC-Lizenz, bereits im Bestand).
- **Nur als Ideen erwähnt, Lizenz ungeprüft ⇒ Blocker vor jeder Adoption** (gemäß Lizenzpflicht): `plexapi`, `jellyfin-apiclient-python`, `pyemby`, `tmdbsimple`; TMDb-API-Terms bei V2. In diesem Briefing **nicht** benötigt (keine neuen Abhängigkeiten).

---

## 12. Zeit-/Engpass-Abschätzung (KI vs. Mensch, getrennt)

- **KI-Implementierung E1+E2:** je Session umsetzbar (Diff klein, Testliste fertig) — schnell.
- **Menschlicher Engpass (Alex):** Review der Heuristik-Listen (GENERAL_WORDS, Release-Tags, Füllwörter) und der UI-Texte ist der eigentliche Klotz; realistisch 1-2 Review-Runden je Etappe. Freigaben (FP2-Plan, PR-Merge Klasse C) bleiben Alex-Punkte.
