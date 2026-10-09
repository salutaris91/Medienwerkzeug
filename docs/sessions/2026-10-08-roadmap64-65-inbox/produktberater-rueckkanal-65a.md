# Rohoutput produktberater — Rückkanal-Abnahme #65 Lauf A, 2026-10-09

Hinweis Claude Code (2026-10-09): Mechanisch aus `opencode export ses_ee06a9523ffewYvmhGiv6JaAr9` (ceo-planner, Rückkanal-Sitzung) abgelegt, nicht vom Moderator abgeschrieben (Lehre 59). Einzige Änderung: Trailing Whitespace entfernt. Volle Daten: Kit `scripts/gate-a2/logs/2026-10-09-roadmap65-lauf-a-nachbesserung/export-rueckkanal.json`.

---

## Produktberater: Chancen Lauf A (Subagent-Sitzung ses_ee06225b1ffe9FSbRlwqGwkN9P, Status: completed)

<task id="ses_ee06225b1ffe9FSbRlwqGwkN9P" state="completed">
<task_result>
# Rückkanal Lauf A — Chancen und weitere Features

## Methodische Vorbemerkung

Ich habe den files[]-Mechanismus (Code-Stand 2a5eec5) gegen jede Idee geprüft, die mir begegnet ist. Der zentrale Befund vorab: **Der Server-Pfad ist mächtiger als die aktuelle Inbox-UI ihn ausschöpft.** Lauf B nutzt files[] ausschließlich für Top-Level-Einzeldateien (`is_dir===false`, Root-Ebene). Die Validierung (`helpers.py:828-830`) erlaubt aber **beliebige relative Pfade inkl. Unterordner** — diese Fähigkeit bleibt nach Lauf B ungenutzt, weil `get_inbox_suggestions` (`project_api.py:1320-1342`) nur Top-Level-Ordner und Top-Level-Dateien als Inbox-Einträge liefert. Daran hängen sich die echten neuen Möglichkeiten auf.

---

## Kandidat 1 — „Inbox-Ordner aufklappen": Teil-Verarbeitung von Unterordnern

**Problem (echter Nutzen für Alex):**
Eine Serie liegt in `Inbox/Serie/Staffel 1/`, `Inbox/Serie/Staffel 2/` etc. Die Inbox zeigt `Serie/` als EINEN Eintrag (`is_dir: true`). Alex sieht nicht, welche Folgen in welchen Staffeln liegen. Will er nur Staffel 1 verarbeiten, muss er heute den ganzen Ordner nehmen (inkl. Staffel 2) oder im Finder vorstrukturieren.

**Was files[] neu ermöglicht (vorher unmöglich):**
`files[]` akzeptiert Pfade wie `["Serie/Staffel 1/S01E01.mkv", "Serie/Staffel 1/S01E02.mkv", ...]` — die Validierung (`helpers.py:828-830`) erlaubt `os.path.normpath` mit Unterordnern, das Inbox-Konfinement (`helpers.py:840`) ist erfüllt. Der Processor verarbeitet genau diese Dateien als EINEN Serien-Job mit gemeinsamer Profil-Zuordnung. Vorher: nur „ganzer Ordner" oder „N Einzeljobs".

**Umsetzung (grob):**
- Backend: `get_inbox_suggestions` erweitern — wenn ein Ordner-Entry aufgeklappt wird, rekursiv die Videodateien darin als eigene Einträge liefern (mit `is_dir: false` und dem relativen Pfad ab Inbox-Root als `project`).
- Frontend: Chevron am Ordner-Entry, Klick klappt auf, die Folgen werden als Checkbox-Kandidaten sichtbar (AK12-Regeln gelten unverändert: `media_type==="tv"`, `is_dir===false`).
- Scope: files[]-Mechanismus bleibt unverändert — die Begleitdatei-Suche (`helpers.py:888-918`) findet Same-Directory-Siblings im jeweiligen Unterordner.

**Aufwand:**
- KI-Implementierung: mittel (Backend-Rekursion mit Tiefenbegrenzung, Frontend-Aufklapp-UI, ~2-3 Gate-A2-Runden).
- Alex-Engpass: mittel (Review der Rekursionslogik, Handtest mit echter Staffel-Struktur).

**Risiko/Complexity-Veto:**
- **Kein Veto**, aber klar als **eigenes Feature nach Lauf B** positionieren. Blockiert Lauf B nicht (Lauf B arbeitet auf Top-Level-Einträgen).
- Performance: Inbox typisch <30 Einträge, aber ein Ordner kann 264+ Folgen haben → Aufklappen muss lazy sein (erst auf Klick rekursiv scannen).
- Tiefenbegrenzung: max. 2-3 Ebenen (verhindert Endlos-Rekursion bei verschachtelten Ordnern).

**Abgrenzung:**
- ≠ #65B (gruppiert Top-Level-Einzeldateien, keine Unterordner).
- ≠ #69 (Filmreihe am Stück = mehrere Filme, keine Folgen).
- ≠ #20 (Drag&Drop = Datei verschieben, nicht auswählen).
- ≠ #45 (Dashboard = Speicher/Aufräumen, nicht Verarbeitung).

---

## Kandidat 2 — „Staffel-übergreifende Serien-Gruppierung"

**Problem (echter Nutzen für Alex):**
Spezialfall von Kandidat 1: Die Folgen einer Serie liegen in `Staffel 1/`, `Staffel 2/`, `Extras/`. Alex will sie als EINE Serie verarbeiten (gemeinsames Profil, gemeinsame NFO), nicht als drei separate Jobs.

**Was files[] neu ermöglicht (vorher unmöglich):**
`files[]` = `["Serie/Staffel 1/S01E01.mkv", "Serie/Staffel 2/S02E01.mkv", "Serie/Extras/Special.mkv"]` — ein Job, ein Profil, drei Unterordner. Der Processor bewegt jede Folge in die richtige Staffel im Ziel (`processor.py:1334` = `Staffel N`-Ordnung), die NFO wird einmalig geschrieben. Vorher: drei Jobs, drei NFOs, drei Profil-Zuordnungen.

**Umsetzung (grob):**
- Braucht Kandidat 1 als Vorarbeit (Ordner aufklappen).
- Frontend: Checkboxen über mehrere Unterordner hinweg — der Auswahlzustand (DOM-unabhängiges Set aus AK12) sammelt Pfade aus verschiedenen Ordnern.
- Backend: keine Änderung nötig — files[] akzeptiert die Pfade bereits.

**Aufwand:**
- KI-Implementierung: klein (nur Frontend — die Backend-Infrastruktur existiert).
- Alex-Engpass: klein (Handtest mit echter Staffel-Struktur).

**Risiko/Complexity-Veto:**
- **Kein Veto**, aber **abhängig von Kandidat 1** — ohne Ordner-Aufklappen nicht nutzbar.
- Edge-Case: Begleitdateien sind Same-Directory (`helpers.py:888-918`). Wenn `S01E01.srt` in `Staffel 1/` liegt, wird sie gefunden. Wenn sie in `Serie/Subs/` liegt, wird sie NICHT gefunden — das ist eine bewusste Server-Begrenzung (Scope-Härtung ADR-65-3), keine Lücke.

**Abgrenzung:**
- ≠ #65B (gruppiert nur Top-Level-Einzeldateien mit gleichem `suggested_query`).
- ≠ #69 (Filmreihe = mehrere Filme, keine Folgen).

---

## Kandidat 3 — „Wiedervorlage / Resume": Halbabgeschlossene Serien fortsetzen

**Problem (echter Nutzen für Alex):**
Alex verarbeitet eine Serie mit 264 Folgen. Bei Folge 150 bricht der Job ab (Netzwerk-Fehler, Docker-Neustart, was auch immer). Folgen 1-149 sind in der Outbox, Folgen 150-264 sind noch in der Inbox. Alex will die übrigen 115 Folgen als EINEN Job nachverarbeiten — nicht als 115 Einzeljobs.

**Was files[] neu ermöglicht (vorher unmöglich):**
- **Für Root-Ebene-Dateien:** Funktioniert BEREITS mit Lauf B. Die übrigen Folgen sind als Einzeldateien sichtbar (`is_dir: false`), Checkboxen (AK12) erlauben die Auswahl, files[] übergibt sie als Gruppe.
- **Für Unterordner-Dateien:** Braucht Kandidat 1 (Ordner aufklappen). Wenn die übrigen Folgen in `Serie/Staffel 2/` liegen, sind sie ohne Aufklappen nicht sichtbar.

**Umsetzung (grob):**
- **Minimalvariante (ohne neue UI):** Nach einem abgebrochenen Job zeigt die Inbox die übrigen Folgen als Einzeldateien. Alex hakt sie per Checkbox an (Lauf B). Fertig.
- **Komfortvariante (mit Kandidat 1):** Ordner aufklappen, Folgen auswählen, als Gruppe verarbeiten.
- **Automatik-Variante (Zukunftsmusik):** Server erkennt „halbabgeschlossene Serie" (Profil existiert, einige Folgen schon in Outbox) und schlägt automatisch die übrigen Folgen als files[]-Gruppe vor.

**Aufwand:**
- Minimalvariante: **trivial** (ist Lauf B).
- Komfortvariante: mittel (braucht Kandidat 1).
- Automatik-Variante: groß (braucht neue Server-Logik: Outbox scannen, Profil matchen, Differenz berechnen).

**Risiko/Complexity-Veto:**
- **Kein Veto** für Minimal- und Komfortvariante.
- **Veto für Automatik-Variante** — zu komplex für den Einzelnutzer-Nutzen. Alex kann die übrigen Folgen manuell auswählen; eine automatische Erkennung würde neue Fehlerquellen einführen (falsche Profil-Zuordnung, veraltete Outbox-Daten).

**Abgrenzung:**
- ≠ #65B (Lauf B ist die Minimalvariante — Checkboxen für Top-Level-Dateien).
- ≠ #68 (Leere-Ordner-Cleanup = eigener Bugfix).

**Empfehlung:** Minimalvariante ist **kein eigener ROADMAP-Eintrag** — sie ist ein natürlicher Anwendungsfall von Lauf B. Komfortvariante ist Kandidat 1. Automatik-Variante **verwerfen**.

---

## Kandidat 4 — „Cross-Directory-Serie": Verschiedene Ordner, dieselbe Serie

**Problem (echter Nutzen für Alex):**
Alex hat zwei Ordner in der Inbox: `Heroes.S01/` und `Heroes.S01.Rest/` (z.B. weil er die Serie in zwei Downloads bekommen hat). Beide Ordner enthalten Folgen derselben Serie. Er will sie als EINE Serie verarbeiten.

**Was files[] neu ermöglicht (vorher unmöglich):**
`files[]` = `["Heroes.S01/S01E01.mkv", "Heroes.S01/S01E02.mkv", "Heroes.S01.Rest/S01E03.mkv", "Heroes.S01.Rest/S01E04.mkv"]` — ein Job, ein Profil, zwei Quell-Ordner. Vorher: zwei Jobs, zwei Profil-Zuordnungen, Risiko der Namenskonflikte.

**Umsetzung (grob):**
- Braucht Kandidat 1 (Ordner aufklappen) — Alex muss die Folgen aus beiden Ordnern sehen und auswählen können.
- Backend: keine Änderung nötig — files[] akzeptiert die Pfade bereits.
- Edge-Case: Begleitdateien werden pro Video-Ordner gesucht (`helpers.py:888-918`). `S01E01.srt` in `Heroes.S01/` wird gefunden, `S01E03.srt` in `Heroes.S01.Rest/` wird ebenfalls gefunden. Das funktioniert korrekt.

**Aufwand:**
- KI-Implementierung: klein (nur Frontend — die Backend-Infrastruktur existiert).
- Alex-Engpass: klein (Handtest mit zwei Ordnern).

**Risiko/Complexity-Veto:**
- **Kein Veto**, aber **abhängig von Kandidat 1**.
- Edge-Case: Wenn beide Ordner eine `tvshow.nfo` enthalten, wird nur eine geschrieben (die erste, `processor.py:1032`). Das ist korrekt — die NFOs sind identisch (selbe Serie).

**Abgrenzung:**
- ≠ #65B (gruppiert nur Einzeldateien mit gleichem `suggested_query`, keine Ordner).
- ≠ #69 (Filmreihe = mehrere Filme, keine Folgen).

---

## Zusammenfassung und Empfehlung

| Kandidat | Echte Perle? | Abhängig von | Empfehlung |
|----------|--------------|--------------|------------|
| 1. Inbox-Ordner aufklappen | ✅ Ja — Grundlage für alle anderen | nichts | **Als eigenes Feature nach Lauf B** |
| 2. Staffel-übergreifende Gruppierung | ✅ Ja — natürlicher Use-Case | Kandidat 1 | **Zusammen mit 1 umsetzen** |
| 3. Wiedervorlage / Resume | ⚠️ Teilweise (Minimalvariante ist Lauf B) | Kandidat 1 (Komfortvariante) | **Minimalvariante = Lauf B, Komfortvariante = Kandidat 1** |
| 4. Cross-Directory-Serie | ✅ Ja — echter neuer Use-Case | Kandidat 1 | **Zusammen mit 1 umsetzen** |

**Kernbotschaft:** Kandidat 1 („Inbox-Ordner aufklappen") ist die **Grundlage** für alle anderen. Ohne ihn sind die Dateien in Unterordnern nicht sichtbar, und files[] kann sie nicht erreichen — obwohl der Server-Pfad es technisch erlaubt. Die anderen drei Kandidaten sind **Anwendungsfälle** von Kandidat 1.

**Empfehlung an Alex:**
1. **Lauf B zuerst abschließen** (MVP-Fluss nicht blockieren).
2. **Kandidat 1 als eigenes Feature planen** (nach Lauf B, vor #69). Es ist die natürlichste Erweiterung der Inbox-UI und erschließt die volle Leistungsfähigkeit von files[].
3. **Kandidaten 2-4 sind keine eigenen ROADMAP-Einträge** — sie sind Use-Cases von Kandidat 1 und werden zusammen mit ihm umgesetzt.
4. **Automatik-Varianten (Resume-Erkennung, globale Companion-Suche) verwerfen** — zu komplex für den Einzelnutzer-Nutzen.

**Scope-Wächter-Urteil:** Keine der Ideen blockiert Lauf B. Alle sind „zurückstellen" — sie sind echte Perlen, aber eigene Features, die nach dem MVP kommen. Qualität vor Quantität: lieber einen guten Kandidaten (Ordner aufklappen) sauber umsetzen als fünf halbgare.
</task_result>
</task>
