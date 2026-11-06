---
kind: plan-synthese
status: draft
roadmap_item: 92
session: 2026-11-06-film-assistent
roles: [scout, advocatus, produktberater, grafiker]
date: 2026-11-06
---

# Synthese — Geführter Film-Assistent (ROADMAP #92), Kreativteam Akt 1

**Grundlagen:** `00-kickoff.md` (Alex-freigegeben, „Ja, freigeben", 2026-11-06), eigene Code-Prüfung (read-only), Rohoutputs unverändert in `scout.md`, `advocatus.md`, `produktberater.md`, `grafiker.md`. Hinweis: Die Vorlagen `FEATURE_BRIEFING.template.md` / `ALEX_ZUSAMMENFASSUNG.template.md` fehlen im Arbeitsverzeichnis; diese Synthese folgt der im Auftrag vorgegebenen Struktur. Das technische Briefing und die Alex-Zusammenfassung für den finalen Planreview werden nach dieser Freigabepunkt-1-Entscheidung erstellt.

---

## 1. Zusammenfassung

Der Etappenvorschlag des Kickoffs ist in der Richtung tragfähig, muss aber an zwei Stellen geändert werden (beides kritische Einwände von [advocatus], von [produktberater] bestätigt):

1. **Etappe 1 zerfällt in zwei Teile (1a/1b).** Sie bündelt sonst fünf unabhängige Achsen (Schrittrahmen, Editor-Extraktion, Drei-Orte-Konsolidierung, #91-Umzug, Ergebnis-Schritt) in einem Diff, der das 80-KB-Budget sprengt, nicht isoliert verifizierbar und auf dem NAS (kein automatischer Rollback) nur alles-oder-nichts rückrollbar wäre.
2. **Der Ähnliche-Titel-Hinweis (#91) wandert in Etappe 1 nicht in Schritt 1.** Der Scan hängt synchron an `/api/preview_process` und braucht den finalen Zielordner; ein hängendes SMB/NAS würde sonst den Einstieg des gesamten Assistenten blockieren. Empfehlung: Hinweis bleibt vorerst im Ergebnis-Schritt (Schritt 4); ein Schritt-1-Umzug ist erst mit dem Hintergrund-Index (#91 R12, nach Scan-Dauer-Messung) sinnvoll.

Der Wizard selbst wird als **Eigenbau** im bestehenden `mw-modal`-Muster gebaut (CSS-Klassen umschalten, neue `js/`-Module, keine Wizard-Bibliothek) — Empfehlung von [scout] und [grafiker], Begründung in ADR-03. Das NFO-Agent-Modal läuft **parallel weiter** (kein Big-Bang), der Assistent startet beim Inbox-Import-Pfad.

**Rechtsfrage Bildquellen (Freigabepunkt, unverändert offen):** [scout] hat die Terms von TMDb, Fanart.tv und TVDB am 2026-11-06 live geprüft. Kernergebnis: **Anzeigen** ist mit Attribution gut abgedeckt; **dauerhaftes Speichern auf dem NAS** ist eine Grauzone (TMDb-Site-Terms verbieten „archive", die private Ausnahme §4.A deckt es vermutlich; Fanart.tv CC-BY-3.0 mit Attribution; **TVDB-Bilder sind durch die API-Lizenz ausdrücklich nicht gedeckt**). [advocatus] schärft: Der Blocker heißt Speichern, nicht Anzeigen; Klärung muss schriftlich dokumentiert werden. Etappe 3 startet erst nach Alex' Rechtsfreigabe; der Schrittrahmen muss Schritt 3 überspringbar auslegen.

**Zeitliche Einordnung ([produktberater], strikt getrennt):** KI-Umsetzung je Etappe 1–3 Tage; der Engpass ist Alex: Review + Handtest auf dem NAS je Etappe 3–5 Tage, Freigabe-Wartezeit 1–2 Tage, Rechtsklärung Bildquellen 1–3 Wochen (blockiert nur Etappe 3). Gesamtbild bis Etappe 4 live: realistisch 7–12 Wochen Alex-Zeit.

## 1a. Code-Prüfung der Kickoff-Behauptungen (eigenes Ergebnis, read-only)

Alle Kernbehauptungen stimmen exakt (Zeilennummern verifiziert):

| Behauptung im Kickoff | Prüfung |
|---|---|
| `#context-movie` index.html ca. Z. 764: Suche, Optionen, Mini-NFO ohne FSK/Genre | ✅ Z. 764–872; Mini-NFO (802–818) nur Titel/Jahr/Plot; Verarbeitungsoptionen H.265/löschen/NAS/pCloud/Qualität/Zielordner liegen in diesem Panel (821–871) — beantwortet Kickoff-Frage 1 teilweise |
| `#preview-modal-overlay` ca. Z. 2550: Zielpfad, Renames, Untertitel, Junk, `#preview-similar-existing` | ✅ Z. 2550–2632, alle fünf Blöcke bestätigt |
| `#modal-nfo-agent` ca. Z. 3162: FSK/Genre, keine Schritt-Struktur | ✅ Z. 3162–3315; FSK (3275–3283), Genre (3270–3272); Suche bleibt sichtbar, ein Scroll-Bereich (3245), kein Wizard |
| `nfo_ui.js` nur 74 Zeilen, #50 nicht umgesetzt | ✅ exakt 74 Zeilen (`updateMwDataPanel`, `prepareSeriesPayload`) |
| #55 nicht umgesetzt, nur Einzel-Quellenlabels `nfo-agent-*-source` | ✅ fünf Labels (title/year/plot/genre/fsk), je ein Wert, kein Provider-Vergleich |
| #54 Teil 1 umgesetzt (`fetch_json_with_retry`) | ✅ `gui/mw_metadata.py` Z. 148 (Default timeout=15, attempts=3), flächig genutzt |
| #91-Basis: Scan im Vorschau-Endpoint `queue_api.py` | ✅ Z. 366–395 in `handle_api_preview_process`; Default-Ziel „/Filme" Z. 144–145 |
| app.js wird modularisiert | ✅ 9 ES-Importen aus `./js/*.js`, Cache-Buster `?v=105`; app.js umfasst 18.764 Zeilen |

**Korrekturen/Abweichungen:**
1. **Endpoint-Name:** Der Kickoff nennt „`/api/queue/preview`". Tatsächlich: **`/api/preview_process`** (Route `/preview-process` + Alias `/preview_process`, Blueprint-Prefix `/api`; Frontend-Aufruf app.js Z. 10348). Datei `gui/api/queue_api.py` stimmt.
2. **R8 bestätigt und relevant:** app.js Z. 10488 schreibt `data.destination` unescaped in `innerHTML`; zwei Zeilen weiter (10493–10494) wird korrekt `escapeHTML()` verwendet. Beim Umbau des Ergebnis-Schritts muss das mitgefixet werden (ADR-05).
3. **Kleine Randnotiz (nicht angefasst):** STAND.md nennt Cache-Buster `v=93`, real ist `v=105` — STAND ist an dieser Stelle veraltet (bereits im Kickoff als Bereinigungspunkt notiert). Commit-Angaben differieren (Kickoff main `86fdc26`, STAND `02926ed`); ohne Shell nicht verifizierbar — vor jedem Git-Vorschlag ist `git status --short --branch` von Alex nachzuliefern (Git-Preflight-Pflicht).

---

## 2. Executive-Recommendation

**Empfehlung:** Den Etappenschnitt in der revidierten Form freigeben: **1a** (Schrittrahmen + Film-Editor-Kern, NFO-Agent und Serien-Pfad unangetastet) → **1b** (Zusammenführung der drei Orte inkl. Ergebnis-Schritt, R8-Fix beim Umzug) → **2** (#55 Provider-Vergleich + #54 Teil 2) → **3** (#51 Artwork, erst nach schriftlicher Rechtsfreigabe) → **4** (#69 als Vorab-Queue). #91 bleibt bis auf Weiteres im Ergebnis-Schritt; ein Schritt-1-Umzug wird an #91 R12 (Index, nach Messung) gekoppelt. Wizard als Eigenbau im `mw-modal`-Muster, neue `js/`-Module, Schritt 3 von Anfang an überspringbar.

**Kurzbegründung:** Beide kritischen Einwände von [advocatus] (Etappe-1-Überladung, #91-Timing) sind am Code belegt und werden von [produktberater] in der Zerlegung unabhängig gestützt; die Teilung hält den Serien-Pfad (höchstes Regressionsrisiko, keine E2E-Abdeckung) in der ersten Etappe komplett unberührt und schafft zwei unabhängige Rollback-Punkte auf dem NAS.

**Trade-off / wichtigster Nachteil:** Ein geteilter Start liefert etwas später „den einen runden Ablauf" (1b zieht nach) und akzeptiert vorübergehend zwei Anlaufstellen (neuer Wizard für Import, alter NFO-Agent für Bestandsordner) — genau die Dreifach-UI, die #92 eigentlich auflöst, nur temporär neu sortiert. [advocatus] benennt diesen Nachteil selbst; er bleibt kleiner als das Regression-/Rollback-Risiko des Big-Bang.

**Alex-Entscheidung (Freigabepunkt 1):** Freigabe dieses revidierten Etappenschnitts — insbesondere (a) 1a/1b-Teilung, (b) #91 verbleibt in Schritt 4 (Abweichung vom Kickoff-Wunsch „Schritt 1"), (c) Form der E2E-Absicherung vor der Extraktion (Optionen in Abschnitt 5.3), (d) #69 als Vorab-Queue statt Dialog-Schleife. Die Rechtsfrage Bildquellen (Abschnitt 5.1) bleibt als eigener Freigabepunkt vor Etappe 3 reserviert und ist hier **nicht** mitentschieden.

---

## 3. ADR-Blöcke

### ADR-01: Etappe 1 zerfällt in 1a und 1b
- **Entscheidung:** Etappe 1 wird in zwei eigenständige, einzeln nutzbare und einzeln rückrollbare Etappen geteilt. **1a:** Wizard-Schrittrahmen + extrahierter Film-Haupt-NFO-Editor (Titel, Jahr, Plot, FSK, Genre) als neue `js/`-Module, angebunden an den Inbox-Import-Pfad; NFO-Agent, Episoden-/Serien-Mapping und Preview-Modal unangetastet; Schritt 3 (Artwork) als überspringbarer Platzhalter angelegt. **1b:** Zusammenführung der drei Orte — Import-Optionen und Preview-Inhalt werden zum Ergebnis-Schritt (4), der Film-Pfad des NFO-Agenten dockt an den extrahierten Editor an; R8-Fix (ADR-05) reist in 1b mit.
- **Alternativen:** (a) Kickoff-Plan unverändert als eine Etappe — von [advocatus] als [kritisch] verworfen: fünf Achsen in einem Diff, Budgetsprengung, Alles-oder-nichts-Rollback; (b) drei oder mehr Teilschnitte — vom Team nicht gefordert, erhöht Coordination-Overhead ohne zusätzlichen Schutz.
- **Begründung:** Diff-Budget ≤ 80 KB ist bei 18.764 Zeilen app.js nur mit Teilung haltbar (Diff zählt Löschung + Neubau, [advocatus] Pkt. 5); der Serien-Pfad bleibt in 1a komplett unberührt (höchstes Regressionsrisiko, Pkt. 1/2); NAS-Deploy ohne Auto-Rollback braucht kleine Rückroll-Einheiten (Pkt. 9). [produktberater] zerlegt unabhängig ebenfalls in 1a/1b (nutzensgetrieben), die Schnitte von [advocatus] und [produktberater] laufen dabei fast deckungsgleich (beide: 1a lässt den NFO-Agent unangetastet).
- **Konsequenzen:** Zwei Gate-A2-Ketten statt einer; vorübergehend zwei Anlaufstellen (temporäre Doppel-UI, von [advocatus] als Gegenargument benannt und akzeptiert); 1b kann nur nach stabil laufendem 1a starten.

### ADR-02: #91-Hinweis bleibt vorerst im Ergebnis-Schritt (Schritt 4)
- **Entscheidung:** Der Ähnliche-Titel-Hinweis wird in Etappe 1 nicht in Schritt 1 umgezogen, sondern läuft unverändert im `preview_process`-Pfad und erscheint im Ergebnis-Schritt. Ein Umzug nach Schritt 1 ist an #91 R12 (Hintergrund-Index) gekoppelt und setzt die vorherige Scan-Dauer-Messung voraus (Roadmap-Alternative, ohnehin offen).
- **Alternativen:** (a) eigener lighter Scan-Endpoint für Schritt 1 — verworfen ([advocatus] [kritisch]): hängendes SMB/NAS blockiert dann den Wizard-Einstieg, doppelte Scan-Pfade, Zielordner in Schritt 1 noch unbekannt; (b) R1/R12 in Etappe 1 vorziehen — verworfen: eigenes Feature, Budget-Killer, und ohne Messung wird ein nicht gemessener Flaschenhals optimiert; (c) wie Kickoff (Scan in Schritt 1 gegen Default-Ordner) — verworfen: Kombination doppelter Scan + evtl. falscher Ordner.
- **Begründung:** Der Scan ist synchron, läuft heute pro Vorschau doppelt und braucht `target_base` (queue_api.py 366–395, 144–145). Der Wizard-Einstieg darf nie von einem Netzwerk-Scan abhängen. UX-Nachteil (Duplikat-Info erst am Ende) ist für den Einzelfilm-Alltag akzeptabel; [produktberater] ergänzt: #91 ist bereits live und wirkt ohnehin.
- **Konsequenzen:** Schritt-1-Integration wird später mit R12 nachgeliefert (dann auch ohne doppelten Scan); [grafiker] hatte Fehler-UX „NAS hängt beim Scan in Schritt 1" entworfen — diese Szenario-Behandlung wandert mit dem Hinweis in Schritt 4 (Notiz an den späteren Briefing-Text).

### ADR-03: Wizard als Eigenbau im `mw-modal`-Muster, keine Bibliothek
- **Entscheidung:** Vier Schritt-Panels in einem Modal (max-width 960px, fixer Fortschrittskopf als Punktesystem mit Labels, Footer-Navigation), Umschalten per CSS-Klassen, Wizard-State als JS-Objekt; Code in neuen Modulen unter `gui/static/js/` (z. B. `film_wizard.js`), nicht als weitere app.js-Monolith-Edits; nur CSS-Variablen, keine neuen `inline-style-NN`-Klassen.
- **Alternativen:** Bibliothek SmartWizard (`@smart-wizard/core`, ~15 KB, Vanilla-Modus) — von [scout] selbst als Overkill für vier Schritte verworfen (eigene CSS-Klassen gegen Glasmorphismus-Design, Abhängigkeit ohne Gegenwert); Trivial-Muster „Tab-Modals" ohne Fortschrittskopf — widerspricht dem Ziel „Orientierung ohne Scroll-Wand".
- **Begründung:** Kein Parsing/Escaping/Netzwerk in der Rahmenschicht — triviale Helfer bleiben nach Hausregeln Eigenbau; das Projekt hat mit Onboarding (`.step-dot`, style.css ~2753) und `mw-modal` bereits zwei bewährte Muster, die [grafiker] direkt adaptiert; neue `js/`-Module sind zugleich die wirksamste Diff-Budget-Leine ([advocatus] Pkt. 5) und setzen die laufende Modularisierung fort. Keine neue Abhängigkeit nötig.
- **Konsequenzen:** Fokus-Management, ESC/Enter-Verhalten und Abbruch-Dialog werden explizit mitgebaut ([scout] Fallstrick-Tabelle, [grafiker] Abschnitt 5); Theme-Prüfliste über alle 5 Themes wird Akzeptanzkriterium je Etappe.

### ADR-04: Paralleler Betrieb — Assistent startet am Inbox-Import, NFO-Agent bleibt
- **Entscheidung:** Der Assistent ersetzt in 1a keinen der drei Orte vollständig. Einstieg ist „Film verarbeiten" in der Inbox. Das NFO-Agent-Modal (Health-Einstieg, Serien) läuft unverändert weiter und wird erst in 1b für den **Film**-Pfad an den extrahierten Editor angedockt; Ablösung/Umzug von Health-Funktionen entscheidet Alex später.
- **Alternativen:** Big-Bang (alle drei Orte in Etappe 1 verschmelzen) — von [produktberater] und [advocatus] verworfen (Serien-Regression, Rollback-Risiko); Assistent zuerst im NFO-Agent bauen — verworfen, weil der Alltagspfad (Import) damit später bedient würde.
- **Begründung:** Häufigster und schmerzfreier Pfad zuerst (Import), Bestands-Pflege (Health) bleibt stabil in bewährter UI; verhaltensneutrale Extraktion bleibt nachweisbar, weil der untouched-Referenzpfad weiterläuft.
- **Konsequenzen:** Übergangsphase mit zwei Film-Bearbeitungs-Einstiegen (1a → 1b); [grafiker] notiert die hartcodierten Farben des NFO-Agent-MODALS (rgba(30,30,45,0.95) etc.), die bei 1b in Variablen mitmigrieren (kleiner Aufwand).

### ADR-05: R8-XSS wird beim Umzug des Zielpfads mitgefixt, nicht verschleppt
- **Entscheidung:** Bei 1b wird `data.destination` im Ergebnis-Schritt mit dem vorhandenen `escapeHTML()`-Muster gerendert (app.js 10493–10494); der unescaped Code (10488) wandert nicht 1:1.
- **Alternativen:** Separater Mini-Fix als eigene Kette vor 1b — möglich, aber extra Gate-A2-Lauf für drei Zeilen; Mitnehmen wie gehabt — verworfen (bekannten XSS in neuen Code tragen).
- **Begründung:** Die Zeile wird ohnehin angefasst; Ein-Nutzer-App relativiert, aber `destination` enthält NAS-/Import-Daten, die nicht vollständig nutzerkontrolliert sind ([advocatus] Pkt. 6).
- **Konsequenzen:** Der ROADMAP-Punkt #91 R8 (und die offene Alternative #67+R8) kann nach 1b als erledigt bzw. erledigt-teilweise geführt werden; Rest von #67 bleibt unberührt.

### ADR-06: Bildquellen-Korridor und Rechts-Gate vor Etappe 3
- **Entscheidung (Prozess-Teil, jetzt): ** Etappe 3 (Artwork) startet erst nach schriftlich dokumentierter Rechtsfreigabe von Alex; der Wizard-Schrittrahmen (1a) legt Schritt 3 von Anfang an als überspringbar an. TVDB-Bilder werden unabhängig von der Freigabe nicht als Artwork-Quelle angeboten.
- **Empfehlung (Inhalts-Teil, wartet auf Alex):** Option B aus der Scout-Tabelle — TMDb als Primärquelle (Poster/Backdrops), Fanart.tv als Ergänzung (Logos/Clearart/Extra-Fanart, CC-BY-3.0-Attribution); OFDb-Cover zurückstellen (Scraping, keine API); Attribution beider Quellen in der App; TMDb-Cache-Limit 6 Monate beachten.
- **Alternativen:** A (nur TMDb, geringste Rechtsunsicherheit), C (+OFDb, rechtlich grau), D (nur manuell, praktisch kein Nutzen) — Details in `scout.md` Abschnitt 5.
- **Begründung:** [scout] verifiziert: Anzeige ok mit Attribution; **dauerhaftes Speichern** bleibt Grauzone (TMDb-Site-Terms §3.B verbietet „archive", Ausnahme §4.A privat; Fanart.tv ohne explizites Download-Verbot, Verantwortung beim Nutzer; TVDB-ToS schließen Bildnutzung ausdrücklich aus). [advocatus]: Kernrisiko ist das Speichern, Klärung nur schriftlich.
- **Konsequenzen:** Diese Synthese **entscheidet die Rechtsfrage nicht** — sie ist als Freigabepunkt an Alex formuliert (Abschnitt 5.1). Bis zur Klärung bleibt das Zielbild „Emby-ähnlich" ohne Artwork-Galerie vollständig funktionsfähig.

---

## 4. Etappenzuschnitt mit Diff-Schätzung

Richtwert ≤ 80 KB je Etappe. **Schätzgrundlage und Unsicherheit:** Byte-Größen der Dateien sind ohne Shell nicht gemessen (app.js ~18.764 Zeilen ≈ 750–900 KB, index.html 3.317 Zeilen mit langen SVG-Zeilen ≈ 350–450 KB, grobe Annahme ~40–60 Bytes/Zeile); die Werte unten sind Planungsschätzungen, keine Messwerte — die exakte Diff-Kante fällt je Gate-A2-Lauf ohnehin neu an.

| Etappe | Inhalt | Diff-Schätzung | Budget |
|---|---|---|---|
| **1a** Schrittrahmen + Film-Editor-Kern | Neues Modal + `js/film_wizard.js` + `js/nfo_editor.js` (Extraktion Titel/Jahr/Plot/FSK/Genre für den Film-Import, reine Verschiebung, keine Signaturänderungen), CSS `mw-wizard-*`, Draht in den Inbox-Import; Schritte 3/4 als Platzhalter; Frontend-Tests. NFO-Agent/Serien/Preview **unangetastet**. | ~55–80 KB | **knapp, aber haltbar** — bei Überschreitung zuerst Schritt-2-Feldumfang (Originaltitel, Studios) zurückstellen |
| **1b** Drei-Orte-Zusammenführung + Ergebnis | Import-Optionen (H.265, Zielordner, pCloud …) und Preview-Inhalt (Renames/Subs/Junk/#91-Box) werden in den Ergebnis-Schritt überführt; NFO-Agent-Filmpfad dockt an; app.js-Altblöcke entfallen; R8-Fix; Testanpassungen. | ~60–110 KB | **Risiko > 80 KB** — wenn überschreitend: in 1b-i (Ergebnis-Schritt) und 1b-ii (NFO-Agent-Anbindung) nachziehen; Regel „Verschieben ohne Refactoring nebenbei" ist hart |
| **2** #55 Vergleich + #54 Teil 2 | API liefert Felder je Provider statt Merge; Badge-UI ([grafiker] Feld-Karten); Retry-Helfer HTML/Binär + Backoff-Rahmenwerk ([advocatus] Pkt. 7); Tests inkl. Provider-Fehler-UX. | ~40–70 KB | ok |
| **3** #51 Artwork | Bildquellen-Abruf + Grid-UI + Download mit Retry/Integritätsprüfung + Attribution + CSP-Prüfung. **Nur nach Alex-Rechtsfreigabe.** | ~35–60 KB | ok |
| **4** #69 Reihen | Vorab-Queue (Mehrfachauswahl #65-Kästen, „als Filme einreihen"), Fortschrittskopf „Film X von N" im bestehenden Rahmen. | ~15–30 KB | ok |

Reihenfolge-Bestätigung durch [produktberater]: „erst Vergleich ohne Wizard" und „erst Artwork" sind aus Nutzensicht falsch (Rahmen nötig; Poster ohne Metadaten wertlos) — der Schnitt 1a→1b→2→3→4 bleibt.

## 4a. Beantwortung der sieben Kickoff-Fragen

1. **Drei Orte → ein Ablauf / #50-Schnittlinie / Verarbeitungsoptionen:** Schnitt an der Kopplung (ADR-01/04): 1a extrahiert nur den Film-Editor in `js/`-Module (ES-Importe statt window-Hacks, reine Verschiebung), 1b führt zusammen. Verarbeitungsoptionen liegen heute im `#context-movie`-Panel (index.html 821–871) und wandern in Etappe 1b in den Ergebnis-Schritt 4.
2. **Zerfällt Etappe 1?** **Ja** — 1a/1b wie oben; Begründung und Alternativen in ADR-01.
3. **#91-Timing:** bleibt in Schritt 4; Schritt-1-Umzug erst mit R12-Index nach Messung;ADR-02.
4. **UI ohne Scroll-Wand:** Konzept von [grafiker] (960px-Modal, Punkt-Fortschrittskopf mit Labels, Feld-Karten statt Tabelle, Poster-Grid 2D, zusammenklappbare Ergebnis-Gruppen, Theme-Prüfliste über alle 5 Themes); Details `grafiker.md`, Design-Fragen 1–5 in Abschnitt 5.5.
5. **Artwork-Quellen/Rechtliches:** recherchiert und optionsiert ([scout]), **nicht entschieden** — Freigabepunkt an Alex (Abschnitt 5.1), Gate vor Etappe 3 (ADR-06).
6. **Einzelfilm vs. Reihe:** Empfehlung Vorab-Queue statt Dialog-Schleife ([produktberater]); Rate-Limit-Risiko ist Fehlerhäufung, nicht Kontingent — Backoff/Teil-Erfolg vor Etappe 2/4 ([advocatus] Pkt. 4); endgültige Form + Import-Häufigkeit entscheidet Alex (5.4).
7. **Zusammenspiel NFO-Agent/Inbox:** ADR-04 — Inbox zuerst, NFO-Agent parallel, Migration nach Stabilität.

---

## 5. Offene Entscheidungen für Alex (gesammelt, nicht einzeln gestellt)

### 5.1 Freigabepunkt (Rechts-/Sicherheitsfrage): Bildquellen-Nutzungsbedingungen — **muss vor Etappe 3 von Alex entschieden werden**
- **Was zu entscheiden ist:** Darf der Assistent Poster/Fanart **dauerhaft auf dem NAS speichern** (nicht nur anzeigen), und welche Quellen sind dafür freigegeben?
- **Rechercheergebnis ([scout], Terms am 2026-11-06 live geprüft; Quellen in scout.md):** Anzeige mit Attribution bei TMDb klar ok; Speichern bei TMDb Grauzone (Site-Terms verbieten „archive", private Ausnahme vermutlich greifend); Fanart.tv CC-BY-3.0 (Attribution Pflicht, kein explizites Download-Verbot, Verantwortung beim Nutzer); **TVDB: Bildnutzung durch API-Lizenz ausdrücklich ausgeschlossen** — daher kein Kandidat.
- **Empfehlung:** Option B — TMDb primär + Fanart.tv ergänzend, TVDB-Bilder ausschließen, OFDb-Cover zurückstellen; schriftliche Festhaltung der Freigabe im Briefing ([advocatus] verlangt zu Recht „schriftlich dokumentiert" statt informell).
- **Trade-off:** Je breiter die Quellen, desto besser die Heimkino-Optik — desto mehr Attribution-Pflichten und Rechts-Grauzone beim Speichern. Nur-TMDb (Option A) wäre die minimal riskante Variante.
- **Alex-Entscheidung:** Speichern ja/nein? Quellenkombination A/B/C/D? (Keine Eile: blockiert nur Etappe 3, nicht 1a/1b/2.)

### 5.2 #91-Platzierung im Wizard (Abweichung vom Kickoff)
- **Empfehlung:** Hinweis vorerst im Ergebnis-Schritt (4) belassen; Schritt-1-Umzug erst mit Hintergrund-Index (#91 R12) nach Scan-Dauer-Messung.
- **Begründung:** [advocatus] [kritisch]: hängendes NAS würde sonst den Wizard-Einstieg blockieren; Zielordner ist in Schritt 1 noch nicht final.
- **Trade-off:** Duplikat-Warnung kommt später, als im Kickoff gewünscht.
- **Alex-Entscheidung:** dieser Abweichung zustimmen?

### 5.3 Regressionsschutz vor der Editor-Extraktion (neue Möglichkeit, Klasse B falls Tool)
- **Empfehlung:** Variante „manuell": vor 1a einen dokumentierten Handtest-Parcours (je ein Film-Durchlauf + ein Serien-Durchlauf gegen den unveränderten Stand) abnehmen und nach 1a/1b wiederholen — ohne neues Tool.
- **Begründung:** [advocatus] [wichtig]: ohne Referenz ist „verhaltensneutral" nur eine Behauptung; es existiert kein E2E-Band. Ein Playwright-Grundgerüst wäre der belastbarere Beleg, ist aber eine neue Test-Infrastruktur (Installation/Dependency = Klasse B, eigener Pflegeaufwand) in einem Projekt, das Frontend-Tests bisher über jsdom macht.
- **Optionen:** (a) Playwright-Minimal-E2E (2 Szenarien) — belastbarster Nachweis, neue Abhängigkeit + Setup; (b) dokumentierter Handtest-Parcours (Empfehlung) — null neue Abhängigkeit, weniger Beweiskraft; (c) nur jsdom-Unit-Tests — fängt Verdrahtungsfehler nicht ab.
- **Alex-Entscheidung:** a oder b?

### 5.4 Form der Reihen-Verarbeitung (#69) und Import-Häufigkeit
- **Empfehlung:** Vorab-Queue (Mehrfachauswahl in der Inbox, Assistent arbeitet die Liste Film für Film ab), keine Schleife, die nach jedem Film zu Schritt 1 zurückspringt.
- **Begründung:** [produktberater]: übersichtlicher, abbruchfest, testbarer; Fortschrittskopf „Film X von N" passt in [grafiker]s Rahmen ohnehin.
- **Trade-off:** Weniger „geführt"-Gefühl pro Reihen-Film; wer jeden Film einzeln starten will, kann das weiterhin.
- **Alex-Entscheidung:** Form bestätigen — und die Datumsfrage beantworten: Wie oft kommen Reihen am Stück vor (bestimmt mit, ob #69 wirklich die letzte Etappe bleibt)?

### 5.5 Design-Einzelentscheidungen ([grafiker], je mit seiner Empfehlung — können gebündelt per „Empfehlungen ok" entschieden werden)
1. Fortschrittskopf: Punkte mit Labels (Empfehlung) vs. Balken.
2. Artwork: Tab-Wechsel Poster/Fanart (Empfehlung) vs. beide Raster sichtbar.
3. „Überspringen"-Button in Schritt 2/3: ja (Empfehlung) vs. Pflichtauswahl.
4. Provider-Fehler: Inline-Badge-Fehler + Banner (Empfehlung) vs. nur Banner.
5. Abbruch-Dialog: nur bei geänderten Eingaben (Empfehlung) vs. immer.

### 5.6 Formales
- **Git-Zustand fehlt:** Für diese Doku-Archivierung und jeden späteren Commit/PR wird vor Git-Schreiboperationen `git status --short --branch` von Alex benötigt (Git-Preflight; harter main-Stop bei `main`). Die Kickoff-Commit-Angabe `86fdc26` konnte ohne Shell nicht gegen STAND (`02926ed`) aufgelöst werden.
- **Nach Freigabepunkt 1** folgt Akt 2 der Kette: technisches Briefing/ADR nach Kit-Vorlage (Vorlagen-Dateien fehlen im Arbeitsverzeichnis — Struktur wird dem bestehenden `FEATURE_BRIEFING.md` / früheren Session-Artefakten nachgebaut) + Alex-Zusammenfassung + plan-reviewer-Check, danach je Etappe ein Gate-A2-Lauf (Start = Klasse B).

---

## 6. Dissens- und Bedenkendokumentation (Pflicht)

- **[advocatus] VERDICT: REVISE** gegen den Kickoff-Etappenschnitt (nicht gegen die Richtung). Die beiden [kritisch]-Einwände sind in ADR-01 und ADR-02 aufgenommen; die [wichtig]-Punkte 3–7 sind als Entscheidungen 5.3, ADR-05, ADR-06, Abschnitt 4 (Backoff-Rahmenwerk vor Etappe 2) und 5.1 (schriftliche Rechtsklärung) verarbeitet. Eingestanden wird der von [advocatus] selbst benannte Nachteil der Teilung: temporäre Doppel-UI (alter NFO-Agent + neuer Wizard) bis 1b.
- **[produktberater] gegen den Kickoff-Umfang von #55:** „Vergleich" sei MVP-verzichtbar, Bearbeiten reiche. Nicht übernommen als Streichung, sondern als Reihenfolge-Härtung: #55 bleibt Etappe 2 (nach dem stabilen Editor), weil die reale Lücke (TMDb ohne FSK, OFDb ohne Plot — ROADMAP #55) den Vergleich braucht, aber nicht für den ersten Alltagsgewinn. Dokumentiert als zurückgestelltes Risiko, falls Alex' Import-Alltag doch „immer nur ein Standard-Provider" ist (Entscheidung 5.4/5.6 berührt das).
- **[scout] vs. [advocatus] bei den Bildquellen:** [scout] bewertet privates Speichern als „vermutlich gedeckte Grauzone"; [advocatus] verlangt es als harten, schriftlich zu dokumentierenden Blocker. Synthese folgt der schärferen Linie ([advocatus]) — die weichere Einschätzung bleibt als Begründungsmaterial in scout.md erhalten.
- **[grafiker] nahm #91-Scan in Schritt 1 an** (Fehler-UX „NAS hängt beim Scan" in seinem Abschnitt 5) — Kollidiert mit ADR-02; Szenario-Behandlung wird mit dem Hinweis in Schritt 4 weitergetragen (notiert in ADR-02 Konsequenzen).
- **Bibliotheks-Optionen verworfen mit Begründung:** SmartWizard ([scout] selbst: Overkill für vier Schritte — Details ADR-03); Playwright nicht automatisch eingeführt, sondern als Entscheidung 5.3 vorgelegt (neue Abhängigkeit nur als Optionen-Tabelle, Hausregel Klasse B).
- **Kein Konsenszwang:** Die drei Rollen waren sich nur in der 1a/1b-Teilung und dem Artwork-Rechts-Gate einvernehmlich einig; alle übrigen Punkte sind Empfehlungen mit Gegenstimme oder Vorbehalt und bleiben Alex-Vorlage.

## 7. Quellen, Referenzen und Lizenzen

- **Kein Third-Party-Code übernommen.** Alle Muster (Emby Identify, Stash Tagger, Picard Farbcode, Kodi Choose Art, TMM, Stripe/Punkt-Indikator) sind Patterns/Inspiration, keine Kopiervorlagen; Details und URLs in `scout.md` Abschnitt 6.
- **Künftige Assets (bei Etappe-3-Freigabe zu dokumentieren):** TMDb-Logo + Attributionstext („This product uses the TMDB API but is not endorsed or certified by TMDB."), Fanart.tv-Hinweis (CC-BY-3.0). Icons: Lucide ist im Projekt bereits im Einsatz (bestehende SVGs in index.html) — keine neue Lizenzlast.
- **Rechtsstand:** Terms-Zitate von 2026-11-06 in scout.md; keine Rechtsberatung, Entscheidung liegt bei Alex (5.1).

## 8. Ergebnis dieser Session (Akt 1)

Rohoutputs und Synthese liegen unter `docs/sessions/2026-11-06-film-assistent/`. Kein Produktionscode geändert, keine Git-Schreiboperation. **Die Kette stoppt hier an Freigabepunkt 1:** Alex entscheidet Abschnitt 2 (Etappenschnitt) und Abschnitt 5 (offene Entscheidungen); erst danach folgt Akt 2 (technisches Briefing + Alex-Zusammenfassung + plan-reviewer) und je Etappe die Gate-A2-Kette.
