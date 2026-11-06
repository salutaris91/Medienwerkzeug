# Advocatus-Risikoprüfung — ROADMAP #92 „Geführter Film-Assistent" (Etappenvorschlag Kickoff)

**Rolle:** Advocatus (Risikoprüfer) im Kreativteam. Ich schreibe nicht, ich prüfe. Ziel dieses Beitrags ist nicht, den Etappenvorschlag schönzurechnen, sondern die Stellen zu benennen, an denen er zuerst bricht — mit Zeilenbeleg und konkretem Gegenvorschlag.

> Archivierungsvermerk (Orchestrator, 2026-11-06): Beitrag unverändert übernommen.

**Prüfmaßstab:** Eigenbau und Bibliothek werden gleich streng geprüft. Beim Eigenbau sind das Parsing/Escaping/Rendering und geteilte Film-/Serien-Codepfade; bei der (hier kaum involvierten) Bibliotheksseite sind es Lieferkette, Lizenz und Pinning. Das Diff-Budget (≤ 80 KB je Etappe), die Ein-Nutzer-Realität und der NAS-Deploy ohne automatischen Rollback bilden den Rahmen.

---

## 1. Etappe 1 zu groß — sie bricht zuerst an der Editor-Extraktion

**Befund:** Etappe 1 bündelt fünf unabhängige Achsen: (a) neuen Wizard-/Schrittrahmen, (b) Extraktion des NFO-Editors aus `app.js` in `js/`-Module, (c) Zusammenführung dreier UI-Orte (`#context-movie`, `#preview-modal-overlay`, `#modal-nfo-agent`) in vier Schritte, (d) Umzug von #91 aus Schritt 4 in Schritt 1, (e) neuen Ergebnis-Schritt. Das ist kein Schnitt, das ist ein Querschnitt durch die risikoreichste Stelle der Codebasis.

**Was zuerst bricht:** Die Editor-Extraktion. `app.js` hat 18.764 Zeilen und steckt mitten in der Modularisierung (9 ES-Importe). `js/nfo_ui.js` ist erst 74 Zeilen und enthält mit `prepareSeriesPayload()` (Zeile 60–74) bereits die **Serien**-Payload-Logik. Das beweist: Der NFO-Editor-Pfad ist nicht sauber nach Film/Serie getrennt, sondern verzahnt. Wer den Editor „für Film" extrahiert, berührt zwangsläufig Serien-Codepfade (Episoden-Mappings im `#modal-nfo-agent`, `media_type == "tv"` in `queue_api.py` ab Zeile 397). Extraktion + Zusammenführung + #91-Umzug + neuer Ergebnis-Schritt in einer Etappe bedeutet: vier Achsen, die sich gegenseitig im Review blockieren, und ein Diff, das sich nicht isoliert rollbacken lässt.

**Zerlegungsvorschlag prüfen:** „Rahmen + Editor für Import zuerst, NFO-Agent später" ist der richtige Instinkt, aber die Begründung muss schärfer sein als „NFO-Agent ist komplex":

- **Dafür spricht:** Der NFO-Agent (`#modal-nfo-agent`, index.html 3162–3315) ist der einzige der drei Orte, der Provider-Suche, FSK/Genre-Editor *und* Episoden-Mappings vereint — also die höchste Serien-Kopplung. Ihn aus Etappe 1 herauszulassen hält den Serien-Pfad komplett unangetastet. Der Film-Kern-Haupt-NFO-Editor (#50, „ohne Serien-Mapping") kann in Etappe 1 mit rein manuell/importierten Daten arbeiten, ohne Provider-Abrufe.
- **Dagegen spricht:** Ein Wizard mit vier Schritten, dessen Schritt 2 zunächst nur einen halben Editor (ohne Provider-Suche) zeigt, ist *alltagstauglich*, aber er erzwingt eine zweite Anlaufstelle für den Nutzer (alter NFO-Agent für Provider-Suche, neuer Wizard fürs Editieren). Das ist genau die Dreifach-UI, die #92 eigentlich beseitigen soll — nur temporär neu aufgeteilt.

**Gegenvorschlag:** Etappe 1 in zwei Schnitte teilen: **1a** = Schrittrahmen + Extraktion des Film-Editors (ohne Serien-Mapping, ohne Provider-Suche) in neue `js/`-Module; **1b** = Konsolidierung der drei Orte + #91-Umzug + Ergebnis-Schritt. Kopplung 1a→1b ist klar (1b verbraucht die 1a-Module), aber 1a ist isoliert verifizierbar und rückrollbar, ohne den NFO-Agent anzufassen.

---

## 2. Serien-Regression bei #50 — geteilte Pfade und fehlende E2E-Tests

**Befund — geteilte Film-/Serien-Pfade:**
- `gui/static/js/nfo_ui.js` Zeile 60–74: `prepareSeriesPayload()` schreibt `mw_data`, `source_url`, `resolved_topic` in den Payload — Serien-Logik liegt schon im Modul, nicht isoliert in `app.js`.
- `gui/static/app.js` `#modal-nfo-agent` (index.html 3162–3315): Episoden-Mappings-Rendering ist im selben Modal wie der Film-Editor.
- `gui/api/queue_api.py` Zeile 397: `elif media_type == "tv"` — der `preview_process`-Pfad verzweigt nach Film/Serie, mit eigener Subtitle-/Naming-Logik.
- `gui/mw_metadata.py`: Film und Serie teilen sich die Provider-Abruf- und Metadaten-Pfade.

Die Gefahr ist nicht „Serie kaputt", sondern **still verändertes Serien-Verhalten beim Film-Umbau**: `nfo_overrides`, Episoden-Mappings und Subtitle-Matching teilen sich Funktionen, deren Signaturen beim Extrahieren verschoben werden.

**Verhaltensneutral extrahieren ohne window-Hacks:** Das Projekt hat bereits das saubere Muster (ES-Importe aus `./js/*.js`). Der window-Hack-Verzicht ist machbar, aber nur wenn die Extraktion reine *Verschiebung* bleibt (Funktion 1:1, Signatur unverändert) und kein „Refactoring nebenbei" passiert. Das ist die einzige Verteidigungslinie gegen stille Serien-Regressionen — und genau deshalb darf Etappe 1 den NFO-Agent nicht anfassen (siehe Punkt 1).

**Regressionstests — was fehlt:** Vorhanden sind Backend-Tests (`test_similar_titles_hint.py`, `test_nfo_and_series_folder_fixes.py`, `test_match_episodes_season.py`, `test_fix_series_queue_and_naming.py`) und Frontend-Unit/jsdom-Tests (`tests/frontend/nfo_ui.test.js` u. a.). **Es gibt kein E2E/Integrationstest-Band** (kein Playwright/Cypress o. Ä. im Baum sichtbar), das einen vollständigen Nutzer-Durchlauf „Film wählen → editieren → verarbeiten" bzw. „Serie → Episoden-Mapping → verarbeiten" abdeckt. Damit ist genau die Regression, die eine Editor-Extraktion verursacht (UI-Element-ID verschoben, Handler-Reihenfolge geändert, Payload-Feld umbenannt), durch die vorhandenen jsdom-Tests *nicht* abfangbar — die testen Funktionen isoliert, nicht den verdrahteten Ablauf.

**Gegenvorschlag:** Vor der Editor-Extraktion ein minimales E2E-Grundgerüst (Playwright, zwei Happy-Path-Szenarien: Film und Serie) aufsetzen, das gegen den *unveränderten* Stand grün ist. Das ist der Referenzpunkt, gegen den jede Extraktion verhaltensneutral nachgewiesen wird. Ohne diesen Referenzpunkt ist „verhaltensneutral" eine Behauptung, kein Beleg.

---

## 3. #91-Timing — der Scan darf nicht in Schritt 1 wandern

**Befund:** Der #91-Scan läuft synchron in `/api/preview_process` (`queue_api.py` Zeile 366–395): `find_movie_folders_by_id` (Stufe 1) und `find_similar_movie_folders_by_name` (Stufe 2), beide gegen `target_base` (Default `"/Filme"`, Zeile 144–145). Er läuft **pro Vorschau zweimal**, blockierend, und der Zielordner existiert erst als finale Auswahl — nicht als Eingabe in Schritt 1.

**Optionen-Bewertung:**
- **(a) Eigener lighter Scan-Endpoint in Schritt 1:** Der Killer-Fehlerfall ist nicht der doppelte Scan, sondern: **Ein hängendes NAS/SMB-Mount blockiert den Einstieg des gesamten Assistenten.** Der Wizard startet mit Schritt 1; hängt der Scan dort, kommt der Nutzer nicht einmal bis zur manuellen Eingabe. Zusätzlich entsteht ein zweiter Fehlerpfad (neuer Endpoint + neue Timeout-/Fehler-UX) zusätzlich zum bestehenden. Und es gibt *immer noch* kein Ergebnis in Schritt 1, solange der finale Zielordner nicht gewählt ist — der Scan in Schritt 1 müsste gegen einen Default-Ordner laufen, der in Schritt 4 falsch sein kann. Doppelter Scan plus falscher Ordner: schlechte Kombination.
- **(b) Hinweis bleibt in Schritt 4:** Am wenigsten riskant. Die Ähnliche-Titel-Logik bleibt, wo sie heute verifiziert funktioniert (Schritt 4 = Ergebnis/Vorschau). UX-Nachteil: Der Nutzer erfährt Duplikate erst am Ende. Für einen Ein-Nutzer-Assistenten, der ohnehin pro Film durchläuft, ist das akzeptabel — vor allem gegenüber einem blockierten Wizard-Einstieg.
- **(c) R1/R12 vorziehen (Hintergrund-Index statt Live-Scan):** Der architektonisch saubere Weg, aber er ist ein eigenes Feature, kein Etappen-Teil von #92. Er müsste mit Scan-Dauer-Messung (die ausdrücklich noch nicht gemacht ist) *vor* einer Entscheidung belegt werden. Als Teil von Etappe 1 aufgebläht ist er ein Budget-Killer.

**Gegenvorschlag:** #91 in Etappe 1 **nicht umziehen**, sondern in Schritt 4 belassen (Option b). R1/R12 als separate Vor-Etappe führen — aber erst nach Scan-Dauer-Messung, sonst optimiert man einen nicht gemessenen Flaschenhals. Option (a) verwerfen: Der Wizard-Einstieg darf unter keinen Umständen von einem Netzwerk-Scan abhängen.

---

## 4. Rate-Limits und Last — Fehlerhäufung ist das eigentliche Risiko, nicht das Limit

**Befund:** `gui/mw_metadata.py` `fetch_json_with_retry` (Zeile 148, `timeout=15`, `attempts=3`) deckt nur JSON ab. HTML (OFDb, fernsehserien.de, Mediathek) und **Binär (Artwork-Downloads) haben kein Retry**. Das ist heute bewusst als „Teil 2 offen" eingetragen.

**Die drei Last-Quellen und ihre Fehlerprofile:**
- **#55 Multi-Provider-Badges (parallele Detail-Abrufe pro Feld):** Viele parallele Requests pro Feld erhöhen die Wahrscheinlichkeit, dass *einer* scheitert — nicht wegen TMDb-Global-Limit (~50 req/s), sondern wegen OFDb-Scraping/HTML-Instabilität und TVDB-Token. Ein einzelner fehlgeschlagener Provider darf nicht das Feld auf „unbekannt" setzen.
- **#69 Reihen-Schleife (N Filme = N Metadaten-Abrufe):** Das Risiko ist nicht das Rate-Limit, sondern die **Fehlerhäufung**: Bei N Abrufen mit je 3 Retries à 15 s Timeout wächst die Worst-Case-Dauer linear und ein hängender Provider blockiert die ganze Schleife. Backoff ist für HTML/Binär nicht vorhanden.
- **#51 Artwork-Downloads (Binär ohne Retry):** Ein abgebrochener Binär-Download hinterlässt heute potenziell eine halbe Datei oder gar kein Feedback. Ohne Retry und ohne Partial-Download-Erkennung ist das eine stille Fehlerquelle — genau die Klasse, die die Hausregeln („Fehler müssen sichtbar sein, kein stilles Scheitern") verbieten.

**UX bei Teilerfolg:** Schritt 2 darf nicht atomar scheitern. Der Editor muss „3 von 4 Provider geladen, 1 fehlgeschlagen (mit Grund)" darstellen können, nicht alles verwerfen.

**Gegenvorschlag:** Vor Etappe 2 (#55) und Etappe 4 (#69) ein einheitliches Abruf-Rahmenwerk einführen (Backoff mit Jitter, Timeout-Budget pro Feld statt pro Request, Teil-Erfolg-Status). Artwork-Downloads (Etappe 3) erhalten Retry + Integritätsprüfung (Bytes erwartet vs. empfangen). Ohne das ist #69 eine Schleife, die am ersten hängenden Provider hängen bleibt.

---

## 5. Diff-Budget ≤ 80 KB vs. Realität — Etappe 1 sprengt es am Umbau, nicht am Zuwachs

**Befund:** `app.js` hat 18.764 Zeilen. Ein Diff zählt Löschung *und* Neubau. Die drei UI-Orte umfassen zusammen mehrere hundert Zeilen (`#modal-nfo-agent` ~150, `#preview-modal-overlay` ~80, `#context-movie` ~110 in index.html plus die zugehörigen app.js-Handler). Hinzu kommen: neuer Wizard-Rahmen (neues Markup + Steuerlogik), #91-Umzug (Handler verschieben), Ergebnis-Schritt (neu). Selbst wenn die Netto-Zeilenzahl sinkt, entsteht der Diff aus „alte Blöcke entfernt" + „neue Blöcke angelegt" — das summiert sich bei einer monolithischen Datei schnell über 80 KB, *bevor* ein einziges neues Modul angelegt ist.

**Leinen, die das begrenzen:**
- **Neue `js/`-Module statt app.js-Edits:** Reduziert den app.js-Diff auf Import-Zeile + Löschung des alten Blocks. Aber der alte Block muss trotzdem gelöscht werden — die Ersparnis ist real, aber nicht null.
- **Etappe 1 zwingend in zwei PRs/Etappen (1a + 1b)** — siehe Punkt 1. Das ist die effektivste Budget-Leine, weil jede Achse ihren eigenen Diff bekommt.
- **Kein „Refactoring nebenbei"** während des Verschiebens (window-Hacks raus, aber keine Umbenennungen/Signatur-Änderungen), sonst explodiert der Diff ohne Verhaltensgewinn.

**Gegenvorschlag:** Etappe 1 als zwei Etappen budgetieren und die ≤ 80 KB **je Etappe** als harte Kante durchsetzen. Wer die Editor-Extraktion *und* die Konsolidierung *und* den #91-Umzug in einem Diff sieht, hat faktisch schon drei Etappen gebaut.

---

## 6. R8-XSS (Zeile 10488) — der richtige Moment zum Fixen ist das Verschieben, nicht das Mitnehmen

**Befund (verifiziert):** `gui/static/app.js` Zeile 10488: `dest.innerHTML = data.destination.replace(/\n/g, '<br>');` — `data.destination` wird **ohne Escaping** in `innerHTML` geschrieben. Bekannt als R8-XSS, offen, in ROADMAP mit #67+R8 als Alternative notiert. Direkt darüber (Zeile 10493–10494) wird bei den Checkboxen korrekt `escapeHTML()` verwendet — der Code weiß also, wie es geht, wendet es aber an dieser Stelle nicht an.

**Wird der Code mitgenommen?** Wenn der Ergebnis-Schritt (Schritt 4) den Zielpfad anzeigt, wandert exakt diese Zeile (oder ihr Äquivalent) in den neuen Schritt. Das ist eine **Verschleppung eines bekannten XSS in neuen Code** — das Gegenteil dessen, was ein Umbau leisten soll.

**Schweregrad-Einordnung:** Ein-Nutzer-App relativiert das Risiko stark (kein fremder Angreifer mit DOM-Zugriff), aber `destination` kann importierte/abgeleitete Daten (Dateinamen, Ordnernamen, API-Rückgaben) enthalten, die nicht vollständig nutzerkontrolliert sind. Es ist kein akutes Remote-XSS, aber eine Stelle, die beim Anfassen des Codes ohnehin angefasst wird.

**Gegenvorschlag:** Beim Verschieben in den Ergebnis-Schritt `escapeHTML()` anwenden (Zeile 10488 fixen), **nicht** den unescaped Code 1:1 mitnehmen. Das ist ein Drei-Zeilen-Fix im Zuge einer ohnehin stattfindenden Bewegung — die billigste Art, R8 abzuräumen, die es geben wird.

---

## 7. Theme-/Layout-Risiko — externes Artwork ist mehr als ein CSS-Problem

**Befund:** 5 Themes (deep-space, nordic-slate, amber-warmth, apple-black, superfood-light), wobei alte Bereiche generierte `inline-style-NN`-Klassen nutzen und das neue `mw-modal`-Muster existiert. Artwork (Etappe 3) bringt **externe Bilder** (TMDb/fanart.tv) in ein Grid.

**Fehlerfälle:**
- **Ladezeit:** Externe Bilder ohne Lazy-Loading/Preconnect blockieren das Rendern des Ergebnisschritts; bei 5 Themes braucht es Overlay/Kontrast je Theme, sonst ist Text auf hellen Postern unlesbar.
- **Fehlende Poster:** Kein Poster vorhanden → Broken-Image-Icon ohne Fallback. Ein Grid mit 20 Einträgen, von denen 5 kein Poster haben, braucht ein definiertes Platzhalter-Bild/State — das ist ein eigenes UI-Element, kein Einzeiler.
- **CSP/Hotlinking:** Falls eine Content-Security-Policy mit restriktivem `img-src` gesetzt ist, bricht externes Hotlinking. Heute lädt die App offenbar ohne CSP-Bildrestriktion, aber das ist eine Annahme, die vor Etappe 3 **geprüft** werden muss (Header/Config), nicht angenommen.

**Gegenvorschlag:** Artwork-Grid in Etappe 3 mit explizitem Broken-Image-Fallback, Lazy-Loading und Theme-Overlay-Klasse spezifizieren; CSP-`img-src`-Ist-Zustand vorher feststellen. Das gehört in die Etappe-3-Spezifikation, nicht als Nachgedanke.

---

## 8. Rechtsrisiko Artwork — scharf als harter Blocker formulieren

**Befund:** Der Etappenvorschlag setzt Etappe 3 (#51 Artwork) bereits als „erst nach Rechtsklärung TMDb/fanart.tv" an. Das ist richtig, aber zu weich formuliert, weil der Kern des Rechtsrisikos unbenannt bleibt: **Es geht nicht ums Anzeigen, sondern ums Speichern.** TMDb-Bilder sind über die TMDb-API (Terms) abrufbar, aber dauerhaftes lokales Ablegen (in Ordner/NFO, ins Docker-Image, in `data/`) ist urheberrechtlich eine andere Kategorie als Hotlinking/Anzeige. fanart.tv hat eigene API-Key-Bedingungen und Nutzungsregeln, die vom TMDb-Vertrag abweichen.

**Wie scharf formulieren:** „Etappe 3 startet erst nach **schriftlich dokumentierter** Klärung folgender Fragen: (a) Darf das Tool Artwork dauerhaft lokal speichern (nicht nur anzeigen)? (b) Unter welcher Lizenz/Attribution? (c) Ist fanart.tv für diesen Zweck überhaupt zulässig, oder fällt es auf TMDb-only zurück?" — „Schriftlich" ist wichtig: Eine informelle „das passt schon"-Einschätzung ist bei Urheberrecht kein Freigabepunkt, sondern ein späteres Rechtsproblem im Betrieb.

**Konsequenz für den Etappenschnitt:** Solange die Klärung offen ist, muss der Assistent auch **ohne** Artwork vollständig funktionieren (Schritt 3 optional/überspringbar). Das muss Etappe 1 bereits einplanen — der Schrittrahmen darf nicht hart vier Schritte verlangen, wenn Schritt 3 rechtlich blockiert ist.

---

## 9. Betrieb — Etappengröße als Rollback-Risiko

**Befund:** NAS-Deploy per CI-Image (`.github/workflows/docker-build.yml`), kein Git auf dem NAS, kein automatischer Rollback, kein DB-Migrationsschritt (Settings als `data/settings.json`/`.env`). Rollback bedeutet manuell: vorheriges Image-Tag/-Digest gezielt pullen (sofern noch in der Registry) statt `latest`, dann `docker compose up -d`.

**Das eigentliche Risiko:** Je größer die Etappe, desto mehr Features fallen bei einem Rollback gemeinsam zurück. Eine 5-Achsen-Etappe 1 bedeutet: Schlägt der Ergebnis-Schritt fehl, muss der Nutzer auch den neuen Editor, den #91-Umzug und den Wizard-Rahmen zurückrollen — alles oder nichts. Das widerspricht dem Etappenziel „jede Etappe einzeln alltagstauglich", weil „einzeln rückrollbar" nicht mit „einzeln alltagstauglich" gleichgesetzt wurde.

**Gegenvorschlag:** Etappenschnitt so wählen, dass jede Etappe **einzeln rückrollbar** ist, ohne Datenverlust. Vor jedem Update das laufende Image-Digest notieren (`docker inspect --format '{{.Image}}' …`), damit Rollback nicht davon abhängt, ob die Registry das alte `latest` noch kennt. Die 1a/1b-Teilung aus Punkt 1 zahlt hier doppelt ein: zwei unabhängige Rollback-Punkte statt einem.

---

## VERDICT: REVISE

Der Etappenvorschlag des Kickoffs ist als Richtung tragfähig, aber Etappe 1 ist überladen und enthält einen Designfehler (#91-Umzug in den Wizard-Einstieg). Der Schnitt muss so geändert werden, dass (a) der Serien-Pfad in der ersten Etappe unberührt bleibt, (b) der Wizard-Einstieg nie von einem Netzwerk-Scan abhängt und (c) jede Etappe einzeln rückrollbar ist.

**Nummerierte Einwände:**

1. **[kritisch]** Etappe 1 bündelt fünf unabhängige Achsen (Rahmen, Editor-Extraktion, Drei-Orte-Konsolidierung, #91-Umzug, Ergebnis-Schritt) in einem Diff, der weder verifizierbar noch rückrollbar ist. → In 1a (Rahmen + Film-Editor-Extraktion) und 1b (Konsolidierung + Ergebnis) teilen; NFO-Agent/Serien-Mapping aus Etappe 1 komplett heraushalten.

2. **[kritisch]** #91-Hinweis soll in Schritt 1, aber der Scan hängt synchron an `/api/preview_process` (`queue_api.py` 366–395) gegen den finalen Zielordner. Ein hängendes SMB/NAS im Wizard-Einstieg blockiert den gesamten Assistenten (Option a). → #91 in Schritt 4 belassen (Option b); R1/R12 als separate Vor-Etappe erst nach Scan-Dauer-Messung (Option c).

3. **[wichtig]** Die Editor-Extraktion berührt geteilte Film-/Serien-Pfade (`nfo_ui.js` 60–74, `queue_api.py` 397, Episoden-Mappings im `#modal-nfo-agent`). Es existiert **kein E2E-Testband**, das einen vollständigen Film-/Serien-Durchlauf gegen den unveränderten Stand abdeckt — damit ist „verhaltensneutral extrahieren" nicht nachweisbar. → Minimales E2E-Grundgerüst (Playwright, Film + Serie) vor der Extraktion aufsetzen.

4. **[wichtig]** R8-XSS (`app.js` 10488, `data.destination` unescaped in `innerHTML`) würde mit dem Zielpfad in den neuen Ergebnis-Schritt verschleppt. → Beim Verschieben `escapeHTML()` anwenden (Muster existiert direkt darüber, Zeile 10493–10494); nicht 1:1 mitnehmen.

5. **[wichtig]** Das ≤ 80-KB-Budget wird durch Löschung + Neubau der monolithischen `app.js` (18.764 Zeilen) gesprengt, nicht durch Feature-Zuwachs. → Etappe 1 als zwei Etappen budgetieren; neue `js/`-Module statt app.js-Edits; strikt „Verschieben ohne Refactoring".

6. **[wichtig]** Artwork-Rechtslage (TMDb/fanart.tv) ist als Blocker zu weich formuliert — es geht ums **dauerhafte lokale Speichern**, nicht ums Anzeigen. → Etappe 3 erst nach schriftlich dokumentierter Klärung (Speichern erlaubt? Lizenz? fanart.tv zulässig?); der Schrittrahmen in Etappe 1 muss Schritt 3 optional/überspringbar auslegen.

7. **[wichtig]** Fehlerhäufung bei #55/#69/#51: HTML/Binär ohne Retry (`mw_metadata.py`, nur JSON via `fetch_json_with_retry` 148), N-fache Abrufe ohne Backoff, Artwork-Downloads ohne Integritätsprüfung. → Einheitliches Abruf-Rahmenwerk (Backoff/Jitter, Timeout-Budget pro Feld, Teilerfolg-Status) vor Etappe 2; Artwork mit Retry + Byte-Prüfung.

8. **[kosmetisch]** Artwork-Grid (Etappe 3) ohne Broken-Image-Fallback, Lazy-Loading und Theme-Overlay; CSP-`img-src`-Ist-Zustand ungeprüft. → Vor Etappe 3 spezifizieren und Header/Config prüfen.

9. **[kosmetisch]** Kein automatischer Rollback auf dem NAS; Etappengröße = Alles-oder-nichts-Rollback. → Image-Digest vor jedem Update notieren; Etappen einzeln rückrollbar schneiden (korreliert mit Einwand 1 und 5).
