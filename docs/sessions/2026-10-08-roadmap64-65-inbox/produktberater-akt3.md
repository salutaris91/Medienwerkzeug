# Rohoutput produktberater — Kreativteam-Session 2026-10-08 (Akt 3, #65)
Hinweis Claude Code (2026-10-08): Mechanisch aus `opencode export ses_ee533a3c8ffesW6v133rMvr61E` (ceo-planner) abgelegt, nur Aufrufe ab dem Akt-3-Auftrag, nicht vom Moderator abgeschrieben (Lehre 59). Einzige Änderung: Trailing Whitespace am Zeilenende entfernt (Pre-Commit-Hook). Volle Prompts und Antworten: Kit `scripts/gate-a2/logs/2026-10-08-roadmap64-65/export-ceo-planner-akt3.json`.

---

## produktberater zu #65 Briefing (Subagent-Sitzung ses_ee5025a57ffePZL1jabl7doIYs, Status: completed)

<task id="ses_ee5025a57ffePZL1jabl7doIYs" state="completed">
<task_result>
## Produktberater-Einschätzung: ROADMAP #65 „Als Serie gruppieren"

### 1. MVP-Schnitt PR1
**Empfehlung:** PR1 = tv-Erkennung + Gruppenzeile + Vorschlag + Checkboxen + files[]-Übergabe. **Verzichtbar:** Einklappbarkeit (Nice-to-have, erhöht UI-Komplexität ohne funktionalen Mehrwert), Staffel-Zwischenebene (Overengineering – eine Ebene „Serie → Folgen" reicht für MVP, Staffel-Struktur kann später kommen). **Nicht verzichtbar:** Strenges Pattern-Matching (ohne `1x05`), `files[]`-Übergabe, Pfadvalidierung, Scope-Begrenzung auf Gruppe+Begleitdateien.

### 2. Regel 2 (Film-Sperre + Ausnahme)
**Empfehlung:** Sinnvoll, keine Überregulierung – verhindert Fehlgruppierungen. **Ausnahme erreichbar machen:** Standardmäßig gesperrt mit klarer Warnung („Filme werden nicht gruppiert"). Ausnahme über expliziten Sekundär-Button „Trotzdem als Serie behandeln" (nicht im Haupt-Flow, sondern als bewusste Entscheidung). Hinweis muss kurz und handlungsleitend sein, nicht belehrend.

### 3. #68 im selben PR oder getrennt?
**Veto für Zusammenlegung.** #68 ändert bestehendes Verhalten (Einzel-Jobs), #65 führt nur neuen `files[]`-Pfad ein. **Empfehlung:** Strikt getrennt. #65 ist isoliert und sicher (kein bestehendes Verhalten geändert), #68 ist riskant (Behavior-Change). Mixing erhöht Review-Komplexität, Testaufwand und Regression-Risiko. #68 gehört in eigenen PR nach #65.

### 4. Akzeptanzkriterien (ausführbar)
1. TV-Dateien mit identischem Namensanteil vor `SxxExx` erscheinen in der Inbox als visuell gruppiert (Gruppenzeile).
2. Klick auf Gruppe öffnet bestehendes Vorschau-Modal mit allen Dateien der Gruppe + Begleitdateien.
3. Dateiname mit „1920x1080" erzeugt **keinen** Serien-Vorschlag (Regel-1-Falle getestet).
4. Film-Dateien (`media_type: "movie"`) zeigen Sperr-Hinweis, keine Gruppen-Option.
5. Einzelner TV-Eintrag kann über Sekundär-Button explizit als Serie freigegeben werden.
6. Verarbeitung berücksichtigt **nur** Dateien der Gruppe + Begleitdateien; fremde Inbox-Dateien bleiben unberührt (Pfadvalidierung + Scope-Grenze).

### 5. Komplexitätsfalle
**Empfehlung:** PR1 strikt auf „Gruppierung anzeigen + `files[]`-Übergabe" beschränken. **Keine** Gruppen-Editier-UI (Drag&Drop zwischen Gruppen → #20), **kein** Modal-Refactor (bestehendes 264-Zeilen-Modal wiederverwenden, nur `files[]`-Parameter ergänzen), **keine** doppelte Sortier-/Gruppierungslogik (Sortierung bleibt auf Dateiebene, Gruppierung ist reine visuelle Darstellung). Cache-Buster v95 → v96 nach #64-Merge.
</task_result>
</task>
