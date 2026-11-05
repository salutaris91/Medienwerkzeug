# Rückkanal (Abnahme) — Kette „Ähnliche-Titel-Hinweis"

**Datum:** 2026-11-05 · **Worktree/Branch:** `plan/aehnliche-titel-hinweis` (Basis 21dfb28) · **Prüfer:** Rückkanal-Instanz (Synthese aus eigener Dateiprüfung + `advocatus` + `produktberater`)
**Grundlagen:** `docs/sessions/2026-11-05-aehnliche-titel/briefing.md` (Frontmatter `status: approved`, `approved_by: alex`, `approval_quote: "Freigabe: Ja"` — vorhanden und konsistent), `rueckkanal-gesamt-diff.patch` (1537 Zeilen), die echten Dateien im Worktree.
**Rohoutputs (ungekürzt archiviert):** `advocatus-rueckkanal.md`, `produktberater-rueckkanal.md` (in diesem Ordner).

---

## 0. Prüfumfang und Grenzen der Verifikation

- **Was ich selbst verifiziert habe (Leszugriff auf den Worktree):** Der Gesamt-Diff stimmt Zeile für Zeile mit dem tatsächlichen Dateistand überein — `gui/core/similar_titles.py` (339 Z., identisch), `gui/api/queue_api.py:366-395`, `gui/static/app.js` (`:1-9` Imports `?v=105`, Reset `:10276-10283`, XSS-Fix `:10380`, Render-Block `:10417-10484`), `gui/static/index.html` (Box `:2581-2585` zwischen Mismatch-Box `:2578-2579` und Zielverzeichnis `:2587-2591`, `app.js?v=105` `:2766`), `API.md:267ff`, beide neuen Testdateien.
- **Verbotene Zonen gegen den echten Stand geprüft:** `read_nfo_metadata` unverändert (der `tmdbid`→`tmdb_tv`-Label-Fehler ist in `gui/core/nfo_helper.py:142-145` und im Regex-Fallback `:180-183` weiterhin vorhanden — der beste Beleg, dass niemand „nachhilfe-getauft" hat); `calculate_match_score` existiert unverändert in `gui/mw_metadata.py:2551` und wird vom neuen Code nirgends referenziert; der TV-Zweig beginnt unverändert bei `queue_api.py:397`; die bestehende Kollisionswarnung `:273-364` ist im Diff nur als Kontext, nie als Änderung, sichtbar.
- **Grenze:** Mir stehen kein Bash und kein Git-Zugriff zur Verfügung. Die Behauptungen „Gesamt-Diff = Commit-Umfang", „550 pytest / 238 Frontend grün", „Rot-Proben rot", „Gate-A2 je Etappe APPROVED" und „Browser-Probe E2" konnte ich **nicht** selbst ausführen bzw. nachprüfen; ich plausibilisiere sie über den konsistenten Dateistand und die innere Stimmigkeit der Tests, treat sie aber als vom Hauptassistenten geliefert. Die Sync-Commits der generierten `AGENTS.md` sind im Code-Diff nicht enthalten (mechanisch, offengelegt) — nicht Teil der Code-Abnahme.

---

## 1. Akzeptanzkriterien AK1–AK19: geprüft, alle abgedeckt

| AK | Abdeckung (Test) | Code-Stelle | Urteil |
|---|---|---|---|
| AK1 | `test_similar_titles_hint.py::test_ak1…` — 3 subTests: `tmdb`/`movie.nfo`, `tmdb_movie`/`<ordnername>.nfo`, Fremdname `xmen_cut.nfo` via `find_primary_nfo`-Fallback | `similar_titles.py:173-187,235-292` | ✓ |
| AK2 | `test_ak2…` — `warning` bleibt, `exact` ohne Zielordner | `queue_api.py:372` (`exclude_folder=clean_movie_name`) | ✓ |
| AK3 | `test_ak3…` — leere Listen + `renames`/`subs`/`junk`/`destination` intakt | `queue_api.py:366` | ✓ |
| AK4 | `test_ak4…` — 7 Fälle (`manual`, `mediathek`, `ytdlp`, `ytdlp_movie`, `ofdb`, `movie_id` None/leer): HTTP 200, Log „Stufe-1-ID-Abgleich übersprungen", Stufe 2 läuft | `similar_titles.py:242-250` (Whitelist-Gate) | ✓ |
| AK5 | `test_ak5…` — Treffer in Ebene 2, Ebene 3 ignoriert (beide Stufen) | `similar_titles.py:123-170` | ✓ |
| AK6 | `test_ak6…` — defekte NFO → Skip + Log, Scan läuft weiter, HTTP 200 | `similar_titles.py:262-289` | ✓ |
| AK7 | `test_ak7…` — fehlender `category_root` → leere Listen, normaler Preview | `similar_titles.py:252,302` | ✓ |
| AK8 | FE `AK8…` — `<img onerror>` in Stufe 1/2 + `relative_path` + `overlap`: kein `img`/`script` im DOM, Rohstring in `textContent` | `app.js:10436-10443` (alle drei Felder escaped) | ✓ |
| AK9 | FE `AK9…` — Box ohne Buttons, Execute aktiv, Process-Payload unverändert, `similar_existing` leakt nicht | `app.js:10486` (`currentPreviewPayload = basePayload`) | ✓ |
| AK10 | BE `test_ak10…` — `assertNotIn("similar_existing")` bei TV, Staffelwarnung + `show_name_mismatch` intakt; TV-Zweig im Diff unberührt. Bestehende Tests `test_utils.py:3123/:3665` laut Beleg grün (nicht selbst ausgeführt, s. Abschnitt 0) | `queue_api.py:397ff` unverändert | ✓ (Restverifikation Suite-Grün) |
| AK11 | `test_ak11…` — 12 Namens→10, 7 ID→5 + Log „kappe auf 5", sortiert nach `overlap`, nur Treffer | `queue_api.py:377-381,387`, `similar_titles.py:334-338` | ✓ |
| AK12 | `test_ak12_ak13_ak14…` — „X-Men (2000)"→„X-Men 2" (Wortregel über „x"), „Hobbit"→„Hobbits" (Präfix), „300"→„300 (2006)" | `similar_titles.py:82-98` (`v`/`x` bewusst nicht als Sequel-Tokens), `:321-323` | ✓ |
| AK13 | dito — „Die X-Men Origins"↔„Iron Man" kein Treffer; „Night"↔„Nightcrawler" in **beiden** Richtungen kein Treffer (Leer-Guard gilt für beide Zweige); „Teil 2" matcht in beide Richtungen nicht | `similar_titles.py:306-308,317-319` | ✓ |
| AK14 | dito — „Der Hobbit (2012) [1080p][GERMAN]"→„Hobbit - Eine unerwartete Reise" | `similar_titles.py:100-102,211-228` | ✓ |
| AK15 | FE `AK15…` — 7 Treffer: 5 sichtbar, 2 in geschlossenem `<details>` „Weitere 2 Treffer anzeigen"; leere Listen → Box hidden | `app.js:10459-10470,10431` | ✓ |
| AK16 | BE `test_ak16…` (direkt + Endpoint) **und** FE `AK16…` (UI-Sicht) | `queue_api.py:374-376` + `app.js:10421-10429` | ✓ |
| AK17 | FE `AK17…` — index 105 + exakt 9 Imports 105; `cache_busting.test.js` ist dynamisch (liest Versionen, hartcodet keine 104) → ohne Änderung kompatibel | `app.js:1-9`, `index.html:2766` | ✓ |
| AK18 | FE `AK18…` — beide Felder der Bestandsbox escaped | `app.js:10380` | ✓ |
| AK19 | `test_ak19…` — `<tvdbid>`+`<tmdbid>`-NFO (Label `tvdb`) wird nicht Stufe-1-Treffer + Log; Scan läuft weiter | `similar_titles.py:25,279-284` | ✓ |

**Erlaubt-Listen eingehalten:** Der Diff ändert exakt 7 Dateien — E1: `similar_titles.py` (neu), `queue_api.py`, `tests/test_similar_titles_hint.py` (neu), `API.md`; E2: `index.html`, `app.js`, `tests/frontend/similar_titles_hint.test.js` (neu). `cache_busting.test.js` wurde nicht angefasst (nur lesend als Prüfinstanz genutzt, wie gefordert). Keine Abbruchkriterium-Verletzung sichtbar (keine Datei außerhalb der Listen, keine Test-Hintertür, kein Eingriff in `read_nfo_metadata`/`calculate_match_score`/TV-Zweig).

**Nicht-Ziele eingehalten:** Serien/Outbox/Doku/Anime/YouTube laufen in keinen neuen Zweig; keine neue Abhängigkeit (Imports: `os`, `re`, `unicodedata` + drei interne Module, `similar_titles.py:13-19`); keine Franchise-/Index-/Cache-Funktionalität; `btn-preview-execute` und Ausführungs-Payload unverändert.

**Test-Hintertüren im Produktivcode: keine.** Die Tests nutzen `MW_SETTINGS_FILE`/`MW_JOBS_STATE_FILE`/`MW_ENV_FILE`/`MW_DATA_DIR` — das ist eine **bestehende** Mechanismus der Persistence-Schicht (`gui/core/persistence.py:28-136`), kein neuer Test-Sonderpfad; im neuen Produktcode gibt es keinen Env-Branch. Artefakte nur in `tempfile.TemporaryDirectory` (Backend) bzw. reine Mock-DOM-Parsing-Tests (Frontend) — Hausregel Test-Artefakte erfüllt.

---

## 2. Befunde nach Schwere

### Blocker
**Keine.** Beide konsultierte Rollen (`advocatus`, `produktberater`) melden unabhängig „keine Blocker"; meine eigene Prüfung bestätigt das.

### Sollte behoben werden (nicht merge-blockierend — alsROADMAP-/Follow-up-Punkte beschlossen)

1. **[advocatus S1, von mir verifiziert] Frontend-Render-Block ohne eigene Fehlerkapselung.** Der Block `app.js:10417-10484` liegt im gemeinsamen Preview-`try` (`:10347`); der `catch` (`:10520-10524`) ruft `alert(...)` und `closePreviewModal()`. Eine Exception im neuen Block würde also die gesamte Vorschau kippen — formaler Widerspruch zur Scope-Zusicherung „lässt die Vorschau nie fehlschlagen" (Briefing §1). Eingestuft **nicht kritisch**, weil (a) der Block defensiv ist (`Array.isArray`/`typeof`-Guards `:10418-10428`, `escapeHTML` wirft nie, `:245-253`), (b) die Bestandsblöcke (Mismatch-Box etc.) im selben try stehen — das neue Muster wiederholt nur Hausmuster. → ROADMAP: eigenes try um den Block, Fehler ⇒ Box bleibt hidden.
2. **[advocatus S2] Namespace-Restrisiko `tmdb_tv`:** Stufe 1 akzeptiert NFO-Labels `{tmdb, tmdb_movie, tmdb_tv}` (`similar_titles.py:25`), weil `read_nfo_metadata` generierte Film-NFOs fälschlich als `tmdb_tv` labelt (`nfo_helper.py:142-145`). Ein TV-Show-NFO mit Zahlenwert-Kollision in der Film-Kategorie könnte kategorisch „Diesen Film hast du schon" (`app.js:10452`) behaupten. Bewusste, im Briefing (Korrektur 4) dokumentierte Abwägung; OFDB- und TVDB-Seite sind nachweislich dicht (Payload-Whitelist `similar_titles.py:22`; AK19 testet den tvdb-Fall). → ROADMAP: langfristige Korrektur des NFO-Labelings.

### Optional / Notizen

3. **[produktberater S1 vs. advocatus O3 — Dissens dokumentiert] Doppeltes Dedup Backend (`queue_api.py:374-376`) + Frontend (`app.js:10421-10429`):** produktberater nennt es unnötige Komplexität mit Entfernungsempfehlung; advokatus' verwandter Befund O3 zeigt, dass der Ausschluss über Ordnernamen (nicht Pfad) konservativ ist — nie False-Positive, höchstens ein verpasster Zweitordner. **Synthese-Entscheidung: beide Schichten behalten** (Defense-in-Depth; Backend-Dedup schützt API-Konsistenz, Frontend-Dedup schützt bei Dritt-Clients). Kein Code-Change in dieser Kette.
4. **[advocatus O3] Dedup/Exclude über `folder`-Name statt `relative_path`** (`similar_titles.py:259,314`) — konservativ, dokumentiert.
5. **[produktberater O1] `data-overlap`-Attribut** (`app.js:10442`) wird von CSS/JS nirgends gelesen — tote Deklaration, harmlos (AK8 nutzt `overlap` nur als Datenwert). Follow-up-Kandidat.
6. **[advocatus O4] Bestand, außerhalb Scope:** `app.js:10488` setzt `data.destination` unescaped in `innerHTML`. Nicht vom Feature verursacht, nicht angefasst — als separaterROADMAP-Punkt festgehalten (wie die Bestands-XSS `:10380` vor diesem PR).
7. **Grenze der Belegkette:** Suite-Grün/Rot-Proben/Browser-Probe sind Hauptassistenten-Behauptungen (Abschnitt 0). Für die Abnahme akzeptiert, weil der statische Code- und Testbefund konsistent ist; Restrisiko: ich konnte `pytest`/`npm run test:frontend` nicht selbst ausführen.

---

## 3. Antwort auf die beiden bekannten Beobachtungen

**(a) Doppelter Ordner-Scan + Unterordner-Kandidaten:** **Bestätigt, und zwar stärker als der produktberater behauptet.** Der Rohoutput des produktberater (Abschnitt 4a) enthält einen Faktfehler: „nicht zwei separate Scans des Dateisystems" stimmt nicht — `find_movie_folders_by_id` (`similar_titles.py:258`) und `find_similar_movie_folders_by_name` (`:313`) rufen `_iter_candidate_folders` je **einmal mit frischem `os.listdir`-Durchlauf** auf; pro Vorschau läuft der Kategorie-Scan also real zweimal über das Dateisystem (advocatus O1 recht). Unterordner jedes Filmordners werden als Ebene-2-Kandidaten gesammelt (`:150-168`) — Stufe 1 liest damit auch NFOs in Film-Unterordnern, Stufe 2 vergleicht deren Namen. Bewertung: **akzeptable MVP-Grenze, kein Blocker** — 2-Ebenen-Cap begrenzt die Menge, Leer-Guard/Allgemeinwörter fangen die typischen „Extras/Staffel"-Namen ab, Fehlerpfade sind abgedichtet; der Preis ist Latenz (potenziert R1) und theoretisches Rauschen. →ROADMAP: Scan-Ergebnis einmal erheben und beiden Stufen zuführen, gekoppelt mit R1-Maßnahme.

**(b) Singular/Plural und „X2":** **Beide Grenzen bestätigt und mechanisch erklärt** (advocatus und produktberater unabhängig deckungsgleich, von mir gegen `similar_titles.py:190-232,321-323` verifiziert): kein Stemming; die Präfixregel wirkt nur auf den **gesamten** bereinigten Titel, deshalb findet „Alien: Romulus" (→ `alien romulus`) „Aliens" nicht — ein reiner Einwortfall „Alien"→„Aliens" würde dagegen treffen; „X2" bleibt ein Token (`SEQUEL_NUMBER_TOKENS` enthält nur das isolierte „2"), also kein Anschluss an „X-Men". Bewertung: **bewusste MVP-Grenze, kein Blocker** — es sind False-Negatives bei semantisch *verschiedenen* Filmen; der Kernfall „derselbe Film, anderer Ordnername" wird primär von Stufe 1 abgedeckt. Zur Ehrlichkeit der FP1-Rhetorik („lieber mehr Fehlalarme als verpasste Treffer"): Die Heuristik ist an dieser Stelle konservativer als die Rhetorik — deshalb als dokumentierte Grenze in dieROADMAP (V2: Stemming/Token-Präfix/Aliasse), nicht als stiller Defekt.

---

## 4. EmpfehlungROADMAP-Einträge (nach Merge von der Pflege-Instanz zu übernehmen)

Beide Rollen haben fertigen Text geliefert (`advocatus-rueckkanal.md` Abschnitt 4, `produktberater-rueckkanal.md` Abschnitt 5). Synthese — ein gebündelter Block „Ähnliche-Titel-Hinweis — bekannte Grenzen & Restrisiken" mit folgenden Punkten:

1. **R1 SMB-Hänger (kritisch, aus Briefing §9):** Timeout-/Thread-Kapselung des synchronen Scans; **gekoppelt:** Scan nur einmal pro Vorschau (Beobachtung a).
2. **Frontend-Kapselung:** Render-Block `app.js:10417-10484` in eigenes try (Finding 2.1).
3. **Namespace `tmdb_tv`:** Film-NFOs korrekt labeln, dann `tmdb_tv` aus `ALLOWED_NFO_PROVIDER_LABELS` entfernen (Finding 2.2).
4. **Heuristik V2:** Singular/Plural (Stemming oder Mapping), Token-Präfix statt nur Gesamttitel-Präfix, Akronyme („X2"↔„X-Men") (Beobachtung b).
5. **Architektur-Schuld:** vier driftende Ähnlichkeitssysteme (`calculate_match_score`, `_titles_match`, `normalize_series_name`, `similar_titles`) — bei nächstem Ähnlichkeits-Feature konsolidieren (aus Briefing §9).
6. **R3:** doku/anime/youtube erreichen keinen Warn-Zweig (bewusstes Nicht-Ziel, dokumentieren).
7. **Bestand-XSS `destination`** (`app.js:10488`, Notiz advocacy, außerhalb Scope).
8. **Geparkte Ideen aus §9 nicht verlieren:** V2-Franchise via `belongs_to_collection` (Lizenz-/Terms-Prüfung + Alex-Go, **stichproben-pflichtig**), Sammelreport/Sidebar-Badge (scout 5), Prüfung im Suchschritt (scout 6), Bibliotheks-Index/Cache (scout 1).
9. **Kosmetik-Follow-ups:** `data-overlap`-Attribut ohne Nutzer; optionale Bereinigung des doppelten Dedups nur nach Alex-Entscheidung (Dissens Finding 3 — Default: behalten).

---

## 5. Dissens-/Rollenzuordnung (Pflicht)

- [advocatus] meldet zwei SOLLTE-Punkte (Frontend-Kapselung, `tmdb_tv`), sieht beides als nicht-blockierend; korrigiert damit meine Erwartung, der doppelte Scan sei „nur" Listenzugriff — O1/O2 sind real.
- [produktberater] bestätigt Scope-Treue vollumfänglich, nennt doppeltes Dedup und `data-overlap` als Komplexitätsballast (Optional), bewertet (a)/(b) als akzeptable MVP-Grenzen; **seine Faktenaussage zum „einen" Dateisystem-Scan ist falsch** und wurde in Abschnitt 3(a) widerlegt (Code: `similar_titles.py:258` + `:313`).
- Zwischen den Rollen besteht kein inhaltlicher Grundkonflikt; die Unterschiede (Dedup-Entfernung ja/nein) sind im Abschnitt 2.3 mit Begründung entschieden.
- Gegenüber dem Briefing: keine neue Entscheidung nötig — alle Findings liegen innerhalb der bereits von Alex in FP1/FP2 abgewogenen Risiken (R1, Fehlalarm-Toleranz, `tmdb_tv`-Äquivalenz).

## 6. Verdikt

Die Kette erfüllt alle 19 Akzeptanzkriterien nachweislich durch Code und Tests, hält Erlaubt-Listen, Nicht-Ziele und Sicherheitsgrenzen ein, enthält keine Test-Hintertüren und keine verbotenen Eingriffe. Die verbleibenden Befunde sind dokumentierte Restrisiken und Pflegepunkte, keiner davon ein Blocker. DieROADMAP-Einträge aus Abschnitt 4 sind bei der nächstenROADMAP-Pflege (Huckepack) zu übernehmen.

STOPP gemäß Auftrag — Ende des Rückkanal-Laufs; keine Git-Aktionen, kein Push, kein Code.

ABNAHME: JA
