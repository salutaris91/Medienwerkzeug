VERDICT: APPROVE

Plan-Review Runde 2 zu `docs/sessions/2026-10-22-roadmap89-sample-ordner/briefing.md` (ROADMAP #89).
Geprüft am 2026-10-22 vom Subagenten `plan-reviewer` im Worktree `fix-roadmap-89-sample-ordner`.
Runde 2 als Änderungs- und Konsistenzprüfung (kein Neuaufroll von Runde 1).
Dies ist die Zusammenfassung; der vollständige Rohoutput des plan-reviewer wird von Claude Code
mechanisch exportiert und ist hier nicht abschrieben.

## Ergebnis in Kurzform

[plan-reviewer] bestätigt beide Runde-1-Einwände und das übernommene Potenzial als korrekt,
widerspruchsfrei und code-konsistent umgesetzt:

- Einwand 1 [wichtig] (Rot-Probe, ADR-89-5): alle drei geforderten Elemente enthalten —
  explizite Rot-Probe-Liste (AK1, AK2, AK3, AK5, AK7, AK8), Bestandsschutz-Kennzeichnung
  (AK4 + Vorschau-Teil AK6, erwartbar grün gegen `f0a29a4`), AK6-Bauart als kombinierter
  analyze+preview-Test. Liste code-seitig nachgeprüft und stimmig mit dem Basisverhalten.
- Einwand 2 [kosmetisch] (AK5): Präzisierung „einzige Videodatei per Kriterium 1 ein Sample"
  plus Zusatz („einzelne kleine Datei ohne Sample-Marke bleibt Einzelvideo-Ordner") umgesetzt;
  [plan-reviewer] verifiziert: AK5-Kern ist damit rot-fähig, Zusatz beschreibt das Basisverhalten
  korrekt (`queue_api.py:202` braucht >300-MB-Gegenstück; `project_api.py:1508` liefert bei genau
  1 Video `single_video_relpath`).
- Potenzial (AK9 / `API.md:265`): als „unberührt" festgelegt; [plan-reviewer] prüft die Klammer
  „enthält keine Aussage zu Begleitdateien" gegen `API.md:265` für faktisch korrekt.

Neue Widersprüche: keine. [plan-reviewer] prüft ausdrücklich: Aufzählungen ADR-89-5 vs.
Änderungsabschnitt (Zeilen 172–176) deckungsgleich; AK5 konsistent mit AK2/AK3/AK4 und AK6-Fußnote;
AK6-Bauart konsistent mit Abschnitt 3 und Abschnitt 11 (Punkt 6 braucht keine Zusatzpräzisierung,
da Bauart im selben Briefing bei der Rot-Probe-Anweisung steht); AK9/:265 berührt den erlaubten
Dateiumfang nicht (Nicht-Änderung, API.md-Änderungen bleiben auf :146/:270 begrenzt);
Erlaubnis-/Nicht-anfassen-Liste, Frontend-Freiheitsversprechen und Alex' wörtliche Zitate
unverändert; Frontmatter bleibt `draft`/`TBD`; Abschnitt 7 (Lizenzen) gepflegt, kein Third-Party-Einsatz.
Zusätzlich vorgefundene `ALEX_ZUSAMMENFASSUNG.md`: [plan-reviewer] findet keine im Briefing
verlorenen oder verfälschten Einwände/Bedenken. Kein Befund durch die bewusst fehlenden
Session-Rohoutputs (schlanke Kette, vertragsgemäß).

## Einwände

1. [kosmetisch] AK9-Deklaration unscharf (Bestand, nicht durch Runde-2-Änderungen entstanden).
   [plan-reviewer] moniert: briefing.md:35 („AK1–AK9 sind ausführbare Tests (pytest)") und
   briefing.md:84 („AK1–AK9 als pytest") deklarieren AK9 als pytest, obwohl AK9 (briefing.md:46)
   ein Doku-Kriterium ist und Abschnitt 11 es operativ eindeutig als API.md-Änderung (Punkt 5)
   behandelt, während Punkt 6 Tests nur für AK1–AK8 nennt. In Runde 1 nicht moniert; operativ
   durch Abschnitt 11 und den AK9-Titel („Doku") aufgelöst, nicht blockierend. Fix mit einem Wort:
   „AK1–AK8" an beiden Stellen.

Keine [kritisch]en oder [wichtig]en Einwände.

## Restrisiken / nicht ausgeführte Prüfungen (selbst deklariert vom plan-reviewer)

- Keine Tests ausgeführt — alle Rot-Fähigkeits-Aussagen bleiben statische Code-Analyse (wie Runde 1).
- Git-Zustand (Abschnitt 10) gemäß Auftrag als gegeben hingenommen; keine Git-Befehle,
  kein `.git`/`.env`-Zugriff.
- U2-Kette (`processor.py:1078–1089`, `:1568–1572`) und `app.js`-Stellen nicht erneut selbst
  gelesen — in Runde 1 vollständig verifiziert und durch die Runde-2-Änderungen nicht berührt;
  die gelesenen Stellen (`queue_api.py:598–627`, Kollisionstest `:768ff.`) stützen die Kette.
- AK5-Zerlegungs-Restrisiko: zerlegt der Worker AK5 in zwei Tests, wäre der Zusatz-Teil ein grüner
  neuer Test, den die Bestandsschutz-Aufzählung von ADR-89-5 nicht namentlich nennt; AK5-Wortlaut
  („weiterhin") trägt die Erklärung selbst — Restrisiko gering.
- Live-NAS-Bestand (Abschnitt 1) als Claude-Code-Angabe übernommen (Runde 1).

## Potenzial (keine Revisionsbedingungen)

- [plan-reviewer] regt an: Bestandsschutz-Aufzählung in ADR-89-5 könnte den AK5-Zusatz
  ausdrücklich aufnehmen, falls eine künftige Fassung AK5 in mehrere Tests zerlegen will — Absicherung.
- [plan-reviewer] regt an: Kanal-Klammer in ADR-89-5 könnte `/api/preview-process` ergänzen,
  da der preview-Teil des kombinierten AK6-Tests über diesen Endpunkt läuft — unkritisch.

## Nächster Schritt

Briefing unverändert gelassen (Auftrag). Da `VERDICT: APPROVE`: Vorlage der
ALEX_ZUSAMMENFASSUNG an Alex zum finalen Planreview (Freigabepunkt 2); erst nach echter
Alex-Freigabe Frontmatter auf `status: approved` inkl. `approval_quote` (bis dahin bleibt `draft`).
