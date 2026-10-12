# Rohoutput plan-reviewer — Kreativteam 2026-10-12 (Akt 2, Ordner-Folgen)
Hinweis Claude Code (2026-10-12): Mechanisch aus `opencode export ses_ed092b3e0ffe9iDPDyHyWFilqY` (ceo-planner, Akt 2) abgelegt, nicht vom Moderator abgeschrieben (Lehre 59). Einzige Änderung: Trailing Whitespace entfernt. Volle Daten: Kit `scripts/gate-a2/logs/2026-10-12-inbox-ordnerfolgen/export-ceo-planner-akt2.json`.

---

## plan-reviewer: plan-reviewer Runde 1 briefing (Subagent-Sitzung ses_ed07d4ffdffekoOwmrwfvAI6wf, Status: completed)

<task id="ses_ed07d4ffdffekoOwmrwfvAI6wf" state="completed">
<task_result>
Die Prüfung ist abgeschlossen. Alle Stichproben sind durchgeführt; hier der Bericht.

---

# Plan-Review: `docs/sessions/2026-10-12-inbox-ordnerfolgen/briefing.md`

**Prüfumfang:** Kickoff-Bindungen (00-kickoff.md), Formalvorgaben, Code-Realität (Stichproben mit Datei:Zeile im Worktree), innere Konsistenz & Hausregeln. Read-only; keine Git-Befehle, kein Web, keine .env gelesen.

## 1. Verifizierte Code-Behauptungen (alles bestätigt)

**app.js:** `extractStrictSeasonEpisode` :12477–12490 mit Muster :12479 (linke Gruppe `(?:^|[._\s\-\[])`, rechte `(?:[._\s\-\]]|$)`) ✓; `detectInboxGroups` :12492–12515 mit `is_dir`-Rauswurf :12496, Sentinel :12498, einziger Aufrufer :12499, ≥2-Regel :12508–12513 ✓; globalThis-Export :13234 ✓; Banner-Apply :12630, `detectManualGroupSeriesName` :12641–12661 (Separator-Strip :12645), Bulk :12698, fallbackName :12706, Gruppen-Knopf :13075 ✓; Meta :13109, `isProcessing` :13121, Eligibility :13126, disabled :13133, Film-Sperre :13139–13145, Zeilenklick :13178–13179, Auswahl-Handler :13192–13202, Badges :13094–13104, Mitgliederstruktur :13019–13033 ✓; neun Importe `?v=99` in :1–9 ✓; `selectShow` :3280–3283, Payload `show_name` :4429 / `files` :4447–4448, Manuell-Fallback :7649–7674 ✓. Grep: genau **drei** `startSeriesGroupWorkflow`-Übergaben (12631/12709/13076) — deckungsgleich mit Auftrag Punkt 4.

**project_api.py:** :4 `from gui.core.helpers import *` (helpers.py hat kein `__all__` → `GROUP_VIDEO_EXTENSIONS` ist im Scope — ADR-71a-1-Behauptung stimmt); 6er-Liste :1321, Walk :1333–1340, `video_count == 0 → continue` :1345–1346, tv_pattern :1413, Pipeline :1417–1421 + :1438–1440, Payload :1490–1503, `is_dir` :1502, Cache :1303–1305 ✓.

**helpers.py:** 10er-Liste :798 (exakt 10 Endungen), `validate_group_files` :801–867 mit Ordner-Ablehnung :851–852, Endungen :857–859, Existenz :848–849; `find_group_companion_files` :870–918 (vdir :890, Präfix :902/:911) ✓.

**processor.py:** files[]-Zweig :870–884, `current_dir = inbox_root` :875, Prüfblöcke :947–997 (Subs-new :969–978, Renames-new :988–997) vor erster Bewegung ab :999+, Hochziehen :1058–1068, Cleanup nur ohne files :1084–1091 und :1717 ✓.

**queue_api.py:** Preview :73–95, Process :815–833, legitimes `new` als reiner Dateiname :568–569/:622–644 ✓. **These bestätigt:** grep über `gui/` ergibt `explicit_renames`/`explicit_subs` nur in app.js (Sender, :10646–10647) und processor.py (Konsument) — **nicht** in queue_api.py.

**Sonstiges:** `index.html:2760` = `app.js?v=99` ✓; `inbox_group.test.js` :646–667/:661–667/:672–700/:968–995/:997–1026/:1067–1092/:1094–1099 alle zeilengenau ✓; `cache_busting.test.js:13–47` ✓; `ROADMAP.md:1967–1987` (#71) und :1996 (#72 Punkt 1) ✓; beide Python-Testdateien existieren ✓; `clean_show_name` (utils.py:23–30) behält Punkte → B3-Nuance korrekt ✓; `renderMatchingMatrix` (app.js:3687) filtert mit der vollen 10er-Liste → kein stiller Modal-Skip für `.ts`/`.wmv`-Einzelvideos ✓; `test_cmd` **byte-identisch** zu briefing-65.md Abschnitt 11 (Zeile 180 vs. briefing-65.md:192), ohne eigenes `timeout`, `test_timeout_s` 600 dokumentiert ✓.

**Regex-Logik AK1b:** `ThWaDeS11E24720p` mit `/(?<!\d)[sS](\d{1,2})[eE](\d{1,3})(?!\d)/i` → E247/E24/E2 scheitern alle an nachfolgender Ziffer, kein zweites S → `null` ✓; `ThWaDeS11E23` matcht („e" vor S, Ende nach 23) ✓; `…S01E01PROPER…` matcht künftig ✓; die vier bestehenden Null-Fälle enthalten kein `s\d+e\d+` ✓.

## 2. Kickoff- & Formalprüfung (erfüllt)

- **Alex-Entscheidungen 1–7** wörtlich zitiert (Zeile 14) und vollständig operationalisiert (1→AK1/ADR-71a-3, 2→AK2/ADR-71a-1, 3→AK3/AK4/ADR-71a-4, 4→AK6, 5→ADR-71a-5+Dissens 1, 6→ADR-71a-7+Abschnitt 12, 7→AK8). **F1** unter „Bewusst verworfen" (Zeile 68) mit wörtlichem Zitat und Verweis „**Folgepunkt zu ROADMAP #71**" ✓.
- **Frontmatter:** `status: draft`, `source: roadmap#71` mit Teilmenge + #72.1 im Text (Zeile 12), `approved_on`/`approval_quote` Platzhalter („von Alex einzusetzen, nicht vom Agenten") — keine stellvertretend eingesetzte Freigabe ✓. 12 Abschnitte vollständig, 7 ADRs, AK0 als Claude-Code-Messung in `ak0-ausgangsmessung.md` ✓. Alle Mindest-AKs vorhanden (Muster a inkl. Ziffern-Fall, 1/0/≥2-Videos, Pipeline-Identität, gemischte Gruppe, AK6-Begleiter/Fremddateien/Ordner-bleibt, #72.1-`new`-Fälle inkl. Backslash/`./`/leer, ohne-files[]-unverändert, v100, `git diff --check`) ✓.
- **Abschnitt 11:** Erlaubnisliste deckt jede geforderte Änderung (10er-Import in project_api.py abgedeckt; AK5 braucht über Cache-Buster hinaus nichts in index.html, da Checkboxen dynamisch in app.js generiert werden; API.md hat natürliche Stellen in :122–145 und :263–268); Nicht-anfassen-Liste vollständig (ROADMAP.md, docs/sessions/**, STAND.md, VERLAUF.md, scripts/**, .env nie lesen); Erfahrungswerte (Timer, Trailing Whitespace, ~120 KB) alle vorhanden ✓.
- **Abschnitt 12:** nativ arm64 OrbStack, alle geforderten künstlichen Testdaten (XyzS01E01/Xyz.Show…, .de.srt, .nfo/sample.mkv/Bild, 2-Video-Ordner, lose Datei, Ziffern-Fall), Live-Test zuerst nur Staffel 11 per Auswahlkästchen ✓.
- **Dissens-Pflicht:** Dissens 1–4 mit Subagenten-Positionen als verworfene Alternativen, Risiken-Block, IOU-Hinweis für Rohoutputs (Zeile 141, Muster briefing-65) ✓. Keine Duplikat-Widersprüche zwischen ADRs und Abschnitt 4. Git-Zustand offengelegt, Feature-Branch (kein main-Stop), KI/Engpass getrennt, keine Secrets ✓.
- **Lizenzen:** Abschnitt 7 vorhanden und gepflegt — Lucide-Inline-SVG (ISC) benannt, keine neuen Third-Party-Assets/Icons, Referenz-Apps nur als Muster → **kein Lizenz-Blocker** ✓.

## 3. Findings

**Blocker:** keine.

**Sollte behoben werden:** keine.

**Optional:**

1. **„Fünf-Stellen-Invariante" unbelegt und mit AK5b inkonsistent** — ADR-71a-2 (briefing.md:88) sagt „[advocatus] K1 zählt fünf Stellen" und die Konsequenzen „hält die Fünf-Stellen-Invariante testbar (AK5b)", aber AK5b (Zeile 56) und Auftrag Punkt 4 (Zeilen 232–236) benennen nur **drei** Übergabestellen (Banner :12630, Gruppen-Knopf :13075, Bulk :12698) plus fallbackName :12706. Code-Realität (grep): genau diese drei files-Bau-Stellen + fallbackName existieren — funktionale Deckung ist vollständig, aber die Zahl „fünf" ist weder aufgeschlüsselt noch belegbar (Rohoutputs IOU). Änderung: „fünf" streichen oder die fünf gemeinten Stellen benennen, sonst sucht Worker/Reviewer zwei Phantom-Stellen.
2. **AK0-Basis mehrdeutig (main vs. Branch-Head)** — AK0 (Zeile 35) und Schritt 0 (Zeile 316): „Basis ist `main` nach Merges von #65 Lauf A+B (`dd65244`, `17b96d1`, Stand des Kickoff-Git-Zustands)". Der Kickoff-Head `fc75466` liegt **ahead 1** und nicht auf main; die Formulierung vermischt main-Stand (17b96d1) und Branch-Head. Da `fc75466` laut Commit-Titel reine Doku ist, funktional unkritisch — aber AK0-Messung und Worker-Klon sollten dieselbe eindeutig benannte Basis haben (z. B. „origin/main @ 17b96d1; fc75466 (docs-only) nicht Teil der Worker-Basis").
3. **Handtest Punkt 5 missverständlich formuliert** — Abschnitt 12 (Zeile 330): „keine Falschgruppe mit Staffel 11" und „Gruppe `Xyz Show`-Schlüsselbildung". Tatsächlich fällt der Ziffern-Fall-Ordner (Datei `S11E24`, Schlüssel aus AK3 = `Xyz.Show`) **korrekterweise** in dieselbe Seriengruppe wie die S01-Folgen — das ist gewünschtes Verhalten; „Falschgruppe" meint vermutlich nur die Gruppe nach dem kryptischen Ordnernamen. Zudem heißt der Schlüssel literal `Xyz.Show` (Punkte, B3-Nuance), nicht „Xyz Show". Präzisieren, damit der manuelle Test die richtige Ist-Erwartung prüft (Ordner in der Gruppe mit S11E24-Badge; entscheidend: kein Schlüssel/S/E aus dem Ordnernamen).

## 4. Restrisiken / nicht ausgeführte Prüfungen

- **Rohoutputs der Akt-2-Subagenten** (produktberater/advocatus/grafiker) sind noch nicht archiviert (Session-Ordner enthält nur Kickoff + Briefing). Alle Rollenzitate (K1, K2, W2–W4, KOS1–KOS3, grafiker-/produktberater-Positionen) sind damit IOU gemäß Zeile 141 — Belegbarkeit erst mit dem Archiv; insbesondere die F1-Absage-Begründung („von Alex angenommen", Zeile 68) und die „fünf Stellen" sind dann nachbelegbar. Der IOU-Hinweis genügt dem etablierten Muster (briefing-65).
- Keine Testausführung durch mich (Review-Modus, read-only) — AK-Ausführbarkeit nur formal geprüft.
- Inhalt von `fc75466` im Detail nicht prüfbar (keine Git-Befehle in dieser Prüfung); Commit-Titel („docs: …") deutet auf Doku-only.

## 5. Potenziale-Block (optional, keine Bedingungen)

- **Client-10er-Liste als AK sichern:** `renderMatchingMatrix` (app.js:3687) filtert mit der vollen 10er-Liste — ein AK-Fall „Einzelvideo-Ordner mit `.ts`" würde diese Client-Liste gegen künftige 5er-Regressionen festzurren (Thema #72 Punkt 8) und den End-to-End-Pfad Ordner→Modal-Row→Mapping abdecken.
- **Bulk-Weg-Randfall spezifizieren:** Wenn ein ausgewählter project-Key nach Re-Load nicht mehr in `currentSmartInboxRawSuggestions` auflösbar ist, führt die natürliche Implementierung (Fallback auf project-Namen) zu einem lauten HTTP 400 — kein Datenrisiko, aber UX-rau; eine Fallback-Regel im Auftrag Punkt 4 würde das deterministisch machen.
- **Nachbelegung mit Rohoutputs:** „fünf Stellen" (K1) und F1-Absage-Begründung nach Archivierung verifizieren (IOU einlösen).

---

**Zusammenfassung:** Alle Zeilenangaben des Briefings stimmen in den Stichproben, die queue_api-These ist per grep bestätigt, alle Kickoff-Bindungen (B1–B7, Entscheidungen 1–7, N1–N4, F1-Absage mit ROADMAP-Verweis) sind eingehalten, `test_cmd` ist byte-identisch zum Präzedenz, die Erlaubnislisten decken jede geforderte Änderung, und der Lizenz-Abschnitt ist vollständig gepflegt. Keine Blocker, keine wichtigen Einwände — drei kosmetische Präzisierungen empfohlen.

VERDICT: APPROVE

1. [kosmetisch] ADR-71a-2 (briefing.md:88): „[advocatus] K1 zählt fünf Stellen" / „Fünf-Stellen-Invariante testbar (AK5b)" ist mit AK5b (Zeile 56) und Auftrag Punkt 4 (Zeilen 232–236) inkonsistent — nur drei Übergabestellen + fallbackName sind benannt und existieren im Code (app.js:12630/:12698/:13076/:12706). „Fünf" streichen oder die fünf Stellen aufschlüsseln (Prüfschritt: grep `startSeriesGroupWorkflow\(` → genau 3 Aufrufe).
2. [kosmetisch] AK0 (briefing.md:35) und Schritt 0 (Zeile 316): Basis-Angabe „main nach Merges … Stand des Kickoff-Git-Zustands" vermischt origin/main (17b96d1) und den ahead-1-Branch-Head fc75466; eindeutig benennen, damit AK0-Messung und Worker-Klon dieselbe Basis haben (fc75466 ist laut Commit-Titel docs-only, funktional unkritisch).
3. [kosmetisch] Abschnitt 12 Punkt 5 (briefing.md:330): „keine Falschgruppe mit Staffel 11" ist missverständlich (der Ordner fällt korrekt in die `Xyz.Show`-Gruppe mit S11E24-Badge) und „Xyz Show" sollte literal `Xyz.Show` (Punkte) heißen — präzisieren, damit der Handtest die richtige Ist-Erwartung prüft.
</task_result>
</task>
