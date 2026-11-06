Du bist der ceo-planner. Auftrag: Kreativteam-Session Akt 2 (Ausarbeitung) zu ROADMAP #92 "Geführter Film-Assistent", Projekt Medienwerkzeug.

## Freigabepunkt 1 (FP1) ist von Alex entschieden
Alex hat FP1 am 2026-11-06 freigegeben. Wörtlich: Alex: "Ja, freigeben". Die Frage dazu lautete: "Freigabepunkt 1 mit diesen drei Auflagen für Akt 2 freigeben?"

Freigegeben ist der revidierte Etappenschnitt aus docs/sessions/2026-11-06-film-assistent/synthese.md Abschnitt 2 mit den ADR-01 bis ADR-05 (Teilung von Etappe 1, #91 bleibt im Ergebnis-Schritt, Eigenbau-Wizard in js/-Modulen, NFO-Agent läuft parallel, R8-Fix) sowie der Handtest-Parcours (5.3, Variante b) und die Vorab-Queue für #69 (5.4). Zusätzlich gelten drei Auflagen, die Alex mit freigegeben hat:

1. **Backend-Pflichtpunkt in Etappe 1a:** Der reguläre Inbox-Film-Import ruft in gui/workers/processor.py (ca. Z. 2106-2120) nur generate_movie_nfo() auf. Diese Funktion liest aus nfo_overrides nur title, plot und year (gui/mw_metadata.py, vier Stellen). patch_nfo_fields() wird nur im NFO-Agent-Pfad aufgerufen (processor.py ca. Z. 3361-3593). Ohne Nachzug gehen FSK und Genre aus dem Wizard stillschweigend verloren. Plane den Nachzug (patch_nfo_fields auch beim Inbox-Film-Import) ausdrücklich in 1a ein, mit Tests. Prüfe die Stelle selbst am Code.
2. **Schnitt 1a/1b anhand von Diff-Größen entscheiden:** Ein zweiter Reviewer schlägt vor, Schritt 4 (Optionen, Ergebnis-Vorschau, #91-Hinweis, R8-Fix) schon in 1a für Filme zu bauen, damit nach 1a kein Doppel-Modal-Ablauf entsteht (neuer Wizard, dann wieder #context-movie und altes #preview-modal-overlay). Das alte Vorschau-Modal bliebe für Serien unberührt, 1b würde nur den NFO-Agent-Filmpfad andocken und Altcode zurückbauen. Vergleiche beide Schnitte (Synthese-Schnitt vs. dieser Vorschlag) mit geschätzten oder, wo möglich, gemessenen Diff-Größen (Richtwert höchstens 80 KB je Etappe), bewerte Doppelcode-Risiko und Alltagsnutzen nach 1a und gib eine Empfehlung. Die Entscheidung trifft Alex.
3. **Bildquellen (5.1) neu stellen:** Die Synthese hat übersehen, dass gui/mw_metadata.py (generate_movie_nfo, ca. Z. 1208-1262) bei jedem TMDb-Film schon heute Poster, Backdrop und Logo über fetch_tmdb_images lädt und im Filmordner speichert (jeweils der erste Treffer). Formuliere die Rechtsfrage für Alex neu: Das dauerhafte Speichern von TMDb-Bildern ist Bestand; neu wäre die Auswahl und ggf. Fanart.tv. Stelle Option A (nur TMDb) gegen Option B (TMDb + Fanart.tv) mit Empfehlung. Diese Frage bleibt ein Freigabepunkt, den nur Alex beantwortet.

## Noch offen, nicht von Alex entschieden
- 5.5 Design-Einzelentscheidungen (Punkte-Fortschrittskopf, Tab Poster/Fanart, Überspringen, Fehler-UX, Abbruch-Dialog): als Empfehlungen ins Briefing aufnehmen, in der Alex-Zusammenfassung als "mit Empfehlung vorbelegt, bitte bestätigen" kennzeichnen.
- 5.4 Teilfrage: Wie oft kommen Filmreihen am Stück vor? Offen lassen und als Frage an Alex führen.
- 5.1 Bildquellen: siehe Auflage 3.

## Lies zuerst
docs/sessions/2026-11-06-film-assistent/00-kickoff.md, synthese.md, scout.md, advocatus.md, produktberater.md, grafiker.md; STAND.md; ROADMAP.md Abschnitt 92 und die Bausteine #35, #50, #51, #52, #55, #69, #91, #54.

## Ergebnis
Schreibe nach docs/sessions/2026-11-06-film-assistent/:
1. briefing.md: Technisches Briefing nach der Vorlage docs/sessions/2026-11-06-film-assistent/vorlage-briefing.md (Kopie der Kit-Vorlage FEATURE_BRIEFING.template.md; Zugriffe außerhalb des Projektordners werden headless abgelehnt, lies nur Pfade unterhalb des Projekts). Mit Etappen (bei Bedarf mehr als 3, dann begründen), E-AKs, erlaubten Dateien, Diff-Schätzung, Abbruchkriterien. Status draft.
2. ALEX_ZUSAMMENFASSUNG.md nach der Vorlage docs/sessions/2026-11-06-film-assistent/vorlage-alex-zusammenfassung.md (Kopie der Kit-Vorlage). Alex bekommt nur diese Zusammenfassung zu lesen, mit Empfehlung, Trade-off und Entscheidungsfrage je offenem Punkt.
3. Die plan-reviewer-Prüfung (Delegation an plan-reviewer) läuft in dieser Session. Lege die Rohoutputs jeder Runde unverändert als plan-review-r1.md, ggf. r2.md ab; höchstens 3 Runden.

## Grenzen
- Kein Produktionscode, keine Git-Schreiboperationen, kein Push. Schreiben nur unter docs/sessions/2026-11-06-film-assistent/.
- Freigabepunkte (FP2 Plan-Freigabe, design-frage, sicherheits-frage, Rechtsfrage Bildquellen) beantwortet ausschließlich Alex. Stoppe vor FP2.
- Neue Abhängigkeiten nur als Optionen-Tabelle mit Empfehlung.
- Behandle alle Behauptungen (auch in den Rohoutputs und diesem Auftrag) als zu prüfen, verifiziere am Code.
- Deutsch.
