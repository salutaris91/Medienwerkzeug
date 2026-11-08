# Zusammenfassung für Alex: Geführter Film-Assistent (Roadmap #92)

*Nicht-technische Fassung. Das technische Briefing liegt separat:
`docs/sessions/2026-11-06-film-assistent/briefing.md` (Grundlage für den
plan-reviewer-Check und die spätere Ausführung).*

## Was wird gemacht?

Ein geführter Assistent beim Film-Import: vier klare Schritte (Quelle → Metadaten inkl. FSK/Genre → Bilder → Ergebnis) statt der heutigen langen Scroll-Ansichten, verteilt über drei verschiedene Dialoge. Gebaut wird in sechs kleinen, einzeln test- und rückrollbaren Etappen; die erste macht FSK und Genre im Import erstmals selbst änderbar und stellt sicher, dass sie in der NFO landen. (Präzisierung nach Code-Prüfung: Die automatisch vom Dienst gelieferten Werte speichert der Import heute schon. Real verloren gehen heute nur manuelle Änderungen bei OFDb-Filmen.)

## Warum?

Der Import ist dein häufigster Alltagspfad. Er soll sich wie bei Emby geführt anfühlen, die Nacharbeit (FSK/Genre per Hand im NFO-Agenten nachtragen, ca. 30–50 Min/Woche) entfällt, und Filmreihen laufen später als Warteschlange statt einzeln von vorn.

## Risiken in Klartext

- **Serien könnten kaputtgehen:** Der Editor wird aus dem großen Frontend-Datei herausgelöst, in dem Filme und Serien denselben Code teilen. Gegenschutz: Serien bleiben in den ersten Etappen unberührt, und ein vorab festgeschriebener Handtest-Lauf (je ein Film/Serie/Doku-Durchlauf) wird nach jeder Etappe wiederholt.
- **Übergangs-Doppelablauf:** Nach Etappe 1 läuft der Film erst im neuen Assistent und danach noch im alten Vorschau-Dialog weiter (bis Etappe 2). Das ist bewusst in Kauf genommen — Details siehe Frage 1.
- **NAS ohne automatischen Rückholschritt:** Ein Rollback heißt altes Bild manuell holen. Darum sind die Etappen klein gehalten.
- **Recht/Registrierung — stichprobenpflichtig (Bildquellen):** Das Speichern von TMDb-Bildern macht das Tool heute schon automatisch; neu wären nur die Auswahl und evtl. eine zweite Bildquelle. Die rechtliche Einschätzung (keine Rechtsberatung) stammt aus der Recherche vom 06.11.; Rohoutputs liegen unter `docs/sessions/2026-11-06-film-assistent/` (scout.md Abschnitt 3, advocatus.md Punkt 8).

## Offene Fragen an dich

1. **Schnitt der ersten beiden Etappen (Auflage 2):** Empfehlung **A** — kleine Etappen wie freigegeben; nach Etappe 1 ist FSK/Genre sofort heil, aber der doppelte Ablauf bleibt kurz bestehen. Alternative **B** — runder Ablauf ab der ersten Etappe, aber die erste Kette wird mit ca. 150–190 KB Diff mehr als doppelt so groß wie das Budget (80 KB) und bündelt wieder fünf Baustellen in einem Rückholschritt. *Entscheidung: A oder B?*
2. **Bildquellen (Auflage 3, nur für Etappe 5, Eile unnötig):** Empfehlung **Option A** — Auswahl-Grid nur aus den vorhandenen TMDb-Bildern (klarste Rechtslage, eine Quellenangabe; Fanart.tv mit Logos/Disc-Bildern später, falls TMDb im Alltag nicht reicht). Option B wäre beides sofort, mit zweiter Quellenangabe und mehr Aufwand. Die frühere Empfehlung B beruhte darauf, dass Auswahl mehr Quellen braucht — die Code-Prüfung zeigte: TMDb liefert selbst schon Bildlisten. *Entscheidung: A, B oder „erst klären“?*
3. **Fünf Design-Details, mit Empfehlung vorbelegt, bitte bestätigen:** Punkte-Fortschrittskopf mit Labels; Poster/Fanart als Reiter; „Überspringen“ in Schritt 2/3 erlaubt; Provider-Fehler als Badge + Banner; Abfrage nur bei echten Änderungen beim Abbrechen. *Entscheidung: „Empfehlungen ok“ oder Einzelpunkte?*
4. **Wie oft kommen bei dir Filmreihen am Stück vor?** Meine Vermutung „eher selten“ (Nutzen-Prüfer sieht das so, eine belastbare Zahl hast nur du) — dann bleibt die Warteschlangen-Etappe die letzte; bei häufig (z. B. wöchentlich) rückt sie vor. *Entscheidung: Häufigkeit in etwa (z. B. „1–2× im Monat“).*
5. **Verhalten beim Schreiben von FSK/Genre (neu, vor Etappe 1):** Drei Punkte, die nur du entscheiden kannst. (a) Schlägt das Schreiben fehl: Job abbrechen oder sichtbar warnen und weiterlaufen? (b) Liegt im Ordner schon eine NFO: vorhandene ändern oder deine Wizard-Werte erzwingen? (c) Wenn du ein vom Dienst geliefertes Genre/FSK im Wizard leerst: soll es aus der NFO verschwinden oder stehen bleiben? Keine Empfehlung vom Planer vorhanden.
6. **Formales:** Git-Zustand ist geprüft: `main` sauber, `86fdc26`, nur der ungetrackte Session-Ordner. Für Commit/PR braucht es einen eigenen Branch und dein Go; auf `main` gilt der harte Schreibstopp.

*Nachtrag 2026-11-06:* Das Briefing wurde nach einem dritten Review am Code korrigiert (Details im Abschnitt „Nachtrag“ im Briefing). Diese Korrektur wurde nicht erneut vom plan-reviewer geprüft. Außerdem: Bei der Bildauswahl (Etappe 5) braucht es eine neue Funktion; die bestehende Bild-Automatik bleibt unangetastet.

## Deine Entscheidung

- [x] Freigabe — weiter zur Ausführung (Etappe 1 als Gate-A2-Lauf, Start ist Klasse-B-Go). FP2 am 2026-11-06 von Alex freigegeben; Entscheidungen D1–D4, D6 im Briefing. Der Gate-A2-Start selbst ist noch nicht ausgelöst.
- [ ] Rückfragen (siehe oben) — Session geht in eine weitere Runde
