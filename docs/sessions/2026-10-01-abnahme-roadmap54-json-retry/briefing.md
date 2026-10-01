# Feature Briefing: ROADMAP #54 Teil 1 — JSON-Metadatenabrufe auf Retry-Helfer (Abnahme-Review 2026-10-01)

> Session-Ordner: `docs/sessions/2026-10-01-abnahme-roadmap54-json-retry/`
> Rohoutputs: `advocatus.md`, `produktberater.md`, `scout.md` (ungekürzt)
> Stand: Umsetzung laut Auftrag auf Branch `a2/20261001T171506Z` (nicht gemergt, nicht gepusht — Branch-Status laut Alex' Auftrag, durch mich unverifiziert, siehe Abschnitt 10). Dieses Briefing ist die Abnahme-Bewertung, nicht der Umsetzungsplan.

## 1. Problemstellung

`gui/mw_metadata.py` enthielt ca. 25 direkte `urllib.request.urlopen`-Aufrufe mit Ein-Schuss-Verhalten (10 s Timeout). Bei transienten Network-Hängern auf dem NAS schlugen Metadatenabrufe (TMDb/TVDB/TVmaze/Mediathek) fehl — teils still. Der Retry-Helfer `fetch_json_with_retry` existierte seit dem gezielten Fix vom 16.07.2026, deckte aber nur einen Teil der Pfade ab. ROADMAP #54 fordert die flächendeckende Umstellung; Teil 1 = JSON-Abrufe, Teil 2 = HTML/Binär (offen).

## 2. Zielnutzer

Alex als Einzelnutzer der Heimnetz-App. Betroffene, unmittelbar spürbare Flows (produktberater bestätigt): NFO-Agent-Suche und -Details, Episodenlisten (TVDB-Pagination), Mediathek-Suche/-Episoden, TVDB-Login-Pfad. Reiner Backend-Pfad, keine UI-Änderungen.

## 3. Akzeptanzkriterien (Abnahme-Status)

- [x] AK1 Kein direkter `urlopen`+JSON-Rest in `mw_metadata.py`: verifiziert (Orchestrator + advocatus unabhängig; verbleibende `urlopen` nur Zeile 13 Binär, 136 Helfer-intern, 554/816 HTML; `opener.open` 2641 HTML; alle `json.load(f)`-Treffer sind Dateizugriffe).
- [x] AK2 Frisches Request-Objekt pro Versuch: verifiziert (alle umgestellten Stellen übergeben Lambda `build_request`; POST-Body in `get_tvdb_token:182` ist bytes und damit Retry-sicher).
- [x] AK3 HTML/Binär nicht angetastet: verifiziert im Ist-Zustand (Zeilen 13/554/816/2641 weiterhin direkt). `fetch_html_with_retry`-Aufrufstellen 900/1418 sind OFDb-HTML-Pfade, nach Nachbarschaftsanalyse Bestand aus dem Juli-Fix — mit git-Diff endgültig zu bestätigen (siehe Q2).
- [x] AK4 `timeout=10` an den umgestellten Stellen: per Codelesung bestätigt (Zeilen 184/220/265/424/433/441/487/516/745/944/1133/1535/1780/1909/2173/2278/2401/2410/2418/2724/2788/2806). Nicht mehr assertionsgeprüft (siehe offenes Risiko R2).
- [x] AK5 Tests: ≥3 umgestellte Funktionen mit URLError→zweiter-Versuch-Erfolg (geliefert: `search_tvmaze`, `fetch_tmdb_tv`, `search_tvdb`, `search_mediathek`), HTTPError-404-no-retry auf Helfer- und Funktionsebene, `time.sleep` monkeygepatcht, keine echten Netzaufrufe (URLs `example.invalid` bzw. gepatcht).
- [x] AK6 ROADMAP-Pflege: Tabelle Zeile 63 „teilweise (Teil 1 erledigt)", Abschnitt #54 Zeilen 1632-1634 mit Teil-2-Offenhaltung — konsistent (produktberater).
- [ ] AK7 Fehlerverhalten der Aufrufer identisch zum Vorher-Zustand: **nicht unabhängig verifizierbar** (kein git-Diff, kein Bash in dieser Session). Strukturanalyse durch advocatus: plausibel erhalten, aber zwei dokumentierte Eigenheiten (R3, R4).
- [ ] AK8 Testsuite grün: **nicht verifiziert** (Orchestrator und Subagenten haben keinen Bash-Zugriff). Beleg (pytest-Ausgabe lokal/CI) muss Alex nachliefern oder vom A2-Loop-Log übernehmen.

## 4. Bewusst verworfen (Scope-Eingrenzung)

- **Teil 2 (HTML/Binär)**: fernsehserien.de (Zeile 554), `search_ofdb` (Zeile 816), `resolve_mediathek_url_topic` (Zeile 2641), Artwork via `_download_with_timeout` (Zeile 9-17) — bleibt offen, in ROADMAP dokumentiert. scout: Teil 2 ist mechanisch (~30-45 Min KI-Arbeit), Binär braucht eigene Variante mit frischem File-Handle pro Versuch.
- **Andere Module** (`helpers.py`, `search_api.py`, `youtube_worker.py`, `telemetry.py`, `notifications.py`, `processor.py`): nicht angefasst. scout bewertet einen „Teil 3" als Scope-Creep, da diese Abrufe keine Metadaten-Abrufe sind oder eigene Fehlerpfade haben. **Dissens dokumentiert:** advocatus ordnet dieselben Stellen („Notiz für Teil 2"), scout widerspricht („eigene Items, nicht Teil 2/3; #54 nach Teil 2 als erledigt markieren") — die Zuordnung ist vor der Teil-2-Planung von Alex zu klären (siehe Q5). Rest: `processor.py:2705` Thumbnail-Binär gehört nach scout zu Teil 2.
- **Circuit-Breaker/Max-Total-Timeout**: nicht gebaut (produktberater-Rückfrage 3, Entscheidung offen, Default: nicht tun).
- **`pytest.mark.parametrize`-Refactoring der Tests**: verworfen nach scout-Bewertung als Overkill (scout empfiehlt ausdrücklich „so lassen"); bestehende Teststruktur bleibt (verworfene Alternative, dokumentiert).
- **UI-Logging-Monitor für Retry-Events**: nur als Anschlussidee notiert (scout 3), kein Scope.

## 5. ADR-Blöcke

**D1 — Zweiteilung JSON zuerst / HTML+Binär später.**
Entscheidung: Teil 1 nur JSON. Alternativen: alles in einem Rutsch; nur interaktive Pfade. Begründung: JSON ist der häufigste Fehlerfall in interaktiven Flows; Binär/HTML braucht eigene Helfer-Varianten (frischer File-Handle) und war explizit ausgeschlossen. Konsequenz: #54 bleibt bis Teil 2 auf „teilweise"; Artwork-Robustheit (Anschluss #51) verzögert sich.

**D2 — Wiederverwendung des Bestehenden Helfers statt neuer Abstraktion.**
Entscheidung: `fetch_json_with_retry(build_request, timeout=10, context=...)`, HTTPError nie wiederholt, URLError/Timeout/ConnectionError 3× mit Backoff `sleep(attempt)`. Alternativen: eigene Retry-Schleife je Aufrufer; Retry auch bei 5xx. Begründung: einheitliches Verhalten, sichtbares Logging bereits implementiert (`log_message`, Zeile 142); 429/5xx sind echte Antworten (Bestand-Entscheidung vom Juli-Fix). Konsequenz: Worst-Case-Latenz 33 s/Abruf statt 10 s (Risiko R5); Rate-Limit-Stürme bei 429 unwahrscheinlich, weil HTTPError sofort durchgereicht wird.

**D3 — Fehlerpfad der Aufrufer unverändert lassen.**
Entscheidung: nur den inneren Aufruf getauscht, umgebende `try/except`-Struktur nicht angetastet. Alternativen: Fehlerpfade mitbereinigen (z. B. `print stderr` → `log_message`). Begründung: Auftragsvorgabe „Fehlerverhalten beibehalten"; Minimierung des Regressionsradius. Konsequenz: zwei ererbte Schwächen bleiben bestehen und sind dokumentiert (R3: `TimeoutError`/`ConnectionError` umgehen `_handle_metadata_error`; R4: Endfehler in TVDB/TMDb-Suchpfaden nur auf stderr statt im App-Log — produktberater: „teils still scheitern" nur für Retry-Versuche gelöst).

**D4 — Teststrategie: Funktionsebene + Helfer-Ebene, monkeypatch, kein Netzwerk.**
Entscheidung: 4 umgestellte Funktionen mit URLError→Erfolg, 404-no-retry auf zwei Ebenen, `sleep` neutralisiert. Alternativen: VCR/HttpLib gegen echten Provider (verworfen: Netz im CI); parametrize über alle Provider (verworfen: scout-Overkill-Bewertung). Konsequenz: Lücken bleiben (R2: kein `timeout=10`-Assertion; Pagination, TVDB-Login-POST, HTTPError-Durchgriff je Funktion ungetestet) — vertretbar, da Helfer-Ebene die Logik abdeckt.

## 6. Dissens & offene Risiken (Pflichtabschnitt)

**Dissens-Lage:** Die drei Rückkanal-Rollen sind sich in der Grundrichtung einig (saubere, disziplinierte, testabgedeckte Teilumstellung), aber **advocatus urteilt REVISE, produktberater „trifft Bedarf teilweise"**. Diese Einwände sind zwingend dokumentiert und nicht wegdiskutiert:

- **R1 [wichtig, offen — Abnahme-blockierend nach advocatus]:** Die Implementierungs-Session selbst hat `a2-eskalation.md` im Repo-Root hinterlassen: Worker↔Reviewer-Loop nach 1 Runde ohne APPROVE, Finding „[wichtig] Fehlerbehandlung für den externen Aufruf fehlt". Ohne A2-Review-Log ist nicht entscheidbar, welche Stelle gemeint war und ob der Punkt erledigt ist. advocatus' plausibelster Kandidat: Helfer-Zeile 150 (`json.loads(...decode())` ohne eigenes try/except → JSONDecodeError/UnicodeDecodeError propagieren roh). **Das ist ein echter Rückkanal-Befund und muss vor dem Merge geklärt oder von Alex explizit als Restrisiko akzeptiert werden.**
- **R2 [wichtig]:** „timeout=10 beibehalten" ist nicht testabgesichert; Helfer-Default ist 15. Versehentliche Nicht-Übergabe würde unbemerkt bleiben.
- **R3 [wichtig, wahrscheinlich Bestand]:** Read-Timeouts (`TimeoutError`) sind keine `URLError`; betroffene Aufrufer fallen in `except Exception` statt `_handle_metadata_error` → keine Übersetzung in `MetadataProviderUnavailable(503)`. Kein Test deckt das.
- **R4 [wichtig, produktberater]:** Endgültige Fehlschläge in TVDB/TMDb-Suchpfaden loggen weiter nur `print(..., file=sys.stderr)`, nicht `log_message` — ROADMAP-Ziel „Fehlversuche sichtbar loggen" nur teilweise erfüllt.
- **R5 [kosmetisch/UX]:** Kumulierte Offline-Latenz: bis ~33 s/Abruf (timeout=15-Pfade ~48 s), `search_all_db` sequenziell bis 8 Provider → minutenlang bei Ausfall; UI asynchron, kein Blocker.
- **R6 [kosmetisch]:** `json.loads(bytes.decode())` verliert BOM-/UTF-16-Toleranz von `json.load` (praktisch irrelevant für die vier Provider).
- **R7 [offen, Diff-Frage]:** Helfer-Aufrufe ohne `timeout`-Argument (Zeilen 576/597/619/656/678/698/1305/1339/1439/1591, Default 15 s): laut ROADMAP-Nachbarschaft Bestand des Juli-Fixes; wäre eine dieser Stellen in DIESEM Branch neu umgestellt, wäre die Auftragsvorgabe verletzt. Nur per `git diff` entscheidbar. (Kleine Rollen-Diskrepanz: advocatus nannte Zeile 1305 nicht, produktberater schon; verifiziert: 1305 = „TVDB Serien-Details", ohne timeout — Bestand plausibel.)
- **R8 [Prozess]:** `a2-eskalation.md` im Root ist ein Ablage-Fehler (scout: künftig nach `docs/sessions/`); Datei muss vor dem Commit als Beifang behandelt werden (nicht stillschweigend stagen).
- **Test-Hygiene [wichtig, aus advocatus #3]:** `test_fetch_movie_nfo_data_logs_and_returns_error_after_retries` (Zeilen 88-101) patcht `TMDB_API_KEY` nicht; ohne Key in Umgebung testet er den Key-Fehlerpfad statt des Retries (grün ohne Retry). Fix-Empfehlung: patchen wie Zeile 150.

## 7. Quellen, Referenzen & Lizenzen

Kein Third-Party-Code, keine Assets, keine Fonts, keine Screenshots. Ausschließlich Python-Stdlib (`urllib`, `json`, `time`) und projekteigene Helfer. Keine Lizenzblocker.

## 8. Offene Fragen an Alex (gesammelt, nicht einzeln eskaliert)

**Benötigte Belege von Alex (keine Entscheidungsfragen, daher ohne Empfehlungspflicht-Optionen):**
- Q2: Git-Belege nachliefern: `git status --short --branch`, `git log --oneline -5` und `git diff main...a2/20261001T171506Z -- gui/mw_metadata.py` (Kurzfassung reicht), um R7/AK3 endgültig zu bestätigen. Ohne diese Belege gilt die harte main-Stop-/Preflight-Regel: kein Commit/PR-Vorschlag von mir.
- Q3: pytest-Beleg: Ausgabe `pytest tests/test_metadata_retry.py` (idealerweise komplett `pytest`) — in dieser Session von niemandem ausgeführt.

**Entscheidungsfragen (je mit Empfehlung):**

- Q1: A2-Loop-Auflösung zu R1 — Review-Log des A2-Call 1 sichten: ist „Fehlerbehandlung für den externen Aufruf fehlt" erledigt oder Nacharbeit nötig? (Empfehlung: vor Merge klären; mini-Nacharbeit wäre ein try/except um decode/json.loads plus ein Test „leerer Body → sauberer Fehler".)
- Q2: Git-Belege nachliefern: `git status --short --branch`, `git log --oneline -5` und `git diff main...a2/20261001T171506Z -- gui/mw_metadata.py` (Kurzfassung reicht), um R7/AK3 endgültig zu bestätigen. Ohne diese Belege gilt die harte main-Stop-/Preflight-Regel: kein Commit/PR-Vorschlag von mir.
- Q3: pytest-Beleg: Ausgabe `pytest tests/test_metadata_retry.py` (idealerweise komplett `pytest`) — in dieser Session von niemandem ausgeführt.
- Q4: R2+Test-Hygiene: Nachbesserung (timeout-Assertion, Key-Patch im nfo-Test) jetzt als Mini-Fix auf dem Branch oder als ROADMAP-Notiz zu Teil 2? (Empfehlung: Mini-Fix, ~15 Min KI-Arbeit, macht die Abnahme sauber.)
- Q5: R4 (stderr→log_message) und R3: als expliziter Teil-2-Punkt in ROADMAP #54 nachtragen? (Empfehlung: ja, ein Satz im Abschnitt #54.)
- Q6: Latenz-Akzeptanz R5: 33 s Worst-Case ok? (Empfehlung: ja, kein Circuit-Breaker — Heimnetz, asynchron.)
- Q7: `a2-eskalation.md`: nach `docs/sessions/2026-10-01-abnahme-roadmap54-json-retry/` verschieben oder löschen? (Empfehlung: verschieben — Inhalt ist Abnahmerelevant; Ausführung über repo-operator nach Alex-Go.)
- Q8: Freigabe-Pfad: Merge direkt auf main nach Klärung von Q1-Q3 oder PR mit Teil 2 zusammen? (Empfehlung: PR für Teil 1, Teil 2 als eigener kleiner PR danach.)

## 9. Aufwand (AI vs. Engpass Alex)

- KI-Arbeit erledigt (Implementierung + Tests): bereits geschehen. Verbleibende KI-Nacharbeit je nach Q1/Q4: ~15-30 Min.
- Teil 2 (HTML/Binär, nächste Session): ~1-2 h KI-Arbeit (scout-Mechanik), Engpass bleibt Alex-Review.
- Menschlicher Engpass jetzt: Q1-Q3 beantworten (Git-/Test-/A2-Belege sichten) ≈ 15-20 Min, dann Abnahme-Entscheidung.

## 10. Git-Zustand (Preflight)

Mir liegt kein `git status --short --branch` vor (kein Bash-Zugriff in dieser Session). Branch `a2/20261001T171506Z` ist nur aus Alex' Auftrag bekannt, nicht verifiziert. **Daher: harte Stoppe Regel — kein Staging/Commit/Push/PR-Vorschlag, bis Alex den Git-Zustand liefert (Q2).** Untracked-Beifang ist bereits identifiziert: `a2-eskalation.md` (Q7), dieser Session-Ordner, ggf. `STAND.md`-Nachführungen.
