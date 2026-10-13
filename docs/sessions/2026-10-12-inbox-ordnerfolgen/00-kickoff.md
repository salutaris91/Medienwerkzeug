# Kickoff — Kreativteam-Session 2026-10-12: Gruppierung für Ordner-Folgen und Namen ohne Trennzeichen

**Session-Ordner:** `docs/sessions/2026-10-12-inbox-ordnerfolgen/`
**Phase:** Akt 1 — Kickoff / Scope-Abstimmung (Freigabepunkt 1). Danach STOPP.
**Rolle hier:** Kreativteam-Leitung (innere Schleife). Kein Briefing, keine Subagenten-Konsultation vor Alex' Antwort.
**Absender des Start-Prompts:** Claude Code (Reviewer/Vermittler), NICHT Alex. Alex' Entscheidungen sind unten wörtlich zitiert.

## Git-Zustand (von Claude Code ausgeführt, wörtlich übernommen — ich habe `bash: deny` und habe Git nicht selbst laufen lassen)

```
## feat/inbox-gruppe-ordnerfolgen...origin/main [ahead 1]
fc75466 docs: mark ROADMAP #64/#65 done, add native ARM64 test variant (#73), document emulation hang
17b96d1 feat(inbox): group series episodes in the smart inbox (ROADMAP #65, run B) (#150)
dd65244 feat(inbox): server-side files[] group processing (ROADMAP #65, run A) (#149)
```

Feature-Branch, kein main-Stop relevant. Arbeitsverzeichnis dieses Worktrees:
`/Users/alex/Documents/Medienwerkzeug/.worktrees/feat-inbox-gruppe-ordnerfolgen`

## Scope in einem Satz

Teilmenge von ROADMAP #71 (`ROADMAP.md:1967–1987`): Ordner mit **genau einer** Videodatei sollen in der Smart Inbox wie Einzeldateien gruppierbar und per Auswahlkästchen wählbar sein, inkl. Muster-Erweiterung der Folgen-Regex (Namen ohne Trennzeichen wie `ThWaDeS11E24`); plus ROADMAP #72 Punkt 1 (`ROADMAP.md:1996`, Härtung `explicit_renames`/`explicit_subs` gegen Unterordner-Ziele). **Nicht** enthalten: das volle Aufklapp-UI aus #71, die Endungslisten-Bereinigung (#72 Punkt 8), Ordner-Aufräumen (#68).

## Read-only-Prüfung der Behauptungen aus dem Start-Prompt

Alle Prüfschritte gegen den Code in diesem Worktree; jede Zeilenangabe von mir verifiziert.

### Ursachen des Live-Befunds — beide bestätigt

- **U1 bestätigt.** `extractStrictSeasonEpisode` (`gui/static/app.js:12477–12490`) verlangt vor dem `S` zwingend `(?:^|[._\s\-\[])` (Zeile 12479). Bei `ThWaDeS11E23` steht links ein Buchstabe (`e`) → kein Match → `null`. Zusätzlich: die rechte Seite ist heute `(?:[._\s\-\]]|$)` (ebenfalls Zeile 12479) — Alex' Muster (a) ersetzt sie durch `(?!\d)`, siehe Hinweis N2 unten.
- **U2 bestätigt.** `detectInboxGroups` (`gui/static/app.js:12492–12515`) wirft Ordner-Einträge mit `item.is_dir === true` raus (Zeile 12496). Die Auswahlkästchen-Eligibility (`gui/static/app.js:13126`) verlangt `is_dir === false` (`isTvSingle`). Ordner sind also doppelt ausgeschlossen — Gruppierung und Checkbox.

### B1 — bestätigt

`validate_group_files` (`gui/core/helpers.py:801–867`) akzeptiert relative Pfade mit Unterordnern (Join auf `inbox_root`, Zeile 836; keine Separator-Ablehnung). Abgelehnt werden: absolute Pfade (825–826), `..` (828–830), Ausbruch aus der Inbox per `commonpath`/`realpath` (838–843), nicht existierende (848–849), Ordner (851–852), Nicht-Dateien (854–855), falsche Endungen (857–859). `GROUP_VIDEO_EXTENSIONS` = 10 Endungen (`helpers.py:798`), wie im Prompt angegeben. Deduplizierung case-insensitive, Reihenfolge erhalten (832–834, 861–862).

### B2 — bestätigt

`find_group_companion_files` (`helpers.py:870–918`): Begleitdateien werden im **Ordner der jeweiligen Videodatei** gesucht (`vdir = os.path.dirname(full_vpath)`, Zeile 890) mit Präfix `<stem>.` (902, 911), ausgenommen Videos und Dotfiles (904–907), zurück als Inbox-relativer Pfad (912). Bei `Ordner/Datei.mkv` sucht der Code also korrekt in `Ordner/`.

### B3 — bestätigt, mit einem Genauigkeits-Nuance

Der Server bildet `suggested_query` für Ordner-Einträge aus dem **Eintragsnamen**: `tv_pattern` (`project_api.py:1413`) ist `(?i)(s\d{1,2}e\d{1,2}|season\s*\d+|staffel\s*\d+)` ohne Trennzeichen-Forderung links — trifft auf `ThWaDeS11E23` → `media_type = "tv"` (1417–1419, daher das live gesehene „Serie erkannt") → `suggested_query = item[:match.start()].strip(' ._-')` = `ThWaDe` (1421) → `clean_show_name` (1438–1440). Der Dateiname `The.Walking.Dead.S01E01.…` würde durch dieselbe Pipeline `The.Walking.Dead` ergeben. **Nuance:** `clean_show_name` (`gui/core/utils.py:23–30`) erhält Punkte — das Ergebnis ist wörtlich „The.Walking.Dead" (Punkte), nicht „The Walking Dead" (Leerzeichen). Für Entscheidung 3 (gleiche Gruppe aus loser Datei + Ordner) ist exakt das zwingende Kriterium: `single_video_query` muss **dieselbe Pipeline wie bei Einzeldateien** durchlaufen, dann sind die Schlüssel automatisch identisch. Als Test-AK formuliere ich „Gleichheit mit dem Einzeldatei-Ergebnis", nicht einen wörtlichen String mit Leerzeichen.

### B4 — bestätigt; Serienauswahl überschreibt den Gruppennamen

Kette verifiziert:
1. Bulk-Checkbox-Weg: `fallbackName` = `suggested_query` des ersten ausgewählten Eintrags (`app.js:12706–12708`), Gruppenname via `detectManualGroupSeriesName` (12641–12661, Common-Prefix über die Dateinamen-Basis; bei Ordnernamen als Input entsteht dort „ThWaDeS", bei `Ordner/Datei.mkv`-Input automatisch der bereinigte Dateiname-Präfix).
2. `startSeriesGroupWorkflow` setzt `activeSeriesGroupName` (12723–12726).
3. Manuell-Modus-Fallback: leerer Titel + aktive Gruppe → `titleVal` = Gruppenname (`app.js:7649–7674`), `selectedShow.provider = "manual"`.
4. Payload: `show_name: selectedShow.name` (`app.js:4429`), `files: [...activeSeriesGroupFiles]` (4447–4448).
5. Server: `show_name` → `resolve_series_folder_name` (`gui/workers/processor.py:1111–1132`) → `Output/Serien/<name>`; Priorität `nas_show_folder` > ID-Match NAS/Outbox > Fuzzy > Name (`gui/core/series_helper.py:35–77`).

**Ohne Entscheidung 3 entstünde tatsächlich `Output/Serien/ThWaDe` bzw. `ThWaDeS`** — aber nur, wenn der Nutzer in der Manuell-Modus-Fallback-Route bleibt (leerer Titel, keine Auswahl). **Auswahl TMDB/TVDB überschreibt:** `selectShow()` (`app.js:3280–3283`) ersetzt `selectedShow` vollständig durch den Provider-Treffer; dann kommt `show_name` aus dem Provider (bzw. ID-Match in `resolve_series_folder_name`). Entscheidung 3 ist damit korrekt, aber kein harter Blocker für Nutzer, die den Treffer aktiv auswählen.

### B5 — bestätigt

30-s-Cache: `project_api.py:1303–1305`. Video-Zählung in Ordnern rekursiv per `os.walk` (`1333–1340`) mit der **6er-Liste** `{'.mp4','.mkv','.avi','.mov','.ts','.webm'}` (`1321`); `video_count == 0` → Eintrag wird übersprungen (`1345–1346`). Antwort-Feldliste (`1490–1503`): `single_video_relpath`/`single_video_query` fehlen dort bis heute — die additive Ergänzung gehört genau in dieses Dict.

### B6 — bestätigt

`gui/static/index.html:2760` → `app.js?v=99`; die 9 ES-Module-Importe in `app.js:1–9` tragen alle `?v=99`. `tests/frontend/cache_busting.test.js:13–47` erzwingt Übereinstimmung Index-Version ↔ Import-Versionen (CSS nur „nicht leer", Zeilen 50–64). Sprung auf `v=100` = Index + alle 9 Importe.

### B7 — bestätigt; und die gute Nachricht für die Behebung

Die `new`-Ziel-Prüfung bei `files[]`-Jobs (`processor.py:969–978` für Subs, `988–997` für Renames) lehnt nur absolut, `..` und Ausbruch aus `current_dir` (= `inbox_root`, `processor.py:875`) ab. Ein relatives `new` wie `ThWaDeS02E05/Neuer.Name.mkv` (Ziel-Ordner existiert, Ziel-Datei nicht) passiert alle Prüfungen — exakt ROADMAP #72 Punkt 1 (`ROADMAP.md:1996`). **Entscheidend für die Behebung:** der legitime Client sendet `new` immer als reinen Dateinamen ohne Verzeichnis (`queue_api.py:568–569` für Videos, `622–644` für Subs/Meta; `target_filename = f"{clean_title}{ext}"`). Die Prüfung „`new` darf bei `files[]`-Jobs kein Separator enthalten" verletzt also keinen legitimen Pfad; das „Hochziehen" aus dem Unterordner passiert ohnehin über `os.rename(current_dir/old → current_dir/new)` (`processor.py:1058–1068`).

### Zusätzliche Belege für die Alex-Entscheidungen 4 und 7

- **Entscheidung 4 (Ordner bleibt liegen):** leerer-Ordner-Cleanup läuft nur bei `files_param is None` (`processor.py:1084–1091`), und `cleanup_empty_dirs=(files_param is None)` (`processor.py:1717`). Kein Löschcode für Ordner bei Gruppen-Jobs vorhanden — die Zusage ist strukturell schon jetzt erfüllt, muss nur per AK festgeschrieben werden.
- **Entscheidung 7 (Aufträge ohne `files[]` unverändert):** alle `files[]`-Pfade sind strikt in `if files_param is not None`-Zweigen gekapselt (`queue_api.py:73–95`, `815–833`; `processor.py:870–884`, `947–997`, `1062–1080` usw.); der Else-Zweig ist der unangetastete Legacy-Pfad.
- **Vollständige `files_param`-Konsumenten (für Entscheidung 5):** `gui/api/queue_api.py` (Preview ab Zeile 73; `/process` ab Zeile 815) und `gui/workers/processor.py` (ab Zeile 865) — mehr findet die grep-Passage in `gui/` nicht. Tests existieren bereits in `tests/test_inbox_group_files.py` (in #72.5 benannt) und `tests/frontend/inbox_group.test.js`.

## Bindende Alex-Entscheidungen (nicht neu verhandelt)

Wörtlich 2026-10-12: „ja zu 1) darfst du und den Rest entsprechend deinen empfehlungen" und „ja, beides wie empfohlen, starte das Kreativteam". Punkte 1–7 des Start-Prompts (Muster (a) mit `(?!\d)`; zwei additive Felder `single_video_relpath`/`single_video_query`; Schlüssel/Serienname aus dem Dateinamen; nur Datei + Begleiter bewegen, Ordner bleibt; #72 Punkt 1 mit allen `files_param`-Konsumenten; ein Gate-A2-Lauf + Handtest nativ arm64 + NAS-Livetest erst Staffel 11; Aufträge ohne `files[]` byte-genau unverändert) gelten als gesetzt und werden in Akt 2 nur noch in Tests und Worker-Auftrag übersetzt.

## Echte Scope-Frage an Alex (Freigabepunkt 1) — genau eine

**F1: Sollen einzelne-Videodatei-Ordner auch dann tv-gruppierbar werden, wenn der ORDNERNAME kein `SxxExx` enthält, sondern nur der Dateiname?**

- **Befund:** Die Server-Tv-Erkennung läuft nur gegen den Eintragsnamen (`project_api.py:1417`). Der Live-Fall `ThWaDeS11E23` hat `S11E23` im Ordnernamen → wird heute schon als „tv" erkannt; die Kette funktioniert für deinen konkreten Fall **auch ohne** diese Erweiterung. Aber ein Ordner wie `CD1` oder `Neuer Ordner`, der genau `The.Walking.Dead.S01E01.…mkv` enthält, bleibt heute „movie" (bzw. tv nur bei `video_count > 1`, `project_api.py:1433–1435`) → weder Gruppe noch Kästchen, obwohl Entscheidung 3 sagt: „Folgenerkennung am Dateinamen, Ordnername nur als Ausweichweg."
- **Empfehlung:** **Ja, mitnehmen.** Bei Ordnern mit genau einer Videodatei (10er-Liste) zusätzlich `tv_pattern` gegen den Dateinamen laufen lassen; Treffer → `media_type = "tv"`. Das macht Entscheidung 3 konsistent (sonst gilt „Dateiname primär" nur für die Folge-Extraktion, nicht für die Typ-Erkennung) und ändert ausschließlich Einträge, die heute falsch als „Film erkannt" dastehen.
- **Trade-off / Risiko:** geht über die zwei additiven Felder hinaus — der `media_type` solcher Ordner-Einträge kippt von „movie" auf „tv" (Badge in der UI ändert sich; Film-Lock/Gesperrt-Hinweis `app.js:13139–13145` entfällt für sie). Kleine, aber echte Verhaltensänderung über den wörtlichen Entscheidungsumfang hinaus; Regressionstest: Ordner mit ≥2 Videos und lose Filme bleiben unverändert.
- **Entscheidungspunkt:** „F1: mitnehmen (empfohlen)" oder „strikt auf den Fall Ordnername enthält SxxExx beschränken".

## Keine weiteren echten Scope-Fragen — nur Notizen für Akt 2 (nichts zu entscheiden)

- **N1:** Für `single_video_query` formuliere ich die AK als „identisch zum Ergebnis der Einzeldatei-Pipeline auf denselben Dateinamen" statt als wörtlichen String (siehe B3-Nuance Punkte vs. Leerzeichen).
- **N2:** Muster (a) lese ich wörtlich so, dass `(?!\d)` die rechte Seite **global** ersetzt (auch für lose Dateien). Folge: Namen wie `…S01E01PROPER…` matchen künftig (heute rechte Seite Trennzeichen/Ende zwingend, `app.js:12479`). Ich habe die bestehenden Frontend-Erwartungen durchgeprüft (`tests/frontend/inbox_group.test.js:648–666`): alle fünf Null-Erwartungen (`1920x1080`, `The Rock (1996)`, `1x05`, `Staffel 2 Folge 3`) enthalten gar kein `s\d+e\d+`-Muster und bleiben Null — die Suite kippt nicht. Kein Blocker, wird im Briefing als Verhaltensänderung dokumentiert.
- **N3:** Ordner, deren einzige Videodatei `.flv`/`.m2ts`/`.3gp`/`.wmv` ist, tauchen in der Inbox gar nicht erst auf (`video_count == 0` → `continue`, `project_api.py:1345`, 6er-Liste bei 1321). Die 10er-Liste der Ein-Videodatei-Erkennung kann dort nie greifen. Bewusste Konsequenz deiner Entscheidung 2 (`video_count` unverändert, Listen-Bündelung ist #72 Punkt 8) — als bekannte Grenze ins Briefing, keine Frage.
- **N4:** B4 zeigt: der Gruppenname „ThWaDe" landet nur im Manuell-Fallback, wenn der Nutzer keinen Provider-Treffer wählt. Mit Entscheidung 3 (Schlüssel aus `single_video_query`) ist auch dieser Fallback korrekt benannt. Kein Handlungsbedarf über den gesetzten Scope hinaus.

## Nächster Schritt

STOP an Freigabepunkt 1. Ich warte auf Alex' Antwort zu **F1** (sowie ggf. Korrektur der Notizen-Lesarten). Danach Akt 2: interne Ausarbeitung mit Subagenten (plan-reviewer-Pflicht, Dissens-Pflicht), ein Briefing `docs/sessions/2026-10-12-inbox-ordnerfolgen/briefing.md` (Frontmatter `source: roadmap#71`, Teilmenge explizit benannt) plus `ALEX_ZUSAMMENFASSUNG.md`, dann Freigabepunkt 2.
