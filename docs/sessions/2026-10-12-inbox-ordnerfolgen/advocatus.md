# Rohoutput advocatus — Kreativteam 2026-10-12 (Akt 2, Ordner-Folgen)
Hinweis Claude Code (2026-10-12): Mechanisch aus `opencode export ses_ed092b3e0ffe9iDPDyHyWFilqY` (ceo-planner, Akt 2) abgelegt, nicht vom Moderator abgeschrieben (Lehre 59). Einzige Änderung: Trailing Whitespace entfernt. Volle Daten: Kit `scripts/gate-a2/logs/2026-10-12-inbox-ordnerfolgen/export-ceo-planner-akt2.json`.

---

## advocatus: advocatus Risiko-Jagd Akt 2 (Subagent-Sitzung ses_ed09005fdffeQr5dsDaNzbWCGO, Status: completed)

<task id="ses_ed09005fdffeQr5dsDaNzbWCGO" state="completed">
<task_result>
# Risikoprüfung (advocatus) — Session 2026-10-12 Akt 2, Medienwerkzeug

Alle Befunde read-only gegen den Worktree verifiziert. Die Alex-Entscheidungen 1–7 behandle ich als gesetzt; ich prüfe nur die Umsetzungsrisiken.

---

## [kritisch]

### K1 — „project“-Name vs. `single_video_relpath`-Dualismus bricht bei jeder Ordner-Auswahl
**Betroffen:** Scope-Punkt 3, Key-Vertrag V1, Entscheidung 3.

Der Server liefert für den Ordner `project = "ThWaDeS11E23"` (Ordnername, `project_api.py:1491`), aber der `files[]`-Eintrag soll `single_video_relpath = "ThWaDeS11E23/ThWaDeS11E23.mkv"` sein. Der Server lehnt Ordner in `files[]` hart ab (`helpers.py:851–852`: „Ordner sind im files-Parameter nicht erlaubt"). **Mindestens fünf Frontend-Stellen** verwenden heute `m.project` und würden den Ordnernamen statt des relpaths senden → HTTP 400 bei *jeder* Ordner-Auswahl:

- `detectInboxGroups` gruppiert und `push({ ...item, _se: se })` ohne relpath (`app.js:12492–12515`).
- Banner-Apply: `const files = members.map(m => m.project)` (`app.js:12630`).
- Gruppen-Knopf: `const files = item.items.map(m => m.project)` (`app.js:13075`).
- Bulk-Checkbox: `selectedInboxProjects.add(item.project)` (`app.js:13196`) und `files = Array.from(selectedInboxProjects)` (`app.js:12698`).
- `fallbackName`-Lookup `currentSmartInboxRawSuggestions.find(s => s.project === files[0])` (`app.js:12706`) matcht nicht mehr, wenn `files[0]` ein relpath ist → `firstItem` wird `undefined`, Fallback kippt auf `cleanSeriesName(relpath)`.

**Gegenmittel:** Eine einzige Hilfsfunktion `filesForItem(item)` (bei `is_dir && single_video_relpath` → relpath, sonst `project`), die an **allen** fünf Stellen verwendet wird; `selectedInboxProjects` muss entweder relpaths speichern oder ein `project → relpath`-Map führen.

**Test-AK:** *„Es prüft, dass die Auswahl eines Ordners mit `single_video_relpath` in allen vier Auswahlpfaden (Bulk-Checkbox, Banner-Apply, Gruppen-Knopf, Einzel-Checkbox) exakt den relpath-String in `files[]` legt — und dass der `fallbackName`-Lookup für einen relpath-`files[0]` nicht `undefined` liefert."*

### K2 — „genau eine Videodatei (10er-Liste)" darf **nicht** aus der bestehenden `video_files`-Liste abgeleitet werden
**Betroffen:** Scope-Punkt 2, Entscheidung 2, Notiz N3.

`video_files` wird mit der **6er-Liste** gefüllt (`project_api.py:1321`, `:1337`). Würde der Implementierer `len(video_files) == 1` als Einzelvideo-Kriterium nehmen:
- Ordner mit `.mp4` + `.wmv`: `video_files = [.mp4]` (len 1) → würde fälschlich `single_video_relpath = ".mp4"` setzen, obwohl es **2** 10er-Videos sind. Die `.wmv` bliebe unverarbeitet liegen.
- Ordner mit nur `.wmv`: `video_files = []` → `continue` (`:1345–1346`) — korrekt (N3), aber nur „zufällig".

Die Server-Logik muss eine **eigene 10er-Liste** (`GROUP_VIDEO_EXTENSIONS`, `helpers.py:798`) per `os.walk` zählen und `== 1` exakt prüfen; der relpath muss `os.path.relpath(p, inbox_dir)` sein (os.walk liefert absolute Pfade).

**Test-AK:** *„Es prüft, dass ein Ordner mit `.mp4`+`.wmv` (2 Videos nach 10er-Liste) kein `single_video_relpath` bekommt, und ein Ordner mit genau einer `.m2ts`/`.flv` (10er, aber nicht 6er) wegen `video_count == 0` gar nicht im Payload auftaucht."*

---

## [wichtig]

### W1 — `single_video_query` muss die **Dateinamen**-Pipeline laufen, nicht die Ordnername-Pipeline
**Betroffen:** Entscheidung 3, B3-Nuance, Notiz N1, offene Frage F1.

Bei losen Dateien ist `item` = Dateiname → `tv_pattern.search(item)` (`project_api.py:1417`) läuft gegen den Dateinamen. Bei Ordnern läuft dieselbe Zeile gegen den **Ordnernamen**. Für Key-Gleichheit („lose Datei + Ordner in derselben Gruppe") muss `single_video_query` die tv-Pipeline gegen `video_base` (Dateiname) durchlaufen. Sonst: Ordner `CD1/The.Walking.Dead.S01E01.mkv` liefert Schlüssel `"CD1"`, lose Datei `The.Walking.Dead.S01E01.mkv` liefert `"The.Walking.Dead"` → **keine** gemeinsame Gruppe. Zusätzlich die `clean_show_name`-Punkt-Nuance (`utils.py:23–30`: Punkte bleiben erhalten) — als AK „Gleichheit mit Einzeldatei-Ergebnis" formulieren, nicht wörtlichen String (N1). Eng gekoppelt an **F1** (Kickoff:84–85): läuft `extractStrictSeasonEpisode` in `detectInboxGroups` weiter gegen `item.project` (`app.js:12499`), wird `CD1/…` nie gruppiert.

**Test-AK:** *„Es prüft, dass `single_video_query` eines Ordners byte-identisch zum `suggested_query` ist, das die Einzeldatei-Pipeline auf denselben Dateinamen erzeugt (Punkte, nicht Leerzeichen)."*

### W2 — #72.1-Separator-Check muss Backslash explizit fangen; `os.path.basename()` genügt auf POSIX nicht
**Betroffen:** Scope-Punkt 5, `processor.py:969–978` / `:988–997`.

`os.path.basename("sub\\file.mkv")` ist auf POSIX = `"sub\\file.mkv"` (Backslash ist dort kein Separator). Ein `new` mit `\` würde den „reiner-Dateiname"-Check umgehen. Robust und portabel: `if '/' in new_s or '\\' in new_s: raise`. Der Check gehört **nur auf `new`**, nie auf `old` (das legitime „Hochziehen" `old="Sub/Datei.mkv"` → `new="Datei.mkv"` muss weiter erlaubt bleiben — B7). URL-Encoding ist im JSON-Payload irrelevant: `%2F` wird vom JSON-Parser **nicht** zu `/` dekodiert (kein Ausbruch, kein Check nötig).

**Empfehlung zum Ort:** Zusätzlich früh in `queue_api.py` `/process` (`:815–833`, wo `mappings`-Keys geprüft werden) abweisen, damit manipulierte Anfragen **sofort** 400 erhalten statt erst im Worker-Thread (`processor.py` läuft async; dort wäre es nur ein `RuntimeError`-Abbruch). Das entspricht der AK6(e)-Lehre (zwei getrennte Validierungsstränge).

**Test-AK:** *„Es prüft, dass `new = "Sub/Neuer.Name.mkv"`, `"Sub\\Neuer.Name.mkv"` und `"./x.mkv"` bei `files[]`-Jobs abgelehnt werden, während `old = "Sub/Datei.mkv"` mit reinem `new = "Datei.mkv"` erlaubt bleibt."*

### W3 — Show-Level-Dateien (`tvshow.nfo`, `poster.jpg`, `fanart.jpg`, `season.nfo`) bleiben beim Einzelvideo-Ordner zurück
**Betroffen:** Entscheidung 4, Scope-Punkt 4.

`find_group_companion_files` zieht nur Begleiter mit Präfix `<video-stem>.` (`helpers.py:902–911`). Dateien auf Ordner-Ebene (`tvshow.nfo`, `poster.jpg`, …) werden **nicht** mitbewegt. Erstmals sind jetzt Ordner über `files[]` verarbeitbar — bei einem sauberen Serien-Ordner bleibt nach dem Job ein Ordner mit Metadaten zurück, der beim nächsten Listing (`video_count == 0`, `:1345–1346`) aus der Inbox verschwindet. Kein Löschen (kein Datenverlust), aber eine dokumentations-/AK-pflichtige Konsequenz, sonst „verschwinden" Nutzer-Metadaten scheinbar.

**Test-AK:** *„Es prüft, dass der `files[]`-Job eines Einzelvideo-Ordners mit `tvshow.nfo`/`poster.jpg` auf Ordner-Ebene diese Dateien unangetastet lässt und nur Video + `<stem>.*`-Begleiter bewegt."*

### W4 — Bestehende Frontend-Tests müssen neu formuliert werden (Regression/Abdeckung)
**Betroffen:** Frage F, Scope-Punkt 3.

- `inbox_group.test.js:968–995` (AK12): `assert 'Folders must not have checkboxes'`. Die Fake-Ordner haben **keine** `single_video_*`-Felder → Test bleibt grün, aber die Aussage wird falsch: „Ordner **ohne** Einzelvideo" bleibt ausgeschlossen. Es fehlt ein **neuer** Test für „Ordner **mit** Einzelvideo bekommt Checkbox".
- `inbox_group.test.js:672–700` (AK2) und `:1067–1092` (AK11, echter Ordner „Show"): bleiben grün, Semantik ebenfalls zu präzisieren.
- `test_inbox_suggestions.py` prüft nur Einzelfelder (`video_count`, `total_size`, `modified_at`, `is_dir`), **nicht** die exakte Key-Menge → additive Felder kippen nichts.
- `cache_busting.test.js` ist versions-agnostisch (vergleicht Index ↔ Import-Gleichheit) → kippt durch v99→v100 nicht, fängt aber vergessene der 9 Importe ab. Mechanisch: alle 9 (`app.js:1–9`) + `index.html:2760`.

**Test-AK:** *„Es prüft, dass ein Ordner-Eintrag mit `single_video_relpath` in `detectInboxGroups`/Checkbox-Eligibility einbezogen wird, ein Ordner ohne Einzelvideo weiterhin ausgeschlossen bleibt."*

### W5 — 30-s-Cache-TOCTOU: „hinzugefügtes zweites Video" nach dem Listing
**Betroffen:** Frage C, AK7-Muster.

`validate_group_files` + TOCTOU-Check (`processor.py:947–951`) fangen „gelöscht/verschoben" sauber ab (400/Abbruch, `realpath`-Commonpath gegen Symlink-Ausbruch `helpers.py:838–843`). Der verbleibende Fall: nach Listing (30-s-Cache, `:1303–1305`) wird ein **zweites** Video in den Ordner gelegt → Job verarbeitet nur das deklarierte Einzelvideo, das neue bleibt liegen, Ordner verschwindet nicht (video_count > 0). Harmlos, kein Datenverlust, aber als bewusste Grenze im Briefing nennen.

---

## [kosmetisch]

### KOS1 — Regex-Muster (a): theoretische False-Positives durch entfallene linke Trennzeichen-Pflicht
`extractStrictSeasonEpisode` läuft nur bei `media_type === "tv"` (`app.js:12496`), also nach Server-Klassifizierung. `PS4S01E01`/Base64-Substrings matchten nur, wenn der Server den Namen zuvor als „tv" erkannt hat — Exposition begrenzt, durch N2 bereits als Verhaltensänderung akzeptiert. `(?!\d)` + `(\d{1,3})` garantiert `ThWaDeS11E24720p → null` (greedy 3 Ziffern, dann Ziffer → fail, kein weiteres `s\d{1,2}e`-Vorkommen). Anime `S01E1080p → null` (4-stellige Ziffernfolge nicht sauber trennbar). `\d` ohne `u`-Flag = ASCII only (keine Unicode-False-Positives).

### KOS2 — Client `\d{1,3}` (Episode) vs. Server `\d{1,2}`
Bereits als ROADMAP #72 Punkt 7 dokumentiert (`ROADMAP.md:2002`), nicht im Akt-2-Scope. Episode 100–999 wird client-seitig erkannt, Server-`tv_pattern` (`project_api.py:1413`) kürzt auf 2 Ziffern. Kein Crash; die mappings-S/E-Werte selbst kommen aus dem Matching-UI (`app.js:4340–4400`), nicht aus `extractStrictSeasonEpisode`, und werden vom Server **nicht** gegen ein Muster validiert (nur `mappings`-Key ∈ `files[]`, `queue_api.py:85–90`, `:826–832`).

### KOS3 — #72.1: leerer String `new`
`if new_s:` (`processor.py:969`, `:988`) überspringt `""` (falsy) — manipulierte `new=""` endet in `os.rename`-Fehler, kein stummer Datenverlust. Für Robustheit `if new_s is not None` + explizite Leerstring-Ablehnung.

---

## VERDICT-Beitrag

**Kein echter Blocker** im Sinne eines unbeherrschbaren Sicherheits-/Datenverlust-Risikos: Alle Findings sind durch präzise AKs + ausführbare Tests abdeckbar, und keiner verändert Aufträge ohne `files[]` (Entscheidung 7 bleibt strukturell erfüllt, `processor.py:870–884` kapselt strikt).

Aber **zwei AKs sind nicht-optional** und betreffen die Kernfunktion selbst: **K1** (project-vs-relpath an fünf Stellen — ohne ihn schlägt *jede* Ordner-Auswahl mit Server-400 fehl) und **K2** (eigene 10er-Zählung statt `len(video_files)` — ohne ihn werden `.mp4`+`.wmv`-Ordner falsch als Einzelvideo deklariert und `.wmv` bleibt stumm liegen). **W1** ist der dritte nicht-optionale Punkt, weil er die Key-Gleichheit aus Entscheidung 3 trägt und an die noch offene Frage **F1** gekoppelt ist.

Empfehlung für den Freigabe-Mechanismus: **VERDICT: APPROVE** unter der Bedingung, dass Briefing + Tests für K1, K2, W1, W2, W3, W4 explizit formuliert sind — und dass **F1** vor Akt-2-Ausarbeitung beantwortet wird, da W1 (`extractStrictSeasonEpisode` gegen Ordnername vs. Dateiname) ohne diese Antwort nicht eindeutig spezifizierbar ist.
</task_result>
</task>
