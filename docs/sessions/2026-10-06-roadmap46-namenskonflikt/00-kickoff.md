# Kreativteam-Session 2026-10-06 — ROADMAP #46 + Namenskonflikt-Bugfix
## Akt 1: Kickoff (Moderator/Synthese) — vor Freigabepunkt 1

Input war der Entwurf des Reviewers (Claude Code), KEIN abgenommener Plan.
Alle Behauptungen wurden read-only gegen den Code im Worktree
`feat-roadmap-46-namenskonflikt` geprüft. Ich habe kein `bash` — Git-Zustand
und Testausführung sind mir nicht direkt verifizierbar.

## 1. Verifizierter Scope

### #46 Profil-Dropdown (bestätigt)
- `gui/static/app.js:10569` — `await fetch("/api/profile", ...)` in
  `btn-preview-execute`; kein `response.ok`-Check, kein Aufruf von
  `populateLocalProfilesDropdown()` nach dem Speichern.
- `populateLocalProfilesDropdown()` existiert (`app.js:12385`, aufgerufen
  u. a. `12428`, `15052f.`); `appendConsoleLog` ist vorhanden (z. B. `app.js:10597`).
- Reiner Client-Fix, keine Server-Änderung — konsistent mit Alex' "F5 reicht".

### Bug: Endlosschleife Namenskonflikt-Hinweis (bestätigt)
- `gui/api/queue_api.py:750-762` (Handler `/preview_process`, Route ab Zeile 19/20):
  `show_name_mismatch` wird aus `nas_match_folder` (via Show-ID gefunden) vs.
  `metadata_show_name` berechnet. Das Request-Feld `nas_show_folder` wird zwar
  in Zeile 407 gelesen und an `resolve_series_folder_name` (Zeile 412-421)
  übergeben, BUT der Mismatch-Block ignoriert es komplett.
- `gui/static/app.js:10286-10313`: beide Buttons ("NAS-Namen übernehmen" /
  "Metadaten-Namen übernehmen") setzen `basePayload.nas_show_folder` und rufen
  `openPreviewModal(basePayload)` → Server meldet denselben Hinweis erneut →
  Endlosschleife. Mechanik exakt wie beschrieben.
- Alex' Entscheidung 1 (nicht neu verhandeln): kein Hinweis, wenn
  `nas_show_folder` dem gefundenen NAS-Ordner ODER dem bereinigten
  Metadatennamen entspricht; dritter Name → Hinweis bleibt.

### Herkunft "... 2010 US TMDB TV" (bestätigt, nur zu dokumentieren; Fix = #66)
- Suchlabel-Kette real, mit Pfadkorrektur gegenüber dem Entwurf:
  - `gui/mw_metadata.py:233` — TVDB-Label `f"{title} ({year}) [{country}]"`;
  - `gui/mw_metadata.py:398` — Provider-Anhängung `f"{r['name']} [{provider.upper()}]"`;
  - `clean_show_name` in `gui/core/utils.py:23` (nicht `gui/utils.py`) —
    entfernt Klammerklammern `[^\w\s._-]`, lässt KlammerINHALT als Klartext übrig;
  - `clean_series_name_for_fs` in `gui/core/helpers.py:97` — entfernt nur
    * trailing* `[...]`-Tags, nicht die im Dateiname stehen gebliebenen
      Klartext-Reste ("2010 US TMDB TV").

### Tests & Umgebung (bestätigt)
- `tests/test_utils.py:18` `class TestMediawerkzeugLogic`;
  `test_find_folder_by_id_and_name_mismatch` (Zeile 3047),
  `test_false_positive_show_name_mismatch_with_different_years` (Zeile 3123) vorhanden.
- Frontend-Harness: `package.json` → `test:frontend = node --test "tests/frontend/**/*.test.js"`;
  DOM-Mock-Muster vorhanden (z. B. `tests/frontend/app_warning.test.js`) —
  neue Tests `profile_dropdown_refresh.test.js` sind so modellierbar.
- `ROADMAP.md`: #46 existiert (Zeile 1404); höchste Nummer ist **63** →
  #64/#65/#66 sind die nächsten freien Nummern, Einträge existieren noch NICHT.
- `scripts/check_updates.py` existiert nicht im Worktree → Capability-Check:
  nicht nötig. `STAND.md` existiert nicht im Worktree (flüchtig, ok).

## 2. BEFUND gegen den Entwurf: AK7 ist zu eng (wichtig)

`tests/frontend/cache_busting.test.js` (bestehend, AK1-treu zu haltend) erzwingt:
Version im `index.html`-Script-Tag == Version in ALLEN ES-Module-Imports von
`app.js`. Aktuell: `index.html:2752` `app.js?v=93` UND `app.js:1-9` neun
Importe mit `?v=93`. Würde der Worker nur `index.html` auf v94 heben (wie AK7
formuliert), fällt der bestehende Cache-Busting-Test um → AK1 und AK7
widersprechen sich.
Korrekter AK7: **alle 10 Vorkommen `?v=93` → `?v=94`** (index.html +
app.js-Zeilen 1-9). Kein Produktiv- oder Testcode-Umbau nötig.

## 3. Konsultationsplan Akt 2 (nach Scope-Go)
- `produktberater` — Scope-Wächte: Bündelung 2 Fixes + 3 ROADMAP-Texte in
  einem PR sinnvoll? MVP-Grenze.
- `advocatus` — Risiken/Edge-Cases: Normalisierung beim
  nas_show_folder-Vergleich (clean_series_name_for_fs +
  limit_filename_length auf beiden Seiten? Groß-/Kleinschreibung? leerer/
  whitespace-Wert?), Fehlerpfad #46 (Race mit closePreviewModal, await vs.
  fire-and-forget), Test-Design AK2-AK6.
- `grafiker` — optional, nur Kurzvotivtext der
  appendConsoleLog-Fehlermeldung.
- `scout`, `rechercheur` — nicht nötig (Inhalt #64-#66 von Alex entschieden;
  keine neuen externen Tools).
- `plan-reviewer` — Pflicht vor finalem Planreview (VERDICT: APPROVE auf
  briefing.md).
- `repo-operator` — nur nach Alex-Go für Git-Schreibaktionen.

## 4. Offene Scope-Fragen an Alex (Freigabepunkt 1)

**Q1 — ROADMAP-Mechanik #64-#66:** Gate-A2-Worker darf ROADMAP.md nicht
anfassen; meine Editierrechte schließen ROADMAP.md aus.
Empfehlung: Ich formuliere die drei Einträge (Nummern 64/65/66, Format wie
bestehende Einträge) wörtlich in
`docs/sessions/2026-10-06-roadmap46-namenskonflikt/roadmap-neue-eintraege.md`;
`repo-operator` übernimmt sie nach Alex-Go wortgleich in ROADMAP.md — im
selben ersten PR. Trade-off: ein Delegationsschritt mehr.
Entscheidung: Verfahren ok?

**Q2 — Tragweite #64-#66 im "ersten PR":** Ich verstehe das als reine
Backlog-TEXT-Einträge (ohne Implementierung), denn die Grenzen sagen
"keine Migration", #66 aber enthält "sanfte Migration".
Empfehlung: ja, nur Texte. Bestätigung?

**Q3 — AK7-Korrektur:** Vorschlag wie oben (alle 10 `?v=93`-Stellen).
Empfehlung: AK7 so ersetzen; sonst Selbstwiderspruch des Plans.

**Q4 — Git-Preflight (Formalie):** Die Eingabe behauptet "Branch
feat/roadmap-46-namenskonflikt, sauber, Stand origin/main 3522ef2". Ohne
`bash` kann ich das nicht selbst prüfen. Bitte vor dem ersten
Commit-Vorschlag die wörtliche Ausgabe von `git status --short --branch`
sowie `git log --oneline -3` liefern (Herkunft-von-Text-Regel).

## 5. Status
Stop am Freigabepunkt 1 (Scope-Abstimmung). Keine interne Ausarbeitung,
keine Subagenten-Konsultation, keine Writes über diese Doku-Datei hinaus,
bis Alex' Antwort über Claude Code vorliegt.
