# Zusammenfassung für Alex: Profil-Dropdown live + Namenskonflikt-Schleife fixen (ROADMAP #46)

## Was wird gemacht?
Zwei kleine Reparaturen an der Serien-Vorschau: (1) Ein neu angelegtes
Serien-Profil taucht sofort im Dropdown auf, ohne dass du die Seite neu
laden musst; wenn Speichern fehlschlägt, siehst du es künftig in der
App-Konsole statt nichts. (2) Der "Namenskonflikt"-Hinweis, der sich nach
einem Klick auf "Namen übernehmen" immer wieder selbst zeigte
(Endlosschleife), verschwindet, sobald du einen der beiden angebotenen
Namen übernimmst. Dazu kommt der obligatorische Versions-Bump (v93→v94,
10 Stellen) und die Aufnahme der drei neuen Wunsch-Zettel #64 (Inbox
sortierbar), #65 ("Als Serie gruppieren") und #66 (Profile entkoppeln)
in die ROADMAP — nur als Text, ohne Bau.

## Warum?
Beides nervt direkt beim Serienimport: ohne F5 kein neues Profil, und die
Hinweis-Schleife blockiert den Flow. Die Grundursache der komischen Namen
("… 2010 US TMDB TV") bleibt dokumentiert und gehört zu #66 — hier wird
sie bewusst nicht geflickt.

## Risiken in Klartext
- **Ganz seltener Randfall:** Bei extrem langen Seriennamen (über 160
  Zeichen, Sonderzeichen exakt an der Abschneidekante) könnte der
  "Metadatenname übernehmen"-Button die Schleife weiterhin nicht brechen.
  Dann bleibt exakt das heutige Verhalten — nichts Neues bricht.
- **Konsole kann Meldung übersehen:** Die Fehlermeldung erscheint in der
  App-Konsole (Absicht), nicht als Pop-up.
- **Test-Harness fragil:** Die neuen Browser-Tests bauen auf einem
  bestehenden, etwas empfindlichen Test-Aufbau auf; künftige Umbauten an
  app.js könnten diese Tests zum Nachpflegen zwingen.
- **Bündelung:** Ein PR für alles — ein Rollback würde beide Fixes
  gleichzeitig zurückrollen (beide leicht rückholbar).
- Kein Geld, keine Außenwirkung, keine Registrierung, keine Käufe
  berührt. Einziger Sicherheits-Punkt ist ein **vorbestehender**,
  nicht behobener Fund (unescaped Namen im Hinweis → theoretisch
  Einschleusbarkeit von Anzeige-Tricksen), der nur als Wunsch-Zettel
  #67 vorgeschlagen wird. Rohoutputs aller Prüfer:
  `docs/sessions/2026-10-06-roadmap46-namenskonflikt/` (advocatus.md,
  plan-reviewer.md, produktberater.md, grafiker.md).

## Offene Fragen an dich
1. **Wunsch-Zettel #67** (XSS-Härtung, s. o.) als vierter Text-Eintrag
   mit in die ROADMAP? **Empfehlung: ja** — kostet nichts, sonst geht der
   Fund in den Session-Unterlagen unter.
2. **Farbe der neuen Fehlermeldung:** Mit Präfix "[System]:" erscheint sie
   in Akzentfarbe (wie 14 bestehende Fehlermeldungen); echtes Rot ginge
   nur ohne Präfix (8 Vorbilder existieren auch dafür). **Empfehlung:
   Präfix behalten** — Konsistenz vor punktueller Hervorhebung.
3. Zur Kenntnis, keine Entscheidung nötig: zwei winzige
   Namens-Grenzfälle bleiben wie heute (erster Punkt oben); Details im
   technischen Briefing, Abschnitt 6/8.

## Deine Entscheidung
- [ ] Freigabe — weiter zur Ausführung (Gate-A2-Worker nach
      `briefing.md`, dann repo-operator für Commits/PR)
- [ ] Rückfragen (siehe oben) — Session geht in eine weitere Runde

*Stand: plan-reviewer hat das technische Briefing nach 2 Runden mit
APPROVE abgenommen (letzter kosmetischer Punkt wurde vor der Vorlage
korrigiert). Briefing: `docs/sessions/2026-10-06-roadmap46-namenskonflikt/briefing.md`
(status: draft — Freigabe-Platzhalter werden nur aus deinem wörtlichen
Kommentar gefüllt). Nichts committet; Branch feat/roadmap-46-namenskonflikt,
Stand 3522ef2, sauber außer dem Session-Ordner.*
