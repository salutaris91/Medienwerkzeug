---
kind: plan
status: approved
roadmap_item: 92
session: 2026-11-06-film-assistent
fp1_approved_by: alex
fp1_approved_on: 2026-11-06
fp1_approval_quote: "Ja, freigeben"
approved_by: alex
approved_on: 2026-11-06
approval_quote: "Damit gebe ich FP2 frei."
# FP2: Entscheidungen D1-D4 und D6 siehe Abschnitt "Entscheidungen FP2".
---

# Feature Briefing: Geführter Film-Assistent (ROADMAP #92) — Kreativteam Akt 2

**Grundlagen:** `00-kickoff.md` (FP1-freigegeben), `synthese.md` (ADR-01 bis ADR-06, FP1-freigegeben mit drei Auflagen), Rohoutputs `scout.md` / `advocatus.md` / `produktberater.md` / `grafiker.md`. Alle Code-Behauptungen wurden in Akt 2 erneut am Code verifiziert (siehe Abschnitt „Verifikation und Korrekturen“).

## 1. Problemstellung

Der heutige Film-Ablauf ist auf drei getrennte UI-Orte verteilt: `#context-movie` (Inbox-Import: Suche, Mini-NFO-Editor ohne FSK/Genre, Verarbeitungsoptionen), `#preview-modal-overlay` (Vorschau: Zielpfad, Renames, Untertitel, Junk, #91-Hinweis) und `#modal-nfo-agent` (Bestands-Nachpflege mit FSK/Genre, ohne Schrittstruktur). Alex muss pro Film lange Scroll-Ansichten bedienen, FSK/Genre sind im Importpfad gar nicht editierbar, und Filmreihen müssen Film für Film von vorn durchlaufen werden.

Zusätzlich ist durch Auflage 1 (FP1) eine Backend-Lücke belegt (Präzisierung im Nachtrag vom 2026-11-06, siehe Abschnitt „Nachtrag“): Provider-FSK/-Genres schreibt der Import heute bereits in die NFO; nicht möglich ist, sie im Import zu ändern oder zu ergänzen. Selbst wenn ein Wizard FSK/Genre sammeln würde, gingen manuelle Werte im Inbox-Pfad stillschweigend verloren — `generate_movie_nfo()` liest aus `nfo_overrides` nur `title`, `plot`, `year` (vier Stellen in `gui/mw_metadata.py`: Z. 1028–1031, 1057–1060, 1096–1099, 1167–1170), und `patch_nfo_fields()` (das FSK/Genre kann) wird im Inbox-Pfad nicht aufgerufen.

## 2. Zielnutzer

Alleiniger Nutzer ist Alex (Ein-Nutzer-Heimkino-Tool auf dem NAS). Der Assistent bündelt den häufigsten Alltagspfad — „neuer Film in der Inbox → Quelle wählen → Metadaten bearbeiten → Artwork → verarbeiten“ — in einem geführten Vier-Schritte-Ablauf; Filmreihen laufen als Vorab-Queue. Bestands-Nachpflege (NFO-Agent/Health) bleibt übergangsweise in der bewährten UI erhalten.

## 3. Akzeptanzkriterien

Formuliert als ausführbare Tests („es prüft, dass …“) bzw. dokumentierter Handtest. Der **Handtest-Parcours** (FP1: Variante b, kein Playwright) wird vor E1 als `docs/sessions/2026-11-06-film-assistent/handtest-parcours.md` festgeschrieben (je ein Film-Durchlauf + ein Serien-Durchlauf + ein Doku-Durchlauf gegen den unveränderten Stand) und nach jeder Etappe wiederholt; Abweichungen sind Blocker.

- [ ] **E1-AK1:** jsdom-Test prüft, dass `js/film_wizard.js` zwischen vier Schritt-Panels per CSS-Klassenwechsel umschaltet, „Zurück“ Eingaben erhält, Schritt 3 überspringbar ist und ESC nur im Schritt-1-Panel das Modal schließt.
- [ ] **E1-AK2:** jsdom-Test prüft, dass `js/nfo_editor.js` die Felder Titel, Jahr, Plot, FSK, Genre rendert und als `nfo_overrides.movie` mit Schlüsseln `title, year, plot, fsk, genres` übergibt (heute sendet der Alt-Code nur `title/year/plot`, app.js Z. 4556–4565).
- [ ] **E1-AK3:** Backend-Integrationstest prüft, dass der Inbox-Film-Import (`gui/workers/processor.py`, Block Z. 2102–2124) nach `generate_movie_nfo()` **und** nach `generate_ofdb_nfo()` (OFDb-Zweig Z. 2116–2117 nimmt heute gar keine Overrides entgegen) die Overrides inkl. `fsk`/`genres` via `patch_nfo_fields()` in die Film-NFO schreibt (`<mpaa>`, `<genre>`). **Nachtrag:** Gepatcht wird exakt der Pfad `<clean_movie_name>.nfo`, den `generate_movie_nfo()`/`generate_ofdb_nfo()` schreiben, nicht der von `find_primary_nfo()` (processor.py Z. 2108) gefundene Pfad.
- [ ] **E1-AK4:** Test prüft: ohne Overrides bleibt die NFO byte-identisch; ein Feld nicht in den Overrides → Feld unverändert; `patch_nfo_fields()`-Fehler (Fingerprint-Konflikt, Lesefehler) bricht den Job sichtbar mit Job-Fehler ab (`log_message` + Job-Fehler, D6a), kein stilles Scheitern. **Nachtrag:** Der heutige `except Exception` im NFO-Block (processor.py Z. 2121–2122) loggt nur und lässt H.265/NAS-Transfer weiterlaufen; für den Nachzug muss ein Patch-Fehler stattdessen den Job abbrechen (H.265/NAS-Transfer laufen dann nicht weiter). Der Abbruch gilt für den Wizard-Nachzug; ein Fehler der reinen Provider-NFO-Erzeugung ohne Overrides bleibt wie bisher.
- [ ] **E1-AK5:** Serien- und Doku-Pfad unangetastet: Diff enthält keine Änderungen an `prepareSeriesPayload`, Episoden-Mapping oder `queue_api.py`-TV-Zweig; Handtest-Parcours (Serie + Doku) verhält sich identisch zum Referenzlauf. Achtung: `#context-movie` wird auch für Doku genutzt (app.js Z. 1832 „Doku verarbeiten“) — E1 darf das Panel nicht entfernen.
- [ ] **E1-AK6:** Theme-Prüfliste [grafiker] in allen 5 Themes (deep-space, nordic-slate, amber-warmth, apple-black, superfood-light) manuell abgehakt; nur CSS-Variablen, keine neuen `inline-style-NN`-Klassen.
- [ ] **E1-AK7 (Nachtrag):** Test prüft den Fall „im Inbox-Ordner (Projektordner vor dem Transfer, `current_dir`) liegt bereits eine `.nfo`“: Das Frontend sendet beim Import `overwrite_nfo: false` (app.js Z. 4552; Default auch `processor.py` Z. 806; verifiziert); `should_overwrite_nfo()` (health.py Z. 277–288) gibt dann trotz Overrides `False` zurück, `generate_movie_nfo()` überspringt die Neuerstellung (`skipped (already exists)`, mw_metadata.py Z. 1015–1017; verifiziert). Entschieden (D6b): Der Wizard gewinnt. Bei nicht-leeren Wizard-Overrides wird die NFO neu erzeugt (Overwrite erzwungen) und danach gepatcht. Der Test prüft diesen Fall und dass Aufrufer ohne Wizard-Overrides (NFO-Agent, Health) unverändert bleiben.
- [ ] **E1-AK8 (Nachtrag):** Test dokumentiert das Leeren von Feldern: `patch_nfo_fields()` übernimmt leere Werte nicht (nfo_mutation.py Z. 186–196), ein im Wizard geleertes Provider-Genre bzw. -FSK bliebe in der NFO stehen. Entschieden (D6c): Ein bewusst geleertes Feld entfernt den Provider-Wert auch aus der NFO. Der Test prüft: explizit leer gesendet → Tag entfernt; nicht gesendet → unverändert; und dass der NFO-Agent-Pfad leere Werte weiterhin ignoriert (opt-in-Parameter, siehe Umsetzungshinweise).
- [ ] **E2-AK1:** Test prüft, dass der Zielpfad im Ergebnis-Schritt escaped gerendert wird (R8-Fix: `data.destination` wie app.js Z. 10488 heute darf `<script>`-Inhalt nicht ausführen; Muster `escapeHTML()` existiert Z. 10493–10494).
- [ ] **E2-AK2:** Handtest + jsdom: Film-Lauf endet vollständig im Wizard — `/api/preview-process`-Daten (Zielpfad, Renames, Untertitel, Junk) erscheinen in Schritt 4, „Jetzt final verarbeiten“ löst `/api/process` mit unveränderter Payload-Struktur aus.
- [ ] **E2-AK3:** Das alte Vorschau-Modal bleibt für Serien und Doku in vollem Umfang funktionsfähig (Handtest-Parcours; auch `preview-show-name-mismatch` und `preview-season-warning`, index.html Z. 2563–2579).
- [ ] **E2-AK4:** #91-Hinweis (exact + similar, `queue_api.py` Z. 366–395) wird in Schritt 4 angezeigt; ein Render-Fehler des Hinweises bricht die Bestätigungs-Buttons nicht (eigener try-Block, Muster #91 R4).
- [ ] **E3-AK1:** Test/jsdom: Der Film-Zweig des NFO-Agenten nutzt das `nfo_editor`-Modul (keine duplizierte Feld-Markup-Zeile für Titel/Jahr/Plot/FSK/Genre im Film-Modus).
- [ ] **E3-AK2:** Handtest: Serien-Modus des NFO-Agenten (Episoden-Mappings, `nfo-agent-edit-mode-bar`) unverändert; Health-Einstieg bleibt erreichbar.
- [ ] **E3-AK3:** Film-spezifischer Altcode ist entfernt (app.js `searchMovie`/`selectMovie`/`executeMovieWorkflow` durch Wizard-Module ersetzt bzw. nur noch Doku-Nutzung); toter Code bleibt nicht stehen.
- [ ] **E4-AK1:** API-Test prüft: Provider-Abruf liefert Felder **je Provider** statt vorgemergt (Grundlage für Badges #55; ROADMAP #55: „TMDB ohne FSK, OFDb ohne Plot“ sichtbar machen).
- [ ] **E4-AK2:** Test prüft Teil-Erfolg: Ausfall eines Providers setzt nur dessen Badge auf „nicht erreichbar“, die übrigen Felder bleiben wählbar (advocatus Pkt. 4).
- [ ] **E4-AK3:** #54 Teil 2: HTML-Abrufe (OFDb-Suche, fernsehserien.de) laufen über das **bereits vorhandene** `fetch_html_with_retry` (mw_metadata.py Z. 153); Binär-Downloads bekommen `_download_with_retry` mit frischem File-Handle je Versuch und Byte-Integritätsprüfung; Tests je Kategorie.
- [ ] **E5-AK1:** (nur nach Rechtsfreigabe, siehe D2) jsdom-Test: Schritt 3 zeigt die Bildliste je Rolle (Poster/Hintergrundbild/Logo) aus einer **neuen** Kandidaten-Funktion (z. B. `fetch_tmdb_image_candidates()`; `fetch_tmdb_images()` reduziert intern auf je eine URL und darf in Signatur und Rückgabe nicht geändert werden, sonst bricht der Auto-Download), Auswahl/Abwahl per Klick; für `Poster` und `Logo` exakt ein Auswahl-Zustand je Rolle (1-Klick-Einzelauswahl), für `Hintergrundbild (16:9)` (`backdrop`) geordnete Mehrfachauswahl (`fanart.*` + `fanart-1.*`, `fanart-2.*` / `backdrop-1.*`, `backdrop-2.*`, Handtest-Entscheidung Alex 2026-11-11).
- [ ] **E5-AK2:** Test prüft: gewähltes Bild wird mit Retry + Integritätsprüfung geladen; Fehler zeigt Placeholder-Kachel mit Retry, bricht den Schritt nicht.
- [ ] **E5-AK3:** Attribution sichtbar (TMDb-Logo + „This product uses the TMDB API but is not endorsed or certified by TMDB.“); CSP-`img-src`-Ist-Zustand vor Umsetzung geprüft und protokolliert (advocatus Pkt. 7).
- [ ] **E6-AK1:** Handtest + jsdom: Mehrfachauswahl in der Inbox (Kästen aus #65) → „als Filme einreihen“ → Wizard arbeitet die Vorab-Queue Film für Film ab, Kopf zeigt „Film X von N“.
- [ ] **E6-AK2:** Test prüft: Abbruch der Queue nach Film k verliert die fertiggestellten Filme k-1 nicht; Queue-Filme k+1..N bleiben unbearbeitet in der Inbox.
- [ ] **E6-AK3:** Test prüft: Provider-Fehler bei Film k blockiert die Queue nicht (Teil-Erfolg, Weiter mit Film k+1, Fehler am Kopf sichtbar).

## Etappen

**Mehr als drei Etappen — Begründung:** Die Vorlagenregel „höchstens 3 Etappen“ wird hier bewusst mit FP1-Beschluss und Diff-Budget begründet überschritten: (a) FP1 hat die Teilung Etappe 1 → 1a/1b freigegeben; (b) die Akt-2-Diff-Messung (Abschnitt „Diff-Schätzung und Methodik“) zeigt, dass der Synthese-1b-Schnitt selbst ~90–150 KB kostet und damit die von der Synthese selbst vorgesehene Nachzug-Teilung (1b-i/1b-ii) zum **Regelfall** wird; (c) E5 hängt an einem Rechts-Gate (D2) und darf nicht mit funktionalen Etappen in einer Kette gemischt werden. Sechs Etappen = sechs Gate-A2-Ketten (Start je Klasse B), einzeln alltagstauglich, einzeln rückrollbar (advocatus Pkt. 9, NAS ohne Auto-Rollback).

**Reihenfolge:** E1 → E2 → E3 → E4 → E5 (Gate) → E6.

### E1 — Wizard-Rahmen + Film-Editor + Backend-Nachzug (roadmap#92, #52, #50 Film-Kern, #51 FSK/Genre-Pipeline) (Auflage-1-Beschluss)
- **Ziel:** Vier-Schritte-Wizard als neue `js/`-Module (`film_wizard.js`, `nfo_editor.js`) im `mw-modal`-Muster, Einstieg „Film verarbeiten“ in der Inbox; Schritt 2 editiert Titel/Jahr/Plot/FSK/Genre; Schritt 3 als überspringbarer Platzhalter; **Backend-Nachzug**: `patch_nfo_fields()` auch im Inbox-Film-Import (beide Provider-Zweige), damit FSK/Genre nicht mehr verloren gehen. NFO-Agent, Preview-Modal, Serien-/Doku-Pfad unangetastet. Übergebung an den Alt-Ablauf: „Weiter“ nach Schritt 2/3 öffnet den bisherigen Optionen-/Vorschau-Flow (bewusste Übergangslösung bis E2, siehe D1).
- **Akzeptanzkriterien:** E1-AK1, E1-AK2, E1-AK3, E1-AK4, E1-AK5, E1-AK6, E1-AK7, E1-AK8.
- **Erlaubte Dateien:** `gui/static/js/film_wizard.js`, `gui/static/js/nfo_editor.js`, `gui/static/index.html`, `gui/static/app.js`, `gui/static/style.css`, `gui/static/utilities.css`, `gui/workers/processor.py`, `gui/core/nfo_mutation.py`, `gui/core/health.py`, `tests/test_nfo_write.py`, `tests/test_inbox_movie_overrides.py`, `tests/frontend/film_wizard.test.js`, `tests/frontend/nfo_editor.test.js`
- **Hinweise zu den erlaubten Dateien (E1, nicht Teil der Pfadliste):** film_wizard.js, nfo_editor.js und die beiden neuen Testdateien sind neu. index.html: neues Wizard-Markup plus Cache-Buster. app.js: nur Import-Zeilen und Einstiegs-Verdrahtung, keine Löschungen. style.css oder utilities.css: die neuen Klassen mit Präfix mw-wizard. processor.py: Nachzug im Importblock um Z. 2102–2124. nfo_mutation.py und health.py nur, falls D6(b)/(c) es erfordert, sonst unangetastet. Für test_nfo_write.py darf stattdessen die neue test_inbox_movie_overrides.py genutzt werden.
- **Diff-Schätzung:** ~65–85 KB (geringe Verschiebungsanteile; Hauptlast: neue Module + Markup + CSS + Tests). **Bei Budgetüberschreitung zuerst zurückstellen:** Schritt-2-Feldumfang Originaltitel/Studios, dann „Film X von N“-CSS (in E6 ohnehin neu).
- **Abbruchkriterium:** Diff > 80 KB nach Rückstell-Liste → Kette stoppen, Schnitt mit Alex nachverhandeln; Handtest-Parcours (Serie/Doku) zeigt Abweichung → sofortiger Stopp (Serien-Regression ist der Kern-Alptraum von advocatus Pkt. 2); Nachzug-Tests (E1-AK3/AK4/AK7/AK8) nicht grün → kein PR.

### E2 — Ergebnis-Schritt für Filme + R8-Fix (roadmap#92; #91 bleibt hier, ADR-02) (Schnitt entscheidet D1)
- **Ziel:** Schritt 4 wird echter Ergebnis-Schritt: Verarbeitungsoptionen (H.265, Zielordner NAS/pCloud, Original löschen, Qualität) + Vorschau-Inhalt (Zielpfad, Renames, Untertitel, Junk, #91-Hinweis) in den Wizard überführt; „Jetzt final verarbeiten“ aus dem Wizard; R8-Fix (ADR-05) beim Umzug. Altes Vorschau-Modal bleibt für Serien/Doku unangetastet.
- **Akzeptanzkriterien:** E2-AK1, E2-AK2, E2-AK3, E2-AK4.
- **Erlaubte Dateien:** `gui/static/js/film_wizard.js`, `gui/static/js/preview_render.js`, `gui/static/app.js`, `gui/static/index.html`, `gui/static/style.css`, `tests/frontend/preview_render.test.js`, `tests/frontend/film_wizard.test.js`, `tests/frontend/similar_titles_hint.test.js`, `tests/frontend/inbox_group.test.js`, `tests/frontend/inbox_group_banner.test.js`, `tests/frontend/inbox_group_seasons.test.js`, `tests/frontend/inbox_selection.test.js`, `tests/frontend/series_search_timeout.test.js`
- **Hinweise zu den erlaubten Dateien (E2, nicht Teil der Pfadliste):** preview_render.js und preview_render.test.js sind neu; preview_render.js extrahiert die Render-Logik aus openPreviewModal (app.js, Stand main 7fb0d92: Z. 10318–10590) und wird von Wizard und Alt-Modal genutzt (eine Kopie, kein Doppelcode). app.js: Umzug der Render-/Execute-Logik, Löschungen auf den Film-Pfad beschränkt. index.html: Wizard-Markup für Schritt 4 plus Cache-Buster; der Optionen-Block in #context-movie (Z. 823–871) bleibt stehen, weil der Doku-Pfad ihn nutzt. style.css: neue Klassen mit Präfix mw-wizard-result (Grafiker-Entwurf), keine neuen inline-style-NN-Klassen. Ergänzt durch Alex' Entscheidung vom 2026-11-09: style.css sowie die sechs Bestandstests, die app.js per eval laden und openPreviewModal bzw. dessen Abhängigkeiten nutzen; dort nur Stubs/Imports anpassen, keine Assertions streichen.
- **Diff-Schätzung:** ~70–100 KB (Verschiebungs-Doppelpflicht: app.js-Region ~26 KB + Execute ~9 KB + HTML-Blöcke ~16 KB zählen Löschung + Neubau). **Diese Etappe liegt über dem 80-KB-Richtwert im ungünstigen Fall** — Vorab-Notbremse: wenn der laufende Diff 80 KB überschreitet, Junk-/Untertitel-Abschnitt in E2b nachziehen (Rest bleibt).
- **Abbruchkriterium:** Serien-/Doku-Vorschau zeigt Verhaltensänderung (Handtest) → Stopp, Rollback-Kandidat; Diff > 80 KB ohne mögliche Teil-E2b → Schnitt mit Alex nachverhandeln.

### E3 — NFO-Agent-Filmpfad andocken + Altcode-Rückbau (roadmap#92, #50, #52)
- **Ziel:** Der Film-Zweig von `#modal-nfo-agent` nutzt `nfo_editor.js` (extrahierte Felder, reine Verschiebung, Signaturen unverändert — advocatus Pkt. 2); Film-spezifischer Altcode in `#context-movie`/app.js wird entfernt bzw. auf Doku-Nutzung reduziert; hartcodierte NFO-Agent-Farben migrieren in Variablen ([grafiker] Mitwander, index.html 3163/3189/3193/3218).
- **Akzeptanzkriterien:** E3-AK1, E3-AK2, E3-AK3.
- **Erlaubte Dateien:** `gui/static/app.js`, `gui/static/index.html`, `gui/static/js/nfo_editor.js`, `gui/static/js/film_wizard.js`, `gui/static/style.css`, `tests/frontend/nfo_editor.test.js`, `tests/frontend/film_wizard.test.js`, `tests/frontend/app_warning.test.js`, `tests/frontend/fsk_batch_dom.test.js`
- **Hinweise zu den erlaubten Dateien (E3, nicht Teil der Pfadliste):** app.js: Region 16975–18100 (NFO-Agent), 4159–4625 (Film-Altcode), 1815–1900 / 2925–2945 / 3175–3240 (Modus-Wechsel Film vs. Doku) plus Cache-Buster. index.html: `#modal-nfo-agent` (Film-Editor-Container + Farbvariablen-Migration) und `#context-movie`-Rückbau (Entfernen von `#btn-open-film-wizard`) plus Cache-Buster. nfo_editor.js: optionale Quellen-Badge-Unterstützung (`showSourceBadges`/`setFieldSource`) für den NFO-Agenten. film_wizard.js: Entfernen des toten Übergabe-Altpfads (`triggerHandover`/`getHandoverPayload`/`onHandoverCallback`) plus Cache-Buster. style.css: optionale Hilfsklassen für den eingebetteten NFO-Editor und die migrierten NFO-Agent-Farben. Ergänzt durch Alex' Entscheidung vom 2026-11-10: Option 1A, Option 2A, Option 3A sowie die vier genannten Frontend-Testdateien.
- **Diff-Schätzung:** ~40–60 KB.
- **Abbruchkriterium:** Episoden-Mapping oder Health-Einstieg verändert (Handtest) → Stopp; Extraktion erzwingt Signatur-Änderungen an geteilten Film/Serien-Funktionen → Stopp und Alex-Entscheidung (Verstößt gegen „Verschieben ohne Refactoring nebenbei“).

### E4 — Provider-Vergleich + Abruf-Rahmenwerk (roadmap#55, #54 Teil 2)
- **Ziel:** Schritt 2 zeigt Felder je Provider als Badge-Feld-Karten ([grafiker] Abschnitt 2); API liefert ungemergte Provider-Felder; HTML-Abrufe auf vorhandenes `fetch_html_with_retry`, Binär auf neues `_download_with_retry` mit Byte-Integrität; Backoff-Rahmenwerk (advocatus Pkt. 7) als Basis für E5/E6.
- **Akzeptanzkriterien:** E4-AK1, E4-AK2, E4-AK3.
- **Erlaubte Dateien:** `gui/mw_metadata.py`, `gui/api/search_api.py`, `gui/static/js/film_wizard.js`, `gui/static/js/nfo_editor.js`, `gui/static/app.js`, `gui/static/index.html`, `gui/static/style.css`, `tests/test_metadata_retry.py`, `tests/test_provider_fields.py`, `tests/frontend/nfo_editor.test.js`, `tests/frontend/provider_badges.test.js`, `tests/frontend/film_wizard.test.js`
- **Hinweise zu den erlaubten Dateien (E4, nicht Teil der Pfadliste):** `test_provider_fields.py` und `provider_badges.test.js` sind neu. `gui/api/search_api.py` beherbergt `/api/metadata/fetch` (wird rückwärtskompatibel um den Multi-Provider-Modus erweitert; `briefing.md` vermutete zuvor `queue_api.py`). `gui/static/app.js` ist nur für den konsistenten Cache-Buster-Bump (`?v=116` -> `?v=117`) in der Liste enthalten. Ergänzt durch Alex' Entscheidung vom 2026-11-10 ("ja das passt; Go ist erteilt"): Option 1A, Option 2A, Option 3A sowie die genannten Backend- und Frontend-Testdateien.
- **Diff-Schätzung:** ~40–70 KB.
- **Abbruchkriterium:** Ein Provider-Fehler wirft die ganze Feldansicht (nicht nur das Badge) → Abbruch bis Teil-Erfolg erfüllt; Diff > 80 KB → Badge-UI und Retry-Arbeit in zwei Ketten teilen.

### E5 — Artwork-Auswahl (roadmap#51) — **Gate: nur nach schriftlicher Alex-Rechtsfreigabe (D2)**
- **Ziel:** Schritt 3 wird Bildauswahl: Grid je Rolle (Poster/Backdrop/Logo) aus den TMDb-Bildlisten (die TMDb-API liefert Listen, `fetch_tmdb_images()` reduziert sie aber auf je eine URL; E5 braucht eine neue Kandidaten-Funktion plus Endpoint und lässt `fetch_tmdb_images()` unverändert, weil `generate_movie_nfo()`/`generate_tvshow_nfo()` davon abhängen), Auswahl/Abwahl, Download des Gewählten mit Retry + Integritätsprüfung, Attribution. Quellenumfang final gemäß D2 (Option A nur TMDb / Option B + Fanart.tv).
- **Akzeptanzkriterien:** E5-AK1, E5-AK2, E5-AK3.
- **Erlaubte Dateien:** `gui/mw_metadata.py`, `gui/api/search_api.py`, `gui/workers/processor.py`, `gui/static/js/film_wizard.js`, `gui/static/app.js`, `gui/static/index.html`, `gui/static/style.css`, `tests/test_artwork_download.py`, `tests/frontend/film_wizard.test.js`, `tests/frontend/film_wizard_artwork.test.js`
- **Hinweise zu den erlaubten Dateien (E5, nicht Teil der Pfadliste):** `test_artwork_download.py` und `film_wizard_artwork.test.js` sind neu. `gui/api/search_api.py` stellt `/api/artwork/candidates` bereit (konkretisiert den API-Spielraum „eine Endpoint-Datei unter `gui/api/`“). `gui/workers/processor.py` reicht `artwork_overrides` im Film-Import-Pfad (inkl. `ofdb`/`manual`-Zweig) an `mw_metadata` weiter. `gui/static/app.js` ist ausschließlich für den konsistenten Cache-Buster-Bump (`?v=119` -> `?v=121`) enthalten. CSP-Prüfung vor Umsetzung erledigt (2026-11-11): kein restriktives `Content-Security-Policy` / `img-src` in `gui/main.py`, `gui/core/auth_middleware.py` oder `gui/static/index.html`. Ergänzt durch Alex' Entscheidungen vom 2026-11-11 ("Ja genau, wie von dir vorgeschlagen umsetzen. Ich stimme dir in allen drei Punkten zu." sowie im Handtest: "Lass uns das mit dem Logo und dem Poster genauso machen, wie du jetzt vorgeschlagen hast, und das jetzt auch gleich glattziehen."): Option 1A (lokaler Bild-Upload je Rolle), Option 2A (providerunabhängige TMDb-Bildsuche per Titel/Jahr + Nachsuchzeile in Schritt 3), Option 3A + Handtest-Nachzug (3 Rollen-Tabs `Poster (2:3)`, `Hintergrundbild (16:9)`, `Logo`; Einzelauswahl für Poster/Logo, geordnete Mehrfachauswahl für Hintergrundbild `fanart.*` + `fanart-1.*`/`backdrop-1.*`; Logo-Grid-CSS-Fix ohne Spaltenüberlappung; explizite Abwahl + TMDb-Attribution).
- **Diff-Schätzung:** ~35–60 KB (Option A) bzw. ~50–75 KB (Option B, zweiter Provider).
- **Abbruchkriterium:** D2 nicht schriftlich entschieden → Etappe startet nicht (harter Blocker, ADR-06); CSP-Prüfung ergibt restriktives `img-src` → Planung nachziehen.

### E6 — Filmreihen-Vorab-Queue (roadmap#69)
- **Ziel:** FP1-beschlossene Vorab-Queue (keine Dialog-Schleife): Mehrfachauswahl in der Inbox, „als Filme einreihen“, Wizard arbeitet Liste nacheinander ab, Kopf „Film X von N“; Abbruch fest; Teil-Erfolg je Film dank E4-Rahmenwerk.
- **Akzeptanzkriterien:** E6-AK1, E6-AK2, E6-AK3.
- **Erlaubte Dateien:** `gui/static/app.js` (Inbox-Auswahl #65, Queue-Steuerung), `gui/static/js/film_wizard.js`, `gui/static/index.html`, `tests/frontend/film_queue.test.js` (neu). Bewusster Spielraum API-Schicht: nur falls ein Queue-Endpunkt nötig wird, eine Datei unter `gui/api/` (im PR zu benennen) plus Backend-Test `tests/test_movie_queue.py` (neu).
- **Diff-Schätzung:** ~15–30 KB.
- **Abbruchkriterium:** Häufigkeit laut D4-Antwort „< 1×/Monat“ und Alex kippt die Etappe → Etappe entfällt (Einzelfilm-Ablauf bleibt unabhängig nutzbar).

## Diff-Schätzung und Methodik (Auflage 2)

**Methodik (Akt 2, gemessen statt nur geschätzt):** Zeilenzahlen der betroffenen Blöcke direkt am Code ausgelesen; Bytes/Zeile aus Stichproben derselben Regionen (app.js-Render-Region ~90–120 B/Zeile; index.html-Modal-Regionen wegen Inline-Styles/SVGs ~150–280 B/Zeile). Unsicherheit ±30 %, da keine Shell-Messung möglich. Verschiebungen zählen im Diff doppelt (Löschung + Neubau).

Gemessene Blöcke (Zeilen ≈ KB): `#context-movie` 109 ≈ 16 KB · `#preview-modal-overlay` 83 ≈ 19 KB · `#modal-nfo-agent` 154 ≈ 42 KB · `openPreviewModal` app.js 273 ≈ 26 KB · Preview-Execute 125 ≈ 9 KB · `searchMovie`+`selectMovie` 172 ≈ 15 KB · `executeMovieWorkflow` 59 ≈ 5 KB · NFO-Agent-Region app.js ~1125 ≈ ~95 KB (nur Film-Zweig betroffen). Zeilenzahlen exakt ausgelesen (index.html 3162–3315), KB-Werte gerundete Schätzungen aus B/Zeile-Stichproben.

**Vergleich der beiden 1a/1b-Schnitte:**

| Kriterium | Schnitt A (Synthese, FP1-freigegeben) | Schnitt B (zweiter Reviewer: Schritt 4 schon in 1a) |
|---|---|---|
| 1a/E1-Diff | **~65–85 KB** (Rahmen + Editor + Backend-Nachzug; fast alles Neubau) | **~150–190 KB** (dasselbe + Optionen-Umzug ~30 KB + Preview-Extraktion ~60–70 KB + Execute ~10 KB) → **weit über Budget** |
| 1b/E2+E3-Diff | E2 ~70–100 KB (Notbremse E2b eingebaut) + E3 ~40–60 KB | nur NFO-Docking + Rückbau ~40–60 KB |
| Achsen je Kette | 2–3 je Etappe, isoliert verifizierbar | 5 in einer Kette — genau die Überladung, die [advocatus] Pkt. 1 am Kickoff als [kritisch] verworfen hat |
| Doppelcode-Risiko | temporärer **Doppel-Ablauf** (Wizard → altes Vorschau-Modal) zwischen E1 und E2; keine duplizierte Logik | nach E2 rund; bis E3 bleibt `#context-movie` Film-Altcode tot im Baum; Risiko geteilte Render-Kopie nur bei schlechter Extraktion |
| Alltagsnutzen nach 1a | **Kern-Schmerz schon behoben**: FSK/Genre editierbar und landen in der NFO (Auflage 1); Ausführung noch im alten Dialog | runder Ein-Dialog-Ablauf ab dem ersten Tag |
| Rollback-Granularität | Rahmen/Editor und Ergebnis getrennt rückrollbar (NAS ohne Auto-Rollback) | ein Rollback von 1a wirft Rahmen, Editor, Backend **und** Ergebnis-Schritt gemeinsam zurück |

**Empfehlung (Entscheidung bei Alex, D1): Schnitt A.** Begründung: Schnitt B sprengt das Diff-Budget in der ersten Kette um das Doppelte und bündelt wieder fünf Achsen — derselbe Fehler, den der Kickoff-Schnitt hatte und den FP1 mit der 1a/1b-Teilung ausdrücklich abgestellt hat. Der doppelte Ablauf nach E1 ist auf die Übergangszeit bis E2 begrenzt und wird durch einen expliziten Übergeh-Button („Weiter zur Verarbeitung“) abgefedert; der größte Alltagsschmerz (FSK/Genre verloren) ist bereits nach E1 behoben. [advocatus] hat den temporären Nachteil der Teilung in der Synthese selbst benannt und akzeptiert.

## Verifikation und Korrekturen (Akt 2, eigener Code-Check read-only)

Alle FP1-/Auftrags-Behauptungen wurden geprüft. Bestätigt: processor.py 2102–2124 (Inbox ruft `generate_movie_nfo`, kein Patch) · `generate_movie_nfo` liest Overrides nur title/plot/year, vier Stellen · `patch_nfo_fields` in processor.py nur im NFO-Agent-Block (Import 3361; Aufrufe 3398, 3428, 3534, 3593) · `fetch_tmdb_images` lädt Poster/Backdrop/Logo pro TMDb-Film dauerhaft in den Filmordner (1208–1238, Fallbacks 1241–1261) · R8-Zeile app.js 10488 unescaped, Muster 10493–10494 · Modal-Positionen index.html 764/2550/3162 · `nfo_ui.js` exakt 74 Zeilen · app.js 18.764 Zeilen, 9 ES-Importe, Cache-Buster `?v=105` · `#91`-Scan queue_api.py 366–395 synchron, Default „/Filme“ 144–145, TV-Zweig ab 397 · `fetch_json_with_retry` mw_metadata.py 148 · 5 Themes (theme.js Z. 6) · `.step-dot` style.css 2753 · E-AK-relevante Testdateien vorhanden.

**Korrekturen/Gegenprobe gegenüber Auftrag und Synthese:**
1. **OFDb-Zweig:** Der Inbox-Import ruft bei `provider == "ofdb"` `generate_ofdb_nfo()` (processor.py 2117), das gar keine Overrides entgegennimmt. Der Nachzug muss **beide Zweige** abdecken (E1-AK3).
2. **Frontend sendet heute nur drei Felder:** `executeMovieWorkflow` (app.js 4556–4565) baut `nfo_overrides.movie` nur mit `title/year/plot`. Backend-Nachzug allein reicht nicht — der Wizard muss `fsk`/`genres` in derselben Schlüsselstruktur liefern (E1-AK2).
3. **`patch_nfo_fields` hat einen weiteren Rufer:** `nas_api.py` 747–751 (`write_fsk_to_nfo`, Health-FSK-Quickfix). Für den NFO-Agent-Pfad gilt die Aussage des Auftrags; die Formulierung „nur im NFO-Agent-Pfad“ ist ohne diese zweite Stelle nicht exakt.
4. **„jeweils der erste Treffer“ (Auflage 3) ist ungenau:** `find_best_image` (mw_metadata.py 948–960) wählt Deutsch → sprachlos → Englisch → ersten Treffer. Kern der Auflage bleibt richtig: **dauerhaftes Speichern von TMDb-Bildern ist Bestand.**
5. **`#context-movie` ist nicht nur Film-Panel:** Header wird auch für „Doku verarbeiten“ umgenutzt (app.js 1832). E2/E3 dürfen das Panel nicht film-zentriert löschen (E1-AK5, E3-AK3).
6. **`fetch_html_with_retry` existiert bereits** (mw_metadata.py 153): #54 Teil 2 schrumpft auf „Call-Stellen umstellen + Binär-Variante neu“ (E4-AK3).
7. **Stand-Korrekturen:** Cache-Buster real `app.js?v=105`/`style.css?v=51` (STAND.md nennt v=93 — veraltet, Bereinigungspunkt bleibt notiert); Endpoint real `/api/preview_process` (Kickoff nannte `/api/queue/preview`, Korrektur aus der Synthese bestätigt).
8. **Git-Zustand weiterhin offen:** Commit-Angaben (Kickoff `86fdc26` vs. STAND `02926ed`) ohne Shell nicht auflösbar. Vor jedem Commit/PR-Vorschlag ist `git status --short --branch` von Alex nachzuliefern (Git-Preflight-Pflicht; harter main-Stop).

## Nachtrag 2026-11-06 (dritter Review, am Code verifiziert; nach plan-review-r1 APPROVE, nicht erneut reviewt)

Ein dritter Reviewer fand vier Abweichungen, die der Verifikation oben entgangen waren. Alle wurden am Code bestätigt (mw_metadata.py, health.py, nfo_mutation.py, processor.py); eingearbeitet in Abschnitt 1, E1-AK3/AK4/AK7/AK8, E5-AK1, E5-Ziel, D2 und D6:
1. **`fetch_tmdb_images()`** liefert nur je eine URL (`find_best_image`), keine Listen. E5 braucht eine neue Kandidaten-Funktion; die bestehende bleibt unverändert.
2. **Fehlerbehandlung im Import:** `except Exception` im NFO-Block (processor.py Z. 2121–2122) loggt nur. Verhalten bei Patch-Fehlern ist D6(a).
3. **Bestands-NFO:** `should_overwrite_nfo()` prüft `if not overwrite_nfo` vor `if overrides`; bei bereits vorhandener `.nfo` werden Overrides ignoriert (E1-AK7, D6(b)). Gepatcht wird derselbe Pfad, den die Generatoren schreiben (`<clean_movie_name>.nfo`).
4. **Leeren von Feldern:** `patch_nfo_fields()` ignoriert leere Werte (E1-AK8, D6(c)).
5. **Einordnung des „Datenverlusts“:** Provider-FSK/-Genres schreibt der Import heute schon (TMDb: mw_metadata.py Z. 1177–1191; OFDb: Z. 914–917). Real verloren gehen heute nur manuelle Edits bei **OFDb** (Titel/Jahr/Plot; `generate_ofdb_nfo` nimmt keine Overrides). Für TMDb entsteht der Verlust erst, wenn ein Wizard FSK/Genre anbietet, ohne dass das Backend sie schreibt.
Nicht selbst verifiziert: `overwrite_nfo: false` im Frontend (app.js Z. 4552).

## ADR-Blöcke (FP1-freigegeben, hier unverändert fortgeführt)

- **ADR-01:** Etappe 1 zerfällt in 1a/1b (hier: E1 und E2/E3, mit Vorab-Teilung 1b-i/1b-ii gemäß Diff-Messung).
- **ADR-02:** #91-Hinweis bleibt im Ergebnis-Schritt (E2); Schritt-1-Umzug erst mit #91 R12 nach Scan-Dauer-Messung.
- **ADR-03:** Wizard als Eigenbau im `mw-modal`-Muster, neue `js/`-Module, keine Bibliothek (SmartWizard verworfen — Overkill für vier Schritte, eigene CSS-Klassen nötig).
- **ADR-04:** Paralleler Betrieb — Einstieg Inbox-Import, NFO-Agent läuft bis E3 unverändert weiter.
- **ADR-05:** R8-Fix beim Umzug des Zielpfads in E2 (Escape-HTML-Muster 10493–10494).
- **ADR-06:** Artwork-Etappe (E5) erst nach schriftlicher Rechtsfreigabe; TVDB-Bilder nie als Quelle; Schritt 3 von Anfang an überspringbar.
- **ADR-07 (Auflage 1, beschlossen):** Backend-Nachzug `patch_nfo_fields()` im Inbox-Film-Import ist Pflichtbestandteil von E1, beide Provider-Zweige, mit Tests E1-AK3/AK4.

## 4. Bewusst verworfen (Scope-Eingrenzung)

- **Serien-Episoden-Mapping im Wizard (#50-Teil 2):** nicht Teil dieser Kette (Kickoff-Beschluss); NFO-Agent bleibt dafür die Heimat (bis E3, danach wie bisher).
- **Playwright/E2E-Grundgerüst:** verworfen zugunsten dokumentierter Handtest-Parcours (FP1, 5.3 Variante b) — keine neue Test-Infrastruktur (Klasse B) in einem jsdom-Projekt.
- **Wizard-Bibliothek (SmartWizard):** verworfen (ADR-03).
- **Entwurfsspeicherung (`localStorage`) für abgebrochene Wizard-Läufe:** verworfen für MVP ([scout] Fallstrick-Tabelle: Option a „Abbruch verwirft“).
- **#91-Hinweis in Schritt 1:** verworfen (ADR-02); Hintergrund-Index R12 bleibt eigenes, vorher zu messendes Item.
- **TVDB-Bilder als Artwork-Quelle:** verworfen (ToS schließen Bildnutzung ausdrücklich aus — [scout]).
- **OFDb-Cover (Option C) und Plex-Auto-Vorauswahl:** verworfen ([scout] Scraping rechtlich grau; [grafiker] Alex will explizite Kontrolle).
- **Dialog-Schleife für Reihen:** verworfen zugunsten Vorab-Queue (FP1, 5.4-Form).
- **3D-Poster-Effekte, Rechtsklick-Kontextmenüs im Artwork-Grid:** verworfen ([grafiker] „bewusst ignoriert“).
- **Doku/Anime in den Assistenten:** außen vor; `#context-movie`-Doku-Nutzung bleibt bis E3 erhalten, ein Doku-Wizard ist eigenes Item.

## Entscheidungen FP2 (Alex, 2026-11-06, verbindlich)

Alex: „Damit gebe ich FP2 frei.“ Die Entscheidungen im Wortlaut (zusammengefasst):
- **D1:** Schnitt A (kleine Etappen, E1 und E2 getrennt).
- **D2:** Option A: Auswahl-Grid nur aus TMDb-Bildern, kein Fanart.tv.
- **D3:** Alle fünf Design-Empfehlungen wie vorgeschlagen.
- **D4:** Filmreihen selten (ca. 1–2× im Monat), E6 bleibt am Ende.
- **D6 (a):** Fehler in `patch_nfo_fields()` bricht den Job sichtbar mit Fehler ab, kein stilles Weiterlaufen.
- **D6 (b):** Liegt im Inbox-Ordner schon eine `.nfo`, gewinnt der Wizard (NFO neu erzeugen + Wizard-Overrides schreiben).
- **D6 (c):** Ein im Wizard bewusst geleertes Feld (FSK/Genre/Plot) entfernt den Provider-Wert auch aus der NFO.

**Umsetzungshinweise zu D6 (vom Worker einzuhalten):**
- (b) betrifft nur den Inbox-Import-Pfad mit nicht-leeren Wizard-Overrides: `overwrite` wird dort erzwungen. Das Verhalten des NFO-Agenten und der Health-Quickfixes (`should_overwrite_nfo` für andere Aufrufer) bleibt unverändert.
- (c) braucht eine Unterscheidung „Feld nicht gesendet“ (unverändert) und „Feld bewusst leer gesendet“ (entfernen). Der Payload muss leere Werte explizit übertragen. `patch_nfo_fields()` bekommt dafür nur einen **opt-in-Parameter**; das heutige Ignorieren leerer Werte bleibt für den NFO-Agent-Pfad erhalten (Regressionstest).
- D2: Die TMDb-Rechtslage (dauerhaftes Speichern ist Bestand) ist für E5 durch die Entscheidung „Option A“ als Grundlage bestätigt; die schriftliche Festhaltung geschieht durch diese Freigabe. TMDb-Attribution ist Pflicht (E5-AK3).

## Offene Entscheidungen für Alex (FP2-Unterlage) — **alle entschieden, siehe oben**

- **D1 (Auflage 2):** Schnitt 1a/1b — Empfehlung **Schnitt A** (Vergleichstabelle oben). Entscheidungspunkt: akzeptiert Alex den temporären Doppel-Ablauf zwischen E1 und E2 gegen das Diff-Budget, oder will er den runden Ablauf ab der ersten Kette trotz ~150–190 KB?
- **D2 (Auflage 3, Rechtsfrage, Freigabepunkt):** Bildquellen neu formuliert: **Dauerhaftes Speichern von TMDb-Bildern ist bereits Bestand** (bei jedem TMDb-Import werden Poster/Backdrop/Logo automatisch gespeichert). Neu wäre nur (a) die **Auswahl** aus den vorhandenen TMDb-Bildlisten statt Automatik „bester Treffer“ und (b) **Fanart.tv als zusätzliche Quelle**. Option A (nur TMDb: Auswahl-Grid aus TMDb-Listen, klarste Terms, eine Attribution) vs. Option B (TMDb + Fanart.tv: zusätzlich HD-Logos/Clearart/Disc-Art, CC-BY-3.0-Attribution, zweiter API-Key, mehr Code). **Empfehlung: A als Etappe E5, Fanart.tv als bewusste Folge-Erweiterung, wenn TMDb-Auswahl im Alltag nicht reicht.** Begründung des Wechsels gegenüber der Synthese-Empfehlung B ([scout] hatte B empfohlen, weil sie Auswahl-Vielfalt nur mit Fanart.tv erreichbar sah; die TMDb-API liefert selbst Bild**listen** (Poster/Backdrops/Logos), die Auswahl braucht also keinen zweiten Provider; Nachtrag: die Python-Funktion `fetch_tmdb_images()` reduziert sie heute auf je eine URL, E5 braucht deshalb eine neue Funktion). Trade-off A: keine Disc-Art/Clearart über TMDb-Qualität hinaus. TVDB-Bilder bleiben ausgeschlossen (ToS); OFDb zurückstellen. **Schriftliche Festhaltung nötig** ([advocatus] Pkt. 6/8).
- **D3 (5.5, mit Empfehlung vorbelegt, bitte bestätigen):** gebündelte Design-Entscheidungen [grafiker]: (1) Fortschrittskopf Punkte mit Labels (nicht Balken); (2) Artwork als Tab-Wechsel Poster/Fanart (nicht beide Raster sichtbar); (3) „Überspringen“ in Schritt 2/3 ja (nicht Pflichtauswahl); (4) Provider-Fehler Inline-Badge + Banner (nicht nur Banner); (5) Abbruch-Dialog nur bei geänderten Eingaben (nicht immer).
- **D4 (5.4-Teilfrage, offen):** Wie oft kommen Filmreihen am Stück vor? (Bestimmt, ob E6 als letzte Etappe bleibt oder früher/entfällt; [produktberater] vermutet selten, Beleg fehlt.)
- **D5 (formal):** Git-Zustand (`git status --short --branch`) für die Ablage dieser Doku und alle späteren Git-Operationen. Stand 2026-11-06 (im Chat geprüft): `main...origin/main`, sauber, einziger Beifang der ungetrackte Session-Ordner; `main` HEAD `86fdc26`. Commit/PR braucht einen eigenen Branch und Alex-Go.
- **D6 (Nachtrag, offen, Produktentscheidung für E1):** (a) Soll ein Fehler beim Schreiben von FSK/Genre/Overrides (`patch_nfo_fields`) den Job abbrechen oder als sichtbare Warnung weiterlaufen? (b) Wenn im Inbox-Ordner (`current_dir`) schon eine `.nfo` liegt: Bestands-NFO patchen oder Wizard-Werte erzwingen (Overwrite)? (c) Soll ein im Wizard geleertes FSK-/Genre-Feld den Provider-Wert entfernen oder bleibt er stehen (Ist-Verhalten)? Empfehlung des Planers liegt nicht vor; Alex entscheidet, vor Start von E1.

## Zeitliche Einordnung (strikt getrennt, Hausregel)

KI-Umsetzung je Etappe 1–3 Tage. Engpass ist Alex: Review + Handtest-Parcours je Etappe 3–5 Tage, Freigabe-Wartezeit 1–2 Tage; D2-Rechtsklärung 1–3 Wochen (blockiert nur E5). Realistisch 7–12 Wochen Alex-Zeit bis E6 live; erster Alltagsgewinn (FSK/Genre im Import) bereits nach E1.

## Quellen, Referenzen & Lizenzen

- **Kein Third-Party-Code übernommen.** Externe Vorbilder (Emby Identify/Edit Images, Jellyfin Tabs, Stash Tagger, Picard Farbcode, Kodi Choose Art, TMM, Stripe-Punkt-Indikator, macOS-Finder-Gruppen) sind Patterns/Inspiration, keine Kopiervorlagen; Details + URLs in `scout.md` Abschnitt 1/6.
- **Wizard-Bibliotheken:** SmartWizard (`@smart-wizard/core`) nur geprüft, nicht eingesetzt (ADR-03) — Lizenz wurde nicht eigenständig geprüft und ist gegenstandslos, da die Bibliothek verworfen ist und keine Abhängigkeit/Lockfile-Änderung entsteht.
- **Künftige Assets (bei E5-Freigabe zu dokumentieren):** TMDb-Logo + „This product uses the TMDB API but is not endorsed or certified by TMDB.“ (Pflicht laut API Terms, 6-Monats-Cache-Limit §1.B beachten); bei Option B zusätzlich „Artwork from fanart.tv (CC-BY-3.0)“. Terms-Zitate und Abrufdatum 2026-11-06 in `scout.md` Abschnitt 3.
- **Bestehende Assets:** Lucide-Icons bereits im Projekt (SVGs in index.html) — keine neue Lizenzlast.
- **Rechtsstand:** keine Rechtsberatung; Entscheidung liegt bei Alex (D2), vor E5 schriftlich festzuhalten.

## Dissens- und Bedenkendokumentation (Pflicht)

- **[advocatus] VERDICT: REVISE gegen den Kickoff-Schnitt** — durch ADR-01/02 in den FP1-Schnitt übernommen; sein selbst benannter Nachteil der Teilung (temporäre Doppel-UI) bleibt als Trade-off von D1 dokumentiert und wird durch die E1-AK3-„Kern-Schmerz sofort behoben“-Logik begründet.
- **[produktberater]:** „Vergleich MVP-verzichtbar“ — nicht als Streichung, sondern als Reihenfolge übernommen (#55 bleibt E4). Bleibt offenes Risiko, falls Alex’ Alltag „immer nur ein Standard-Provider“ ist (D4-Antwort berührt das).
- **[scout] vs. [advocatus] Bildquellen:** [scout] „vermutlich gedeckte Grauzone“, [advocatus] „harter schriftlicher Blocker“ — es gilt die schärfere Linie (ADR-06). **Neu in Akt 2:** Empfehlung gewechselt von B ([scout]/Synthese) auf A — Begründung und Trade-off stehen offen unter D2; der Wechsel ist genau die Art von revidierter Empfehlung, die Alex dort explizit entscheidet.
- **[grafiker]:** Fehler-UX „NAS hängt beim Scan in Schritt 1“ kollidierte mit ADR-02 — Szenario-Behandlung wandert mit dem Hinweis nach Schritt 4/E2 (E2-AK4).
- **Zweiter Reviewer (Auflage 2):** sein Schnitt B ist mit Messwerten verglichen und **nicht übernommen** (Budget, Achsenzahl, Rollback) — die von ihm benannte Schwäche von Schnitt A (Doppel-Ablauf E1→E2) bleibt als akzeptierter Trade-off dokumentiert, nicht verschwiegen.
- **Max. 3 Review-Runden:** verbleibende Streitpunkte nach R3 wandern in „Offene Entscheidungen“ an Alex (Hausregel).

## Belege (Ablage dieser Akt-2-Artefakte)

Kein Produktionscode geändert, keine Git-Schreiboperation, keine Shell-Ausführung (bash verweigert). Alle Code-Verifikationen erfolgten mit Read/Grep auf den genannten Pfaden/Zeilen. Geschriebene Dateien: `briefing.md`, `ALEX_ZUSAMMENFASSUNG.md`, `plan-review-r1.md` (+ ggf. r2/r3) in diesem Session-Ordner.
