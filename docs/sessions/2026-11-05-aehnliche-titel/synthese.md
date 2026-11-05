# Synthese — Akt 1 Planungs-Session "Ähnliche-Titel-Hinweis vor finaler Verarbeitung"

**Datum:** 2026-11-05 · **Session-Ordner:** `docs/sessions/2026-11-05-aehnliche-titel/`
**Rohoutputs:** [`scout.md`](scout.md) (unverändert), [`advocatus.md`](advocatus.md) (unverändert), [`produktberater.md`](produktberater.md) (unverändert)
**Charakter:** Recherche-/Design-Synthese (Kreativteam Akt 1). KEIN Umsetzungsbriefing, KEIN Code, keine Git-Schreiboperationen.
**Vorlagen-Hinweis:** `FEATURE_BRIEFING.template.md` / `ALEX_ZUSAMMENFASSUNG.template.md` existieren nicht im Arbeitsverzeichnis; Struktur folgt dem Auftragstext. `scripts/check_updates.py` existiert nicht (kein Update-Check nötig).

---

## 1. Zusammenfassung

**Wunsch (Alex, sinngemäß):** Kurz bevor im Medienwerkzeug "Jetzt final verarbeiten" geklickt wird, soll das Tool nach ähnlichen Namen in der Bibliothek suchen und anzeigen, z. B. "Du hast schon diese X-Men-Filme: …" — damit leicht anders benannte Duplikate auffallen.

**Was ich im Code verifiziert habe (Korrekturen/Ergänzungen zum Brief):**
1. **Der Film-Zweig der Vorschau hat bereits eine Kollisionswarnung** (`gui/api/queue_api.py:272-363`) — aber nur bei **exakt** gleichem Zielordnernamen (`os.path.exists(nas_path)`), inkl. ffprobe-Vergleichstabelle bei Dateiüberschreibung. Die Lücke ist also präzise: *"gleicher/ähnlicher Inhalt, anderer Ordnername"* wird bei Filmen nicht erkannt. Der Brief erwähnte diese Warnung nicht.
2. **Der Movie-Preview-Payload enthält bereits `movie_id` + `provider`** (`gui/static/app.js:4542-4543`), und generierte Film-NFOs tragen `<tmdbid>` (`gui/mw_metadata.py:1188`). Ein ID-basierter Abgleich ist damit ohne neue externe Abhängigkeit möglich.
3. `show_name_mismatch` prüft **nur das NAS**, nicht die Outbox (`queue_api.py:765-767` → `find_existing_series_folder_by_id(nas_serien, …)`, `gui/core/series_helper.py:5-33`); die Staffel-Warnung prüft dagegen beide (`queue_api.py:710-714`). Outbox-Abdeckung ist also je Warnung uneinheitlich.
4. Der Preview-Handler kennt nur `media_type` `"movie"` und `"tv"` — `doku`/`anime`/`youtube` laufen in **keinen** Warn-Zweig ([advocatus], belegt `queue_api.py:125/365`, `project_api.py:1425-1474`, `app.js:5125-5151`).
5. **Bestehender XSS-Pfad:** `app.js:10371` rendert `show_name_mismatch.nas_name` (Fremdordnername vom NAS) per `innerHTML` **ohne** `escapeHTML` — obwohl `escapeHTML` existiert (`app.js:245-253`) und im selben Modal genutzt wird (`app.js:10415-10416`). [advocatus] stuft das als kritisch ein; jedes neue Feld nach demselben Muster (wie Vorschlag A plant) würde den Fehler vervielfältigen.
6. **Rechenbare Similarity-Falle:** `calculate_match_score` (`gui/mw_metadata.py:2551-2611`, Jaccard+Jahr) meldet "X-Men" vs. "X-Men 2" mit ~0,67 als fast identisch — Franchise ≠ Duplikat. Die Jahresstrafe −1,5 greift nur, **wenn beide Seiten ein Jahr tragen** (`2605-2609`), das Verhalten ist also inkonsistent. [advocatus] belegt das; [produktberater] formuliert dasselbe als "Fuzzy-Matching ist eine Falle".
7. Für Serien existiert der ID-Mechanismus bereits (`find_existing_series_folder_by_id`); ein filmäquivalentes Gegenstück fehlt. [scout] und [produktberater] sehen darin die Blaupause.

**Kern-Dissens und wie er sich auflöst:** Der Wunschtext ("Du hast schon diese X-Men-Filme") ist zweideutig. [produktberater] trennt sauber in **Use Case 1 = Duplikatwarnung** (gleicher Film, anderer Name — das Schmerzproblem) und **Use Case 2 = Reihen-/Franchiseübersicht** (nice-to-have, andere Datenquelle nötig). [scout] sieht in B (Franchise) "den eigentlichen Mehrwert", [produktberater] und [advocatus] warnen vor False-Positive-Flut und Gold-Plating. Die Auflösung ist **keine** technische, sondern eine **Design-Frage an Alex** (siehe 6., Q1).

---

## 2. Empfehlung (Executive-Recommendation-Format)

- **Empfehlung:** MVP-Variante **A′** — *ID-basierter Duplikat-Hinweis für Filme im Vorschau-Modal*: nicht-blockierende Warnbox nach Muster `show_name_mismatch`, Abgleich `movie_id`/`provider` aus dem Payload gegen `<tmdbid>`/`mw_showid` der Film-NFOs im Ziel-Kategorieordner (NAS, 2 Ebenen tief wegen Genre-Ordnern). Kein Fuzzy, kein Schwellenwert, keine Franchise-Gruppierung, Outbox zunächst nicht. Zwingende Beipflichte: neues Feld nur escaped rendern; Scan fehler tolerant (fehlendes NAS/defekte NFO ⇒ kein Hinweis, nie abgebrochener Lauf).
- **Kurzbegründung:** Die ID steckt bereits im Payload und in den generierten NFOs — der Abgleich ist deterministisch, hat laut [produktberater] ~90 Zeilen Umfang, beseitigt das von [advocatus] belegte Franchise-False-Positive-Problem komplett und folgt einem bestehenden, erprobten Mechanismus (Serien-ID-Match). Beide Risiko-Prüfer empfehlen ID als Primärsignal; [scout] stimmt zu ("ersetzt A bei ID-verfügbaren Medien").
- **Trade-off / wichtigster Nachteil:** Altbestand **ohne** NFO/ID (Mediathek-Download, manuell verschobene Ordner) wird nicht erkannt — und das ist exentlich die Klasse "leicht anders benannt", die Alex ursprünglich beschreibt. Der Wunschbeispiel ("diese X-Men-Filme: …", Plural) könnte zudem Reihenübersicht meinen; A′ liefert die **nicht**.
- **Alex-Entscheidung (beim finalen Planreview):** (1) Ist der Kern-Wunsch **Duplikatwarnung** (→ A′) oder **Reihenübersicht** (→ Franchise via TMDb-Collection, anderes Feature) oder beides (→ A′ jetzt, Franchise als V2)? (2) Akzeptiert A′ die ID-Lücke bei Altbestand, oder soll ein klar als "evtl. verwandt" getrennter, konservativer Namens-Zusatzsignal später ergänzt werden? (3) Scan-Strategie: synchron, begrenzt (MVP) oder Index/Cache-Ausbau?

---

## 3. ADR-Blöcke (Entscheidungs-Vorschläge; Status: Entwurf, freizugeben durch Alex)

### ADR-1 — Ort der Prüfung: nicht-blockierende Warnbox im bestehenden Vorschau-Modal
- **Entscheidung:** Hinweis erscheint als neue Box im `preview-modal` (Muster `preview-show-name-mismatch`, `index.html:2568-2579`), blockiert "Jetzt final verarbeiten" nicht.
- **Alternativen:** C = eigener Bestätigungsdialog vor dem Knopf; Prüfung schon im Suchschritt ([scout] Idee 6); proaktiver Sammelreport/Badge ([scout] Idee 5).
- **Begründung:** C ist von allen drei Beratern verworfen (unterbricht 100 % der Läufe für ein unscharfes Signal — [advocatus]: "ein Hinweis darf nicht den Prozess anhalten"). Der Preview-Ort ist genau der von Alex benannte Moment ("kurz bevor final verarbeitet wird"). Suchschritt- und Report-Varianten sind ergänzungsfähig, aber nicht Kern.
- **Konsequenzen:** Kleine Erweiterung von `/preview_process`-Response und Modal-HTML/JS; keine Änderung am Ausführungs-pfad. Spätere Ausbaustufen (Report, Suche-Frühwarnung) bleiben möglich, ohne ADR-1 zu brechen.

### ADR-2 — Primärsignal: ID-Abgleich über NFOs statt Namens-Fuzzy
- **Entscheidung:** Duplikat-Erkennung primär über `movie_id`+`provider` (Payload) vs. `<tmdbid>`/`<mw_showid>` in den Film-NFOs der Bibliothek. Namens-Ähnlichkeit (`calculate_match_score`) ist **kein** MVP-Bestandteil.
- **Alternativen:** A (reines Namens-Fuzzy mit Schwellenwert) — vom Hauptassistenten ursprünglich vorgeschlagen; Jellyfin/Emby/Plex-API ([scout] Idee 2); Hybrid ID+Fuzzy.
- **Begründung:** [advocatus] belegt mit ausgerechneten Fällen, dass Jaccard-Fuzzy Franchise-Filme systematisch als Duplikate meldet ("X-Men" vs. "X-Men 2" → 0,67) und die Jahresstrafe inkonsistent greift → Warn-Müdigkeit, Feature verfehlt sein Ziel. [produktberater] legt dar: ID-Abgleich = null False Positives, ~60 statt ~150 Zeilen, kein Schwellenwert-Tuning. ID ist bereits beidseitig vorhanden (verifiziert: `app.js:4542-4543`, `mw_metadata.py:1188`). Jellyfin-API verworfen für MVP: [advocatus] — neue Secrets/Latenz/Verfügbarkeits-Abhängigkeit sprengt den Hinweis-Charakter.
- **Konsequenzen:** Filme ohne ID im Altbestand bleiben unerkannt (dokumentierte Lücke, → offenes Risiko R4). Implementatorische Detailpflicht: `read_nfo_metadata` labeldt `tmdbid`-Fallback fälschlich als `tmdb_tv` (`nfo_helper.py:142-145`) — für Filme muss der Abgleich das korrekt behandeln (direkt `tmdbid` lesen oder Provider-Korrektur; bei Umsetzung zu entscheiden, nicht zu übergehen). Provider-Werte `manual`/`mediathek`/`ytdlp` ohne echte ID ⇒ stiller Skip.

### ADR-3 — MVP-Datenumfang: Filme, NAS-Zielkategorie, 2 Ebenen tief, ohne Outbox
- **Entscheidung:** Nur `media_type == "movie"`; Scan des Ziel-Kategorieordners (z. B. `NAS/Filme`), rekursiv max. 2 Ebenen (Genre-Sammelordner wie `Filme/Action/X-Men (2000)/`); Outbox und Serien bleiben außerhalb des MVP.
- **Alternativen:** NAS-weit über `walk_nas_categories` (`transfers.py:1023`); NAS+Outbox (wie Vorschlag A); Filme+Serien.
- **Begründung:** Alexand Beispiel ist ein Film. Serien deckt `show_name_mismatch` bereits bei ID-Treffer ab (`queue_api.py:764-785`) — dort ist die Lücke kleiner. [produktberater]: begrenzte Zielkategorie hält den Scan bei typisch 100-500 Ordnern; NAS-weit oder + Outbox vergrößert das von [advocatus] kritisch bewertete Latenz-/Hänger-Risiko (stale SMB-Mount ohne Timeout). Genre-2-Ebenen-Pflicht belegt [produktberater] via `_is_genre_container` (`gui/core/film_normalize.py:33`, `health.py`).
- **Konsequenzen:** Duplikate in *anderen* NAS-Kategorien oder nur in der Outbox werden nicht gemeldet (bewusste MVP-Grenze, → offene Fragen Q2/Q3). Die bestehende Outbox-Lücke im Film-Zweig ist damit **nicht** gelöst, nur dokumentiert.

### ADR-4 — Fehler- und Latenz-Contract: der Hinweis darf den Lauf nie blockieren oder kippen
- **Entscheidung:** Der Ähnlichkeits-Scan läuft fehler-tolerant: jeder Ordner-/NFO-Lesefehler ⇒ überspringen + loggen; fehlendes NAS ⇒ kein Hinweis; die Vorschau selbst schlägt nie wegen des neuen Feldes fehl. Trefferliste gekappt (z. B. max. 10 Einträge). Kein dritter, eigener Cache im MVP.
- **Alternativen:** Eigener Timeout/Thread um den Scan ([advocatus] Forderung); sofortiger Ausbau zum Bibliotheks-Index aus `health_cache`/`walk_nas_categories` ([scout] Idee 3).
- **Begründung:** Der Präzedenzfall existiert: Der TV-Zweig macht denselben synchronen NFO-Loop schon heute (`queue_api.py:767`). [advocatus] warnt zurecht, dass ein stale Mount im Kernel-D-State hängt und dass ein dritter Enumerations-Mechanismus ohne Cache die Architektur vermüllt ([advocatus] Finding 5) — aber [scout]s Index-Idee bringt Invalidation-Risiko (veralteter Index = False Negatives, genau der ungünstigste Fehlermodus für eine Duplikatwarnung, so [advocatus] selbst). Für ein MVP mit Zielkategorie-Begrenzung ist der sync-honike Contract vertretbar; Thread-Kapselung und Index sind dokumentierte Ausbaustufen.
- **Konsequenzen:** Restrisiko R1 (Mount-Hänger) bleibt bewusst bestehen und ist Alex offenzulegen. Wenn in der Praxis Latenz auftritt, ist der Index-Ausbau der vorbereitete nächste Schritt (ROADMAP).

### ADR-5 — Sicherheits-Regel für alle neuen Felder: nur escaped rendern; Bestand-XSS separat entscheiden
- **Entscheidung:** Jeder Ordnername/Score aus `similar_existing` wird im Frontend ausschließlich über `escapeHTML()`/`textContent` gerendert. Der **bestehende** XSS-Fehler `app.js:10371` (unescaped `nas_name` in `innerHTML`) wird als eigenes, dokumentiertes Defizit gemeldet; ob er im selben PR mit behoben wird, entscheidet Alex.
- **Alternativen:** Neues Feld "nach Muster show_name_mismatch" inkl. dessen rendering-Schwachstelle kopieren (was Vorschlag A wörtlich nahelegte).
- **Begründung:** [advocatus] Finding 1 [kritisch], von mir im Code verifiziert (Zeilen oben). "Nach Muster" zu programmieren würde den Fehler vervielfältigen; NAS-Ordner sind Fremddaten.
- **Konsequenzen:** Testfall "Ordnernamen mit HTML-Tags wird nur als Text angezeigt" wird Akzeptanzkriterium. Die Bestand-XSS bleibt bis zu einer Alex-Entscheidung offen (Q5) — mindestens als ROADMAP-/Bug-Notiz.

### ADR-6 — Franchise-/Reihenübersicht (Vorschlag B) nicht im MVP; Weg wäre TMDb-Collection, nicht Name-Clustering
- **Entscheidung:** B wird abgetrennt. Falls Alex Use Case 2 will, kommt er als eigenes Feature über TMDb `belongs_to_collection` (ID ist schon im Payload) mit lokalem Collection-Mapping — nicht über Namens-Jaccard.
- **Alternativen:** B wie vorgeschlagen (Jahr + Gruppen im selben Hinweis); Name-Clustering als Franchise-Ersatz; Auslassung ohne ROADMAP-Eintrag.
- **Begründung:** [produktberater]: Franchise-Gruppierung ist ein eigenes Produkt (API-Call, Cache, UI-Gruppierung, MCU-Crossover-Edge-Cases). [advocatus]: lokal liegen keine Franchise-Daten vor (`read_nfo_metadata` liefert nur title/year/provider/showid), B erzwingt also externe Abhängigkeit. [scout] sieht den Mehrwert, benennt aber denselben Weg (TMDb-Collection) und dieselben Kosten — damit ist die Ablehnung als MVP-Bestandteil begründeter Konsens, die Idee selbst lebt als V2-Option.
- **Konsequenzen:** Bei Alex-Vot für Use Case 2: eigener Plan/ADR-Zyklus inkl. Lizenz-/API-Terms-Prüfung für TMDb-Zugriff (→ Abschnitt 7). Name-Clustering wird verworfen dokumentiert (False-Positive-Belege aus ADR-2 gelten hier erst recht).

---

## 4. Dissens — verworfene Alternativen und offene Risiken (mit Rollenzuordnung)

### Verworfene Alternativen (Begründung jeweils)
| Option | Verworfen von/zugunsten | Grund |
|---|---|---|
| C — Bestätigungsdialog | alle drei + Hauptassistent | unterbricht 100 % der Läufe; unscharfes Signal darf nicht blockieren |
| A — Namens-Fuzzy als Primärsignal | [produktberater] Veto, [advocatus] belegt, Empfehlung A′ stattdessen | Franchise-False-Positives (X-Men-Fall, vorgerechnet), Schwellenwert-Tuning, Warn-Müdigkeit, drittes Ähnlichkeits-System im Code |
| B — Franchise im selben Hinweis | [produktberater] (Gold-Plating), [advocatus] (Datenquelle fehlt) | eigene Datenquelle/API nötig; ADR-6 parkt es als V2-Option |
| Jellyfin/Emby/Plex-API als Datenquelle | MVP-verworfen; [advocatus] vor [scout]s Begeisterung | Secrets, Verfügbarkeit, Latenz, Scope-Wandel zur Server-Integration; nur sinnvoll, wenn Alex die Anbindung ohnehin plant |
| Sofortiger Bibliotheks-Index/CACHE | zurückgestellt hinter ADR-4 | [advocatus]: Invalidation-Risiko = False Negatives; [scout]s Vision 1 bleibt als Ausbau dokumentiert |
| Prüfung im Suchschritt / Sammelreport ([scout] Ideen 5-6) | nicht abgelehnt, aber nicht Kern | Alexand Wunsch verortet den Moment explicit "kurz vor final verarbeiten"; als spätere Ergänzung auf ROADMAP-Kandidatenliste |

### Offene Risiken (ungelöst, Alex zur Kenntnis / Entscheidung)
- **R1 [kritisch, advocatus]:** Hängender SMB-Mount ohne Timeout blockiert Flask-Worker; A′ reduziert die Wahrscheinlichkeit (begrenzter Scan), eliminiert sie nicht. Gegenmaßnahmen-Optionen: Thread/Timeout-Kapselung oder Index — beides bewusste Nicht-MVP-Punkte.
- **R2 [kritisch, advocatus]:** Bestehendes XSS in `app.js:10371` — unabhängig vom Feature, Fix-Ownership offen (Q5).
- **R3 [wichtig, advocatus]:** `doku`/`anime`/`youtube`-Läufe erreichen keinen Warn-Zweig — Feature würde dort stillschweigend nichts tun ("false sense of security"). Abdeckung muss bei Umsetzung explizit festgelegt werden (Q4).
- **R4 [wichtig, produktberater+advocatus]:** ID-lose Altbestände (Mediathek, manuell verschoben) bleiben als Duplikate unerkannt — die exakte "leicht anders benannt"-Klasse. Bewusste MVP-Lücke; Gegenoption (konservatives Namens-Zusatzsignal "evtl. verwandt") ist nicht vom Tisch, sondern unentschieden (Q1b).
- **R5 [wichtig, advocatus]:** Score-Anzeige/Flackern bei etwaigen späteren Fuzzy-Signalen; Payload-Cap nötig.
- **R6 [kosmetisch, advocatus]:** Keine NFC/NFD-Normalisierung in `calculate_match_score` (relevant nur bei späterem Fuzzy-Signal).
- **R7 [kosmetisch, produktberater]:** Mehrfilm-Projekte: "der ähnliche Titel" ist im Film-Zweig nicht eindeutig definiert (1 Projekt = 1 Hauptfilm, `queue_api.py:188-208`).
- **Notiz [advocatus, außerhalb Scope]:** Zwei Normalisierungs-/Jaccard-Systeme (`mw_metadata` vs. `duplicates._titles_match` vs. `normalize_series_name`) driften bereits heute auseinander — bei jedem künftigen Ähnlichkeits-Feature Architektur-Schuld.

---

## 5. Testfälle (Akzeptanzkriterien als "es prüft, dass …"-Liste; für ein späteres Briefing)

1. Es prüft, dass beim Verarbeiten des Films "X-Men (2000)" mit TMDb-ID 3409, wenn auf dem NAS ein Filmordner mit gleicher ID in `movie.nfo`/`<tmdbid>` existiert (Ordnername egal, z. B. "X-Men - Der Film"), die Vorschau den Hinweis "Film bereits vorhanden: <Ordnername>" zeigt.
2. Es prüft, dass bei ID-Treffer **und** exakt gleichem Ordnernamen die bestehende Kollisionswarnung (`queue_api.py:272-363`) weiterhin korrekt erscheint und die beiden Hinweise sich nicht gegenseitig auslöschen oder verdoppeln.
3. Es prüft, dass ohne ID-Treffer **kein** Hinweis erscheint und die Vorschau inhaltlich unverändert ist (kein Regression bei `renames`/`subs`/`junk`/`destination`).
4. Es prüft, dass ein Preview-Payload ohne echte ID (`provider` manual/mediathek/ytdlp oder fehlende `movie_id`) fehlerfrei ohne Hinweis durchläuft (stiller Skip, Log-Eintrag).
5. Es prüft, dass ein Duplikat in einem Genre-Zwischenordner (`Filme/Action/X-Men (2000)/`) gefunden wird (2-Ebenen-Scan).
6. Es prüft, dass eine unlesbare/defekte NFO-Datei übersprungen wird (Log), der Restscan weiterläuft und die Vorschau nicht fehlschlägt.
7. Es prüft, dass ein fehlender/nicht eingehängter NAS-Zielordner zu "kein Hinweis, Vorschau normal" führt (kein HTTP-Fehler).
8. Es prüft, dass ein Ordnername mit HTML/Script-Sonderzeichen (`<img src=x onerror=alert(1)>`) im Hinweis **nur als Text** erscheint (escaped; Frontend-Test).
9. Es prüft, dass der Hinweis nicht blockiert: `btn-preview-execute` bleibt aktiv und der Verarbeitungslauf sendet unverändertes Payload.
10. Es prüft, dass die TV-Route (`media_type == "tv"`) sich bit-genau wie heute verhält — insbesondere `show_name_mismatch` und Staffelwarnung (Regression, vgl. bestehende Tests `tests/test_utils.py:3123/3665`).
11. Es prüft, dass die Trefferliste auf das dokumentierte Maximum gekappt wird und die JSON-Antwort nur Treffer (keine Vollbibliothek) enthält.

---

## 6. Gesammelte offene Fragen an Alex (für den finalen Planreview gesammelt, nicht einzeln)

- **Q1 (Design-Frage, entscheidend):** Was ist der Kern des Wunsches — **Duplikatwarnung** ("derselbe Film, anderer Name") oder **Reihenübersicht** ("alle X-Men-Filme, die ich habe") oder beides? Empfehlung: Duplikatwarnung als MVP (A′), Reihenübersicht als V2 via TMDb-Collection (ADR-6). *Bei "beides" ist Q1b relevant.*
- **Q1b:** Akzeptiert das MVP die ID-Lücke bei Altbestand (R4), oder soll später ein klar getrenntes, konservatives Namens-Zusatzsignal ("evtl. verwandt") ergänzt werden?
- **Q2:** Nur Filme (Empfehlung: ja, Beispiel + Serienlücke bereits teilgedeckt) oder auch Serien/Dokus?
- **Q3:** Reicht NAS-Zielkategorie (Empfehlung: ja für MVP) oder soll die Outbox mitgeprüft werden (heute im Film-Zweig ungeprüft)?
- **Q4:** Sollen `doku`/`anime`/`youtube`-Läufe abgedeckt werden (R3) — und wenn nein, ist das dokumentierte Nicht-Tun akzeptiert?
- **Q5:** Wird der bestehende XSS-Fix (`app.js:10371`) im selben PR mit behoben (Empfehlung: ja, 1 Zeile `escapeHTML`) oder als separates Bugfix-Item?
- **Q6 (stichproben-pflichtig, Außenwirkung/Recht):** Falls Franchise-V2: TMDb-API-Nutzung (API-Key, Terms) und ggf. Jellyfin/Emby/Plex-Anbindung (Secrets in `.env`) — Bewilligung nötig, bevor Umsetzung; Lizenzen der von [scout] genannten Bibliotheken (`plexapi`, `tmdbsimple`, `jellyfin-apiclient-python`, `pyemby`) sind **ungeprüft** und gelten gemäß Lizenzpflicht als Blocker vor jeder Implementierung.
- **Kein Geld-/Kaufentscheidungs-Thema** in dieser Session erkannt; Außenwirkung nur via Q6 (externe APIs).

---

## 7. Quellen, Referenzen & Lizenzen

**Eigener Code (Referenz-Basis, keine Lizenzfrage):** Alle zitierten Dateien/Zeilen gehören zum Projekt Medienwerkzeug und wurden in dieser Session lesend verifiziert: `gui/api/queue_api.py`, `gui/api/search_api.py`, `gui/api/nas_api.py`, `gui/api/project_api.py`, `gui/core/series_helper.py`, `gui/core/helpers.py`, `gui/core/nfo_helper.py`, `gui/core/duplicates.py`, `gui/core/health.py`, `gui/core/health_cache.py`, `gui/core/transfers.py`, `gui/core/film_normalize.py`, `gui/mw_metadata.py`, `gui/static/app.js`, `gui/static/index.html`, `tests/test_utils.py`.

**Drittanbieter-Code/Assets:** In dieser Session **nicht verwendet und nicht übernommen**. Kein Code wurde kopiert; Referenzen dienten nur als Pattern (eigene Mechanismen).

**Nur als Ideen erwähnt (Lizenz ungeprüft ⇒ Blocker vor Umsetzung, gemäß Lizenz- & Referenzpflicht):**
- `plexapi`, `jellyfin-apiclient-python`, `pyemby`, `tmdbsimple` (von [scout] genannt) — vor einer Adoption: Lizenz, Pflegeaktivität, CVE-Status, Pinning via Lockfile und Alex-Go (Klasse B) prüfen.
- TMDb-/TVDb-API-Nutzung: API-Key nötig (`.env`-Regel), nicht-kommerzielle Nutzungsbedingungen — bei Franchise-V2 vor Umsetzung zu klären.
- Jellyfin/Emby/Plex-Server-API: Credentials-Handling nötig; Server-Software-Lizenzen (GPL/MIT) betreffen den Client nicht direkt, sind aber bei Bibliotheks-Wahl zu dokumentieren.

**Assets/Icons:** Neue UI-Box würde die im Projekt bereits eingebetteten Lucide-Inline-SVGs (ISC-Lizenz, bereits im Bestand) wiederverwenden — keine neuen Assets.

**Keine Screenshots/Fremddaten** in dieser Session verarbeitet.

---

## Anhang: Konsultationsprotokoll

- Input-Brief an alle drei Rollen: identischer, oben verifizierter Ist-Zustand + Vorschläge A/B/C + Rollenauftrag.
- scout: 7 eigene Ideen + 3 Visionen (archiviert unter `scout.md`).
- advocatus: 7 Findings (2 kritisch), A/B/C-Risikourteil, Alternativ-Ideen-Bewertung, 6 offene Fragen (archiviert unter `advocatus.md`).
- produktberater: Nutzen-Trennung UC1/UC2, MVP A′ mit Scope und Edge-Cases, 5 priorisierte Fragen, 4 Komplexitäts-Warnungen (archiviert unter `produktberater.md`).
- Diese Synthese ordnet jede Aussage ihrer Rolle zu; wörtliche Zitate wurden nicht verändert.
