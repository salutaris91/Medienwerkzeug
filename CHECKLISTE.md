# CHECKLISTE.md — Abschluss jeder Coding-Aufgabe

Dieser Prozess wird am Ende jeder Coding-Aufgabe abgearbeitet.
Verlinkt aus `CLAUDE.md`.

---

## Abschlusszusammenfassung

Nach jeder Coding-Aufgabe ausgeben:

- **Geänderte Dateien:** (jede Datei auflisten)
- **Was wurde geändert:** (eine Zeile pro Datei)
- **Nicht angefasste Dateien:** (explizit nennen)
- **Offene Punkte:** (falls vorhanden)

---

## Checkliste vor jedem "Fertig"

- [ ] Keine Secrets im Code oder in der Versionskontrolle
- [ ] `.env.example` vorhanden
- [ ] Fehlerbehandlung für alle externen Aufrufe
- [ ] Berechtigungen geprüft
- [ ] Rate Limiting bedacht (falls öffentlich erreichbar)
- [ ] Code ist lesbar und kommentiert
- [ ] Testfälle formuliert und umgesetzt
- [ ] Abschlusszusammenfassung ausgegeben

---

## Fix-Checkliste

Diese Zusatzliste gilt für Bugfixes und Stabilitätskorrekturen. Sie ergänzt die
allgemeine Abschluss-Checkliste oben.

- [ ] Der Fehler ist konkret beschrieben (Symptom, betroffene Ansicht/Route, Log-Auszug oder Screenshot).
- [ ] Der Repro-Fall ist benannt: Welche Schritte führen zum Fehler?
- [ ] Die Ursache ist eingegrenzt und im Abschluss kurz erklärt.
- [ ] Der Fix ist eng begrenzt und verändert keine unrelated Funktionen.
- [ ] Bestehende Nutzer-Daten, Einstellungen und Dateien bleiben kompatibel.
- [ ] Falls Pfade betroffen sind: keine hardcodierten lokalen Nutzerpfade, Mac-Pfade oder Container-internen App-Code-Pfade.
- [ ] Falls Docker/Desktop betroffen ist: beide Laufzeitmodi wurden getrennt betrachtet.
- [ ] Falls UI sichtbar betroffen ist: Texte, Platzhalter, Buttons und Fehlermeldungen passen zum tatsächlichen Verhalten.
- [ ] Falls externe Tools betroffen sind: Installation, Version, Update-Weg und Docker-/Desktop-Unterschied sind geklärt.
- [ ] Falls Secrets/API-Keys betroffen sind: Speicherung nur über `.env`/persistente Config, keine Defaults mit echten Keys.
- [ ] Automatisierte Tests wurden ergänzt oder bewusst begründet, warum ein manueller Test reicht.
- [ ] Manuelle Verifikation wurde mit konkreten Befehlen/Schritten dokumentiert.
- [ ] Relevante Dokumentation wurde aktualisiert (README, Hilfe/FAQ, API-Doku oder Roadmap).
- [ ] `STAND.md` wurde aktualisiert, falls der Fix Teil einer Übergabe oder laufenden Phase ist.
- [ ] `scripts/refresh_graphify.sh` wurde nach Codeänderungen ausgeführt.
