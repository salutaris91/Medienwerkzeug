# produktberater — Rückblick-Abnahme ROADMAP #54 Teil 1 (2026-10-01)

> Kontext: Abnahme-Session zu Branch a2/20261001T171506Z. Diff-Check/Nutzen-Check als fester Teil der Rückkanal-Konsultation (seit 2026-09-02). Beitrag ungekürzt archiviert, Original vom 01.10.2026.

---

## Bewertung je Prüfauftrag

### 1. Trifft Teil 1 das Nutzerbedürfnis?

**Ja, die relevanten Flows sind abgedeckt.** Ich habe ~25 Umstellungen gezählt, darunter alle kritischen Pfade:

- **NFO-Agent-Suche (interaktiv):** TMDb Film/TV (IMDB/TMDB-ID/Text, 6 Stellen), TVDB Suche, TVmaze Suche
- **NFO-Agent-Details:** TMDb Film/Serie/Episode, TVDB Serie/Episode, TVmaze Episoden
- **Episodenlisten (Pagination):** TVDB (2×, mit Cache), TMDb TV
- **Mediathek:** Suche, Episoden, Fallback-Query
- **Artwork-Beschaffung:** TMDb Bilder (JSON, nicht der Download)

Die UI-relevanten Such-Flows (Nutzer tippt Titel → Ergebnisliste) profitieren direkt. Batch-Jobs (Staffel-Scan über alle Seasons) ebenfalls.

### 2. Ist die 1/2-Teilung sinnvoll?

**Ja, die Teilung ist produktseitig sauber begründet.** `fetch_html_with_retry` existiert bereits (Zeile 153), Teil 2 ist wirklich mechanisch. Die offen gelassenen Stellen sind:

- `_download_with_timeout` (Binär, Zeile 9-13) — 15+ Aufrufe für Poster/Fanart/Logo/Banner/Thumbnails
- `search_ofdb` (Zeile 816) — HTML-Scraping
- `resolve_mediathek_url_topic` (vermutlich HTML)

Artwork-Downloads sind weniger zeitkritisch (kein "Hängen" in der UI-Suche, sondern Batch-Import). Die Teilung erzeugt kein "halbfertig"-Gefühl, sondern ist eine sinnvolle Risikominimierung: JSON ist der häufigste Fall und betrifft die interaktiven Flows direkt.

### 3. Scope-Disziplin

**Die Änderungen wirken diszipliniert mechanisch.** Ich sehe:

- Keine Funktions-Umbenennungen
- Keine neuen Funktionen oder Abstraktionen
- Keine Logik-Änderungen in den Fehlerpfaden (try/except drumherum unverändert)
- Konsistentes Muster: `urlopen(req, timeout=X)` → `fetch_json_with_retry(lambda: ..., timeout=10, context="...")`
- Die `context=`-Parameter sind aussagekräftig (`"TVDB Episoden {show_id} S{season} p{page}"`) und helfen beim Debugging.

**518 Zeilen sind plausibel** für ~25 Umstellungen mit Lambda-Wrapper, context-String und Einrückung.

**Eine subtile Abweichung:** Einige Stellen nutzen `fetch_json_with_retry` **ohne** `timeout=10` (Zeilen 576, 597, 619, 656, 678, 698, 1305, 1339, 1439, 1591). Der Default ist `timeout=15`. Das ist eine konsistente, aber nicht dokumentierte Abweichung vom "10s-Timeout" aus der ROADMAP. Könnte Absicht sein (TMDb braucht länger?) oder Übersehen.

### 4. Latenz-Kaufpreis

**Worst-Case hat sich verdreifacht:** 3 Versuche × 10s + 1s + 2s Backoff = **33s pro Abruf** statt 10s.

- Bei TVDB-Pagination: pro Seite bis zu 33s
- Bei NFO-Agent-Suche (TMDb + TVDB hintereinander): mehrere Abrufe
- **Normalfall:** 10s + sofortige Antwort (kein Retry nötig)
- **UI-Verhalten:** asynchron, blockiert nicht

**Für den Ein-Personen-Heimnetz-Fall akzeptabel**, aber Alex sollte wissen:
- Die 33s sind nur im Fehlerfall (transiente Hänger)
- Die `context=`-Parameter machen sichtbar, **wo** es hängt
- Die Alternative (kein Retry) wäre: sofortiges Scheitern bei transienten Hängern

### 5. Sichtbarkeit ("teils still scheitern")

**Nur teilweise gelöst.** `_open_with_retry` loggt via `log_message(f"⚠️ [Metadaten] Versuch {attempt}/{attempts} fehlgeschlagen ({context}): {e}")` — das ist sichtbar.

**Aber:** Die umgestellten Funktionen haben weiterhin ihre eigenen Fehler-Logs:

- TVDB Login/Suche: `print(f"[TVDB Login Error] ...", file=sys.stderr)` — **NICHT** `log_message`
- TMDb TV Fetch: `print(f"[TMDB TV Fetch Error] ...", file=sys.stderr)` — **NICHT** `log_message`
- NFO-Agent-Flows: `log_message(f"⚠️ [NFO Agent] ...")` — **sichtbar**

Das "teils still scheitern" ist nur für die Retry-Versuche behoben, nicht für den endgültigen Fehlschlag in den interaktiven Such-Flows. Die ROADMAP sagt "loggen Fehlversuche sichtbar" — das ist nur teilweise erfüllt.

### 6. ROADMAP-Pflege

**Konsistent.** Zeile 63 (`teilweise (Teil 1 erledigt)`) spiegelt den Detail-Stand in Zeile 1632-1634 wider. Die Aufteilung JSON jetzt / HTML+Binär später ist klar dokumentiert.

---

## Gesamturteil: **trifft Bedarf teilweise**

**Begründung:**
Die mechanische Umstellung ist sauber, diszipliniert und testabgedeckt. Die relevanten NFO-Agent- und Such-Flows profitieren direkt. Aber:

1. **Sichtbarkeit unvollständig:** Retry-Versuche sind sichtbar (`log_message`), aber endgültige Fehlschläge in den Such-Flows (TVDB, TMDb) gehen immer noch via `print stderr` — nicht in den für Alex sichtbaren Log.
2. **Timeout-Abweichung undokumentiert:** Einige Stellen nutzen 15s Default statt 10s — nicht in ROADMAP oder Commit-Message erwähnt.
3. **Latenz-Kaufpreis nicht explizit gemacht:** 33s Worst-Case sind akzeptabel, aber Alex sollte das wissen.

---

## Rückfragen an Alex

1. **Sichtbarkeit der endgültigen Fehlschläge:** Soll das noch Teil 2 werden (oder separater Fix), dass die Such-Flows (TVDB, TMDb) ihre `print stderr` auf `log_message` umstellen? Das wäre konsistent mit den NFO-Agent-Flows.

2. **Timeout-Vereinheitlichung:** Ist die 15s-Default an den TMDb-Stellen Absicht (TMDb braucht länger?) oder soll das auf 10s vereinheitlicht werden? Die ROADMAP sagt "10s-Timeout".

3. **Latenz-Akzeptanz:** Akzeptierst du die Worst-Case-Latenz von 33s pro Abruf, oder soll ein Circuit-Breaker / Max-Total-Timeout diskutiert werden (z.B. "nach 20s gesamt abbrechen")?

---

## Bewusst nicht getan (gut so)

- **HTML/Binär-Abrufe** (Artwork-Downloads, OFDb-Scraping, Mediathek-HTML) — sinnvoll als Teil 2, weniger zeitkritisch
- **Keine Nebenrefactorings** — keine Logik-Änderungen, keine Funktions-Umbenennungen, keine neuen Abstraktionen
- **Fehlerbehandlungs-Struktur unverändert** — try/except drumherum blieb wie vorher, nur der innere Aufruf wurde getauscht
- **Keine Änderungen an Cache-Logik** — TVDB-Episoden-Cache (tempfile) blieb unverändert
- **Keine UI-Änderungen** — reine Backend-Umstellung, kein Risiko für Frontend-Regressionen
