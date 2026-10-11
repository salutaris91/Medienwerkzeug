# Zusammenfassung für Alex: #64 Inbox sortierbar + #65 „Als Serie gruppieren"

## #64 — Sortierbare Inbox-Liste: **gemergt** (PR #148, Merge `6152839`)

Erledigt und auf `main`: die Inbox-Liste hat die drei Klick-Felder Name | Datum | Größe, die Reihenfolge bleibt pro Browser-Tab erhalten, der Server liefert Datum und Größe je Eintrag. Die Abnahme lief über den Rückkanal (`rueckkanal-64.md`, ABNAHME: JA). Zwei Dinge aus dieser Abnahme sind hier noch wichtig:

- **R6** (Gruppenzeilen dürften versehentlich einen Lösch-Knopf auf einen echten Ordner bekommen) ist als **Testpflicht in #65 aufgenommen** — siehe unten.
- Der **Typ-Filter** (Klick aufs Kennzeichen „Serie/Film/…") wurde als ROADMAP **#70** vorgemerkt, nicht hier gebaut.

## #65 — „Als Serie gruppieren" (Plan überarbeitet, Planprüfer: APPROVE in Runde 3)

**Was wird gemacht?** Folgen mit „S01E02"-artigen Namen in der Inbox werden automatisch zu EINER Gruppe zusammengefasst — nur in der Ansicht, es wird keine Datei verschoben. Dazu kommen zwei Wege, die im alten Plan noch fehlten und die du am 08.10. freigegeben hast:
1. **Ankreuzen von Hand:** Serien-Einzeldateien bekommen ein Auswahlkästchen, dazu einen Knopf „Ausgewählte als Serie gruppieren". Damit funktionieren auch Serien, die die Automatik bewusst nicht erkennt (Namen wie `1x05` oder „Staffel 2 Folge 3 – Show.mkv").
2. **Ausnahme pro Film:** Ein als Film eingestufter Eintrag lässt sich einzeln „trotzdem als Serie freigeben" — nicht mehr auf genau einen Eintrag insgesamt begrenzt. Falsch als Film eingestufte Folgen bleiben so gruppierbar.

Beides läuft über denselben Weg ins System: eine Dateiliste geht an den Server, und der Server bearbeitet **genau diese Dateien samt ihren Untertiteln** — nichts sonst in der Inbox. Die Bestätigung bleibt vor der Ausführung nötig.

**Warum?** Deine 11-Staffel-Serie liegt als Hunderte Einzeldateien in der Inbox; bisher müsstest du jede Datei einzeln verarbeiten.

**Wie wird gebaut (neu):** nicht mehr direkt von Antigravity, sondern über die **Gate-A2-Pipeline in zwei Läufen**, die aufeinander aufbauen:
- **Lauf A = Server:** Dateiliste, Prüfregeln, die harte Begrenzung, welches File angefasst werden darf, und das neue Merkmal „Ordner oder Datei".
- **Lauf B = Oberfläche:** Erkennung, Gruppe, Banner, die Kästchen, der Sammel-Knopf, die Übergabe.

Jeder Lauf hat seine eigene erlaubte Dateiliste und muss für sich grün sein. Grund: Der Server-Teil ist der riskante Eingriff im Kern; so kannst du ihn **getrennt reviewen**, bevor die Oberfläche existiert. Zwischen beiden Läufen akzeptiert der Server die Dateiliste, ohne dass sie jemand nutzt — toter Code, kein Risiko, aber das Feature ist erst nach Lauf B spürbar.

**Risiken in Klartext:**
- Der Eingriff liegt im Verarbeitungskern — dem am besten getesteten, aber wichtigsten Teil. Absicherung: neue Regressionstests (fremde Dateien bleiben unberührt, auch bei listigen Namensähnlichkeiten), alle bestehenden Abläufe unverändert, plus dein Einzelreview des Server-Teils.
- **Lösch-Falle (R6):** Eine Gruppe ist nur ein Ansichtsinhalt, kein Ordner. Wenn sie den Namen eines echten Ordners trägt, dürfte trotzdem kein Lösch-Knopf darauf zeigen. Das ist jetzt als eigener Test vorgeschrieben.
- **Auswahl-Falle:** Wenn du 200 Dateien anhakst und dann sortierst, darf die Auswahl nicht verschwinden; Ordner und Doku-Einträge sind bewusst **nicht** anhaktbar. Beides ist als Test festgeschrieben.
- Die Vorschau-Liste mit 264 Zeilen könnte unhandlich sein (die Runde war hier uneins). Plan: nichts ändern, beim Handtest mit deiner echten Serie beobachten, nachrüsten falls nötig.
- Zwei Serien mit gleichem Namensanfang könnten in einer Gruppe landen; Gegenmittel: du siehst alle Original-Dateinamen und kannst einzelne Folgen abwählen.
- Ein „Alle auswählen" auf der Liste gibt es bewusst **nicht** (Massen-Job-Risiko) — ein Nachzug, wenn du ihn willst.

**Offene Fragen an dich:**
1. **Freigabe von #65 als Plan** — und damit der Reihenfolge: erst Lauf A (Server) starten und nach deinem Review mergen, dann Lauf B (Oberfläche). Jeder scharfe Pipeline-Lauf braucht dein Go, jeder Merge auch.
2. **„Alle auswählen" (Liste) und Staffel-Zwischenüberschriften** bleiben raus — bestätige ich so, oder willst du eines davon doch jetzt?
3. **Doku-Einträge** sind in dieser Version nicht gruppierbar (nur Serien und freigegebene Filme). Passt das, oder soll Doku wie Film behandelt werden?

*Hinweis zu stichproben-pflichtigen Themen (Geld, Außenwirkung, Recht/Registrierung, Kaufentscheidungen): keine betroffen — #65 ist reine Lokal-Funktion für dich als Einzelnutzer, ohne neue Dienste, Einkäufe oder öffentliche Wirkung.*

*Rohoutputs und technische Details in diesem Ordner: `briefing-65.md` (Planprüfer APPROVE, Runde 3; 7 ADRs, 13 Akzeptanzkriterien, zwei Worker-Aufträge), `65-uebergabe-optionen.md`, `rueckkanal-64.md`, `grafiker-akt3.md`, `advocatus-akt3.md`, `produktberater-akt3.md`, `plan-reviewer-akt3.md`. Nacharchivieren per `opencode export`: die **Akt-4**-Rohoutputs ([grafiker] Kästchen-UI, [advocatus] Schnitt/R6, plan-reviewer Runden 1–3) — das Briefing verweist darauf (Archiv-Hinweis), und die Akt-4-Entscheidung „1–3 wie empfohlen" wurde mir von Claude Code übermittelt, nicht direkt von dir.*

**Deine Entscheidung**
- [ ] **#65-Plan freigeben** (Freigabepunkt 2): dann AK0-Messung im Worker-Image durch Claude Code, danach **Lauf A** starten (Server), Review + Merge, anschließend **Lauf B** (Oberfläche), Review + Handtest + Merge.
- [ ] „Alle auswählen" / Staffel-Überschriften / Doku: bei der Empfehlung belassen (Empfehlung) oder ändern?
- [ ] Rückfragen — Session geht in eine weitere Runde.
