---
kind: plan
status: approved
approved_by: alex
approved_on: 2026-10-16
approval_quote: "ja, R3a übernehmen wie empfohlen, starte den Lauf"
source: roadmap#78
---

# Feature Briefing: #78 — Folgenzuordnung erkennt „Staffel X Folge Y“ serverseitig

**Bindende Alex-Entscheidungen (wörtlich, 2026-10-16):** „1–3 wie empfohlen, starte die Kette“ — (1) **enges** Server-Muster statt Kopie des Client-Musters, (2) Ablauf Gate-A2 → Plausibilität → Rückkanal → Handtest (TMDB-Anbietermodus, „Alle Staffeln“) → `kit-push-approved-head`, (3) Push mit minimalem Planer-Prompt (Test der neuen `ceo-planner`-Anweisung).

**Nachtrag (Alex, wörtlich, 2026-10-16):** „ja, R3a übernehmen wie empfohlen, starte den Lauf“ — R3a gehört zum Umfang; der Worker darf dafür zusätzlich den R3-Zweig in `handle_api_match_episodes` ändern.

## 1. Problem

`gui/api/search_api.py`, `handle_api_match_episodes`: Die Hilfsfunktion `parse_season_episode` (Z. 118–126, aus #76) erkennt Staffel/Folge nur bei `s(\d+)e(\d+)` und `(?<!\d)(\d+)x(\d+)(?!\d)`. Namen wie `The Walking Dead Staffel 11 Folge 14.mkv` fallen in den alten Pfad (`guess_ep_num` → isolierte Zahl → `absolute_number`/Suffix) und können bei „Alle Staffeln“ einer fremden Staffel zugeordnet werden. Die Staffel-Regeln R1–R3 (Z. 141–164) greifen für diese Namen nicht.

## 2. Regel (verbindlich)

- **R6 Ausgeschriebene Staffel/Folge:** `parse_season_episode` erkennt zusätzlich — **nach** den beiden bestehenden Mustern, die Vorrang behalten — folgendes Muster (case-insensitive):
  `\b(?:staffel|season)[\s._-]*(\d{1,3})\b.{0,40}?\b(?:folge|episode|ep)[\s._-]*(\d{1,4})\b`
  Ergebnis `(Staffel, Folge)` als Zahlen. Damit gelten für diese Namen R1–R3 aus #76 unverändert (exakter Schlüssel zuerst; Staffel vorhanden, Folge fehlt → `None`; Staffel nicht in der Liste → bisheriges Verhalten).
- **R3a Folgennummer bei Einzelstaffel-Listen:** Wurde Staffel/Folge erkannt (R6 oder die bestehenden Muster), die Liste enthält die Staffel aber nicht (R3), und es gibt einen einfachen Nummern-Schlüssel `str(Folge)` (z. B. `"14"`), dann ist **dieser** die Zuordnung — vor dem bisherigen Pfad. Grund: Der bisherige Pfad nimmt bei `Staffel 11 Folge 14` die erste freistehende Zahl (`11`). Für `SxxEyy` ändert R3a nichts (der bisherige Pfad liefert dort schon die Folgennummer).
- **Nicht** erkennen: Kurzformen `s`, `st`, `e`, `f` allein (das Client-Muster in `gui/static/js/parse.js:74–77` ist bewusst großzügiger und bleibt unverändert).
- **R4a unverändert:** Eine Zahl in Klammern außerhalb 1900–2100 hat weiterhin Vorrang (z. B. `Staffel 2 (Folge 14)` oder `(381)` → bisheriger Klammer-Pfad); Klammer-Jahre 1900–2100 werden ignoriert.
- **R4 unverändert:** Namen ohne Staffelangabe (`Folge 381`, `ep 05`, isolierte Zahlen) und mit Staffel ohne Folge (`Staffel 2`) → bisheriges Verhalten.
- `guess_ep_num` bleibt unverändert.

## Akzeptanzkriterien

- AK0 Ausgangsmessung: bestehende Suite vor der Änderung grün (vom Reviewer belegt).
- AK1 Liste `S01E01 … S11E24` (mit `absolute_number`), Datei `The Walking Dead Staffel 11 Folge 14.mkv` → `S11E14`.
- AK2 Schreibweisen → `S11E14`: `The.Walking.Dead.Staffel.11.Folge.14.mkv`, `The Walking Dead - Season 11 - Episode 14.mkv`, `twd_staffel_11_ep_14.mkv`, `THE WALKING DEAD STAFFEL 11 FOLGE 14.mkv`.
- AK3 Liste mit `S11E01 … S11E10` und `S01E01 … S01E20`, Datei `… Staffel 11 Folge 14 …` → `None` (R2).
- AK4 Einzelstaffel-Liste `"1" … "23"`, Datei `… Staffel 11 Folge 14 …` → `"14"` (R3a; ohne R3a wäre es `"11"`). Zusätzlich: `…S11E14…` gegen dieselbe Liste → `"14"` (unverändert).
- AK5 Unverändert (gegen den Stand vor der Änderung gleich): `Folge 381.mkv`, `Show (381).mkv`, `Show Staffel 2.mkv`, `Show Staffel 2 (Folge 14).mkv` — Zuordnung identisch zum Verhalten ohne R6 (Test vergleicht mit erwarteten Werten aus dem alten Pfad, z. B. über absolute Nummer bzw. `None`).
- AK6 Abstandsgrenze: `Staffel 11 <mehr als 40 Zeichen Text> Folge 14` → R6 greift **nicht** (bisheriges Verhalten).
- AK7 Vorrang: `The.Walking.Dead.S10E18.Staffel.11.Folge.14.mkv` → `S10E18` (SxxEyy hat Vorrang vor R6).
- AK8 Alle bestehenden Tests in `tests/test_match_episodes_season.py` und `tests/test_utils.py` bleiben unverändert grün.
- AK9 Gesamte Suite grün (`pytest` ohne den bekannten Umgebungs-Test, Frontend-Tests), `git diff --check` sauber.

## Worker-Auftrag

1. Nur `gui/api/search_api.py` ändern, und dort nur (a) `parse_season_episode` (drittes Muster R6 ergänzen) und (b) den R3-Zweig in `handle_api_match_episodes` (Staffel nicht in der Liste → R3a vor dem bisherigen Pfad); keine anderen Stellen, `guess_ep_num` unverändert.
2. Neue Tests **ergänzend** in `tests/test_match_episodes_season.py` (bestehende Tests nicht ändern) für AK1–AK7, Muster wie die vorhandenen Tests (`fetch_*` mocken, im `tearDown`/`finally` zurücksetzen, keine Netzwerkzugriffe, keine Dateien außerhalb von `tmp_path`).
3. Nicht anfassen: `gui/static/**`, `tests/test_utils.py`, `ROADMAP.md`, `API.md`, `docs/**`, `scripts/**`, übrige `gui/**`, `data/**`; `.env` nie lesen. Kein Cache-Buster.

## Freigabe- und Merge-Pfad

Gate-A2-Lauf → Plausibilitätsprüfung (Claude Code) → Rückkanal (`ceo-planner` über `scripts/opencode-guarded-run.py`, Ergebnis `docs/sessions/2026-10-16-roadmap78-staffel-folge/rueckkanal.md` mit `ABNAHME: JA|NEIN`) → Handtest Alex im TMDB-Anbietermodus mit „Alle Staffeln“ → Freigabe-Datei (Reviewer, nach dem Rückkanal-Commit) → `ceo-planner` (minimaler Prompt) → `pr-operator` → `kit-push-approved-head` → PR → Merge Alex → NAS-Update (Klasse C).
