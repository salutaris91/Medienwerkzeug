# Plan-Review Runde 1 — briefing.md (plan-reviewer, 2026-11-05)

> Ungekürzter Rohoutput des plan-reviewers (task-Aufruf, subagent_type plan-reviewer).
> Eingabe: briefing.md + Prüfauftrag (Frontmatter, Abschnittsvollständigkeit, AK-Form,
> Etappenvertrag, Dissens-Pflicht, Lizenzpflicht, Code-Fakt-Verifikation gegen den
> Worktree, FP1-Konsistenz, Kommunikationsregeln).

---

# Formelle Prüfung — Briefing „Ähnliche-Titel-Hinweis" (plan-reviewer, Inner-Loop)

**Artefakt:** `docs/sessions/2026-11-05-aehnliche-titel/briefing.md` (208 Zeilen)
**Grundlage mitgelesen:** `synthese.md`, `scout.md`, `advocatus.md`, `produktberater.md`, `ALEX_ZUSAMMENFASSUNG.md` (alle ungekürzt)
**Verifikationsbasis:** Worktree `plan-aehnliche-titel-hinweis` (read/grep, keine Änderungen)

---

## A. Findings — Blocker (kritisch)

**Keine kritischen Blocker gefunden.** Frontmatter, Abschnittsstruktur, Lizenzpflicht, Dissens-Pflicht, Etappen-Vertrag und alle 30+ Code-Fakten sind konform bzw. verifiziert korrekt.

## B. Findings — Sollte behoben werden (wichtig)

**B1. Stufe-2-Trefferregel: Geltungsbereich der „kein Treffer"-Bedingung mehrdeutig — AK13 nur in einer Lesart erfüllbar.** (briefing.md:59, gegen AK13 :117) Die Regel definiert zwei ODER-verknüpfte Zweige (gemeinsames bedeutungstragendes Wort / String-Präfix) und sagt danach: „Sind nach der Bereinigung auf einer Seite keine bedeutungstragenden Wörter mehr übrig ⇒ kein Treffer". Unklar ist, ob dieser Satz beide Zweige überschreibt. In der engen Lesart (Bedingung gilt nur für die Wortregel) gilt: (a) „Night" matcht „Nightcrawler" über die Präfixregel — AK13-Fall 2 verletzt; (b) schlimmer: ein bereinigt **leerer** Titel (reiner Füllwort-/Fortsetzungszahl-Ordnername, z. B. „Part 2") ist Präfix von **jedem** String — ein Total-Matcher, der genau die „Totalausfälle" erzeugt, die die Regel verhindern will. AK13-Fälle 2 und 3 erzwingen faktisch die weite Lesart, aber die Regel selbst lässt beide zu. Spezifikation muss die weite Lesart verbindlich machen (ein Satz genügt).

**B2. „300"-Hinweis widerspricht der eigenen Regel-Spezifikation.** (briefing.md:59–60) Der Hinweis „'300' (reines Zahlentitel) liefert damit bewusst nie einen Stufe-2-Treffer" ist aus der spezifizierten Pipeline nicht ableitbar: Die Fortsetzungszahl-Regel entfernt nur Tokens `2..9` und römische Zahlen — „300" bleibt Token; die Allgemeinwort-Liste enthält keine Zahlen; also ist „300" bedeutungstragend und „300" vs. „300" matcht über Wort- **und** Präfixregel. Entweder die Regel um „reine Zahl-Tokens sind nie bedeutungstragend" ergänzen (dann verliert aber auch z. B. „1917" vs. „1917" den Stufe-2-Treffer — ein realer Duplikat-Fall, den Alex wissen sollte) oder den Hinweis streichen. So ist die dokumentierte Grenze nicht prüfbar spezifiziert.

**B3. AK12-Begründung „Treffer über 'x'" inkonsistent mit der eigenen Fortsetzungszahl-Liste.** (briefing.md:58 vs. :116) Die Fortsetzungszahl-Regel entfernt explizit „x" als eigenes Token (römisch 10). „X-Men" bereinigt zu {men} — „x" kann also kein „gemeinsames bedeutungstragendes Wort" sein, wenn die Wortregel greift. AK12 bleibt erfüllbar (Präfixregel: „men" vs. „men"), aber die im Briefing primär genannte Begründungskette trägt nach eigener Spezifikation nicht. Ein Test-Autor, der AK12 wörtlich umsetzt („prüfe gemeinsames Wort 'x'"), baut einen roten Test. Begründung korrigieren.

**B4. NFO-Seiten-Provider-Check nicht spezifiziert — Namespace-Lücke vom Typ, den das Briefing selbst ausschließen will.** (briefing.md:38) Fakten-Korrektur 4 regelt die Äquivalenz `tmdb`/`tmdb_movie`/`tmdb_tv` und sagt „Vergleich nur der ID, Provider-Whitelist auf Payload-Seite". Nicht geregelt: NFOs, deren `read_nfo_metadata`-Label `tvdb` lautet — und der `<tvdbid>`-Fallback hat Vorrang vor `<tmdbid>` (verifiziert: `nfo_helper.py:136-145`, Kodi-Film-NFOs mit beiden Tags werden als `tvdb` gelesen). Wird „Vergleich nur der ID" label-agnostisch implementiert, matcht eine TVDB-ID 3409 gegen eine TMDb-Film-ID 3409 — exakt der Namespace-False-Positive, den Fakten-Korrektur 2 bei ofdb als Whitelist-Grund nennt. Es fehlt der Satz: „NFO-Seite: nur Label ∈ {tmdb, tmdb_movie, tmdb_tv} nimmt am ID-Vergleich teil; tvdb/andere Labels ⇒ Ordner-Skip." Kein AK deckt dieses Verhalten ab.

## C. Findings — Optional (kosmetisch)

**C1. Skip-Provider-Aufzählung unvollständig: `ytdlp_movie` fehlt.** (briefing.md:36) `ytdlp_movie` ist ein real lesbarer `metadata_provider`-Wert (verifiziert: `app.js:2887`; kein Erzeuger im Codebase, d. h. Alt-NFOs) und kann via `app.js:2897-2901` als `selectedMovie.provider` in den Film-Payload gelangen. Die geschlossene Whitelist-Logik fängt ihn strukturell ab (Skip defensiv korrekt, da ID-Raum unklar), aber die illustrative Aufzählung „ofdb, mediathek, ytdlp, manual, fehlend" ist unvollständig. Anmerkung: Die Whitelist {tmdb, tmdb_movie} ist sonst gut getroffen — `tmdb_movie` ist real (verifiziert: `project_api.py:507`, `app.js:17376`).

**C2. „nach :272-363, vor Return" irreführend.** (briefing.md:66) Der Film-Zweig hat kein eigenes Return; das gemeinsame Return liegt bei `queue_api.py:787` **hinter** dem TV-Zweig. Wörtliche Umsetzung von „vor Return" würde den Block außerhalb des Film-Zweigs platzieren. Gemeint (und durch „Im movie-Zweig" + AK10 abgesichert) ist: am Ende des Film-Zweigs vor `elif :365`. Formulierung präzisieren.

**C3. AK16 erst in E2-Done, obwohl das Dedup Backend-Logik ist.** (briefing.md:131 vs. :136) Das Stufe-1/Stufe-2-Dedup (`exclude_folders`) wird in E1 gebaut, aber erst über E2 (Frontend-Test) geprüft; E1-Done-Kriterium listet AK16 nicht. Als Frontend-Test formulierbar, aber das Backend-Dedup selbst bliebe bis E2 ungetestet. AK16 (oder ein Backend-Äquivalent) in E1-Done aufnehmen.

**C4. Scout-Ideen 5/6 aus der Synthese-ROADMAP-Kandidatenliste fehlen in Abschnitt 9.** (briefing.md:177–184 vs. `synthese.md`:86) Die Synthese parkte „Sammelreport" (Idee 5) und „Suchschritt-Frühwarnung" (Idee 6) explizit als ROADMAP-Kandidaten; das Briefing übernimmt ROADMAP-Notizen für R1/R3/R4/V2-Franchise/Index, lässt diese beiden aber still fallen. Keine Dissense (in Rohoutputs erhalten), aber Übernahme-Lücke mit Verlustgefahr bei der ROADMAP.md-Pflege.

---

## D. Verifikationsstatus der geprüften Behauptungen

**Code-Fakten (alle gegen den Worktree verifiziert):**

| Behauptung | Status |
|---|---|
| `app.js:10371` interpoliert `nas_name` **und** `metadata_name` unescaped in `innerHTML` | ✓ bestätigt (Korrektur 1 zur Synthese zutreffend) |
| `nfo_helper.py:142-145` labelt `<tmdbid>`-Fallback als `tmdb_tv`; Regex-Fallback `:180-183`; `errors='ignore'` `:110`; `<tvdbid>`-Vorrang `:136-145` | ✓ bestätigt |
| `mw_metadata.py:1188` schreibt `<tmdbid>`; Block `:1172-1201` ohne `<mw_provider>`/`<mw_showid>` | ✓ bestätigt |
| `mw_metadata.py:2551-2611` `calculate_match_score` (Jaccard, Jahresstrafe nur bei beidseitigem Jahr) | ✓ bestätigt |
| `queue_api.py:19-20` doppelter Mount; `:30-31` `movie_id`/`provider`; `:125` Film-Zweig; `:365` TV-Zweig; `:152-155` `target_base`; `:263` `<ordnername>.nfo`; `:272-363` Kollisionswarnung; `:707-714` Staffelwarnung NAS+Outbox; `:765-785` `show_name_mismatch` nur NAS (Aufruf `:767` mit `nas_serien`) | ✓ alle bestätigt |
| `series_helper.py:5-33`; Stringvergleich `:21`; `tmdb_tv`-Abhängigkeit `:27`; Fehler-Log `:29-30` | ✓ bestätigt |
| `health.py` `find_primary_nfo(folder, is_movie=True)`, Prio `<videostem>.nfo` → `movie.nfo` | ✓ bestätigt (Funktion `:291-333`; Briefing „~295-333" minimal ungenau, durch „~" gedeckt) |
| `index.html:2568-2579` Mismatch-Box (Inline-Stile `:2569`); `:2581` Zielpfad; `:2621` `btn-preview-execute`; `:2760` `app.js?v=104`; `:9` `style.css?v=51`; `:13` `utilities.css?v=1` | ✓ alle bestätigt |
| `app.js:1-9` genau 9 ES-Imports, alle `?v=104` | ✓ bestätigt |
| `cache_busting.test.js`: index-Version == alle Imports (strikt), ≥ 8 Imports, CSS nur nicht-leer | ✓ bestätigt (Regel im Briefing korrekt beschrieben) |
| `search_api.py:515` Provider `ofdb` für Filme | ✓ bestätigt |
| `app.js:245-253` `escapeHTML`; `:4542-4543` `movie_id`/`provider` im Payload; `:5124-5151` YouTube-Route (`media_type: "youtube"`, `movie_id`/`provider` nur im Movie-Modus) | ✓ bestätigt |
| `film_normalize.py:33` `_is_genre_container` | ✓ bestätigt |
| `project_api.py:1425-1474` setzt `doku`/`anime` | ✓ bestätigt |
| `tests/test_utils.py:3123`/`:3665` TV-Referenztests existieren; `:2969ff` Preview-Endpoint-Test-Muster | ✓ bestätigt |
| `tests/test_movie_processing_fixes.py`, `tests/frontend/inbox_group.test.js`, `API.md` existieren; `gui/core/similar_titles.py` existiert nicht (korrekt „neu") | ✓ bestätigt |
| `tmdb_movie` realer Provider-Wert (`project_api.py:507`, `app.js:17376`) — Whitelist sinnvoll | ✓ bestätigt |
| Alex-FP1-Zitat „Ja, genau so. Bauen, wie du jetzt empfohlen hast." (briefing.md:13) | ⚠ nicht unabhängig verifizierbar (Chat, nicht archiviert); inhaltlich gedeckt durch Prüfauftrag-Kontext und `ALEX_ZUSAMMENFASSUNG.md` („lieber mehr Fehlalarme als verpasste Treffer") |

**Formale Kriterien:**
- **Frontmatter (Kriterium 1):** ✓ konform — `kind`/`status: draft`/`approved_by`/`approved_on`/`approval_quote` (Platzhalter, keine Vorfreigabe)/`source` vorhanden; `source`-Datei existiert.
- **Abschnitte (Kriterium 2):** ✓ vollständig — Ziel & Scope (1), Kern-Features (3), AKs (4), Etappen (5), Nicht-Ziele (6), Sicherheit/Architektur (7), UX/UI (8), Quellen/Lizenzen (11), Potenziale (9); Zusatzabschnitte 2/10/12 erlaubt.
- **AKs (Kriterium 3):** ✓ 18 AKs, alle „Es prüft, dass …", tmp_path zugesichert, Test-Hintertür als Abbruchkriterium 3 verboten; Testdateien + Muster benannt und existent. Einschränkung: AK12/AK13-Begründungen siehe B2/B3.
- **Etappen (Kriterium 4):** ✓ je Etappe Erlaubte-Dateien-Liste, 5 Abbruchkriterien, Diff-Schätzungen deutlich unter 80 KB, `API.md` in E1 (Doku-Pflicht erfüllt); `cache_busting.test.js` nur lesend. Einschränkung C3.
- **Dissens (Kriterium 5):** ✓ — produktberater-Fuzzy-Veto (mit Alex-Überstimmung + Abmilderungen), advocatus-Timeout-Forderung (verworfen mit Präzedenz-Begründung `queue_api.py:767`, verifiziert; R1 bleibt dokumentiert, nicht bestritten), scout-Franchise-Mehrwert (V2 mit Lizenz-Vorbehalt) — alle drei mit Urheber, Entscheidungsträger, Begründung; keine Verfälschung der Subagenten-Positionen gefunden. R1/R3/R4 erhalten (Abschnitt 9); R2 durch Fix gelöst (3.4/AK18); R6 in die Bereinigung integriert (3.1). Rest: C4.
- **Lizenzen (Kriterium 6):** ✓ — Abschnitt 11 vollständig; `plexapi`/`jellyfin-apiclient-python`/`pyemby`/`tmdbsimple`/TMDb-Terms als ungeprüfte Blocker vor Adoption markiert; Lucide ISC (Bestand); keine stillschweigende Abhängigkeit („keine neuen Abhängigkeiten" als Nicht-Ziel).
- **FP1-Konsistenz (Kriterium 8):** ✓ in allen Strukturpunkten — nicht-blockierend nur Filme, Stufe 1 ID-Abgleich, Whitelist, 2 Ebenen, Stufe 2 nur Ordnernamen, EIGENE Hilfsfunktion `gui/core/similar_titles.py`, `calculate_match_score` weder ändern noch wiederverwenden (auch Abbruchkriterium 4), Stufe 1 oben, Dedup, Cap 10/5, Fehler-Contract, Kollisionswarnung unangetastet, nur `escapeHTML`/`textContent`, XSS-Fix im selben PR, Cache-Buster, Nicht-Ziele vollständig. **Ausnahme:** Stufe-2-Trefferregel-Spezifikation siehe B1–B3.
- **Kommunikation (Kriterium 9):** ✓ Deutsch; keine Git-Schreib-/Umsetzungsanweisung; FP2 und PR-Merge ausdrücklich als Alex-Punkte benannt (Abschnitt 12).

---

## E. Potenziale (Zusatzblock, nicht bewertungsrelevant)

- Die Whitelist {tmdb, tmdb_movie} ist durch die Verifikation von `project_api.py:507`/`app.js:17376` besser begründet, als das Briefing selbst sagt — ein Satz dazu würde die Whitelist-Wahl gegen künftige „Warum nicht tvdb?"-Diskussionen härten.
- B2 bietet die Gelegenheit, Alex die Trade-off-Entscheidung „Zahlentitel (300, 1917) matchbar oder bewusst nie?" explizit vorzulegen — das ist ein Heuristik-Review-Punkt in seinem ohnehin geplanten Wortlisten-Review (Abschnitt 12).
- Die in B4 geforderte NFO-Seiten-Regel könnte als ein einziger AK ergänzt werden („NFO mit tvdb-Label in der Film-Kategorie ⇒ kein Stufe-1-Treffer, Log"), was die Lücke testbar macht.

---

## F. Urteil

Die Architektur des Briefings ist solide: alle Code-Fakten halten der Verifikation stand, die vier Synthese-Korrekturen sind echt und zutreffend, Dissense und Lizenzen sind sauber dokumentiert, Etappen und Abbruchkriterien sind regelkonform. Blockierend sind allein vier Spezifikationslücken der Stufe-2-Trefferregel bzw. des ID-Abgleichs (B1–B4): Sie führen zu zwei unterschiedlich verhaltenden Implementierungen, von denen eine AK13 verletzt, eine einen Total-Matcher öffnet und eine den Namespace-Fehler reproduziert, den das Briefing selbst als Ausschlusskriterium formuliert. Diese Punkte sind mit jeweils einem Satz textlich behebbar, bevor Alex FP2 freigibt.

VERDICT: REVISE
1. [wichtig] Stufe-2-Trefferregel: Geltungsbereich der „keine bedeutungstragenden Wörter ⇒ kein Treffer"-Bedingung mehrdeutig; in der engen Lesart verletzt Präfixregel AK13 („Night" vs. „Nightcrawler") und macht bereinigt-leere Titel (reiner Füllwort-Ordnername) zu Total-Matchern (briefing.md:59, AK13 :117)
2. [wichtig] „300 liefert bewusst nie einen Stufe-2-Treffer" (briefing.md:60) widerspricht der eigenen Pipeline-Spezifikation (briefing.md:58): „300" ist kein Fortsetzungszahl-Token (nur 2..9) und nicht auf der Allgemeinwort-Liste, also bedeutungstragend ⇒ „300" vs. „300" matcht; Regel ergänzen oder Hinweis streichen
3. [wichtig] AK12-Begründung „Treffer über 'x'" (briefing.md:116) inkonsistent mit eigener Fortsetzungszahl-Liste, die „x" als Token entfernt (briefing.md:58); AK12 nur über die Präfixregel erfüllbar — wörtliche Test-Konstruktion nach der Primärbegründung wird rot
4. [wichtig] NFO-Seiten-Provider-Check fehlt in der Spezifikation: Verhalten bei `tvdb`-gelabelten NFOs (Vorrang von `<tvdbid>` in `nfo_helper.py:136-145`) offen; blindes „Vergleich nur der ID" (briefing.md:38) erzeugt TVDB↔TMDb-Namespace-False-Positives — derselbe Fehlertyp, den Fakten-Korrektur 2 (briefing.md:36) explizit ausschließen will
5. [kosmetisch] Skip-Provider-Aufzählung unvollständig: real existierender Wert `ytdlp_movie` (`app.js:2887`, Alt-NFOs via `metadata_provider`) fehlt in der Aufzählung (briefing.md:36); Whitelist-Logik fängt ihn strukturell ab
6. [kosmetisch] „nach :272-363, vor Return" (briefing.md:66) irreführend — der Film-Zweig hat kein eigenes Return (gemeinsames Return `queue_api.py:787` hinter dem TV-Zweig); gemeint ist „vor `elif :365`"
7. [kosmetisch] AK16 (Stufen-Trennung/Dedup) erst in E2-Done (briefing.md:136), obwohl das Dedup (`exclude_folders`) E1-Backend-Logik ist; Backend-Dedup bis E2 ungetestet (briefing.md:131)
8. [kosmetisch] Scout-Ideen 5/6 (Sammelreport, Suchschritt-Frühwarnung), von der Synthese als ROADMAP-Kandidaten geparkt (`synthese.md`:86), fehlen in Briefing-Abschnitt 9 (briefing.md:177-184) — Übernahme-Lücke mit Verlustgefahr bei der ROADMAP.md-Pflege
