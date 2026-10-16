ABNAHME: JA

# Rückkanal: ROADMAP #78 — R6/R3a-Patch (Folgenzuordnung „Staffel X Folge Y“)

Datum: 2026-10-16. Geprüft: Arbeitsbaum im Worktree `fix-roadmap-78-staffel-folge` (HEAD `acd5fa5`, Patch uncommittet).
Auftragsgrundlage: `docs/sessions/2026-10-16-roadmap78-staffel-folge/briefing.md` (status: approved, Alex-Zitat: „ja, R3a übernehmen wie empfohlen, starte den Lauf“).

## Prüfmodus und Grenzen (Transparenz)

- Diese Prüfung ist **rein lesend** (Auftrag: „nur lesen“). Kein Git, keine Testausführung — `bash` steht im Rückkanal nicht zur Verfügung.
- **Nicht selbst verifiziert** (Übernahme als Behauptung von Claude Code, plausibel, aber unbelegt durch eigenen Lauf): Suite 529 passed/1 deselected + Frontend 186/186 (AK8/AK9), `git diff --check` sauber, „0 entfernte Zeilen“.
- Indiz für „nur Zusätze, keine Löschungen“ (eigenständig geprüft): Die Zeilenlage passt exakt zur Additionsarithmetik — `parse_season_episode` alt 118–126 → neu 118–134 (+8 Zeilen R6-Block, `search_api.py:126–133`); R1–R3 alt 141–164 → neu 154–177 (+13 = +8 R6 +5 R3a, `search_api.py:173–177`). Der Rest des Alt-Blocks (R4a `:140–147`, alter Pfad `:179–235`, `guess_ep_num` `:83–112`) ist inhaltlich deckungsgleich mit der in #76 dokumentierten Fassung.

## Auftrag 1 — Umsetzung R6/R3a, Unversehrtheit R4a/R4/`guess_ep_num`, Testdeckung

**R6 (`search_api.py:126–133`):** Muster wortgleich zum Briefing (`:128`). Eingereiht **nach** `s(\d+)e(\d+)` (`:120`) und `(?<!\d)(\d+)x(\d+)(?!\d+)` (`:123`), die per Early-Return den Vorrang behalten — AK7-Vorrang ist damit strukturell korrekt, nicht nur per Test belegt.

**R3a (`search_api.py:173–177`):** Korrekt platziert — **nach** R1 (exakter Schlüssel, `:164–167`) und R2 (Staffel vorhanden, Folge fehlt → `None`, `:168–171`), **vor** dem Abfall in den alten Pfad (`:179`). `str(file_e) in episodes` greift nur, wenn die Staffel nicht als `sXe`-Schlüssel in der Liste vorkam. R4a (`:140–147`) kurzschließt den gesamten Parse-Block (`:149`) — Klammer-Vorrang bleibt gewahrt.

**Unverändert:** `guess_ep_num` (`:83–112`), alter Pfad inkl. Fuzzy (`:179–235`), R4a (`:140–147`). Keine Änderungen außerhalb der zwei per Briefing erlaubten Stellen sichtbar.

**Testdeckung AK1–AK7 (7 neue Tests, `tests/test_match_episodes_season.py:202–340`, alle Erwartungen einzeln gegen den Code durchgespielt):**

- **AK1** (`:202–216`): Liste S01E01…S11E24 mit `absolute_number`, `The Walking Dead Staffel 11 Folge 14.mkv` → erwartet `S11E14`. Korrekt: ohne R6 hätte der alte Pfad 11 → `absolute_number` 11 → `S01E11` geliefert — der Test unterscheidet wirklich alt/neu. ✓
- **AK2** (`:218–238`): alle vier Schreibweisen aus dem Briefing, inkl. `twd_staffel_11_ep_14.mkv` → `S11E14`. ✓ (zu Unterstrich-Handling siehe Befund 1)
- **AK3** (`:240–259`): S11E01..10 + S01E01..20, `Staffel 11 Folge 14` → `None` via assertIn+assertIsNone — prüft R2, nicht nur „irgendein None“. ✓
- **AK4** (`:261–282`): Liste `"1".."23"`, ausgeschriebener Name → `"14"` **und** `S11E14`-Name → `"14"`. Ersteres unterscheidet R3a (neu `"14"`) vom alten Pfad (isolerte erste Zahl → `"11"`); zweiteres belegt „unverändert für SxxEyy“. ✓
- **AK5** (`:284–307`): alle vier Namen mit erwarteten **Alt-Pfad-Werten** — `Folge 381`→`S2010E39` (R6 liefert None, kein Staffel-Token), `Show (381)`→`S2010E39` (R4a kurzschließt), `Show Staffel 2`→`S01E02` (R6 braucht zwingend Folge-Token), `Show Staffel 2 (Folge 14)`→`S01E14` (R4a-Vorrang: ohne Kurzschluss hätte R6 (2,14) → `S02E14` geliefert — der Test differenziert also exakt die R4a-Grenze). ✓
- **AK6** (`:309–324`): Lücke 43 Zeichen („Staffel 11 “ + 41×x + “ Folge 14“) > 40 → R6 greift nicht → alt-Pfad-Wert `S01E11`, plus assertNotEqual auf `S11E14`. Durchgespielt: im x-Füllungstext steckt kein `\d+x\d+`-Treffer und kein „ep“-Token — der Fallback-Wert ist korrekt hergeleitet. ✓
- **AK7** (`:326–340`): `S10E18.Staffel.11.Folge.14` → `S10E18` (Muster-1-Vorrang). ✓

Bestehende Tests `:36–199` (Nummerierung aus #76) inhaltlich gegen den gepatchten Code geprüft: alle Erwartungen bleiben erfüllbar (Muster-1/2 unverändert, R3a liefert für `S11E01` gegen `"1".."23"` dasselbe `"1"` wie der alte Pfad; Jahres-Schlüssel-Test `:116–132` fällt durch R3a hindurch, `"39"` ist kein Key). `test_utils.py:2153` (Klammer-/SxxEyy-Fälle) und `:2956` (`episode1.mp4` → kein Staffel-Token, R6/R3a inaktiv) bleiben gültig.

## Auftrag 2 — Hinweise (a)–(d)

**Befund 1 [wichtig] — (a) `norm_name`-Abweichung: angemessen, nötig und eng begrenzt; muss aber als dokumentierte Abweichung zum Briefing-Wortlaut an Alex.**
`search_api.py:126` ersetzt `_`→Leerzeichen **nur** für das R6-Muster (`:127–131`); Muster 1/2 laufen weiterhin auf `clean_name`. Die Begründung von Claude Code stimmt und ist verifiziert: `_` ist ein `\w`-Zeichen, daher greift `\b` zwischen `_` und Buchstabe nicht — das Briefing-Muster (`briefing.md:23`) kann auf `twd_staffel_11_ep_14.mkv` prinzipiell **nicht** matchen, AK2 (`briefing.md:35`, verbindliches Akzeptanzkriterium) wäre mit dem Wortlaut-Muster unerfüllbar. Briefing-interner Widerspruch, vom Worker zugunsten des bindenden AK gelöst. Eng genug: 1:1-Zeichenersetzung (`. {0,40}`-Abstandszählung verschiebt sich nicht), keine neuen False-Positive-Klassen (R6 verlangt weiterhin die Literal-Tokens staffel/season + folge/episode/ep mit Ziffer). Empfehlung: Abweichung in PR-Beschreibung und Alex-Zusammenfassung explizit nennen; **keine** Codeänderung.

**Befund 2 [kosmetisch] — (b) `re.IGNORECASE` (`search_api.py:130`) ist redundant.**
`clean_name` ist bereits lowercase (`:119`), `norm_name` geerbt davon (`:126`), das Muster ist komplett kleingeschrieben — die Flag kann nie wirken. Rein kosmetisch, kann bleiben oder fallen.

**Befund 3 [wichtig] — (c) R3a bei reinen Nummern-Listen: Verhalten ändert sich wie beschrieben, aber es ist die freigegebene Regel; keine Regression, wo der alte Pfad richtig lag.**
Der Fall `Show Staffel 11 Folge 30.mkv` gegen `"1".."500"` (alt `"11"`, neu `"30"`) ist real und reproduziert die Code-Logik (`:175`). Bewertung: **beide** Zuordnungen sind bei absoluter Zählung falsch (korrekt wäre die absolute Nummer von S11E11…S11E30, z. B. ~244) — der alte Wert `"11"` war genau die von #78 behobene Fehlerklasse (Staffelnummer als Folgennummer). Systematisch geprüft über alle drei Parse-Klassen: (i) `sXe`-Namen: alt liefert via `guess_ep_num:91` bereits die Folgennummer = R3a-Ergebnis, keine Änderung; (ii) `NxN`-Namen: alt via `:95` dasselbe, keine Änderung; (iii) ausgeschriebene Namen: alt = erste freistehende Zahl (praktisch immer die Staffelzahl, seltener None/Jahr-Skip) — nie „richtig, wo R3a falsch“; ausgenommen sind nur Klammer-Fälle, die R4a (`:143–147`) vor R3a kurzschließt. **Restgrenze** (neu wie alt, nicht verschlimmert): ausgeschriebene Namen gegen absolute Einzelstaffel-/Playlist-Listen (mediathek/ytdlp `"1".."N"`, `:67–75`) landen auf `"Folgennummer"` statt der wahren absoluten Nummer — Empfehlung: als Follow-up in `ROADMAP.md` notieren (Staffel→Absolut-Mapping bräuchte Metadaten-Kontext), kein Blocker für #78.

**Befund 4 [kosmetisch/Notiz] — (d) Beide genannten Grenzen sind außerhalb des freigegebenen Umfangs und unverändert.**
`Folge 14 Staffel 11` (umgekehrte Reihenfolge): R6-Muster ist gerichtet (staffel vor folge) → kein Match → exakt alter Pfad wie vor dem Patch; das Client-Muster (`gui/static/js/parse.js:74`) ist ebenfalls gerichtet — konsistent, kein neuer Divergenzpunkt. `1920x1080`: Muster 2 (`search_api.py:123`) parst (1920,1080) → Staffel fehlt → R3a prüft `"1080" in episodes` und fällt durch (realistische Listen <1080 Keys; selbst bei ≥1080 Keys, z. B. große ytdlp-Playlists, liefert der alte Pfad via `\d+x(\d+)` in `guess_ep_num:95` **dieselbe** Nummer) → Verhalten vor = nach Patch. Bereits im #76-Rückkanal (`docs/sessions/2026-10-15-roadmap76-staffel/rueckkanal.md:39`) als unkritisch bewertet. Ggf. zusammen mit Befund 3 als Backlog-Eintrag notieren.

## Auftrag 3 — Wirkung auf weitere Aufrufer

Einziger Konsument von `/api/match-episodes` bleibt `gui/static/app.js:3645` (grep über `gui/static/` und API-Suche; `parse_season_episode` ist eine lokal verschachtelte Funktion ohne externe Aufrufer). Serverseitige Nachgelagerte (`processor.py`, `queue_api.py`) konsumieren ausschließlich die bestätigte Auswahl und erhalten damit die **korrigierten** Keys — konsistent mit dem #76-Befund (`docs/sessions/2026-10-15-roadmap76-staffel/rueckkanal.md:41`).

Client-Pfade einzeln durchgespielt:
- **R3a-Treffer `"14"` in Einzelstaffel-Modus:** `app.js:3856` vergleicht `String(guessedEp) === String(num)` → `"14"` selektiert korrekt; vorher wurde `"11"` selektiert — genau die beabsichtigte Verbesserung, kein neuer Zustand.
- **R6/R2-`None` (AK3-Fall):** `app.js:3817` behandelt Server-`null` wie bisher (seit #76) → Fallback auf `guessSeasonAndEpisode` (`js/parse.js:64–78`, unverändert großzügiger) → dessen `S11E14` existiert in der Liste nicht → keine Option selektiert, Default bleibt „Überspringen“ (`app.js:3844`). Keine Fehlzordnung durch den Client-Backstop.
- **mediathek/ytdlp (Nummern-Keys):** R3a kann dort `"e"` liefern; im „Alle Staffeln“-Vergleich `guessedEp === num` (`app.js:3854`) sind beide Strings → korrekt selektiert.
- `gui/static/**` wurde laut Scope nicht angefasst; kein Cache-Buster nötig und gesetzt — konsistent.

## Befunde gesamt (nach Schwere)

1. [wichtig] R6 weicht vom Briefing-Wortlaut ab (`_`→Leerzeichen, `search_api.py:126`) — **begründet und nötig** (Briefing-Muster mit AK2 inkonsistent), eng begrenzt. Empfehlung: als dokumentierte Abweichung in PR/Alex-Zusammenfassung; kein Rückfall.
2. [wichtig] R3a-Restgrenze bei absoluten Nummern-Listen (Befund 3): `"30"` statt wahrer absoluter Nummer — freigegebener Trade-off, alt war nicht richtig. Empfehlung: Follow-up-Eintrag `ROADMAP.md`.
3. [kosmetisch] `re.IGNORECASE` redundant (`search_api.py:130`).
4. [kosmetisch] Umgekehrte Reihenfolge (`Folge 14 Staffel 11`) und `1920x1080` bleiben ungelöst — außerhalb des Umfangs, Verhalten unverändert (Befund 4).
5. [wichtig-Prozess] AK8/AK9 (Suite grün, `git diff --check`) und „0 entfernte Zeilen“ wurden hier **nicht selbst ausgeführt/geprüft** (kein Git/bash im Rückkanal); Indizien (Zeilenarithmetik, Durchspielen aller Alt-Erwartungen) sprechen dafür. Abdeckung obliegt dem nächsten Schritt (Reviewer-Freigabe vor `kit-push-approved-head`).

Keine Blocker. Der Patch setzt R6 und R3a regelkonform um, respektiert R4a/R4/`guess_ep_num` und wird durch die 7 neuen Tests differenzstark gedeckt (AK1/AK4/AK5/AK6 unterscheiden messbar alt vs. neu).

## Empfehlung nächste Schritte

Weiter gemäß Briefing-Ablaufkette: Handtest durch Alex (TMDB-Anbietermodus, „Alle Staffeln“, mit ausgeschriebenen Namen inkl. `_`-Schreibweise), danach Reviewer-Freigabe/`approved-head.json` und `kit-push-approved-head`. PR-Beschreibung soll Befund 1 (Abweichung) und Befund 2 (Restgrenze) erwähnen.

VERDICT: APPROVE
1. [wichtig] Abweichung `_`→Leerzeichen dokumentieren (Befund 1) — Annahme, keine Rückforderung.
2. [wichtig] R3a-Restgrenze absolute Listen als ROADMAP-Follow-up (Befund 3).
3. [kosmetisch] `re.IGNORECASE` optional entfernen (Befund 2).
4. [kosmetisch] Reihenfolge/Auflösungs-Grenzen optional backloggen (Befund 4).
