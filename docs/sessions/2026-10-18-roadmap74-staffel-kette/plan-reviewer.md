# plan-reviewer — Ergebnis der formellen Planprüfung zu `briefing.md`

Session: Kreativteam 2026-10-18, Feature-Kette #74 (E1) + #80-Rest (E2) + #83 (E3), Akt 2.
Prüfer: `plan-reviewer` (Subagent, Inner-Loop). Geprüftes Artefakt: `docs/sessions/2026-10-18-roadmap74-staffel-kette/briefing.md`.
Runden: 2 von maximal 3. Endergebnis: **VERDICT: APPROVE** (Runde 2).

## Runde 1 — VERDICT: REVISE (4 Einwände)

Der Prüfer verifizierte eigenständig gegen Code, Kickoff und #75-Präzedenz: Struktur-/Formvertrag vollständig (Frontmatter `status: draft` mit Platzhaltern, keine erfundene Freigabe; 12 Abschnitte, Etappen direkt nach 3; AK0 + Etappen-Präfixe; Mindestliste des Akt-2-Auftrags vollständig abgedeckt; `test_cmd` byte-identisch zur Referenz 2026-10-16 :194, ohne eigenes `timeout`, `test_timeout_s` 600; Rohausgaben-Liste #75-konform mit Etappen-Rot-Probe; Ampel nur als Verweis auf Kit-Betriebsanleitung §9; FP1- und Plan-Go-Zitate wörtlich korrekt). Code-Treue: alle ~60 gestichprobenen Zeilenangaben stimmen (u. a. Banner-Handler :12834–12857, Gruppenzeile :13271–13379, searchSeries-Guards :3114/:3211 + Registry :3085–3088, F2-Labeltest :1407–1448, Sofort-Stubs :536/:644/:557, validateSelector :55–93, Einzelstaffel-Banner-Fixtures bestätigt, 10 Cache-Buster-Stellen bestätigt, sechs searchSeries-Aufrufer B7-korrigiert). Technische Tragfähigkeit bestätigt (E1-AK6-Nachweis ohne Binding-Überschreiben; advocatus-Gegenmaßnahmen widerspruchsfrei eingearbeitet; Seq-Guard schließt reale String-Guard-Lücke; Delay-Schwelle ≥ 30000 verifiziert — alle betroffenen app.js-Timer liegen darunter).

Einwände Runde 1:

1. **[wichtig]** Akt-2-Subagenten-Rohoutputs fehlen im Session-Ordner; Dissens-Zitate ([advocatus] F1.1–F9.3, [produktberater], [grafiker]) ohne Beleg und ohne IOU-Vermerk (Präzedenz #75 Abschnitt 6) — Gegenprüfung der Dissens-Dokumentation unmöglich.
2. **[wichtig]** Toter Verweis: Abschnitt 8 behandelte `ALEX_ZUSAMMENFASSUNG.md` als existent; Datei fehlt (sie ist Alex' FP2-Grundlage, Kickoff :101).
3. **[wichtig]** ADR-K-2-Konsequenz „jeden Tabellen-Text mindestens einmal exakt" — der Banner-Hinweis (FP2-Wortlaut, U+2013) wurde von keinem AK exakt assertiert.
4. **[kosmetisch]** E3-AK1 implizierte, aber nannte nicht, dass der fetch-Spy bei `signal`-Abort mit `AbortError` rejecten muss.

Nicht geprüft (Werkzeuggrenzen): Git-Zustand (vom Kickoff übernommen), `test_cmd`-Ausführbarkeit (kein bash), Kit-Betriebsanleitung §9 (außerhalb des Worktrees — nur Verweis-Korrektheit), Übereinstimmung der Rollenzitate mit Originalen (→ Einwand 1), ALEX_ZUSAMMENFASSUNG-Inhalt (→ Einwand 2).

## Einarbeitung (Orchestrator, zwischen Runde 1 und 2)

1. IOU-Absatz „Beleg-IOU (Präzedenz #75, Abschnitt 6)" an den Anfang von Abschnitt 6 gesetzt: mechanische Archivierung der Rohoutputs durch Claude Code per `opencode export` in den Session-Ordner vor FP2; Begründung: Akt-2-Auftrag verbietet dem Orchestrator das Abschreiben (Schutz vor Filterung durch den Zitierenden).
2. Abschnitt 8 auf geplante Reihenfolge umgestellt: Zusammenfassung wird nach APPROVE und VOR FP2 erstellt.
3. E1-AK6 zu „Banner-Split + Hinweiszeile" erweitert: exakte Assertion des Hinweis-Wortlauts bei ≥ 2 Staffeln, Fehlen bei genau 1 Staffel.
4. fetch-Spy-Abort-Semantik in E3-AK1 UND in die Erfahrungswerte des Worker-Auftrags aufgenommen.

## Runde 2 — VERDICT: APPROVE

Alle vier Einarbeitungen eigenständig verifiziert: IOU genügt dem #75-Mechanismus (Verantwortlicher, Mechanismus, Zielort, Frist, Stichprobenrecht benannt) und ist formell tragfähig; Verweis-Klärung widerspruchsfrei zur Kickoff-Aufzählung (:101 ist Artefakt-Liste, keine zeitliche Kette); alle fünf UI-Text-Tabellentexte jetzt exakt AK-gedeckt (Staffel-Label + „Alle starten" → E1-AK1; Hinweis → E1-AK6; E2-Meldung → E2-AK1; E3-Meldung → E3-AK1), Etappen-Zuordnung E1 konsistent; fetch-Spy-Formulierung widerspruchsfrei zu ADR-K-6 (Spy liefert genau den `AbortError`, den der bestehende catch-Zweig :3210 behandelt). Edits ohne neue Fehler: Frontmatter byte-identisch, AK-Nummerierung intakt, Abschnittsreihenfolge unverändert.

Verbleibende Vor-FP2-Pflichten (im Briefing verankert, keine Einwände): (1) `opencode export`-Archivierung der Akt-2-Rollenantworten tatsächlich vor FP2 durchführen (sonst läuft FP2 auf unbelegte Dissens-Zitate); (2) `ALEX_ZUSAMMENFASSUNG.md` vor FP2 erstellen und beide FP2-Wortlaute nennen.

1. **[kosmetisch]** IOU-Schlussformulierung „stichprobenfähig halten" sperrig — bei Gefallen glätten. → Wurde vom Orchestrator im genehmigten Sinn geglättet (reine Umformulierung desselben Satzes, kein inhaltlicher Eingriff; Änderungshistorie: diese Datei).

## Festgehaltene „nicht geprüft"-Restrisiken (unverändert über beide Runden)

Git-Zustand nur aus Kickoff übernommen (kein bash im Prüfer); `test_cmd`-Ausführbarkeit nicht ausgeführt; Kit-Betriebsanleitung §9 außerhalb des Worktrees (nur Verweis geprüft); Nebenbehauptung „Akt-2-Auftrag verbietet Abschreiben" erst mit Archivierung des Auftrags gegenprüfbar (für den IOU-Kern nicht tragend).
