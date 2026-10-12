# Zusammenfassung für Alex: Staffel-Ordner in der Inbox endlich mitsortierbar und anhakbar

## Was wird gemacht?
Die Walking-Dead-Ordner in der Inbox (ein Video pro Ordner, Name ohne Trennzeichen wie `ThWaDeS11E23`) werden wie einzelne Dateien behandelt: Sie rutschen automatisch in die Serien-Gruppe derselben Serie — auch zusammen mit lose herumliegenden Folgen-Dateien — und bekommen ein Auswahlkästchen. Ein Klick verarbeitet die ganze Auswahl als EIN Auftrag. Dazu kommt eine kleine Sicherheits- nachrüstung: Bei solchen Gruppen-Aufträgen darf ein Umbenennungs-Ziel nicht mehr in einen fremden Unterordner zeigen.

## Warum?
Aktuell werden diese Ordner doppelt aussortiert: Die Erkennung „das ist Folge S11E23" scheitert an Namen ohne Trennzeichen, und Ordner sind von Gruppierung und Kästchen grundsätzlich ausgeschlossen. Deshalb musstest du 173 Staffel-Ordner einzeln verarbeiten (Staffeln 1–11, je genau eine Video-Datei; Staffel 11 sind 23 Ordner). Nach dem Change bleibt der Ordner selbst unverändert in der Inbox liegen — es wandert nur die Videodatei samt ihrer Begleiter (z. B. Untertitel). Fremde Dateien im Ordner (Info, Poster, Probeklip) werden nicht angefasst. Zum echten Bestand: Bei den Walking-Dead-Ordnern auf dem NAS liegen keine losen Dateien und keine Untertitel — Begleiter und gemischte Gruppen prüft nur der Handtest mit künstlichen Daten.

## Risiken in Klartext
- **Dateien werden verschoben, nicht kopiert.** Der Job bewegt echte Inbox-Dateien ins Output. Absicherung: erst Handtest mit künstlichen Testdaten am eigenen Rechner, dann auf dem NAS **nur Staffel 11** als erster echter Lauf — das haben wir so festgeschrieben. **Stichproben-pflichtig:** Nach dem Staffel-11-Lauf bitte selbst prüfen, dass die 23 Ordner leer liegen geblieben sind, die Staffeln 1–10 unverändert sind und die Dateien im vorhandenen NAS-Ordner „The Walking Dead (2010)" gelandet sind — ein neuer, abweichender Ordner (z. B. `ThWaDe`) wäre ein Fehler.
- **Erkennungsregel wird global etwas lockerer:** Namen wie `…S01E01PROPER…` gelten künftig als Folge (vorher nicht). Betrifft nur die Automatik-Gruppierung, nichts anderes.
- **Ein Ordner, dessen einziges Video ein Exotenformat hat (z. B. `.wmv`), taucht in der Inbox weiterhin gar nicht auf.** Bekannte Grenze, separat vorgemerkt.
- **Alles, was du heute ohne Gruppen-Auswahl verarbeitest, bleibt garantiert unverändert** — das ist als eigener Test festgeschrieben.
- Ein „Film"-Ordner ohne Folgen-Kürzel im Ordnernamen wird weiterhin nicht zur Serie (deine F1-Absage; als Folgethema in der ROADMAP vorgemerkt).

## Offene Fragen an dich
1. **Freigabe dieses Plans** → dann liefere ich die Ausgangsmessung, startet ein einziger Gate-A2-Lauf (KI schreibt Code + Tests), prüfe ich den Stand (Plausibilitätsprüfung), und das Planungsteam nimmt über den Rückkanal ab (Pflichtschritt; bei „Nein" bessert die KI nach). Danach bekommst du den kleinen Diff zum Review.
2. **Vor dem Merge** machst du den Handtest an deinem Rechner (künstliche Daten, ~20–30 min). Dann erst folgt der PR und — wie immer nur nach deinem Ok — der **Merge**, danach NAS-Update und NAS-Livetest Staffel 11.
3. Nichts weiter zu entscheiden — alle Detailfragen (Regex-Form, Feldnamen, Härtungsort) sind mit deinen sieben bindenden Entscheidungen aus Akt 1 und deiner Korrekturrunde-2b-Zusage abgedeckt; abweichende Berater-Positionen sind im technischen Briefing als verworfen dokumentiert (Rohoutputs der Runde: `docs/sessions/2026-10-12-inbox-ordnerfolgen/`, Archivierung per `opencode export` durch Claude Code).

## Deine Entscheidung
- [ ] Freigabe — weiter zur Ausführung
- [ ] Rückfragen — Session geht in eine weitere Runde
