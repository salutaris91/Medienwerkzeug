# Rückkanal-Abnahme ROADMAP #64 — Smart Inbox: sortierbare Liste

**Datum:** 2026-10-08 · **Auftraggeber:** Claude Code (Rolle Reviewer/Vermittler), NICHT Alex.
**Geprüfter Stand:** Worktree `feat-roadmap-64-inbox-sortierbar`, Head `1c8f7ad` (laut geliefertem `git log`; ich habe kein bash, keine eigene Git-Verifikation).
**Plan-Referenz:** `docs/sessions/2026-10-08-roadmap64-65-inbox/briefing-64.md` (status: approved, „Alex: ‚1–4 ja, Regeln 1–3 ja'").
**Rollen im Text:** [ich] = Vermittlungsagent dieses Rückkanal-Laufs; Befunde von [produktberater] und [advocatus] sind den Auftragsgemäß nur in dieser Datei zusammengefasst (Rohoutputs archiviert Claude Code per `opencode export`; Auftragsregel: keine weiteren Session-Dateien schreiben).

---

## ABNAHME: JA

**Begründung in einem Satz:** Der Code auf `1c8f7ad` erfüllt alle neun Akzeptanzkriterien und alle sieben ADRs des freigegebenen Briefings; die gefundenen Abweichungen sind rein formaler Natur (Briefing-Wortlaut vs. ADR-Wortlaut, Zeilenversatz) ohne Funktionswirkung, und die beiden neuen Testdateien prüfen die AKs inhaltlich, wie das Briefing es verlangt.

---

## 1. Planabnahme: AK- und ADR-Abgleich (Code-Prüfung [ich], Datei:Zeile)

| Kriterium | Ergebnis | Beleg |
|---|---|---|
| AK1 Payload-Felder | ✅ erfüllt | `gui/api/project_api.py:1362–1373` (stat-Pass), `:1500–1501` (Felder exakt `modified_at`/`total_size`); Test `tests/test_inbox_suggestions.py:54–100` (Ordner max-mtime/sum-size, Einzeldatei, int-Typen, `os.utime`, tmp-Verzeichnis) |
| AK2 stat-Fehlerfall | ✅ erfüllt | `project_api.py:1366–1373` (try/except OSError pro Datei, Datei zählt 0/entfällt, `log_message` sichtbar `:1371`, alle fehl → `None`/`0`, Eintrag bleibt); Tests `:102–160` (Partial + Totalausfall, Log-Assertion) |
| AK3 Sortier-Funktion | ✅ erfüllt | `app.js:12259–12306`: normale Funktionsdeklaration OHNE `export` (`:12259`), storage-frei; name via `localeCompare('de',{numeric,sensitivity:'base'})` (`:12267`), null IMMER ans Ende in BEIDEN Richtungen (early-return `:12274–12281`, `:12288–12295`), Tie-Break `project` (`:12301–12303`); Tests `inbox_sort.test.js:235–324` inkl. Umlaut-/S01E2/S01E10-Fall |
| AK4 Sortier-Leiste | ✅ erfüllt (mit Wortlaut-Abweichung D1) | `index.html:461–465` drei Buttons in `#smart-inbox-sort-bar role="toolbar"`; Klick-Logik asc/Toggle `app.js:12383–12392`; `aria-pressed` + ▲/▼ aria-hidden `:12366–12368`; leer → ausgeblendet `:12494`; Tests `:336–380` |
| AK5 Persistenz + Rerender | ✅ erfüllt | Key `smart-inbox-sort`, JSON `{field,direction}`, beide Zugriffe try/catch `app.js:12308–12334`; Sortierung VOR Render-Schleife (`:12412` vor `forEach :12415`); Tests `:385–418` inkl. Corrupted-JSON-Fall |
| AK6 Metazeile | ✅ erfüllt | `app.js:12434–12444`: „N Datei(en) · `formatBytes` · de-DE-Datum", „ · "-Trennung, null-Segment entfällt komplett; `formatDateDe` `:12336–12349`; keine neuen XSS-Vektoren (nur Zahlen in den HTML-Fluss, `escapeHTML` für count `:12434`); Tests `:423–451` |
| AK7 Default date desc | ✅ erfüllt | `app.js:12323` (`return { field: 'date', direction: 'desc' }` ohne Storage); Test `:329–334` |
| AK8 Cache-Buster | ✅ erfüllt | `app.js:1–9` alle 9 Importe `?v=95`; `index.html:2758` `app.js?v=95` (Briefing schrieb :2752 — Zeilenversatz durch +6 Zeilen Sortier-Leiste, Inhalt korrekt); `index.html:9` `style.css?v=48` |
| AK9 Hygiene | ⚠️ teilweis nicht selbst verifizierbar | tmp-Verzeichnisse ✅ (`test_inbox_suggestions.py:11`), keine echten Timer in den neuen Tests ✅ (keinsten `setTimeout`-Nutzung in `inbox_sort.test.js` gefunden); `git diff --check` kann ich ohne bash nicht ausführen — stütze mich auf Claude Codes Bericht (481 passed/1 deselected, Frontend 150/150) |

**ADR-Prüfung:** ADR-64-1 ✅ (ein stat-Pass über das bestehende `video_files`, `project_api.py:1362`; Cache-Logik `:1303–1305` und `video_files`-Sammlung `:1329–1342` unangetastet; kein Refactoring — Funktion wächst nur additiv). ADR-64-2 ✅ (reine Funktion, Vor-Render-Sort; `data-project` pro Eintrag `app.js:12452`, reihenfolge-agnostisch). ADR-64-3 ✅ (Buttons statt Dropdown/Chips; `style.css:3835–3863` ist exakt der append-Sortierblock inkl. `min-height:28px`, Datei endet dort — kein Scope-Creep in style.css). ADR-64-4 ✅. ADR-64-5 ✅. ADR-64-6 ✅ (`formatBytes`-Import `app.js:3` unverändert genutzt). ADR-64-7 ✅. API.md-Doku-Pflicht aus ADR-64-1 erfüllt: `API.md:122–143` dokumentiert beide Felder mit Semantik.

**Diff-Umfang:** Die 7 Dateien des Diff-Stat (`9130744..1c8f7ad`) entsprechen exakt der erlaubten Dateiliste des Briefings (Abschnitt 11); keine verbotene Datei berührt.

### Abweichungen (alle formal, keine funktional)

- **D1 — AK4-Wortlaut vs. ADR-64-3-Wortlaut (Briefing-interner Widerspruch, nicht des Workers):** AK4 fordert „die Leiste [wird] bei leerer Liste NICHT gerendert", ADR-64-3 und der Worker-Auftrag schreiben „Leiste wird per JS ausgeblendet". Der Code folgt dem ADR: initial `display:none` (`index.html:461`), ein-/ausgeblendet in `app.js:12407/:12494`; der Test assert `style.display === 'none'` (`inbox_sort.test.js:375–380`). Bewertung: unproblematisch — Buttons ohne Listener-Zugriff sind für einen Einzelnutzer nicht von „nicht gerendert" zu unterscheiden; die ADR-Entscheidung ist die maßgebliche.
- **D2 — AK1-Testmechanik:** Das Briefing nennt „`load_settings` gepatcht"; der Test isoliert stattdessen über `MW_SETTINGS_FILE`-Env-Variablen + Reset von `persistence._cached_settings` (`test_inbox_suggestions.py:19–31`). Absicht (keine echten Settings, deterministisch) ist erfüllt, sogar end-to-end-ärmer am Endpoint. Bewertung: akzeptable Äquivalent-Erfüllung.
- **D3 — Zeilenreferenz AK8:** `index.html:2752` → tatsächlich `:2758` (Versatz durch die eingefügten 6 Zeilen der Sortier-Leiste). Inhalt korrekt.
- **D4 — Zusatz-Element:** Die Leiste enthält ein beschriftendes `<span>„Sortieren:"</span>` (`index.html:462`), das im Briefing nicht explizit steht. Harmlose UX-Verbesserung im Sinne von ADR-64-3 (Affordanz), kein Verstoß gegen die append-Regeln.

---

## 2. Chancen und weitere Features — ROADMAP-Kandidaten

Alex (2026-10-08, wörtlich): „also meiner meinung nach soll das Planungsteam da rüber schauen; inkl. Chanchen und weitere Features ermitteln".
**Wichtig:** Alles below ist nur Vorschlag — **nicht** in `ROADMAP.md` geschrieben (Auftragsgrenze; Aufnahme entscheidet Alex/Claude Code). [produktberater] hat gegen #45, #65, #68, #69, #20, #11, #12, #17 duplettengeprüft.

### K1 — Inbox-Filter nach Medientyp (Film/Serie/Doku/Anime) — klein
- **Problem:** Typ-Badges sind sichtbar, aber nicht interaktiv; bei vielen Einträgen hilft Sortieren nicht bei der Frage „zeig mir nur Filme".
- **Nutzen:** Klick aufs Badge filtert, zweiter Klick hebt auf; kombinierbar mit #64-Sortierung („größte Serien zuerst"). `media_type` ist bereits im Payload — kein Backend-Change.
- **Aufwand:** KI klein (Click-Handler + `filter()` vor dem Render in `renderSmartInboxList`); Alex-Engpass klein (nur visueller Browser-Check).
- **Bezug:** Kein Duplikat. #45 = Aufräumaktionen, #65 = Gruppieren — anderer Use-Case als Filtern.

### K2 — Inbox-Gesamtgröße als Summenzeile — trivial (MVP-Vorstufe von #45 Punkt 1)
- **Problem:** `total_size` je Eintrag vorhanden, die Summe („Inbox: 47 GB in 12 Projekten") fehlt; heute Kopf addieren oder `du -sh` auf dem NAS.
- **Nutzen:** Sofortige Speicher-Orientierung auf der Startseite.
- **Aufwand:** KI trivial (`reduce()` + `formatBytes`, ein DOM-Span); Alex-Engpass trivial.
- **Bezug:** **Überschneidung mit #45** (Dashboard-Speicherbelegung Inbox/Outbox). [produktberater] positioniert es als eigenständige MVP-Vorstufe ohne Löschaktionen/Sicherheitsdialog. Empfehlung [ich]: eher als **Vorzieh-Kandidat aus #45** führen („#45 light") statt als neuen Eintrag — sonst droht Dublette; alternativ #45 um den Verweis ergänzen, dass #64 die Datenbasis (`total_size`) bereits liefert.

### K3 — Speicher aufgeschlüsselt nach Medientyp — klein
- **Problem:** K2 zeigt nicht, WO der Speicher liegt (Serien vs. Filme vs. Dokus).
- **Nutzen:** Entscheidungsgrundlage für Transcoding-Batches und Aufräumreihenfolge.
- **Aufwand:** KI klein (Gruppen-`reduce` nach `media_type`); Alex-Engpass klein.
- **Bezug:** Ebenfalls Vorgriff auf #45; nur sinnvoll **nach** K2 (beides zusammen = ein Eintrag).

### K4 — Sortierfeld „Dateien" (`video_count`) — trivial, Nutzen schwach
- **Problem:** `video_count` wird angezeigt, ist aber kein Sortierfeld.
- **Nutzen:** Begrenzt — „welches Projekt hat die meisten Dateien?" ist meist durch `total_size` besser beantwortet. [produktberater] selbst stuft es als „nice-to-have" ein; Empfehlung [ich]: nur aufnehmen, wenn Alex expliziten Bedarf sieht (4. Button + ein `else if`-Zweig, Infrastruktur aus #64 wiederverwendet).

### Bewusst NICHT empfohlen (verworfen, mit Grund)
- **Server-seitige Sortierung / `?sort=`:** Inbox-Größe typisch < 30 Einträge; Client-Sortierung instantan; Roundtrip + Cache-Key-Komplexität ohne Nutzen ([produktberater] und Briefing Abschnitt 4, konsistent).
- **Sortierung nach `confidence`/`profile_match` („Verarbeitungsreife"):** keine natürlichen Sortierfelder; datum-desc deckt die Priorisierungsfrage besser ab; K1 (Filter „nur mit Profil") wäre die einfachere Antwort auf denselben Use-Case ([produktberater]).
- **Kein neuer Kandidat zu #65/#68/#69:** die dort geplanten Mechaniken (Gruppen-Pseudo-Eintrag, Checkboxen, Mehrfachauswahl) nutzen die #64-Infrastruktur bereits — siehe `briefing-65.md` (AK2, ADR-65-4: Gruppe läuft durch dasselbe `sortInboxSuggestions`). Kein zusätzlicher ROADMAP-Eintrag nötig; #65 bleibt der natürliche nächste Schritt.

---

## 3. Übersehene Risiken (nur Neues gegenüber dem Vor-Review)

[advocatus] Kernaussage wörtlich sinngemäß: **kein neuer [kritisch]- oder [wichtig]-Abnahme-Blocker.** Die bekannten Punkte (Log-Spam bei NAS-Ausfall, Datum-Toggle-Überraschung, stat-I/O, Scope-Creep, Test-Hänger, Reihenfolge-Shift beim Deploy) wurden vertragsgemäß nicht erneut gemeldet.

### Für die Abnahme relevant (blockieren nicht)
- **R1 [wichtig, aber spec-konform] — Semantik-Kollision „Größe":** `total_size` zählt NUR Videodateien (`project_api.py:1362–1373`), der Dashboard-Kopf `inbox_size_gb` zählt ALLE Dateien (`gui/core/helpers.py:514–530` via `get_folder_size_bytes`, Consumer `app.js:11986`). Summe der Listenwerte bleibt systematisch unter der Kopf-Größe (z. B. große `.nfo`/`.srt`/Nicht-Video-Extras). Von [advocatus] als „bewusste, aber aus UI-Sicht mehrdeutige Entscheidung" eingeordnet — API.md:142–143 dokumentiert die Semantik korrekt. **Kein Bug.** Optionale Nachschärfe: Tooltip/Label „Videogröße" oder Doku-Hinweis; Entscheidung bei Alex, könnte in #45 (einheitliche Speicher-Anzeige) mitaufgehen.

### Backlog-/ROADMAP-relevant (keine Merge-Relevanz)
- **R2 [kosmetisch] — globaler `os.stat`-Mock ist eine latente Test-Falle:** `test_inbox_suggestions.py:124/:153` patcht `os.stat` global; `os.path.exists/isdir/getsize` delegieren intern darauf. Aktuell harmlos (kein Mock-Schlüssel-Treffer auf diesen Pfaden, `media.get_video_codec` läuft über subprocess), aber künftige Code-Pfade im selben `with`-Block könnten den Test still falsch machen. Backlog: Mock enger fassen.
- **R3 [kosmetisch, vorbestehend] — `_inbox_cache = {}` (Dict-Init) vs. Liste (`project_api.py:1174` vs. `:1504`):** von #64 nur berührt, nicht verursacht; nie zur Laufzeit gelesen (Cache-Time 0 erzwingt Miss). Trivialer Fix (`= []`) als Hygiene-Punkt; war bereits im Briefing Abschnitt 4 (verworfenes Refactoring, C3) vorausgesagt — [advocatus] bestätigt den Befund im jetzt implementierten Code.
- **R4 [kosmetisch] — „0 Bytes"-Anzeige bei Totalausfall:** sind alle Dateien unlesbar, zeigt die Metazeile „N Datei(en) · 0 Bytes" und sortiert bei Größe asc oben — während `modified_at=null` ans Ende sortiert (Asymmetrie 0 vs. null). Spec-konform (AK2), UX-irreführend im Fehlerfall. Denkwürdig für #68-Nachbarschaft (NAS-Ausfall-Szenarien).
- **R5 [kosmetisch] — TZ-Härte AK6-Test:** `1760000000` = 09.10.2025, 08:53 UTC — fest codiertes „09.10.2025" (`inbox_sort.test.js:433`) kippt nur in Zonen ≤ UTC−10; CI (UTC) und Berlin/Mac sind sicher. Restunsicherheit, kein Handeln nötig.
- **R6 [Backlog, #65-Vorgriff] — Pseudo-Gruppen vs. `deleteProject`:** `app.js:12452/:12485` nutzen `item.project` als Pfad-Schlüssel; #65 plant Gruppen-Pseudo-Einträge mit synthetischem Gruppennamen. Kollisionsflächen: (a) Gruppenname == realer Ordnername → Lösch-Button auf falschem Pfad, (b) Gruppen dürfen keinen Quarantäne-Button tragen. Ist #65-Scope, gehört dort aber zwingend in die AKs — [advocatus] meldet es als Interaktionsrisiko der nächsten Stufe; `briefing-65.md` (in Arbeit, von mir NICHT geändert) muss das aufgreifen.

### Von [advocatus] geprüfte und entkräftete Punkte (keine Findings)
eval-Muster etabliert · Spread-Kopie schützt Raw-Array (`app.js:12264`) · localeCompare-Performance irrelevant bei <100 Einträgen · `int(max(mtime))`-Rundung unkritisch · API rein additiv/abwärtskompatibel (`welcome.js` ohne Feldannahmen) · Cache-Buster synchron konsistent · XSS sauber escaped (`app.js:12432/12457/12473`).

### Restunsicherheiten [advocatus]
Keine Testausführung (schreibgeschützt) — R2/R5 beruhen auf Code-Analyse; kein Live-NAS-Check. [ich] ergänze: `git diff --check` (AK9) und die Test-Ausgabe (481/150 grün, alte Code 3/3+12/12 rot) sind Claude-Code-Berichte, von mir nicht selbst verifiziert.

---

## 4. Empfehlung an Alex

1. **Abnahme annehmen (ABNAHME: JA).** Der freigegebene Plan ist erfüllt; D1–D4 sind Formalia, die keiner Nachbesserung im Code bedürfen. Merge-Entscheidung bleibt Klasse C bei dir (vollständiger Git-Preflight: Branch `feat/roadmap-64-inbox-sortierbar`, Head `1c8f7ad`, 7 Dateien, Diff-Stat oben — geliefert von Claude Code; ich habe keinen eigenen Git-Zustand erhoben und schlage hier selbst nichts vor).
2. **Reihenfolge der Chancen:** #65 ist bereits in Planung und der natürliche nächste Schritt (nutzt die #64-Sortierinfrastruktur direkt). Aus den neuen Kandidaten würde ich **K1 (Typ-Filter)** als eigenständigen kleinen Eintrag aufnehmen lassen und **K2/K3 zusammen als „#45 light"** führen (Vorgriff auf #45, keine neue Dublette). K4 nur auf explizisten Wunsch. Über die Aufnahme in ROADMAP.md entscheidest du; dieser Lauf schreibt sie bewusst nirgends hinein.
3. **R1 (Größen-Semantik) ist die einzige Produktentscheidung, die ich empfehlen würde, jetzt zu treffen oder bewusst zu #45 zu legen:** Tooltip „Videogröße" (Mikro-Fix, könnte im #65-PR mitreisen) oder nichts tun und in #45 vereinheitlichen. Mein Default-Vorschlag: nichts tun, Vermerk zu #45 — der Einzelnutzer-Kontext macht die Kollision selten sichtbar.
4. **R6 an die #65-Sitzung weitergeben** (Lösch-Button/Pseudo-Gruppe) — dort ist `briefing-65.md` in Arbeit; die parallele Sitzung soll das als AK-Kandidat prüfen. Ich habe dort nichts geändert.

**Stichproben-pflichtige Themen (Geld/Aussenwirkung/Recht/Kauf):** keine berührt — #64 ist reine Lokal-UI/Backend-Anzeige für den Einzelnutzer, keine neuen Assets/Lizenzen (▲▼ Unicode gemeinfrei, Briefing Abschnitt 7 bestätigt).

---

*Ende des Rückkanal-Laufs. Gemäß Auftrag: danach STOPP — kein Git, kein Push, keine weiteren Dateien, keine Änderung an `briefing-65.md` oder übrigen Session-Dateien.*
