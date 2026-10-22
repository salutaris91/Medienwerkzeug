VERDICT: REVISE

Plan-Review zu `docs/sessions/2026-10-22-roadmap89-sample-ordner/briefing.md` (ROADMAP #89).
Geprüft am 2026-10-22 vom Subagenten `plan-reviewer` im Worktree `fix-roadmap-89-sample-ordner`.
Dies ist die Zusammenfassung; der vollständige Rohoutput des plan-reviewer wird von Claude Code
mechanisch exportiert und ist hier nicht abschrieben.

## Ergebnis in Kurzform

[plan-reviewer] bestätigt: Alle Datei:Zeile-Angaben im Briefing stimmen mit dem Code dieses
Worktrees überein (vollständig unabhängig nachgeprüft, inkl. `project_api.py:1508`,
`helpers.py:798/:870–918/:927`, `app.js:12527/:12537/:10433`, `queue_api.py:94/:187–215/:217–220/:598–627`,
`processor.py:883/:1078–1089/:1568–1572`, alle genannten Teststellen, `API.md:146/:270`;
`test_cmd` byte-identisch zur #71-Referenz). Die Erlaubnis-/Nicht-anfassen-Liste in Abschnitt 11
ist vollständig — keine AK (auch nicht AK8) braucht eine Datei außerhalb der sechs erlaubten
Dateien; die NFO-Kollisionsstelle in `processor.py` ist durch die `helpers.py`-Änderung allein
entschärft; die Frontend-Freiheit ist code-seitig konsistent. ADRs und AKs sind untereinander
konsistent; Hausregeln/Struktur eingehalten; Alex' wörtlich zitierte Entscheidungen wurden
nicht inhaltlich hinterfragt. Kein Befund durch die bewusst fehlenden Session-Rohoutputs
(schlanke Kette, vertragsgemäß).

## Einwände

1. [wichtig] ADR-89-5 vs. AK4/AK6 — Rot-Probe nicht überall erfüllbar.
   [plan-reviewer] moniert: ADR-89-5 (briefing.md:84) fordert pauschal die „Rot-Probe der neuen
   Tests gegen f0a29a4 ohne neue Symbole“. Für AK4 ist diese Forderung prinzipbedingt unerfüllbar:
   AK4 sichert Basis-Verhalten (zwei echte Videos ohne „sample“ erhalten auch gegen f0a29a4 kein
   `single_video_relpath`, da `project_api.py:1508` bereits 2 zählt) — der Test ist gegen die Basis
   notgedrungen grün, unabhängig von der Bauart. Für AK6 gilt die Rot-Probe nur in einer bestimmten
   Bauart: ein reiner Vorschau-Test ist gegen f0a29a4 notwendigerweise grün (die Vorschau trägt die
   Sample-Kriterien bereits, `queue_api.py:187–215`); rot-fähig ist AK6 nur als kombinierter
   analyze+preview-Test, bei dem der analyze-Teil die Rot-Probe trägt — das legt die
   AK6-Formulierung nahe, erzwingt es aber nicht wörtlich. Das Briefing sagt nirgends, welche AKs
   rot-fähig sind und dass grüne Rot-Proben bei AK4/AK6 erwartbar und korrekt sind.
   Risiko im autonomen Gate-A2-Lauf: unnötiger STOPP bei „grüner Rot-Probe“, Weglassen des
   Regressionsschutzes AK4 oder ein AK6 ohne rot-fähigen Kern.
   Vorgeschlagener Fix (ein Satz in ADR-89-5 oder an AK4/AK6): „Rot-Probe gilt für AK1–AK3, AK5,
   AK7, AK8; AK4 und der Vorschau-Teil von AK6 sind als Bestandsschutz gegen f0a29a4 grün
   (erwartbar); AK6 wird als kombinierter analyze+preview-Test gebaut, sodass der analyze-Teil die
   Rot-Probe trägt.“

2. [kosmetisch] AK5 unterbestimmt.
   [plan-reviewer] bemängelt: „ein Ordner, der ausschließlich ein Sample enthält“ (briefing.md:42) —
   bei nur einer Videodatei kann Sample-Erkennung ausschließlich über Kriterium 1 greifen
   (Kriterium 2 braucht eine zweite Datei > 300 MB). Baut der Worker z. B. eine einzige kleine Datei
   ohne „sample“-Marke, liefert der Ordner korrekt `single_video_relpath` (heute und nach dem Fix)
   und der Test wäre in beiden Ständen rot. Präzisierung empfohlen: „einzige Videodatei ist per
   Kriterium 1 ein Sample (z. B. `xyz-sample.mkv` oder Pfadsegment `Sample`)“.

## Potenzial (keine Revisionsbedingungen)

- [plan-reviewer] regt an: AK9 könnte neben `API.md:270` auch die `/api/preview-process`-Beschreibung
  (`:265`) betrachten oder explizit als „unberührt“ festlegen — die Companion-Änderung wirkt auch auf
  die Vorschau; falsche Aussagen stehen dort nicht.
- [plan-reviewer] gleichwertige Alternative zu Einwand 1: das AK4-Grün-gegen-Basis-Thema im
  Dissens-Abschnitt (6) als bekannte Einschränkung der Prüfstrategie aufnehmen, statt ADR-89-5 zu
  präzisieren.

## Restrisiken / nicht ausgeführte Prüfungen (selbst deklariert vom plan-reviewer)

- Keine Tests ausgeführt — alle Rot-Fähigkeits-Aussagen sind statische Code-Analyse, keine
  ausgeführten Probeläufe.
- Live-NAS-Bestand (Abschnitt 1) außerhalb des Zugriffs; als Claude-Code-Angabe übernommen.
- Git-Zustand (Abschnitt 10) gemäß Auftrag als gegeben hingenommen, nicht verifiziert.
- Prozess-Transparenz: Ein breiter Grep (`89`) listete als Nebentreffer die `.git`-Pointer-Datei des
  Worktrees; [plan-reviewer] meldet, nicht gezielt zugegriffen und den Inhalt nicht in die Prüfung
  einbezogen; keine Git-Befehle ausgeführt, keine Dateien außerhalb des Worktrees gelesen, nichts
  geändert.

## Nächster Schritt

Briefing unverändert gelassen (Auftrag): Claude Code arbeitet die zwei Einwände ein; danach
erneute Prüfung durch den plan-reviewer, erst anschließend Briefing-Freigabe durch Alex
(Freigabepunkt; `status` bleibt bis dahin `draft`).
