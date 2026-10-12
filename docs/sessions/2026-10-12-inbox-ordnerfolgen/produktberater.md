# Rohoutput produktberater — Kreativteam 2026-10-12 (Akt 2, Ordner-Folgen)
Hinweis Claude Code (2026-10-12): Mechanisch aus `opencode export ses_ed092b3e0ffe9iDPDyHyWFilqY` (ceo-planner, Akt 2) abgelegt, nicht vom Moderator abgeschrieben (Lehre 59). Einzige Änderung: Trailing Whitespace entfernt. Volle Daten: Kit `scripts/gate-a2/logs/2026-10-12-inbox-ordnerfolgen/export-ceo-planner-akt2.json`.

---

## produktberater: produktberater Scope-Check Akt 2 (Subagent-Sitzung ses_ed09073cbffenPsrKDqXGK3IDJ, Status: completed)

<task id="ses_ed09073cbffenPsrKDqXGK3IDJ" state="completed">
<task_result>
Jetzt habe ich alle relevanten Code-Stellen gelesen. Hier ist meine Analyse als Scope-Wächter.

---

## 1) Position pro Punkt a–e

### a) Ist der Schnitt ein echtes MVP für den Live-Fall?

**Ja, der Schnitt trifft den Live-Fall.** Die 264 ThWaDe-Ordner (`ThWaDeS01E01` bis `ThWaDeS26E??`) haben `SxxExx` im Ordnernamen → `tv_pattern` (`project_api.py:1417`) matcht heute schon → `media_type = "tv"`. Die zwei Hindernisse sind:

1. `extractStrictSeasonEpisode` (`app.js:12479`) verlangt links ein Trennzeichen — bei `ThWaDeS11E23` steht links `e` → `null`. Muster (a) mit `(?!\d)` rechts und linker Alternative `|[a-zA-Z]` (oder einfach `^|[._\s\-\[]` beibehalten, aber `(?!\d)` rechts) löst das. **Aber Achtung:** `(?!\d)` allein ersetzt nur die *rechte* Seite. Die *linke* Seite `(?:^|[._\s\-\[])` muss ebenfalls erweitert werden, sonst matcht `ThWaDeS11E23` immer noch nicht (links steht `e`, kein Trennzeichen). Der Scope-Punkt 1 sagt „Namen ohne Trennzeichen wie ThWaDeS11E23 matchen" — das erfordert zwingend eine **linke** Alternative. Das ist implizit klar, sollte aber im Briefing explizit gemacht werden.

2. `detectInboxGroups` (`app.js:12496`) und Checkbox-Eligibility (`app.js:13126`) filtern `is_dir === true` aus. Die zwei additiven Felder `single_video_relpath`/`single_video_query` plus Frontend-Anpassung lösen das.

**Komplexität, die weggelassen werden könnte:** Keine. Jeder Scope-Punkt ist notwendig für den Live-Fall. Die Entscheide 4 (Ordner bleibt liegen) und 7 (Legacy unverändert) sind Restriktionen, keine Zusatzaufgaben — sie verhindern Over-Engineering.

### b) #72.1 im selben Lauf — zwingend oder verschiebbar?

**Zwingend im selben Lauf. Begründung mit Risiko:**

`validate_group_files` (`helpers.py:801–867`) akzeptiert relative Pfade mit Unterordnern. Die `new`-Feld-Prüfungen im `files_param`-Pfad (`processor.py:969–978` für Subs, `988–997` für Renames) lehnen nur absolut, `..` und Ausbruch ab. Ein `new` wie `ThWaDeS02E05/Neuer.Name.mkv` passiert alle Prüfungen.

Heute ist das theoretisch: Der legitime Client sendet `new` immer als reinen Dateinamen (`queue_api.py:568`: `target_filename = f"{clean_title}{ext}"`). **Aber:** Nach diesem Lauf wird `files[]` deutlich häufiger benutzt (264 Ordner-Einträge statt nur manueller Gruppen). Jeder additional Code-Pfad, der `new` mit Separator akzeptiert, vergrößert die Angriffsfläche für manipulierte Parameter.

Die Härtung ist trivial: eine Zeile pro Konsument (`os.sep in new_r` → reject). Kein legitimer Pfad wird verletzt (B7 im Kickoff bestätigt). **Verschieben = bewusstes Akzeptieren eines Sicherheitsfensters in dem Moment, wo die Feature-Nutzung skaliert.**

### c) F1-Absage: UX-Lücken im Alltag

**Tragfähig für den Live-Fall, aber dokumentierte Lücke.**

Ohne F1 bleibt die Server-Tv-Erkennung (`project_api.py:1417`) ausschließlich auf dem Eintragsnamen. Ordner wie `CD1`, `Neuer Ordner`, `Downloads` mit einer Videodatei `The.Walking.Dead.S01E01.mkv` drin bleiben `media_type = "movie"` → weder Gruppe noch Checkbox.

Für Alex' konkreten Fall (264 Ordner mit `ThWaDeSxxExx` im Ordnernamen + lose Einzeldateien mit `SxxExx` im Dateinamen) ist das **irrelevant** — alle Ordner haben SxxExx im Namen, alle losen Dateien haben SxxExx im Namen.

**Aber:** Entscheidung 3 („Folgenerkennung am Dateinamen, Ordnername nur Ausweichweg") ist semantisch inkonsistent ohne F1. Die Typ-Erkennung folgt nicht dem Dateinamen, nur die Folgen-Extraktion. Das ist kein Bug, sondern eine dokumentierte Grenze.

**Empfehlung:** Im Briefing als „bekannte Grenze" mit klarem Folgeschritt notieren: „Wenn ein Ordner genau eine Videodatei hat (10er-Liste), `tv_pattern` zusätzlich gegen den Dateinamen laufen lassen." Das ist ein 5-Zeilen-Change in `project_api.py:1417`, kein Architektur-Thema.

### d) 6er-/10er-Listen-Inkonsistenz (N3)

**Bedroht den Nutzen im echten Medienbestand nicht.**

Die 6er-Liste (`project_api.py:1321`: `{'.mp4', '.mkv', '.avi', '.mov', '.ts', '.webm'}`) steuert `video_count`. Die 10er-Liste (`helpers.py:798`: `GROUP_VIDEO_EXTENSIONS`) steuert `validate_group_files`.

Konsequenz: Ordner mit ausschließlich `.flv`/`.m2ts`/`.3gp`/`.wmv`-Dateien erscheinen gar nicht erst in der Inbox (`video_count == 0` → `continue`, `project_api.py:1345`). Die 10er-Liste der Ein-Videodatei-Erkennung kann dort nie greifen.

Für Alex' Walking-Dead-Bestand (.mkv-Dateien): **kein Effekt.** Für exotische Formate im allgemeinen Medienbestand: reale Lücke, aber explizit als #72.8 gebündelt (Endungslisten-Bereinigung). Die Inkonsistenz ist **defensiv** — sie zeigt zu wenig an, nicht zu viel. Kein Feature wird kaputtgehen.

### e) Komplexitätsfallen, die der Worker nicht bauen soll

**Drei konkrete Fallen, die im Briefing stehen müssen:**

**Falle 1: Frontend muss Ordnernamen → Videopfad übersetzen.**
`selectedInboxProjects` enthält `item.project`-Werte (`app.js:13132`), also Ordnernamen wie `ThWaDeS11E23`. Der Payload `files[]` (`app.js:4448`) sendet diese direkt. Aber `validate_group_files` (`helpers.py:851–852`) lehnt Ordner ab: „Ordner sind im files-Parameter nicht erlaubt." **Der Worker muss im Frontend eine Translation-Schicht bauen:** Wenn ein Eintrag `single_video_relpath` hat, diesen statt `item.project` in `files[]` senden. Sonst crasht jeder Ordner-Auftrag mit `ValueError`. Das ist keine optionale Eleganz, sondern eine harte Notwendigkeit.

**Falle 2: `detectManualGroupSeriesName` mit gemischten Einträgen.**
`detectManualGroupSeriesName` (`app.js:12641–12661`) berechnet Common-Prefix über die `files`-Array-Elemente (= `item.project`-Werte). Bei gemischter Gruppe (Ordner `ThWaDeS11E23` + Datei `The.Walking.Dead.S11E01.mkv`) entstehen Prefixe `ThWaDe` vs. `The.Walking.Dead` → Common Prefix = leer → Fallback auf `firstItem.suggested_query`. Das funktioniert **nur**, wenn `firstItem` ein Ordner mit korrektem `single_video_query` ist. Wenn die Sortierung zufällig die Datei zuerst hat, stimmt der Fallback. **Aber:** die Funktion sollte für Ordner-Einträge `single_video_query` statt des Ordnernamens als Input nehmen. Sonst ist der Gruppenname von der Array-Reihenfolge abhängig.

**Falle 3: `detectInboxGroups` muss `extractStrictSeasonEpisode` auf das richtige Feld anwenden.**
Heute: `extractStrictSeasonEpisode(item.project)` (`app.js:12499`). Für Ordner-Einträge mit `single_video_relpath` sollte die Funktion entweder den Dateinamen aus `single_video_relpath` oder (einfacher) den bereits vom Server extrahierten `single_video_query` verwenden. **Aber:** `single_video_query` enthält nicht die SxxExx-Info (er ist der Show-Name, z.B. „The.Walking.Dead"). Also muss `extractStrictSeasonEpisode` auf `single_video_relpath` (den Dateinamen) laufen, nicht auf `item.project` (dem Ordnernamen). Bei Ordnern ohne Trennzeichen (ThWaDeS11E23/video.mkv) matcht die alte Regex auf `item.project` nicht — die neue Regex (Muster a) muss auch hier die linke Seite erweitern.

**Zusätzliche Falle (Over-Engineering-Gefahr):**
- **Neue Serverlogik über die zwei Felder hinaus:** Der Server soll `single_video_relpath` und `single_video_query` als additive Felder in das bestehende Dict einfügen (`project_api.py:1490–1503`). Keine neue Endpoint, keine Restrukturierung, kein separates „folder detail"-Objekt.
- **Doppelte Zustände im Frontend:** Nicht einen neuen „folder group"-Modus erfinden. Single-Video-Ordner werden einfach wie Dateien behandelt — in `detectInboxGroups`, in der Checkbox-Eligibility, im Payload. Ein Code-Pfad, keine Verzweigung.
- **Ordner-Aufräumen:** `processor.py:1084–1091` und `1717` skippen bereits `files_param is not None`. Kein neuer Code nötig — nur im AK festschreiben, dass der Ordner liegen bleibt.

---

## 2) Dissens/Konflikt mit dem gesetzten Scope

**Kein harter Dissens.** Die Entscheidungen 1–7 sind gesetzt und tragen. Zwei Punkte, bei denen ich konstruktiv widerspreche:

**Punkt 1 (weich): Muster (a) — die linke Seite.**
Der Scope sagt „Namen ohne Trennzeichen wie ThWaDeS11E23 matchen" und spezifiziert `(?!\d)` für die rechte Seite. Aber die linke Seite `(?:^|[._\s\-\[])` (`app.js:12479`) ist genauso ein Blocker. `ThWaDeS11E23` hat links ein `e` vor dem `S`. Ohne eine linke Alternative (z.B. `[a-zA-Z]` hinzufügen oder die linke Gruppe komplett auf `(?<!\d)` ändern) matcht der Name nicht. Das ist kein Dissens mit der Entscheidung, sondern eine **Spezifikationslücke** im Scope — die Entscheidung ist richtig, aber die Regex-Spezifikation ist unvollständig. Im Briefing muss die linke Seite explizit benannt werden.

**Punkt 2 (weich): Frontend-Translation Ordnernamen → Videopfad.**
Der Scope sagt „Gruppenschlüssel/Serienname bei solchen Ordnern aus dem DATEINAMEN" (Entscheidung 3) und „files[]-Job bewegt nur die Videodatei" (Entscheidung 4). Aber er sagt nicht explizit, dass das Frontend `selectedInboxProjects` (Ordnernamen) in `single_video_relpath` (Videopfade) übersetzen muss, bevor es den Payload baut. Ohne diese Translation crasht der Server-Aufruf. Das ist keine neue Entscheidung, sondern eine **Implementierungsnotwendigkeit**, die im Briefing als explizite AK stehen muss.

---

## 3) Empfehlung für das Briefing

**Scope ist tragfähig. Drei Ergänzungen fürs Briefing:**

1. **Regex-Spezifikation komplettieren:** Muster (a) muss beide Seiten benennen. Links: entweder `[a-zA-Z]` zur Alternativen-Gruppe hinzufügen oder die linke Gruppe durch `(?<!\d)` (negativer Lookbehind für Ziffer) ersetzen — das verhindert `ThWaDeS11E24720p` → null (die `7` nach `E24` ist eine Ziffer, aber `247` wäre als Episodennummer unsinnig; mit `(?!\d)` rechts und `(?<!\d)` links wäre `S11E24` in `S11E24720p` trotzdem gematcht, weil vor `S` kein Trennzeichen sein muss — **Moment, das ist falsch**).

   **Korrektur nach eigenem Code-Blick:** `ThWaDeS11E24720p` — die Regex `[sS](\d{1,2})[eE](\d{1,3})` matcht `S11E247` (3 Ziffern für E, `\d{1,3}` ist gierig). Mit `(?!\d)` rechts: nach `E247` kommt `2`, eine Ziffer → kein Match. Gut. Dann backtrack: `E24` → nach `E24` kommt `7`, eine Ziffer → kein Match. Backtrack: `E2` → nach `E2` kommt `4`, Ziffer → kein Match. Also: `null`. **`(?!\d)` rechts allein reicht für den Ziffern-Fall.**

   Für die **linke** Seite: `ThWaDeS11E23` — vor `S` steht `e`. Die heutige linke Gruppe `(?:^|[._\s\-\[])` matcht `e` nicht. Notwendig: entweder die Gruppe erweitern oder durch etwas wie `(?:(?<=[._\s\-\[])|(?<=[a-zA-Z])|^)` ersetzen. **Oder einfacher:** die gesamte linke Gruppe entfernen und stattdessen `(?<!\d)` verwenden — dann matcht `S11E23` in `ThWaDeS11E23` (vor `S` steht `e`, keine Ziffer → Match), und `S11E23` in `Something3S11E23` (vor `S` steht `3`, eine Ziffer → kein Match, was korrekt ist, weil `3S11` keine sinnvolle Serienkonvention ist).

   **Empfehlung fürs Briefing:** Linke Seite = `(?<!\d)` statt `(?:^|[._\s\-\[])`. Rechte Seite = `(?!\d)` statt `(?:[._\s\-\]]|$)`. Das ist die konsistente, minimale Spezifikation.

2. **Frontend-Translation als explizite AK:** „Wenn ein ausgewählter Eintrag `single_video_relpath` hat, wird dieser Pfad statt `item.project` in `payload.files[]` eingefügt." Plus: „`detectInboxGroups` ruft `extractStrictSeasonEpisode` auf `single_video_relpath` (Dateiname) statt auf `item.project` (Ordnername) auf, wenn `single_video_relpath` vorhanden ist."

3. **F1-Grenze dokumentieren:** „Ordner ohne SxxExx im Ordnernamen (z.B. `CD1`) werden auch mit genau einer TV-Videodatei nicht als Serie erkannt. Folgeschritt: `tv_pattern` bei Ordnern mit genau einer Videodatei zusätzlich gegen den Dateinamen laufen lassen."

**Keine weiteren Scope-Änderungen empfohlen.** Der Schnitt ist ein echtes MVP: minimal, testbar, und jeder Punkt direkt am Live-Fall begründet.
</task_result>
</task>
