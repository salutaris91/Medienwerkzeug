# Rohoutput advocatus — Rückkanal 2026-10-12 (Ordner-Folgen)
Hinweis Claude Code (2026-10-12): Mechanisch aus `opencode export ses_ecf9d329bffenaBDzh0B97oY3K` (ceo-planner, Rückkanal) abgelegt, nicht vom Moderator abgeschrieben (Lehre 59). Einzige Änderung: Trailing Whitespace entfernt. Volle Daten: Kit `scripts/gate-a2/logs/2026-10-12-inbox-ordnerfolgen/export-rueckkanal.json`.

---

## advocatus: Risikoprüfung Worker-Patch (Subagent-Sitzung ses_ecf90fbc9ffefyWd8jJxyGYdSZ, Status: completed)

<task id="ses_ecf90fbc9ffefyWd8jJxyGYdSZ" state="completed">
<task_result>
Prüfung abgeschlossen. Ich habe den uncommitteten Stand im Arbeitsbaum gegen das Briefing (AKs, ADRs, Abschnitt 6) und die drei Testdateien geprüft. Da ich in dieser Session kein `bash` habe, konnte ich kein `git diff` laufen lassen — die Analyse stützt sich auf den gelesenen Arbeitsbaum-Code an den im Briefing benannten Zeilen.

---

## Findings (nach Schwere)

### [wichtig] F1 — Queue-Überschneidung Folder-Job ↔ Gruppen-Job ist in beide Richtungen blind
**Dateien:** `app.js:4314–4334` (Prüfung), `app.js:10860–10869` (activeProjectsProcessing), `queue_api.py:909–910` (queue-Eintrag)

**Szenario A (Gruppe nach Folder-Job):** Ein klassischer Ordner-Job (`project_name="ThWaDeS11E23"`, ohne `files`) läuft. Der Gruppen-Weg (`activeSeriesGroupFiles` = relpaths) baut `activeFilesSet` ausschließlich aus `job.files`. Der Ordner-Job hat KEIN `files`-Feld im Queue-Payload (`queue_api.py:909` setzt `files` nur wenn `params.get("files") is not None`) → `activeFilesSet` bleibt leer → `overlapping` leer → kein Alert. Der Gruppen-Job mit demselben `ThWaDeS11E23/….mkv` wird gestartet.

**Szenario B (Folder-Job nach Gruppe):** Ein Gruppen-Job läuft. Er registriert `project_name=""` (aus `startSeriesGroupWorkflow`, `app.js:12750`). In `renderQueue` wird `activeSet` nur gefüllt, wenn `p` nicht leer ist (`app.js:10864`) → der Ordner `ThWaDeS11E23` landet NICHT in `activeProjectsProcessing`. Der klassische Zweig (`app.js:4330`) prüft `activeProjectsProcessing.has(currentProject)` → false → kein Alert. Zusätzlich: die Inbox markiert die Ordnerzeile während des Gruppen-Jobs nicht als `isProcessing` (`processingSet` = `activeProjectsProcessing`), die Checkbox/`Auswählen`-Button bleiben aktiv.

**Effekt:** Zwei Jobs greifen auf dieselbe Datei zu. Der Processor fängt einen Teil davon laut ab (TOCTOU `processor.py:947–951` nur bei `files_param is not None`; klassischer Job ohne `files` überspringt verschwundene Dateien dagegen **stillschweigend**, `processor.py:1069–1072`). Das eigentliche Risiko liegt auf der **Ausgabeseite**: beide Jobs schreiben in denselben Zielordner `Serien/<show>/…` → doppelte/kollidierende Ausgaben, partielle Reads. Kein Quell-Verlust (`os.rename` atomar, kein Löschen), daher [wichtig], nicht [kritisch].

**Testdeckung:** Keiner. Kein E2E-Test gegen echten Server (im Briefing als Restrisiko „Kein E2E-Test" dokumentiert); die Frontend-Tests mocken `fetch` und prüfen diesen Guard nicht.

---

### [wichtig] F2 — `.replace('\\','/')` kann auf POSIX still auf eine ANDERE Datei zeigen
**Datei:** `project_api.py:1510`

`os.path.relpath(...).replace('\\', '/')` ist auf dem Zielsystem (NAS/Linux, auch macOS) ein reiner Schadensvektor: `relpath` liefert dort bereits `/`, und ein **echter Backslash im Dateinamen** ist auf POSIX legal. Ein Ordner `A` mit genau einer Datei, die literal `B\C.mkv` heißt, liefert nach dem Replace `single_video_relpath = "A/B/C.mkv"`.

- Existiert zusätzlich `A/B/C.mkv` → `validate_group_files` validiert **die falsche Datei** (sie existiert, ist Video) → der Job verarbeitet still eine fremde Datei; `A/B\C.mkv` bleibt unangetastet. **Stiller Fehler.**
- Existiert sie nicht → laut „Datei existiert nicht" (HTTP 400).
- In beiden Fällen ist auch die UI falsch: Tooltip (`app.js:13154`) zeigt `A/B/C.mkv`, und die Basename-Extraktion (`app.js:12511`, die defensiv auf `/` UND `\` splittet) erhält den bereits gemanglten String → gruppiert/zeigt falschen Namen.

Der Replace ist nur auf Windows „nötig", wo ein Backslash im Dateinamen ohnehin unmöglich ist. Empfehlung: auf POSIX weglassen oder nur bei `os.sep == '\\'` normalisieren.

**Testdeckung:** Keiner. `test_ak7_explicit_targets_path_separator_hardening` testet `new`-Ziele, nicht den relpath-Fall. Pathologisch selten, aber real; [wichtig] wegen der stillen Fehl-Adressierung.

---

### [wichtig] F3 — Sehr große Gruppen: Matching-Matrix-DOM-Explosion + All-or-Nothing-Job
**Dateien:** `app.js:3811–3904` (Matrix), `app.js:13038–13052` (Mitglieder), `app.js:4326` (Alert)

Der Live-Fall 173 Ordner → EINE Gruppe, dann Bulk-`Ausgewählte als Serie verarbeiten`:

- **DOM:** `renderMatchingMatrix` baut für jede der 173 Dateien eine Zeile und iteriert je Zeile **über alle** `episodesData` (`app.js:3844–3868`, `<option>` je Episode). Bei voller Serie (~250 Folgen über 11 Staffeln) sind das ≈ 43.000 `<option>`-Knoten plus 173 `select`-/NFO-Details-Blöcke in einem einzigen `innerHTML`-String. Browser-Freeze beim Rendern ist realistisch, vor allem nativ arm64 in OrbStack.
- **All-or-Nothing:** Ein Fehler bei Folge 87 (Metadata-Fetch, NFO-Kollision, Codec) setzt den ganzen Job auf `error`; es gibt kein Resume/Partial — 173-Folgen-Verarbeitung muss komplett neu gestartet werden. Der Alert-Text bei Überschneidung (`overlapping.join(", ")`, `app.js:4326`) würde mit 173 relpaths einen mehrzeiligen, faktisch unlesbaren Dialog erzeugen.
- **Payload/Runtime:** `files[]` + `mappings` mit 173 Keys sind größenmäßig unkritisch; die Job-Laufzeit (Convert/Transfer) ist die eigentliche Langläufer-Gefahr — ohne Teilfortschritt-Persistenz über einen Worker-Neustart hinweg.

Kein Datenverlust, aber Nutzbarkeits-/Stabilitätsrisiko. Der erste Live-Batch ist zwar nur Staffel 11 (23 Ordner), aber das Feature ist explizit für den 173er-Bestand gebaut.

**Testdeckung:** Keiner (kein Performance-/Großgruppen-Test; Matrix-Test nutzt 10 Dateien).

---

### [kosmetisch] F4 — Symlink-Einzelvideo: Checkbox sichtbar, Job wird erst beim Submit laut abgewiesen
**Dateien:** `helpers.py:838–843` (realpath-Konfinement), `helpers.py:113–140` (`is_path_allowed`), `project_api.py:1334` (`os.walk`)

`os.walk` folgt Symlink-**Verzeichnissen** nicht (`followlinks=False`); eine Symlink-**Datei** (`video.mkv` → `/außerhalb/real.mkv`) wird aber gelistet und gezählt → Ordner erhält `single_video_relpath` + Checkbox und erscheint gruppierbar. Beim Submit greift dann `validate_group_files` (`realpath` → `commonpath` gegen `inbox_real`, plus `is_path_allowed`) und weist **laut** ab („liegt außerhalb des Inbox-Verzeichnisses"). Kein Sicherheitsloch, aber ein UX-Bruch: anhakbare Zeile, die erst beim Absenden mit 400 scheitert. `os.rename` auf einen Symlink würde ohnehin nur den Link (nicht das Ziel) bewegen — aber dieser Pfad wird vorher durch die realpath-Prüfung verworfen.

**Testdeckung:** Keiner (kein Symlink-Setup in den Tests).

---

### [kosmetisch] F5 — Gruppenname „video" bei generisch benannten inneren Dateien
**Dateien:** `app.js:12657–12677`, `app.js:12726`

Bei Ordnern, deren einzige Datei ohne `SxxExx` heißt (z. B. `ThWaDeS11E23/video.mkv`), liefert `detectManualGroupSeriesName` den Prefix `"video"` (kein Episode-Match → ganzer Stamm bleibt) und `common` = `"video"` (nicht leer). Der `fallbackName` (`single_video_query`, hier korrekt `"ThWaDe"`, `app.js:12726`) greift nur bei LEEREM `common` — also **nicht** in diesem Fall. Ergebnis: 173-fach Bulk-Auswahl → Gruppenname `"video"`. Verwirrend, aber kein Korrektheitsfehler; im Live-Bestand (Dateinamen mit `S11E23`) korrekt. Konfliktfähig mit `cleanSeriesName`-Fallback, das hier nie zum Zug kommt.

**Testdeckung:** AK5d testet nur den Namensfall mit `SxxExx`; der `video.mkv`-Fall ist ungetestet.

---

## Geprüfte und entkräftete Punkte

- **XSS im `title`-/`data-project`-/`data-group-key`-Attribut (Frage 1):** `escapeHTML` (`app.js:245–253`) escapt `& < > " '` vollständig für Attribut-Kontext in doppelten Anführungszeichen; `aria-label` ist statischer Text; alle Einblendungen (`title` 13154, `data-project` 13154/13156/13166/13172, Gruppen-Titel 13023, Banner 12617/12620, Mitglieder 13045, Matrix 3824) sind escapt. Kein Injection-Vektor. **Offen bleibt nur** das Nicht-Strippen von Unicode-Bidi-/Steuerzeichen (`U+202E` etc.) → rein visuelles Spoofing von Pfad/Name, kein Script. Kein Test prüft Bidi.
- **Namens-Kollision Ordner X + Datei X (Frage 3):** `os.listdir` liefert je Ebene eindeutige Namen → „X" (Ordner) und „X" (Datei) können auf derselben Ebene **nicht koexistieren**. `X` (Ordner) vs. `X.mkv` (Datei) sind verschiedene `project`-Keys → `selectedInboxProjects`/`groupedItemsByProject` unterscheiden sie sauber. Der einzige Überschneidungspunkt — gleicher `single_video_query`/`suggested_query`-Gruppenschlüssel (z. B. beide → `"ThWaDe"`) — führt zur **korrekten** Verschmelzung zu EINER Serie, nicht zu Datenverlust. Entkräftet.
- **Symlink-Konfinement (Frage 4):** `realpath`-Prüfung (`helpers.py:838–843`) + `is_path_allowed` (ebenfalls realpath-basiert, `helpers.py:128`) fangen Ausbrüche zuverlässig **zur Job-Zeit** ab. `os.walk` folgt Symlink-Verzeichnissen nicht. Verbleibend nur der UX-Bruch aus F4.
- **`new`-Härtung, Umgehungen (Frage 9):** `/`- und `\`-Prüfung (`processor.py:979–980`, `:1002–1003`) fängt alle normpath-Tricks (`a/../b`, `a//b`, `./x`, Trailing-Slash) — die Separator-Prüfung greift, bevor `normpath` kollabiert. `..`/absolut/dekodierte Traversals waren schon vorher abgedeckt. Unicode-Separatoren (`U+2215` u. ä.) sind für `os.path` **keine** Separatoren → kein Traversal, nur ein exotischer Dateiname innerhalb `current_dir` (harmlos). `new=None`/fehlendes `new` → `if new_s:` falsy → skip (korrekt). `new` als `dict`/`int`/Liste → `os.path.isabs()` wirft `TypeError`, der in `job_queue_worker` (`processor.py:3779`) als Job-`error` laut endet — **vorbestehend**, nicht durch diesen Patch eingeführt. Der leere-String-`elif` (`:981–982`, `:1004–1005`) ist korrekt hinter dem `if new_s:`-Guard platziert und schließt die vorbestehende `os.rename`-auf-Verzeichnis-Lücke bei `new=""`.
- **Regex-False-Positives (Frage 7):** `extractStrictSeasonEpisode` hat bestätigt nur `detectInboxGroups` (`app.js:12512/12514`) + globalThis-Export (`13257`) als Aufrufer. Der `media_type==="tv"`-Vorfilter (`app.js:12504`, gespeist aus `tv_pattern` `project_api.py:1416`, der seinerseits `s\d+e\d+` verlangt) begrenzt die Treffermenge stark. Realistisch NEU matchen nur: PROPER/REPACK/INTERNAL-Tags ohne Trennzeichen (AK1d, dokumentiert) und kleingeschriebene/ohne-Trennzeichen-Fälle (AK1a/f) — beide echte Episoden. **Hinweis zur Briefing-Bewertung:** das Beispiel „`Windows10E2` → S10E02" aus Abschnitt 6/N2 ist unzutreffend — weder `tv_pattern` noch das neue Muster matchen „Windows10E2", weil kein `S` vor den Ziffern steht; die dort behauptete False-Positive-Klasse existiert in dieser Form nicht. Ein sauberes neues False-Positive-Beispiel aus dem neuen Lookbehind wäre nur `(?<!\d)`-konform mit vorangehendem Buchstaben + `s##e##` (z. B. „Docs01E02"), also weiterhin `tv`-klassifiziert und damit Episode-ähnlich — praktisch vernachlässigbar.
- **30-s-Cache-TOCTOU (Frage 2):** keine neuen Erkenntnisse über W5 hinaus (zweite Videodatei → nur deklariertes Video wird verarbeitet, Rest bleibt liegen; gelöscht/verschoben → lauter Fehler via `processor.py:947–951` + `validate_group_files` `helpers.py:848`). Nichts neu zu melden.

---

## Zusammenfassung

Kein [kritisch]-Fund; drei [wichtig]-Punkte, von denen **F2 (Backslash-Mangling, stiller Fremd-Datei-Fehler)** und **F1 (Queue-Überschneidung Folder↔Gruppe, beidseitig blind)** die substanziellsten sind, beide **ohne** Testdeckung. F3 ist ein Skalierungs-/UX-Risiko für den realen 173er-Fall.

`VERDICT: REVISE`

1. `[wichtig]` `project_api.py:1510` — `.replace('\\','/')` auf POSIX weglassen/guardieren (stiller Fremd-Datei-Fehler möglich).
2. `[wichtig]` `app.js:4314–4334` + `queue_api.py:909` — Überlappungsprüfung deckt Folder-Job↔Gruppen-Job in beide Richtungen nicht ab (folder-Jobs ohne `files`, Gruppen-Jobs ohne `project_name`).
3. `[wichtig]` `app.js:3844–3868` — Matching-Matrix iteriert je Datei über alle `episodesData` (≈43k `<option>` bei 173×250) → DOM-Explosion; kein Resume bei Teilfehler.
4. `[kosmetisch]` `project_api.py:1334`/`helpers.py:838` — Symlink-Einzelvideo-Ordner zeigt Checkbox, scheitert erst beim Submit laut.
5. `[kosmetisch]` `app.js:12657–12677` — Gruppenname `"video"` bei generisch benannten inneren Dateien (Fallback greift nicht).
6. `[kosmetisch]` `app.js:245–253`/`13154` — kein Bidi-/Steuerzeichen-Stripping in `escapeHTML` (visuelles Spoofing, kein XSS).
</task_result>
</task>
