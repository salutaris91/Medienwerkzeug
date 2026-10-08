# ROADMAP-Neueinträge #64–#67 (Wortentwurf für Übernahme in ROADMAP.md)

Session 2026-10-06, Freigabepunkt-1-Entscheidung Q1: Dieser Text wird von
`repo-operator` nach Alex-Go **wortgleich** ans Ende von `ROADMAP.md`
(hinter Eintrag #63, Zeile 1793) übernommen — im selben ersten PR.
Der Gate-A2-Worker fasst ROADMAP.md nicht an. Inhaltlich von Alex
entschieden (Kickoff, 06.10.2026) — hier nur in Existing-Format gegossen.
**Eintrag #67** stammt aus dem advocatus-Befund dieser Session (nicht von
Alex vorgegeben) und wurde beim finalen Planreview von Alex freigegeben
(2026-10-07, wörtlich: „Ja, ich folge deinen Empfehlungen vollständig.").
Er wird als vierter Eintrag wortgleich mit übernommen.

---

## 64. Inbox: Sortierbare Liste

**Einordnung / Priorität:** UX-Verbesserung für die Startseite (Inbox). Bezug zu Item #45 (Inbox/Outbox aufräumen).

**Problem:**
Die Inbox-Liste wird in einer festen Reihenfolge angezeigt. Bei vielen Kandidaten ist nicht schnell erkennbar, welche Projekte zuerst anstehen (z. B. neueste zuerst, größte zuerst, alphabetisch).

**Ziel:**
Die Einträge der Inbox sollen per Klick sortierbar sein (mindestens Name, Datum, Größe; ascendierend/descendierend umschaltbar).

**Umsetzung:**
1. Sortier-Interaktion auf bestehenden Inbox-Daten im Frontend umsetzen (keine Server-Änderung nötig, sofern die Payload die Felder bereits liefert).
2. Sortier-Zustand pro Sitzung erhalten, damit erneutes Öffnen die Wahl nicht zurücksetzt.

### Risiken & Hinweise
- Sortierfelder hängen davon ab, welche Felder die Inbox-Payload liefert (bei #45-Aufräumen prüfen).

### Aufwand (grob)
Klein bis mittel (reine Frontend-Logik, DOM-Tests wie bei bestehenden Inbox-Tests).

---

## 65. „Als Serie gruppieren": SxxExx-Erkennung mit Vorschlag Serie → Staffeln

**Einordnung / Priorität:** Komfort/KI-Assistenz für den Serienimport. Bezug zu Item #45 (Inbox) und Item #20 (Drag & Drop als Ausweichmechanik).

**Problem:**
Mehrere Inbox-Dateien, die nach SxxExx benannt sind, gehören oft zu einer Serie. Bisher muss der Nutzer sie einzeln verarbeiten; eine Gruppierung zu „Serie → Staffeln" fehlt.

**Ziel (von Alex bestätigt, 06.10.2026):**
Dateien mit SxxExx-Muster werden erkannt; das System schlägt vor, sie als Serie mit Staffeln zu gruppieren.

**Umsetzung:**
1. **Erkennung:** Muster `S(\d+)E(\d+)` (case-insensitive) über die Inbox-Dateinamen; Treffer gruppiert anzeigen.
2. **Vorschlag:** Karte/Hinweis „Als Serie gruppieren" mit vorgeschlagenem Seriennamen (aus gemeinsamem Namensanteil) und Staffelaufteilung.
3. **Ausweichwege (von Alex benannt):** manuelles Gruppieren durch Ziehen (Drag & Drop, Bezug #20) sowie über Auswahlkästchen (Checkboxen) — auch ohne automatische Erkennung bedienbar.

### Risiken & Hinweise
- Falsche Gruppierungen möglich (z. B. zwei verschiedene Serien mit gleichem Namenspräfix) — Vorschlag muss vor Ausführung bestätigbar bleiben.
- Kein Zwang zur Automatik: Ausweichwege müssen vollständig funktionsfähig bleiben.

### Aufwand (grob)
Mittel (Erkennung klein; Gruppierungs-UX und Übergabe in den Serien-Flow sind der Hauptteil).

---

## 66. Profile entkoppeln: Identität = Provider + Show-ID, freier Anzeigename (Ansatz B)

**Einordnung / Priorität:** Architektur-/Datenmodell-Klärung der Serien-Profile; behebt die Grundursache mehrerer Namensprobleme. Bezug zu Items #41 (Umbenennen NAS-Serienordner), #46 (Dropdown-Sync) und zur dokumentierten Herkunft der Namensverschmutzung „… 2010 US TMDB TV".

**Problem:**
Die Identität eines Profils hängt heute am (bereinigten) Seriennamen: Suchlabels tragen Metadaten-Anhängsel — `gui/mw_metadata.py:233` baut `f"{title} ({year}) [{country}]"`, `gui/mw_metadata.py:398` hängt `[{PROVIDER}]` an — und `clean_show_name` (`gui/core/utils.py:23`) entfernt nur die Klammern, lässt den Inhalt („2010 US TMDB TV") als Klartext im Profil-/Dateinamen. `clean_series_name_for_fs` (`gui/core/helpers.py:97`) stript beim Laden nur *trailing* `[...]`-Tags, nicht die Klartext-Reste. Folge: verschmutzte Anzeigenamen, Namenskonflikt-Schleifen in der Vorschau, Umbenennen nicht möglich, ohne das Profil zu verlieren.

**Ziel (Ansatz B, von Alex bestätigt, 06.10.2026):**
Profil-Identität und Anzeigename werden entkoppelt.

**Umsetzung:**
1. **Identität:** Provider + Show-ID als eindeutiger Schlüssel des Profils.
2. **Anzeigename:** freies, vom Nutzer änderbares Feld; keine Namens-Ableitung mehr als Schlüssel.
3. **Sanfte Migration:** bestehende Profile beim ersten Zugriff automatisch auf das neue Schema heben; alt bleibt lesbar, bis die Migration abgeschlossen ist.
4. **Sicherung vor Migration:** vor dem Migrationslauf eine Sicherungskopie der Profildateien (z. B. `data/profiles` → Zeitstempel-Backup).
5. **Nach der Entkopplung:** Bereinigung der Suchlabel-Anhängsel (Klammerinhalte) möglich, ohne Bestandsprofile zu brechen (eigentliche Behebung der „… 2010 US TMDB TV"-Herkunft).

### Risiken & Hinweise
- Datenmigration ist der kritische Pfad — ohne Sicherung nicht starten (Alex-Vorgabe).
- Übergangsphase mit zwei Schema-Generationen braucht klare Lesereihenfolge (neu → alt-Fallback).
- Externe Effekte (NFO, NAS-Ordnername) weiterhin namesbasiert — Entkopplung nur im Profilbereich, nicht global erzwingen.

### Aufwand (grob)
Mittel bis groß (Schema, Migration, Sicherung, UI-Anpassungen). Bewusst NICHT Teil des #46-PRs.

---

## 67. Vorschau-Namenskonflikt: Ordnernamen escaped rendern (XSS-Härtung)

**Einordnung / Priorität:** Sicherheits-Härtung (vorbestehender Befund, gefunden 06.10.2026 in der #46-Session durch die Risikoprüfung). Kleine, eigenständige Behebung.

**Problem:**
Der Namenskonflikt-Hinweis der Serien-Vorschau interpoliert `nas_name` und `metadata_name` unescaped in `innerHTML` (`gui/static/app.js:10283`). Ordnernamen auf dem NAS bzw. Metadaten-Namen sind extern beeinflussbar (NAS-Bestand, Metadatendienste). Ein Name mit HTML-Sonderzeichen (z. B. `<`, `"`, `<img onerror=…>`) würde im Browser als Markup interpretiert — gespeites Cross-Site-Scripting (XSS) im eigenen Dashboard. Im Einzelnutzer-Setup geringe Auswirkung, aber unnötiges Einfallstor.

**Ziel:**
Der Hinweis rendert beide Namen rein als Text; HTML-Sonderzeichen werden escaped.

**Umsetzung:**
1. In `app.js:10283` die Interpolation auf `escapeHTML(...)` umstellen (Helfer existiert im Projekt) oder die Box auf `textContent` mit vereinfachtem String umbauen.
2. Frontend-Regressionstest: ein Name mit `<b>`/`"` wird im Hinweis nicht als Markup interpretiert.

### Risiken & Hinweise
- Rein darstellungsseitig; keine API-/Datenänderung. Bestehende Hinweis-Tests unverändert grün halten.

### Aufwand (grob)
Klein (eine Zeile + ein Test).
