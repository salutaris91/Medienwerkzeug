# advocatus — Rückblick-Abnahme ROADMAP #54 Teil 1 (2026-10-01)

> Kontext: Abnahme-Session zu Branch a2/20261001T171506Z (JSON-Abrufe in gui/mw_metadata.py auf fetch_json_with_retry umgestellt). Beitrag ungekürzt archiviert, Original vom 01.10.2026.

---

# Review — ROADMAP #54 Teil 1 (Rückblick-Abnahme, Branch a2/20261001T171506Z)

Rolle: Advocatus/Risikoprüfer, schreibgeschützt. Ich habe die drei Dateien selbst gelesen und gegen die Vorab-Fakten geprüft. **Einschränkung vorab:** Mir steht kein Bash/git-Zugriff zur Verfügung — ich konnte den tatsächlichen `git diff` zum Vorher-Zustand **nicht** ausführen und die Tests **nicht** laufen lassen. Die Fehlerpfad-Treue-Bewertung stützt sich daher auf die noch vorhandenen `except`-Klauseln und den plausiblen Alt-Code, nicht auf den realen Diff.

---

## Findings nach Schwere

### [kritisch]
Keine gefunden.

### [wichtig]

**1. A2-Reviewer-Finding „Fehlerbehandlung für den externen Aufruf fehlt“ ist ungeklärt** (`a2-eskalation.md:7`)
Nicht eindeutig einer Stelle zuordenbar. Meine Prüfung: alle 24 umgestellten Aufrufstellen haben ein umgebendes `try/except` (teils breit `except Exception`, teils spezifisch). Plausibelster Kandidat ist der Helfer selbst (`mw_metadata.py:150`): `json.loads(_open_with_retry(...).decode())` hat **kein** eigenes `try/except` — `JSONDecodeError` (leerer Body, Gateway-Fehler-HTML) und `UnicodeDecodeError` (nicht-UTF‑8) propagieren roh. Aufrufer ohne `except json.JSONDecodeError` (z. B. `fetch_tmdb_tv:742`, `search_mediathek:2713`, `fetch_movie_nfo_data`-TMDB-Zweig `:1437`) fangen das nur als generische Exception. Ob genau das gemeint war, ist ohne Review-Log nicht entscheidbar. **Status: offen/unbestimmt.** → Alex muss das Review-Log des A2-Loops (Review-Call 1) ansehen oder das Finding explizit als offenes Risiko in ROADMAP/STAND dokumentieren.

**2. Fehlerpfad-Klassenhierarchie: Read-Timeouts umgehen `_handle_metadata_error`** (`mw_metadata.py:140-145` vs. Aufrufer)
Nach endgültigem Scheitern re-raiset der Helfer `last_error`, das je nach Ursache `TimeoutError` (Read-Timeout) oder `ConnectionError` ist — beides **nicht** `urllib.error.URLError`. In Aufrufern wie `get_tvdb_token:190-204`, `search_tvdb:237-252`, `search_tmdb_movie:583-591` fängt `except urllib.error.URLError` diese Fälle nicht; sie fallen in `except Exception` und **umgehen `_handle_metadata_error`**. Folge: Read-Timeouts werden nach 3×10 s + Sleeps nur geloggt und als `[]`/`None` zurückgegeben, statt in `MetadataProviderUnavailable(503)` übersetzt zu werden. Dies ist *wahrscheinlich* Bestand-Verhalten (direkt `urlopen`/`read` warf vorher ebenfalls `socket.timeout`), aber die Umstellung adressiert es nicht und kein Test deckt es ab. Als Risiko dokumentieren.

**3. Test `test_fetch_movie_nfo_data_logs_and_returns_error_after_retries` ist irreführend** (`tests/test_metadata_retry.py:88-101`)
Patscht weder `TMDB_API_KEY` noch `make_tmdb_request`. `conftest.py` setzt keinen Key. Bei leerem Key (CI/ohne `.env`) wirft `check_tmdb_auth_method` (`mw_metadata.py:81-83`) `MetadataProviderUnavailable` **bevor** `urlopen` feuert — der Test läuft dann grün, ohne dass ein einziger Retry-Versuch stattfindet. Der Kommentar „Three retry logs“ (Zeile 100) stimmt in diesem Fall nicht. (Bestand aus dem Juli-Fix, aber relevant für die Abnahme-Erwartung.) → Analog zu `test_fetch_tmdb_tv` (Zeile 150) sollte `mw_metadata.TMDB_API_KEY` gepatcht werden.

**4. Testlücke: `timeout=10` wird nirgends assertionsgeprüft** (`tests/test_metadata_retry.py`)
Die Vorgabe „timeout=10 beibehalten“ ist nicht durch Tests abgesichert; der Helfer-Default ist 15 (`mw_metadata.py:148`). Eine versehentliche Nicht-Übergabe bliebe unbemerkt. Ebenfalls ungetestet: `get_tvdb_token`-POST-Retry (`:182`, Wiederverwendung der `data`-Bytes über Lambda), TVDB-Pagination (`:263`, `:1533`, `:2171`), der zweistufige Mediathek-Fallback-Abruf (`:2796`) sowie HTTPError-404-Durchgriff auf Funktionsebene **nur** für `search_tvmaze` (`:222-237`), nicht für `search_tvdb`/`fetch_tmdb_tv`/`search_mediathek`.

### [kosmetisch]

**5. `decode()`-Semantik** (`mw_metadata.py:150`)
Alt `json.load(response)` tolerierte UTF‑8/16/32-BOM; neu `json.loads(bytes.decode())` ist strikt UTF‑8 ohne BOM-Toleranz. Praktisch irrelevant für TMDb/TVDB/TVmaze/mediathekview (liefern UTF‑8 ohne BOM), aber die Toleranz geht verloren.

**6. Kumulierte Latenz bei Offline** (`mw_metadata.py:263`, `:1530`, `:2168`; `search_all_db:323-414`)
Jeder Abruf kann bei persistentem Fehler bis zu 3×(timeout+sleep) ≈ 33 s (timeout=10) bzw. 48 s (timeout=15) dauern. `search_all_db` führt bis zu 8 Provider-Suchen sequenziell aus (+Umlaut-Fallback) → minutenlange Blockade bei offline-NAS. Der Abbruch in den Paginationsschleifen via `break` ist **korrekt** (kein Duplikat/Endlosschleife), aber die kumulierte Latenz ist ein UX-Risiko.

---

## Verifikation der Vorab-Fakten (Bestätigungen/Korrekturen)

- **Vollständigkeit bestätigt:** `urlopen` in `mw_metadata.py` nur noch Zeile 13 (Binär/Artwork), 136 (Helfer selbst), 554 (fernsehserien.de, HTML `read().decode('utf-8')`), 816 (OFDB, HTML `errors='ignore'`). Zusätzlich `opener.open` Zeile 2641 (HTML-Scraping, kein JSON). **Kein urlopen+JSON-Rest.** Alle `json.load(f)`-Treffer sind Datei-/String-Lesezugriffe (Zeilen 761, 1050, 1144, 1270, 1363, 1526, 1653, 2156, 2164, 2349, 2386) — kein Netz.
- **`fetch_html_with_retry` hat doch 2 Aufrufstellen** (Zeilen 900, 1418), nicht „ohne Aufrufstellen“ wie angenommen — korrekt HTML und damit außerhalb des JSON-Scopes.
- **Helfer-Zeilen bestätigt:** `_open_with_retry` 122-145 (HTTPError→`raise`, fängt `(TimeoutError, ConnectionError, URLError, OSError)`, 3 Versuche, Default timeout=15), `fetch_json_with_retry` 148, `fetch_html_with_retry` 153.
- **TMDb-Einzeiler ohne `timeout`-Argument** (Default 15): Zeilen 576, 597, 619, 656, 678, 698, 1339, 1439, 1591 — alle via `make_tmdb_request`-Lambda. Ob das Bestand aus dem Juli-Fix oder Teil dieser Umstellung ist, ist **ohne git-Diff nicht entscheidbar**. Falls sie in dieser Session umgestellt wurden, verletzt das die Vorgabe „timeout=10“. → Alex: Diff prüfen.

---

## Nebenwirkungen (Prüfauftrag 6)

- `monkeypatch.setattr(urllib.request, "urlopen", …)` und `monkeypatch.setattr(mw_metadata.time, "sleep", …)` patchen global das gemeinsame Modulobjekt — wirksam, da `_open_with_retry` über `urllib.request.urlopen` bzw. `time.sleep` zugreift. `monkeypatch` räumt pro Test automatisch auf → **kein Leak im seriellen Lauf**. Restrisiko nur bei `pytest-xdist`/Parallelbetrieb.

---

## VERDICT: REVISE

Die Kerntechnik (Umstellung auf den Helfer, frische `build_request`-Lambdas, HTTPError-nicht-retry) ist sauber und die Vollständigkeit ist belegt. REVISE, weil (a) das zentrale A2-Finding ungeklärt ist und (b) die timeout=10-Vorgabe nicht testtechnisch abgesichert ist.

**Nummerierte Einwände:**

1. **[wichtig]** A2-Reviewer-Finding „Fehlerbehandlung für den externen Aufruf fehlt“ ist unbestimmt — vor Abnahme klären (Review-Log A2-Call‑1 ansehen) oder als offenes Risiko dokumentieren (`a2-eskalation.md:7`).
2. **[wichtig]** `timeout=10` an den umgestellten Stellen wird durch keinen Test assertiert; Vorgabe nicht verifiziert (`tests/test_metadata_retry.py`).
3. **[wichtig]** `test_fetch_movie_nfo_data_logs_and_returns_error_after_retries` (Zeilen 88-101) testet bei fehlendem `TMDB_API_KEY` nicht den Retry, sondern den Key-Fehlerpfad — patchen wie in Zeile 150.
4. **[wichtig]** Read-Timeouts/`ConnectionError` landen im `except Exception`-Zweig und umgehen `_handle_metadata_error` — als Risiko dokumentieren (wahrscheinlich Bestand).
5. **[kosmetisch]** `json.loads(bytes.decode())` verliert BOM-/UTF‑16-Toleranz (praktisch unkritisch für die Provider).
6. **[kosmetisch]** Kumulierte Offline-Latenz in `search_all_db` (bis ~8×33-48 s) — kein Korrektheits-, aber UX-Risiko.
7. **[offen]** TMDb-Einzeiler mit `timeout=15` (Default): Bestand vs. Session-Umstellung via git-Diff klären.

**Restrisiken / nicht ausgeführte Prüfungen:** kein `git diff` gegen den Vorher-Stand möglich (kein Bash-Tool); Tests nicht ausgeführt (grün-Status des Workers nicht unabhängig verifiziert); Fehlerpfad-Treue beruht auf Strukturanalyse statt Diff-Vergleich. Weitere `urlopen`+JSON-Stellen existieren weiterhin in `gui/api/search_api.py:878`, `gui/workers/youtube_worker.py:11`, `gui/core/helpers.py:404/421` — außerhalb des Scopes von Teil 1, als Notiz für Teil 2.
