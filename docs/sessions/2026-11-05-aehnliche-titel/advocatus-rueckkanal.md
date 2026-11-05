# Advocatus — Rückkanal-Beitrag (Abnahme „Ähnliche-Titel-Hinweis"), 2026-11-05

Ungekürzter Rohoutput des Subagenten `advocatus` aus der Rückkanal-Sitzung. Auftrag: Risikoprüfung des Gesamt-Diffs der Kette auf Branch `plan/aehnliche-titel-hinweis` (Basis 21dfb28). Recherche ohne eigene Schreibrechte; Dateizustand wurde gegen den Worktree geprüft.

---

# Advocatus-Risikoprüfung — Feature „Ähnliche-Titel-Hinweis"

Worktree `plan/aehnliche-titel-hinweis`, Recherche gegen die echten Dateien (nicht nur gegen Diff/Briefing). Befunde mit Datei:Zeile.

---

## 1) Kurzes Verdikt

Das Feature ist **sauber implementiert**: Escaping vollständig, Fehler-Contract auf Backend-Ebene eingehalten, keine Test-Hintertüren im Produktivcode, keine neuen Abhängigkeiten, keine Leaks in den Ausführungs-Payload, TV-/Outbox-/Serien-Pfade unangetastet, `read_nfo_metadata`/`calculate_match_score` nicht verändert. **Kein Blocker.** Es bleiben ein SOLLTE-Finding (fehlende Frontend-Kapselung des Render-Blocks) und ein dokumentierter Namespace-Blindfleck (`tmdb_tv`), der sauber in die ROADMAP gehört.

---

## 2) Findings-Liste nach Schwere

### BLOCKER
Keine.

### SOLLTE

**S1 — Frontend-Render-Block ohne eigene Fehlerkapselung widerspricht der Scope-Grenze „Vorschau schlägt nie fehl"** (Punkt 2 der Prüfung)
- Der komplette ähnliche-Titel-Render liegt bei `app.js:10417-10484` **innerhalb** des gemeinsamen `try` (öffnet `app.js:10347`, schließt `catch` bei `app.js:10520`). Der `catch` tut: `alert("Fehler: " + e.message)`, `appendConsoleLog`, **`closePreviewModal()`** (`app.js:10520-10524`).
- Folge: Jede Exception im Render-Block (z. B. ein unerwarteter Wert, der `renderItem`/`escapeHTML` zum Kippen bringt) verwirft die **gesamte** Vorschau und schließt das Modal — obwohl Briefing Abschnitt 1 zusichert, der Hinweis „lässt die Vorschau **nie** fehlschlagen". Das Backend hält diesen Contract formal ein (`queue_api.py:367-395`, try/except → leere Listen); das Frontend hält ihn nur **durch Defensivheit**, nicht durch Kapselung.
- Realistisches Eintrittsrisiko ist niedrig (der Block prüft `Array.isArray`/`typeof` bei `app.js:10418-10428`, `escapeHTML` macht `String(str)` bei `app.js:245-247` und wirft nicht). Aber es ist eine Abweichung von der ausdrücklich dokumentierten Zusicherung. Ein eigenes `try` um den Render-Block (analog zum Backend) würde einen Fehler auf „Box bleibt hidden" degradieren statt auf „Modal zu".
- **Empfehlung:** nicht-merge-blockierend, aber als bewusste Entscheidung festhalten oder eng nachziehen.

**S2 — Namespace-Blindfleck `tmdb_tv`: Stufe 1 behauptet kategorisch „Diesen Film hast du schon", obwohl Movie- und TV-ID-Räume getrennt sind** (Punkt 6 der Prüfung)
- `ALLOWED_NFO_PROVIDER_LABELS = {"tmdb", "tmdb_movie", "tmdb_tv"}` (`similar_titles.py:25`) enthält bewusst `tmdb_tv`, um den bekannten Label-Fehler zu kompensieren: generierte Film-NFOs haben kein `mw_provider`, der Fallback labelt `<tmdbid>` fälschlich als `tmdb_tv` (`nfo_helper.py:142-145` und `:180-183`).
- Konsequenz: Ein echter **TV-Show-NFO** in der Film-Kategorie, der ein `<tmdbid>` (TV-Namespace) trägt, dessen Zahlenwert zufällig mit der TMDb-**Film**-ID des Payloads kollidiert, würde als Stufe-1-Treffer gemeldet — und die UI formuliert Stufe 1 kategorisch: „Diesen Film hast du schon auf dem NAS" (`app.js:10452`). TMDb vergibt Movie- und TV-IDs in getrennten Räumen; solche Zahlenkollisionen sind möglich.
- Abmilderung (verhindert den Blocker): nur ein nicht-blockierender Hinweis, nur in der Film-Zielkategorie, und die tvdb-Seite ist dicht (siehe Bewertung unten).
- **Bewertung der Frage „wirklich dicht?":** OFDB **dicht** (Payload-Whitelist `ALLOWED_MOVIE_ID_PROVIDERS` ohne `ofdb`, `similar_titles.py:22`, verifiziert über `search_api.py`-Providerwerte); TVDB **dicht** (NFO-seitige Label-Whitelist schließt `tvdb` aus, und der `tvdbid`-Fallback hat Vorrang vor `tmdbid`, `nfo_helper.py:136-145` — AK19 testet genau das). **Nur `tmdb_tv` ist nicht dicht** und wird als „äquivalent" behandelt. Das ist im Briefing (Korrektur 4) als bewusste Entscheidung dokumentiert, muss aber als Restrisiko in die ROADMAP.

### OPTIONAL

**O1 — Doppelter Kategorie-Scan pro Vorschau** (Beobachtung a)
- `queue_api.py:368` (Stufe 1) und `queue_api.py:383` (Stufe 2) rufen je `_iter_candidate_folders` (`similar_titles.py:123`) auf. Bei großen Bibliotheken läuft der komplette `os.listdir`/`os.path.isdir`-Durchlauf pro Vorschau **zweimal**, synchron im Request. Begrenzt durch den 2-Ebenen-Cap, aber in Kombination mit R1 (SMB-Latenz) doppelt so viele Mount-Statements.

**O2 — Unterordner als Kandidaten** (Beobachtung a)
- `_iter_candidate_folders` (`similar_titles.py:150-168`) sammelt auf Ebene 2 **auch die Unterordner jedes Filmordners** („Extras", „Featurettes", „Staffel X") als Kandidaten; die NFO-Auflösung (`_resolve_movie_nfo`, `similar_titles.py:173`) läuft damit auch in Film-Unterordnern. Meist harmlos (Leer-Guard `similar_titles.py:306-308` + Allgemeinwortliste), aber ein Quelltitel mit dem Token „extras"/„staffel" könnte theoretisch einen Unterordner als ähnlich melden. Vernachlässigbar, kein Blocker.

**O3 — Dedup/Ausschluss über `folder`-Name statt `relative_path`**
- `exclude_for_similar` (`queue_api.py:374-376`) und die Ausschlussprüfung (`similar_titles.py:259`, `:314`) vergleichen den **Ordnernamen**, nicht den relativen Pfad. Bei zwei gleichnamigen Ordnern in verschiedenen Genre-Unterordnern („Action/X-Men" und „SciFi/X-Men") würde der Ausschluss **beide** treffen. Konservativ (verpasst höchstens einen Treffer, erzeugt nie einen False-Positive), daher nur OPTIONAL.

**O4 — Notiz (außerhalb Scope, nicht anfassen):** `app.js:10488` setzt `data.destination` **unescaped** in `innerHTML` (`dest.innerHTML = data.destination.replace(/\n/g, '<br>')`). Das ist Bestandscode und betrifft nicht die neuen Felder (`folder`/`relative_path`/`overlap` der neuen Box werden vollständig escaped), aber es ist ein offenes XSS-Fenster über einen Backend-gelieferten Pfadstring. Nur Notiz, kein Feature-Finding.

---

## 3) Bewertung der Beobachtungen (a) und (b)

**(a) Doppelter Scan + Unterordner-Kandidaten:** Reines Performance-/Rausch-Problem, kein Blocker. Der 2-Ebenen-Cap (`similar_titles.py:124`, nur `<Kategorie>/<Film>` und `<Kategorie>/<Genre>/<Film>`) begrenzt die Tiefe plausibel; der Preisfaktor ist die **zweifache** Ausführung pro Vorschau (O1) plus R1-Potenzierung. Die Unterordner-Kandidaten (O2) erzeugen real kaum Fehlalarme, weil Leer-Guard und Allgemeinwortliste die meisten („extras", „featurettes", „staffel") abfangen. **Keines davon ist ein Blocker.**

**(b) Singular/Plural und „X2" vs „X-Men":** Verifiziert gegen `_clean_title_and_tokens`:
- „Alien: Romulus" → „alien romulus" (meaningful `{alien, romulus}`); „Aliens" → `{aliens}`. Die Präfixregel (`similar_titles.py:322`) vergleicht den **Gesamttitel**: `"aliens".startswith("alien romulus")` ist falsch („aliens" ist kürzer), `"alien romulus".startswith("aliens")` auch — also kein Treffer, **weil „romulus" ein zweites Wort einfügt**. Ein reiner Einworttitel „Alien" → „Aliens" würde über die Präfixregel treffen. Das ist eine echte Heuristik-Grenze (kein Stemming, Präfix nur auf Gesamttitel), aber semantisch vertretbar: „Alien: Romulus" und „Aliens" sind **verschiedene Filme** — die Heuristik soll Duplikate erkennen, keine Reihen.
- „X2" → tokenisiert als **ein** Token `"x2"` („2" wird nicht separat entfernt, weil `SEQUEL_NUMBER_TOKENS` nur das isolierte Token „2" führt, `similar_titles.py:82-98`); „X-Men" → meaningful `{x}`. Kein gemeinsames Token, kein Präfix → korrekt **kein** Treffer. „X2" (X-Men United) und „X-Men" sind ebenfalls verschiedene Filme.

**Gesamteinordnung:** Beide Beobachtungen sind **False Negatives bei semantisch verschiedenen Titeln** — also kein Widerspruch zum Duplikat-Erkennungsziel. Der einzige echte Bezug zur FP1-Rhetorik („lieber mehr Fehlalarme als verpasste Treffer") ist, dass die Heuristik bei False Negatives konservativer ist, als die Rhetorik suggeriert. **Kein Blocker**; die Heuristik-Grenzen gehören als V2-Erweiterung (Stemming/Token-Präfix) in die ROADMAP.

---

## 4) Empfehlung: zwingende ROADMAP.md-Einträge (fertiger Text)

```markdown
## Ähnliche-Titel-Hinweis — Restrisiken (aus Advocatus-Abnahme 2026-11-05)

- [ ] [Frontend-Kapselung] Der Render-Block `app.js:10417-10484` hängt ohne eigenes
      try/catch im gemeinsamen preview-try. Eine Exception dort schließt das gesamte
      Vorschau-Modal (catch `app.js:10520-10524`), statt nur die Box zu verbergen —
      Widerspruch zur Scope-Grenze „Vorschau schlägt nie fehl". Render-Block in eigenes
      try fassen (Fehler → Box hidden, Rest der Vorschau unberührt). Nicht
      merge-blockierend, da Code defensiv ist (Array.isArray/typeof/escapeHTML).
- [ ] [Namespace-Blindfleck tmdb_tv] Stufe 1 behandelt TMDb-Movie- und TMDb-TV-ID-Raum
      als äquivalent (`ALLOWED_NFO_PROVIDER_LABELS` enthält `tmdb_tv`,
      `gui/core/similar_titles.py:25`), um den Label-Fehler in
      `nfo_helper.py:142-145` zu kompensieren. Ein TV-Show-NFO in der Film-Kategorie
      mit kollidierender ID kann einen False-Positive in Stufe 1 erzeugen, der UI-seitig
      kategorisch als „Diesen Film hast du schon" formuliert wird (`app.js:10452`).
      Langfristig: Film-NFOs korrekt als `tmdb` labeln (statt `tmdb_tv`) und
      `tmdb_tv` aus der NFO-Label-Whitelist entfernen.
- [ ] [Performance R1-Potenzierung] Kategorie-Scan läuft pro Vorschau zweimal
      (Stufe 1 `queue_api.py:368` + Stufe 2 `queue_api.py:383`), je O(n) listdir/isdir
      synchron auf dem SMB-Mount. Mit Timeout/Thread-Kapselung (R1) gemeinsam beheben;
      ggf. Scan-Ergebnis einmal erheben und beiden Stufen zuführen.
- [ ] [Heuristik V2] Singular/Plural („Alien: Romulus" vs. „Aliens") und
      Fortsetzungszahlen an Titeln („X2" vs. „X-Men") werden nicht erkannt, weil keine
      Stemming-/Token-Präfix-Logik existiert (Präfixregel wirkt nur auf den Gesamttitel,
      `similar_titles.py:322`). Als bewusste MVP-Grenze akzeptiert; bei Bedarf
      Stemming/Normalisierung erweitern.
- [ ] [Architektur-Schuld] Vier Ähnlichkeits-/Normalisierungssysteme driften
      (`mw_metadata.calculate_match_score`, `duplicates._titles_match`,
      `normalize_series_name`, neu `similar_titles._clean_title_and_tokens`).
      Bei nächstem Ähnlichkeits-Feature konsolidieren.
- [ ] [Bestand-XSS, außerhalb Scope] `app.js:10488` setzt `data.destination` unescaped
      in `innerHTML`. Bestandscode, nicht vom Feature verursacht — separat beheben.
- [ ] [R3] doku/anime/youtube erreichen keinen Warn-Zweig; Feature tut dort stillschweigend nichts.
- [ ] [V2-Franchise] TMDb `belongs_to_collection`; vor Umsetzung Lizenz-/API-Terms-Prüfung + Alex-Go.
- [ ] [scout-Ideen] „Du hast das schon"-Sammelreport mit Sidebar-Badge; Prüfung bereits im Suchschritt vor der Zielauswahl.
```

---

## 5) Blocker ja/nein

**Nein — keine Blocker.** Die Abnahme kann erteilt werden.

Zusammenfassung der geprüften Sicherheitsgrenzen als Beleg:
- **Escaping vollständig:** `folder`, `relative_path`, `overlap` alle via `escapeHTML` (`app.js:10436-10438`); Summary-Zahl escaped (`app.js:10467`); Header-Texte statisch. XSS-Fix `:10380` umschließt **beide** Felder (`nas_name` **und** `metadata_name`). AK8/AK18 decken das testseitig ab.
- **Keine anderweitige Einschleusung:** `folder`/`relative_path` gelangen ausschließlich in die neue Box (escaped); `show_name_mismatch`-Werte werden nur noch in `innerHTML` (escaped) bzw. `.value`/JS-Objekt (sicher) verwendet (`app.js:10392/10395/10407/10409`). Einziges offenes Fenster ist das Bestands-`destination` (`app.js:10488`, Notiz O4).
- **CSRF/Auth unverändert:** Endpoint ist Bestand (`queue_api.py:20-21`), nur Response-Erweiterung. Backend-Tests fahren mit Login + `X-CSRF-Token` (`test_similar_titles_hint.py:86-97`).
- **Keine neuen Abhängigkeiten:** `similar_titles.py` importiert nur `os/re/unicodedata` + drei interne Module (`similar_titles.py:13-19`).
- **Fehler-Contract:** try/except um Gesamtblock (`queue_api.py:367-395`), Skip+Log pro NFO/Lese-Fehler (`similar_titles.py:262-289`, `:132-168`), kein HTTP-Fehler durch das Feature; fehlendes NAS → leere Liste (`similar_titles.py:252`, `:302`).
- **Keine Hintertüren:** Tests nutzen Env-Vars + `patch` (Standard-Testinfrastruktur), kein Env-Branch/Sonderpfad im Produktivcode. `read_nfo_metadata` unverändert, `calculate_match_score` nirgends referenziert (grep bestätigt), TV-Zweig ab `queue_api.py:397` unberührt, Outbox/Serien nicht angesprochen.
- **Kein Payload-Leak:** `currentPreviewPayload = basePayload` (`app.js:10486`), Ausführungs-Payload ist `{...currentPreviewPayload, explicit_*}` (`app.js:10740-10745`) — `similar_existing` existiert nur in `data`, nicht in `basePayload`. AK9 assertiert `similar_existing === undefined` im Process-Payload.
- **Cache-Buster konsistent:** `index.html:2766` `?v=105`, alle 9 Imports `app.js:1-9` `?v=105`.
