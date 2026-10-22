# Zusammenfassung für Alex: Lanterns-Ordner werden gruppierbar

## Was wird gemacht?
Ordner, in denen neben der Folge nur noch ein Sample-Video liegt (wie bei „Lanterns“), werden künftig wie die Walking-Dead-Ordner erkannt: Gruppenvorschlag im Banner und Auswahlkästchen. Beim Verarbeiten wandern nur die Folge und ihre Untertitel; Sample, Release-Infodatei (`.nfo`), Prüfsummen-Datei (`.sfv`) und der Werbe-Ordner bleiben liegen.

## Warum?
Heute zählt das Sample als zweites Video, deshalb fällt der Ordner aus der Gruppierung. Und würde man das allein beheben, bräche die Verarbeitung bei der ersten Folge ab, weil die Release-`.nfo` mitwandert und mit der neu erzeugten Episoden-NFO kollidiert. Beides wird in einem Lauf behoben.

## Risiken in Klartext
- **Nur Erkennung und Begleitdateien:** Keine Änderung an der Oberfläche, an Umbenennungsregeln oder am Kollisionsschutz.
- **Was ein „Sample“ ist:** dieselbe Regel, die die Vorschau schon heute benutzt („sample“ im Namen oder Ordner, oder sehr klein neben einer großen Datei). Ein Serienname mit „sample“ im Titel würde wie bisher falsch als Sample gelten — unverändert.
- **Eine `.nfo` wandert bei Gruppen-Aufträgen nie mehr mit:** Wer ohne Metadatendienst gruppiert, muss eine vorhandene Episoden-NFO selbst mitnehmen (sehr selten; in der API-Doku vermerkt).
- **Reste bleiben in der Inbox:** Sample, `.nfo`, `.sfv` und Werbe-Ordner liegen nach der Verarbeitung weiter dort (Aufräumen = ROADMAP #81).
- **Stichproben-pflichtige Themen:** keine.

## Offene Fragen an dich
Keine. Nach dem Merge braucht das NAS-Update wie immer dein eigenes Go; auf dem NAS prüfen wir zuerst nur, ob „Lanterns“ als Gruppe vorgeschlagen wird.

## Deine Entscheidung
- [ ] Freigabe — weiter zur Ausführung (AK0, ein Gate-A2-Lauf)
- [ ] Rückfragen
