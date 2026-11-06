# Plan-Review Runde 1 — Film-Assistent #92 (2026-11-06)

> Archivierungsvermerk (Orchestrator/ceo-planner, 2026-11-06): Beitrag des plan-reviewer unverändert übernommen.
> Bezogenes Artefakt: `docs/sessions/2026-11-06-film-assistent/briefing.md` (Stand vor den unten nachgezogenen kosmetischen Nachzügen).
> Nachgang: Alle vier [kosmetisch]-Einwände wurden nach dem APPROVE direkt im Briefing bzw. in der Alex-Zusammenfassung behoben (E4/E5/E6 „Erlaubte Dateien" konkretisiert bzw. Verzeichnis-Spielraum ausdrücklich gekennzeichnet; SmartWizard-Lizenzangabe ohne unbelegte „MIT"-Behauptung; Frage 4 der Zusammenfassung mit Vermutungs-Empfehlung; Zeilenzahl `#modal-nfo-agent` 153→154 korrigiert). Keine inhaltliche Änderung — keine weitere Review-Runde nötig (Verdikt bleibt; max. 3 Runden laut Hausregel, hier bei R1 APPROVE).

## Prüfbericht

Geprüft wurde `docs/sessions/2026-11-06-film-assistent/briefing.md` (Status draft, FP2 steht aus) gegen Vorlage, Freigabe-Grundlage (akt2-prompt.md mit drei Auflagen, synthese.md ADR-01–06), Hausregeln und den tatsächlichen Code. Alle Prüfungen read-only.

### 1. Vorlage-Konformität — erfüllt

Alle Pflichtabschnitte vorhanden: Problemstellung (Z. 17), Zielnutzer (Z. 23), Akzeptanzkriterien mit E-AK-Präfixen (Z. 27–52), Etappen mit Ziel/AKs/erlaubten Dateien/Diff-Schätzung/Abbruchkriterium (Z. 54–100), Bewusst verworfen (Z. 145). Frontmatter: `status: draft` ✅; die FP2-Felder sind auskommentiert mit Begründung (Z. 9–10) — kein selbst formuliertes approval_quote ✅. Die gesetzten `fp1_*`-Felder tragen das wörtliche Zitat „Ja, freigeben", das exakt mit akt2-prompt.md Z. 4 übereinstimmt — belegt, nicht simuliert.

### 2. Auflagen aus FP1 — alle drei erfüllt

**Auflage 1 (Backend-Nachzug in 1a):** ✅ E1 enthält den Nachzug als Pflichtbestandteil (ADR-07, Z. 143), mit Tests E1-AK3/AK4. Das Briefing verschärft die Auflage sogar zutreffend: Der OFDb-Zweig (processor.py 2116–2117, `generate_ofdb_nfo()` — verifiziert: Signatur ohne `nfo_overrides`, mw_metadata.py 895) nimmt heute gar keine Overrides entgegen und ist mit abgedeckt. Technische Erreichbarkeit verifiziert: `patch_nfo_fields()` (gui/core/nfo_mutation.py 155–215) unterstützt `title/year/plot/fsk→<mpaa>/genres→<genre>` — E1-AK3/AK4 sind mit bestehendem Code und den gelisteten Dateien umsetzbar; `nfo_mutation.py` muss zu Recht nicht in E1s erlaubte Dateien.

**Auflage 2 (Schnittvergleich mit Diff-Größen):** ✅ Vergleichstabelle Schnitt A vs. B (Z. 108–119) mit (semi-)gemessenen Größen (~65–85 KB vs. ~150–190 KB), Bewertung über Achsen/Doppelcode/Alltagsnutzen/Rollback, Empfehlung **A**, Entscheidung ausdrücklich bei Alex (D1, Z. 160). Die Schwäche von Schnitt A (temporärer Doppel-Ablauf) bleibt dokumentiert, nicht verschwiegen (Z. 115, 119, 184).

**Auflage 3 (Bildquellen neu stellen):** ✅ D2 (Z. 161) neu formuliert: dauerhaftes Speichern ist Bestand (code-verifiziert: mw_metadata.py 1208–1238 lädt Poster/Backdrop/Logo via `fetch_tmdb_images` in den Filmordner, Fallbacks 1241–1261); neu wären nur Auswahl + optional Fanart.tv. Option A vs. B mit Empfehlung **A**, der Wechsel von der Synthese-Empfehlung B ist mit Begründung offengelegt (Z. 161 und Dissens Z. 182) — genau die Art revidierter Empfehlung, die Alex entscheidet. Als Freigabepunkt offen, E5 hart gegated (Z. 88, 93).

### 3. Hausregeln — erfüllt

- **Diff-Richtwert 80 KB:** E1 (~65–85 KB) mit Rückstell-Liste + Abbruchkriterium (Z. 64–65); E2 (~70–100 KB) überschreitet im ungünstigen Fall ausdrücklich benannt mit Vorab-Notbremse E2b (Z. 71) — begründete Überschreitung/Teilung im Sinne der Regel. E3–E6 im Budget.
- **>3 Etappen begründet:** ✅ drei Gründe (FP1-Beschluss, Diff-Messung macht 1b-Teilung zum Regelfall, Rechts-Gate D5/E5 darf nicht mit funktionalen Ketten gemischt werden) — Z. 56.
- **Zeitschätzung getrennt:** ✅ KI 1–3 Tage/Etappe vs. Alex-Engpass 3–5 Tage Review + 1–2 Tage Freigabe + D2-Rechtsklärung 1–3 Wochen (Z. 166–168).
- **Lizenzabschnitt:** ✅ vorhanden (Z. 170–176), vollständig für alle übernommenen Elemente (kein Third-Party-Code, Lucide bestehend, TMDb/Fanart.tv-Attribution mit Terms-Verweis auf scout.md Abschnitt 3 — dort mit Abrufdatum 2026-11-06 gepflegt).
- **Dissens-Pflicht:** ✅ advocatus-REVISE, produktberater-MVP-Vorbehalt, scout-vs-advocatus-Bildquellen, grafiker-#91-Kollision, zweiter-Reviewer-Schnitt B — alle dokumentiert (Z. 178–185); der Wechsel der Bildquellen-Empfehlung B→A ist explizit dokumentiert, nichts verloren oder verfälscht (stichprobenhaft gegen scout.md 306–328, advocatus.md Pkt. 1–9, produktberater.md 65–74 verifiziert — alle referenzierten Punkte/Abschnitte existieren und werden zutreffend wiedergegeben).
- **Neue Abhängigkeiten:** ✅ keine vorgeschlagen — SmartWizard (ADR-03) und Playwright (FP1, 5.3 Variante b) sind als geprüft-und-verworfen dokumentiert.
- **Freigabepunkte nicht stellvertretend beantwortet:** ✅ D1–D4 stehen offen als Alex-Fragen, D2 als expliziter Freigabepunkt, D3 als „mit Empfehlung vorbelegt, bitte bestätigen" gemäß akt2-prompt. FP2 nicht vorweggenommen.
- **Git-Preflight:** ✅ kein Commit/PR vorgeschlagen; Git-Zustand als D5 eingefordert (Z. 164); Belege-Abschnitt bestätigt keine Git-Schreiboperation (Z. 189).

### 4. Code-Belege — alle Stichproben bestätigt

| Zitat im Briefing | Verifikation |
|---|---|
| processor.py 2102–2124 (Inbox ruft `generate_movie_nfo`, kein Patch) | ✅ exakt (Aufruf 2119) |
| OFDb-Zweig 2116–2117 ohne Overrides | ✅ (Signatur mw_metadata.py 895 bestätigt) |
| `patch_nfo_fields` nur im NFO-Agent-Block (Import 3361; Aufrufe 3398/3428/3534/3593) | ✅ alle fünf Treffer stimmen |
| mw_metadata.py 1028–1031 / 1057–1060 / 1096–1099 / 1167–1170 (nur title/plot/year) | ✅ alle vier Stellen exakt |
| mw_metadata.py 948–960 (`find_best_image`: de→sprachlos→en→erster Treffer) | ✅ — Korrektur Nr. 4 des Briefings ist zutreffend |
| mw_metadata.py 1208–1262 (fetch_tmdb_images, dauerhaftes Speichern) + Fallbacks 1241–1261 | ✅ |
| mw_metadata.py 148/153 (`fetch_json_with_retry`/`fetch_html_with_retry` existiert bereits) | ✅ — Korrektur Nr. 6 zutreffend |
| app.js 10488 unescaped / 10493–10494 escapeHTML | ✅ exakt |
| app.js 4556–4565 (nur title/year/plot im Frontend) | ✅ — Korrektur Nr. 2 zutreffend |
| app.js 1832 („Doku verarbeiten") | ✅ — Korrektur Nr. 5 zutreffend |
| app.js 10253–10525 (`openPreviewModal`) / 7719 (Execute-Verdrahtung) / 9 ES-Importe / 18.764 Zeilen | ✅ alles exakt |
| queue_api.py 366–395 (#91-Scan synchron) / 144–145 (Default /Filme) / TV-Zweig ab 397 | ✅ |
| nas_api.py 747–751 (`write_fsk_to_nfo` als weiterer Rufer) | ✅ — Korrektur Nr. 3 zutreffend |
| nfo_ui.js exakt 74 Zeilen | ✅ |
| index.html 764 / 2550 / 3162 / 2563–2579 / 821–871 / 3163/3189/3193/3218 | ✅ alle Positionen stimmen |
| theme.js Z. 6 (5 Themes), style.css 2753 (`.step-dot`), Cache-Buster `?v=105`/`?v=51` | ✅ |
| Testdateien (test_nfo_write.py, test_metadata_retry.py, tests/frontend/) | ✅ vorhanden |

Keine falsche Zeilen- oder Inhaltsangabe gefunden. Die 8 „Korrekturen/Gegenproben" des Briefings habe ich einzeln nachgeprüft — alle sind korrekt.

### 5. Konsistenz briefing ↔ ALEX_ZUSAMMENFASSUNG — widerspruchsfrei

Beide Artefakte empfehlen konsistent Schnitt A und Bildquellen-Option A; dieselben fünf Design-Details (D3), dieselbe Reihen-Frage (D4), derselbe Git-Punkt (D5). Zusammenfassung: 33 Zeilen ≈ eine Bildschirmseite ✅; Fachbegriffe übersetzt („Rückholschritt" für Rollback, Diff über „Budget (80 KB)" kontextualisiert) ✅; jedes offene Thema mit Empfehlung + Trade-off + Entscheidungsfrage (bis auf Frage 4, siehe Finding 3) ✅; stichproben-pflichtiges Thema Recht/Bildquellen explizit benannt mit Pfad zu den Rohoutputs (scout.md Abschnitt 3, advocatus.md Pkt. 8 — beide existieren) ✅. Die Zahl „ca. 30–50 Min/Woche" ist durch produktberater.md Z. 9 belegt.

### Findings

1. **[kosmetisch]** Erlaubte Dateien in E4/E5/E6 teils nur auf Verzeichnisebene (`gui/api/`, `Tests`, `Frontend-Tests`) statt konkreter Pfade, anders als in E1–E3 — ein schwächerer Leash für den späteren Gate-A2-Worker (briefing.md Z. 84, 91, 98). Empfehlung: erwartete Dateien benennen (z. B. `gui/api/queue_api.py` bzw. neue Endpoint-Datei explizit) oder die Verzeichnis-Erlaubnis ausdrücklich als bewussten Spielraum kennzeichnen.
2. **[kosmetisch]** Die Lizenzangabe „SmartWizard (`@smart-wizard/core`, MIT)" (briefing.md Z. 173) ist in den Session-Unterlagen unbelegt — scout.md Abschnitt 2.2 (Z. 159–166) nennt keine Lizenz. Kein blockierender Lizenzverstoß, da die Bibliothek explizit verworfen ist und keine Abhängigkeit/Lockfile-Änderung entsteht; die Angabe sollte aber entweder mit Quelle belegt oder gestrichkt werden, damit der Lizenzabschnitt lückenlos belegt bleibt.
3. **[kosmetisch]** ALEX_ZUSAMMENFASSUNG Frage 4 (Filmreihen-Häufigkeit, Z. 27) hat — anders als alle übrigen offenen Punkte — keine explizite Empfehlung, nur eine Konsequenz-Verzweigung („Selten → … häufig → …"). Bei einer Faktenfrage vertretbar; eine Vermutungs-Empfehlung („vermutlich selten → E6 bleibt letzte Etappe", gestützt auf produktberater.md Z. 67) wäre konsistenter mit dem Hausregel-Muster.
4. **[kosmetisch]** Zeilenzahl-Unschärfe in der als „gemessen" ausgewiesenen Diff-Methodik: `#modal-nfo-agent` mit „153" angegeben (briefing.md Z. 106), real index.html 3162–3315 = 154 Zeilen. Trivial, aber die Tabelle gibt Zeilenzahlen direkt am Code ausgelesen aus — auf Rundung hinweisen oder korrigieren.

### Potenziale-Block (optional, keine Bedingungen)

- **„Verifikation und Korrekturen"-Abschnitt als Vorlagen-Baustein:** Die Akt-2-Gegenprobe (8 Korrekturen mit Zeilenbelegen) hat sich als wertvoll erwiesen — alle Korrekturen waren zutreffend. Für künftige Briefings mit Code-Behauptungen als Pflichtabschnitt in die Kit-Vorlage aufnehmen.
- **OFDb-Override-Lücke als eigener ROADMAP-Vermerk:** Der Defekt (Inbox-Import verliert bei `provider == "ofdb"` *alle* Overrides, nicht nur FSK/Genre) existiert unabhängig vom Wizard und wäre als eigenes Roadmap-Item wertvoll, falls E1 verzögert oder gekippt wird.
- **Robustheitsnotiz für E5:** Bei Option A könnte das bestehende `find_best_image` (mw_metadata.py 948–960) als Fallback dienen, falls die Auswahl-UI leer bleibt — kleine Ergänzung für die E5-Detaillierung.
- **Handtest-Parcours:** `handtest-parcours.md` existiert noch nicht — vom Briefing selbst als Vor-E1-Pflicht zugesagt (Z. 29); bei E1-Start prüfen.

**Nicht ausgeführte Prüfungen / Restrisiken:** Der Git-Zustand des Arbeitsverzeichnisses konnte von mir nicht verifiziert werden (keine Shell in dieser Review-Runde) — die Code-Belege könnten theoretisch gegen einen veränderten Working Tree geprüft worden sein; das Briefing selbst hält den Git-Zustand für offen (D5) und schlägt korrekt keine Git-Operation vor. Die Diff-KB-Zahlen sind Zeilenmessungen mit Byte-Schätzung (±30 %), nicht Shell-gemessen — vom Briefing selbst so deklariert (Z. 104).

VERDICT: APPROVE
1. [kosmetisch] Erlaubte Dateien E4/E5/E6 nur auf Verzeichnisebene statt konkreter Pfade — schwächerer Leash für den Gate-A2-Worker (briefing.md Z. 84, 91, 98)
2. [kosmetisch] SmartWizard-Lizenzangabe „MIT" in den Session-Unterlagen unbelegt (briefing.md Z. 173 vs. scout.md Z. 159–166) — belegen oder streichen; kein blockierender Verstoß, da verworfen und keine Abhängigkeit entstehend
3. [kosmetisch] ALEX_ZUSAMMENFASSUNG Frage 4 ohne explizite Empfehlung, abweichend vom Muster Empfehlung + Trade-off + Entscheidungsfrage der übrigen offenen Punkte (ALEX_ZUSAMMENFASSUNG.md Z. 27)
4. [kosmetisch] Zeilenzahl `#modal-nfo-agent` „153" statt real 154 in der als „gemessen" deklarierten Diff-Methodik (briefing.md Z. 106 vs. index.html Z. 3162–3315)
