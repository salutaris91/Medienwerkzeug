# Rohoutput produktberater — Rückkanal-Abnahme #64, 2026-10-08

Hinweis Claude Code (2026-10-08): Mechanisch aus `opencode export ses_ee4eb3d2effef4wJApV8gwohQt` (ceo-planner, Rückkanal-Sitzung) abgelegt, nicht vom Moderator abgeschrieben (Lehre 59). Einzige Änderung: Trailing Whitespace am Zeilenende entfernt (Pre-Commit-Hook). Volle Prompts und Antworten: Kit `scripts/gate-a2/logs/2026-10-08-roadmap64-65-nachbesserung/export-rueckkanal.json`.

---

## produktberater: Chancen nach #64 (Subagent-Sitzung ses_ee4e8b653ffegIPte1LOsS6DKp, Status: completed)

<task id="ses_ee4e8b653ffegIPte1LOsS6DKp" state="completed">
<task_result>
## ROADMAP-Kandidaten aus #64 (Sortierung + neue Felder)

---

### Kandidat 1: Inbox-Filter nach Medientyp (Film / Serie / Doku / Anime)

**Problem:**
Die Typ-Badges sind sichtbar, aber nicht interaktiv. Bei 15+ Einträgen muss Alex manuell scrollen, um z. B. nur die Serien zu sehen. Die Sortierung nach Name/Datum/Größe hilft nicht, wenn die Frage lautet: "Zeig mir nur Filme."

**Nutzen:**
Ein Klick auf "Serie" filtert die Liste sofort. Kombiniert mit der bestehenden Sortierung: "größte Serien-Projekte zuerst" oder "neueste Filme zuerst". Die Badges (`media_type` ist bereits im Payload) sind die natürliche UI-Ankerstelle — ein Klick auf das Badge filtert, ein zweiter Klick hebt den Filter auf.

**Aufwand:**
- **KI-Umsetzung:** Klein. Reine Frontend-Logik: Click-Handler auf die bestehenden Badge-Spans, `filter()` über `currentSmartInboxRawSuggestions`, Re-Render. Kein Backend-Change.
- **Alex-Review-Engpass:** Klein. Nur Frontend-Diff, keine API-Änderung, keine Datenänderung. Visuelle Abnahme im Browser.

**Bezug zu bestehenden ROADMAP-Einträgen:**
- Kein Duplikat. #45 will Aufräumaktionen (Löschen, Speicher freigeben), nicht Filtern. #65 nutzt `media_type` für die Serien-Gruppierung, aber das ist ein anderer Use-Case (Gruppieren vs. Filtern).
- **Dupletten-Check:** Kein bestehender Eintrag (#11, #12, #17, #20, #45, #65, #68, #69) deckt Typ-Filter ab.

---

### Kandidat 2: Inbox-Gesamtgröße (Summenanzeige)

**Problem:**
Alex sieht die Größe pro Eintrag (`total_size`), aber nicht, wie viel Speicher die Inbox insgesamt belegt. Um das zu erfahren, müsste er die Einzelwerte im Kopf addieren oder zum NAS navigieren (`du -sh`).

**Nutzen:**
Eine Zeile unter der Sortier-Leiste: "Inbox: 47,3 GB in 12 Projekten". Sofortige Orientierung, ohne Nachdenken. Ist die Basis für spätere Speicher-Dashboards (#45), aber ohne dessen Komplexität (keine Aufräumaktionen, keine Sicherheitsdialoge).

**Aufwand:**
- **KI-Umsetzung:** Trivial. `reduce()` über `total_size` im Frontend, ein DOM-Element (z. B. `<span>` links neben der Sortier-Leiste). `formatBytes()` existiert bereits.
- **Alex-Review-Engpass:** Trivial. Kein Backend-Change, kein Risiko. Einzeiler im Frontend.

**Bezug zu bestehenden ROADMAP-Einträgen:**
- **Kleiner Vorgriff auf #45** (Dashboard-Speicherbelegung). #45 will mehr: getrennte Inbox/Outbox-Metriken, Aufräumbuttons, Sicherheitsdialog, Onboarding. Kandidat 2 ist die MVP-Vorstufe: nur die Inbox-Summe, keine Aktionen.
- **Dupletten-Check:** #45 ist größer und umfasst Aufräumaktionen. Kandidat 2 ist ein eigenständiger, kleiner Schritt.

---

### Kandidat 3: Speicherplatz aufgeschlüsselt nach Medientyp

**Problem:**
Die Gesamtgröße (Kandidat 2) sagt nicht, *wo* der Speicher liegt. Alex will wissen: "Belegen meine Serien oder meine Filme den meisten Platz?" — um zu entscheiden, ob sich ein Transcoding-Batch lohnt oder ob die Inbox aufgeräumt werden muss.

**Nutzen:**
Eine kompakte Aufschlüsselung: "Serien: 30 GB · Filme: 10 GB · Dokus: 5 GB". Kombiniert mit Kandidat 2: "Inbox: 47 GB in 12 Projekten (Serien: 30 GB, Filme: 10 GB, Dokus: 5 GB)". Sofortige Entscheidungsgrundlage.

**Aufwand:**
- **KI-Umsetzung:** Klein. `reduce()` über `total_size`, gruppiert nach `media_type`. Ein DOM-Element mit 3-4 Spans. Kein Backend-Change.
- **Alex-Review-Engpass:** Klein. Nur Frontend-Diff, keine API-Änderung. Visuelle Abnahme.

**Bezug zu bestehenden ROADMAP-Einträgen:**
- **Kleiner Vorgriff auf #45** (Dashboard-Speicherbelegung). #45 will getrennte Inbox/Outbox-Metriken — Kandidat 3 zeigt nur die Inbox, aber aufgeschlüsselt.
- **Dupletten-Check:** #45 ist größer. Kandidat 3 ist ein eigenständiger, kleiner Schritt.

---

### Kandidat 4: Sortierung nach Dateianzahl (`video_count`)

**Problem:**
`video_count` ist im Payload und wird in der Metazeile angezeigt ("10 Datei(en)"), aber nicht als Sortierfeld verfügbar. Alex will manchmal wissen: "Welche Projekte haben die meisten Dateien?" — z. B. um zu entscheiden, ob sich ein Serien-Import lohnt (viele Dateien = hoher Aufwand).

**Nutzen:**
Ein vierter Button "Dateien" in der Sortier-Leiste. Kombiniert mit der Typ-Filterung (Kandidat 1): "Serien mit den meisten Dateien zuerst".

**Aufwand:**
- **KI-Umsetzung:** Trivial. Ein weiterer Button in `index.html:461–466`, ein `else if`-Zweig in `sortInboxSuggestions` (`app.js:12259–12306`). Die Infrastruktur aus #64 wird 1:1 wiederverwendet.
- **Alex-Review-Engpass:** Trivial. Kein Backend-Change, kein Risiko.

**Bezug zu bestehenden ROADMAP-Einträgen:**
- Kein Duplikat. #12 (Performance große Bibliotheken) ist ein anderes Thema.
- **Dupletten-Check:** Kein bestehender Eintrag deckt das ab.
- **Hinweis:** Schwächerer Nutzen als Kandidat 1–3. Die Sortierung nach Größe (`total_size`) ist meist aussagekräftiger als die Anzahl Dateien. Kandidat 4 ist ein "nice-to-have", kein Muss.

---

## Bewusst NICHT empfohlen

**Server-seitige Sortierung:**
Die Inbox hat typischerweise 5–30 Einträge. Die Client-Sortierung (`sortInboxSuggestions`) ist instantan. Eine Server-Sortierung würde Roundtrip + Cache-Invalidation komplexer machen, ohne spürbaren Nutzen. Erst bei >100 Einträgen relevant — und das ist #12 (Performance), nicht hier.

**Sortierung nach `confidence` oder "Verarbeitungsreife":**
`confidence` (low/medium/high) und `profile_match` sind im Payload, aber keine natürlichen Sortierfelder. Die Sortierung nach Datum (desc) zeigt ohnehin die neuesten Projekte zuerst — und die sind meist die, die Alex als nächstes verarbeiten will. Eine "Reife"-Sortierung wäre ein zweidimensionales Optimierungsproblem, das Alex in der Praxis nicht hat. Ein Filter "nur mit Profil" (Kandidat 1) ist die einfachere Lösung für denselben Use-Case.
</task_result>
</task>
