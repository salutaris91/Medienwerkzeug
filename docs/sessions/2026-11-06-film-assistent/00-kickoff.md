---
kind: plan-kickoff
status: approved-for-planning
approved_by: alex
approved_on: 2026-11-06
approval_quote: "Ja, freigeben"
source: ROADMAP.md #92
---

# Kickoff Planung — Geführter Film-Assistent (ROADMAP #92)

**Ziel:** Architektur- und Etappenplan für den „Geführten Film-Assistenten“ (ROADMAP #92), direkt am Code geprüft. Kein Produktionscode in der Planungsphase.

Pro Film vier klar getrennte Schritte ohne langes Scrollen:
1. **Quelle wählen** (Suche, Provider/ID, Ähnliche-Titel-Hinweis #91)
2. **Metadaten vergleichen und bearbeiten** (Titel, Jahr, Plot, FSK, Genre; Multi-Provider-Badges #55)
3. **Artwork wählen** (Poster, Fanart; Auswahl/Abwahl #51)
4. **Ergebnis und Datei-Aktionen bestätigen** (Zielpfad, Umbenennung, Untertitel, Junk, Konvertierungs-/Zieloptionen)

Bei mehreren Filmen (#69) läuft derselbe Assistent als Schleife mit Fortschrittsanzeige („Film X von N“).

## Ist-Stand im Code (main `86fdc26`, am 2026-11-06 verifiziert; Zeilennummern im Lauf neu prüfen)

- **Drei getrennte UI-Stellen für Filme:**
  - `#context-movie` (`gui/static/index.html`, ca. Z. 764): Suche, Optionen, Mini-NFO ohne FSK/Genre.
  - `#preview-modal-overlay` (ca. Z. 2550): Zielpfad, Renames, Untertitel, Junk, Ähnliche-Titel-Hinweis (`#preview-similar-existing`).
  - `#modal-nfo-agent` (ca. Z. 3162): Nachpflege mit FSK/Genre, ohne Schritt-Struktur.
- **Nicht umgesetzt:** #50 (gemeinsamer Editor; `gui/static/js/nfo_ui.js` hat nur 74 Zeilen), #52 (Wizard-Schritte), #55 (Provider-Badges; heute nur Einzel-Quellenlabels `nfo-agent-*-source`), #51 Artwork-Teil, #54 Teil 2 (Retry für Binär-Downloads und HTML-Abrufe wie OFDb).
- **Umgesetzt:** #51 FSK/Genre (nur im NFO-Agent), #54 Teil 1 (`fetch_json_with_retry` in `gui/mw_metadata.py`), #91 Basis (Scan im Vorschau-Endpoint, `gui/api/queue_api.py`).

## Vorgeschlagener Etappenschnitt (vom Team zu schärfen)

1. #52 Schrittrahmen + #50 Film-Kern (Haupt-NFO-Editor inkl. FSK/Genre, #91 in Schritt 1, Ergebnis in Schritt 4). Serien-Episoden-Mapping aus #50 ist ausdrücklich nicht Teil von Etappe 1.
2. #55 Vergleich/Badges + #54 Teil 2.
3. #51 Artwork (erst nach Klärung der Nutzungsbedingungen von TMDb-Bildern und Fanart.tv).
4. #69 Filmreihen-Schleife als Hülle um den fertigen Einzelfilm-Assistenten.

Jede Etappe muss einzeln im Alltag nutzbar sein, auch für einen einzelnen Film.

## Fragen, die der Plan am Code beantworten muss

1. Wie werden die drei Film-Orte zu einem Ablauf zusammengeführt? Wo liegt die #50-Schnittlinie, ohne das Serien-Mapping zu brechen (`app.js` wird gerade modularisiert, Schnitt an Kopplung, keine window-Hacks, verhaltensneutral)? Wo liegen Verarbeitungsoptionen (H.265, Zielordner NAS/Cloud)?
2. **Zerfällt Etappe 1 in zwei Teile?** Etappe 1 bündelt Schrittrahmen, Editor-Extraktion und Zusammenführung von drei Orten und ist groß. Vorschlag zur Prüfung: erst Rahmen + Editor-Kern für den Film-Import, dann der NFO-Agent als dritter Ort. Diff-Budget je Etappe beachten (Richtwert ≤ 80 KB).
3. **Timing von #91 in Schritt 1:** Der Scan hängt heute an `/api/queue/preview` und braucht den NAS-Zielordner. Wann und wie wird er in Schritt 1/2 ausgelöst? Muss #91 R1 (Doppel-Scan, Zeitlimit) vorgezogen werden?
4. UI/UX ohne Scroll-Wand: kompaktes Schritt-Layout im bestehenden Theme-System (Orientierung an Emby für Artwork/Metadaten, alle Themes visuell prüfen).
5. **Artwork-Quellen und Rechtliches (#51):** Nutzungsbedingungen TMDb-Images und Fanart.tv. Das ist ein expliziter Freigabepunkt für Alex vor Etappe 3.
6. Einzelfilm vs. Filmreihe (#69): gleicher Dialog mit Schleife oder Vorab-Queue? Umgang mit N Metadaten-/Artwork-Abrufen und Rate-Limits (#54).
7. Zusammenspiel mit NFO-Agent (Health-Einstieg) und Inbox-Ablauf.

## Ergebnisformat

Zusammenfassung, 3–7 ADR-Blöcke (Entscheidung / Alternativen / Begründung / Konsequenzen), offene Entscheidungen für Alex. Quellen, Lizenzen und Third-Party-Hinweise gemäß Briefing-Vorlage. Freigabepunkte (Plan-Freigabe, Rechtsfragen zu Bildquellen) beantwortet ausschließlich Alex.

## Bekannte Randpunkte (nicht Teil des Auftrags)

- Veraltete Blöcke im „Älteren Stand“ der `STAND.md` (Abnahme #54 Teil 1, P1/P2 Escape-Fix) beim nächsten Stand-Update bereinigen.
- Alternativen aus der STAND.md bleiben offen: #67 + R8, #81, Scan-Dauer messen (R1/R12).
