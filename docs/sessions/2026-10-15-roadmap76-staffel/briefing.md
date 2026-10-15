---
kind: plan
status: approved
approved_by: alex
approved_on: 2026-10-15
approval_quote: "1–3 wie empfohlen, starte die Kette"
source: roadmap#76
---

# Feature Briefing: #76 — Folgenzuordnung berücksichtigt die Staffel („Alle Staffeln“)

**Bindende Alex-Entscheidungen (wörtlich, 2026-10-15):** „1–3 wie empfohlen, starte die Kette“ (Plan ADR 1–5: strenge Staffelregel, Ablauf Gate-A2 → Plausibilität → Rückkanal → Handtest → `kit-push-approved-head`, kein Ausweichen auf Handweg) und „ja, ADR 1 so verfeinern wie empfohlen“ (Strenge nur, wenn die Folgenliste die Staffel der Datei enthält). Nach dem ersten Gate-A2-Lauf (Worker grün, Reviewer am Gateway-Guthaben gescheitert, Lücke bei Jahreszahlen in Klammern gefunden): „Guthaben ist aufgeladen, 1 und 2 wie empfohlen“ (R4a + AK10, vollständig neuer Lauf).

## 1. Problem

`gui/api/search_api.py`, Endpoint `/match-episodes` (`handle_api_match_episodes`, ab Z. 42). Für Dateinamen mit `SxxEyy` liefert `guess_ep_num` (Z. 82–110) nur die Folgennummer (`s\d+e(\d+)`, Z. 90–92; ebenso `\d+x(\d+)`, Z. 94–96). Danach (ab Z. 120):
1. Direktprüfung `str(ep_num) in episodes` (Z. 122–125),
2. `absolute_number == ep_num` (Z. 127–138) — trifft bei „Alle Staffeln“ z. B. `S01E01` (absolute 1) für `S11E01`,
3. Suffix-Suche `^s\d+e(\d+)$` (Z. 140–150) — erster Schlüssel mit gleicher Folgennummer, egal welche Staffel.

Live-Befund (NAS, 13.10.2026, The Walking Dead, TMDB, „Alle Staffeln“): S11E01→S01E01, S11E07→S02E07, S11E14→S03E14, S11E17→S10E17. Die Server-Zuordnung hat Vorrang vor der korrekten Client-Erkennung.

## 2. Regel (verbindlich)

Für einen Dateinamen mit erkennbarer Staffel und Folge — `s(\d+)e(\d+)` oder `(\d+)x(\d+)` (case-insensitive) — mit Staffel `S` und Folge `E` (als Zahlen):

- **R1 Exakt zuerst:** Gibt es in `episodes` einen Schlüssel, der dem Muster `^s(\d+)e(\d+)$` (case-insensitive) folgt und dessen Zahlen `(S, E)` sind (führende Nullen egal), ist **dieser** die Zuordnung.
- **R2 Staffel vorhanden, Folge fehlt:** Gibt es Schlüssel mit Staffel `S` (Muster wie R1), aber keinen mit `(S, E)` → Zuordnung `None`. **Weder** `absolute_number` **noch** Suffix-Suche **noch** Fuzzy-Titelabgleich dürfen dann einen Schlüssel einer anderen Staffel liefern.
- **R3 Staffel nicht vorhanden:** Enthält `episodes` keinen Schlüssel mit Staffel `S` (z. B. nur einfache Nummern `1…23` oder Jahres-Schlüssel `S2010E39`), gilt das **bisherige** Verhalten unverändert (Direktprüfung, `absolute_number`, Suffix-Suche, Fuzzy).
- **R4 Ohne Staffel im Namen:** Dateinamen ohne `SxxEyy`/`xxXyy` (absolute Nummern `(381)`, `[381]`, `ep 05`, isolierte Zahlen) → **unverändert**.

- **R4a Jahreszahlen in Klammern:** Eine Zahl in runden oder eckigen Klammern im Bereich **1900–2100** (z. B. `(2010)` in `The Walking Dead (2010) - S11E01 - Acheron.mkv`, das eigene Ausgabeschema des Medienwerkzeugs) ist ein **Jahr**, keine absolute Folgennummer. Für die Staffel-Erkennung (R1–R3) wird sie ignoriert; trägt der Name zusätzlich `SxxEyy`/`xxXyy`, greifen R1–R3.

Die Klammer-Prüfung für absolute Nummern in `guess_ep_num` (Z. 84–87) hat für Zahlen **außerhalb** 1900–2100 weiterhin Vorrang vor `sXXeYY`. Enthält ein Name eine solche absolute Nummer **und** `S11E01` (z. B. `(381)`), entscheidet weiterhin die Klammer (bisheriges Verhalten). `guess_ep_num` selbst bleibt unverändert; R4a gilt nur für die neue Staffel-Erkennung.

## Akzeptanzkriterien

- AK0 Ausgangsmessung: bestehende Suite vor der Änderung grün (vom Reviewer belegt).
- AK1 Liste mit `S01E01 … S11E24` (inkl. `absolute_number`, `S01E01` hat absolute 1), Datei `The.Walking.Dead.S11E01.GERMAN.mkv` → `S11E01`.
- AK2 Datei `…S11E07…` → `S11E07`, obwohl `S02E07` in der Liste vor `S11E07` steht.
- AK3 Liste mit `S11E01 … S11E10` und `S01E01 … S01E10`, Datei `…S11E14…` → `None` (Staffel vorhanden, Folge fehlt).
- AK4 Datei `…11x01…` gegen Liste aus AK1 → `S11E01`.
- AK5 Einzelstaffel-Liste mit Schlüsseln `"1" … "23"`, Datei `…S11E01…` → `"1"` (bisheriges Verhalten).
- AK6 Jahres-Liste nur `S2010E39`, `S2011E40`, Datei `…S01E39…` → `S2010E39` (R3, bisheriges Verhalten).
- AK7 Bestehender Test `tests/test_utils.py::…::test_api_match_episodes` (Absolute `(381)` → `S2010E39`, `S01E05` → `S01E05`) bleibt unverändert grün.
- AK8 Führende Nullen: Datei `…S11E1…` bzw. `…s11e01…` gegen Schlüssel `S11E01` → `S11E01`.
- AK10 Liste aus AK1, Datei `The Walking Dead (2010) - S11E01 - Acheron.mkv` → `S11E01`; Datei `Show (381) S11E01.mkv` → bisheriges Verhalten (Klammer-Pfad, keine Staffel-Logik).
- AK9 Gesamte Suite grün (`pytest` ohne den bekannten Umgebungs-Test, Frontend-Tests), `git diff --check` sauber.

## Worker-Auftrag

1. Nur `gui/api/search_api.py` (Funktion `handle_api_match_episodes` und ihre inneren Hilfsfunktionen) ändern; minimale, lesbare Änderung (z. B. Hilfsfunktion `parse_season_episode(filename) -> (season, episode) | None` und eine vorgeschaltete Prüfung vor dem bisherigen Pfad).
2. Tests in **neuer** Datei `tests/test_match_episodes_season.py` für AK1–AK8 (Muster wie `tests/test_utils.py:2153`: `fetch_*` mocken, `GUIRequestHandler.handle_api_match_episodes(dummy, params)`; Mocks im `finally` zurücksetzen; keine Netzwerkzugriffe, keine Dateien außerhalb von `tmp_path`).
3. Nicht anfassen: `gui/static/**`, `tests/test_utils.py`, `ROADMAP.md`, `API.md`, `docs/**`, `scripts/**`, übrige `gui/**`, `data/**`; `.env` nie lesen. Kein Cache-Buster (reine Server-Änderung).

## Freigabe- und Merge-Pfad

Gate-A2-Lauf → Plausibilitätsprüfung (Claude Code) → Rückkanal (`ceo-planner` über `scripts/opencode-guarded-run.py`, Ergebnis `docs/sessions/2026-10-15-roadmap76-staffel/rueckkanal.md` mit `ABNAHME: JA|NEIN`) → Handtest Alex im **Anbieter-/Profilmodus mit „Alle Staffeln“** → Freigabe-Datei (`approved-head.json`, nur Reviewer, nach dem Rückkanal-Commit) → `pr-operator`/`kit-push-approved-head` → PR → Merge Alex → NAS-Update (Klasse C).
