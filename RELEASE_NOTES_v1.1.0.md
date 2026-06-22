# Release Notes — Medienwerkzeug v1.1.0

Dieses Release bringt wesentliche Stabilitäts- und Robustheitsverbesserungen für die Medien-Pipeline, den Datenverlust-Schutz sowie die Verarbeitung von Online-Medien (YouTube und Mediatheken).

---

## Highlights in v1.1.0

### 1. Pragmatischer Step-Retry für TV- und URL-Serien (Strang 4)
* **Teil-Wiederholungen:** Bei Klick auf "Wiederholen" (Retry) bei einem fehlgeschlagenen oder abgebrochenen Job wird die Pipeline nicht mehr komplett von vorne ausgeführt. Bereits erfolgreiche Stufen (`metadata`, `convert`) werden übersprungen.
* **Intelligenter Outbox-Bypass:** Der Worker prüft die physische Existenz der Zieldateien (oder deren konvertierten `.mkv`-Pendants) in der Outbox. Bei Existenz werden Pfade, Dateinamen und Serien-Titel direkt aus dem persistenten Manifest übernommen, um redundante Konvertierungen oder Downloads zu vermeiden.
* **Selektives Kopieren:** Nachträglich in den Einstellungen aktivierte Storage-Targets (z.B. pCloud), die im ursprünglichen Job nicht ausgewählt waren, werden beim Retry korrekt übersprungen.

### 2. Pro-Job-Logging (Strang 1)
* **Eigene Logdateien:** Jeder Job schreibt seine Ausgaben nun in eine dedizierte Logdatei unter `data/logs/job-{task_id}.log`.
* **Thread-safe Tracing:** Die Logs werden parallel geschrieben, und Thread-Namen werden dynamisch angepasst, um Fehleranalysen präzise und übersichtlich zu gestalten.
* **Automatische Log-Retention:** Logdateien werden automatisch nach 14 Tagen bereinigt, um unnötigen Speicherplatzverbrauch zu verhindern.

### 3. NFO-Datenverlust-Schutz & Quarantäne-Strukturierung (Strang 2 & 3)
* **Sicherheits-Guards:** Ein Schutzmechanismus in der Löschfunktion verhindert, dass kuratierte Sidecar-Dateien (`tvshow.nfo`, `season.nfo`) auf dem NAS durch automatisierte Cleanup- oder Reconciliation-Aktionen gelöscht oder verschoben werden.
* **Papierkorb-Kollisionsschutz:** Dateien im Papierkorb (`.medienwerkzeug-trash`) werden kollisionssicher strukturiert abgelegt, um ein Überschreiben älterer gelöschter Dateien zu verhindern.

### 4. ID-basiertes Serien-Matching (Strang 5)
* **Ordner-Split-Schutz:** Weicht der ermittelte Serienname leicht vom tatsächlichen Ordnernamen auf dem NAS ab, sucht der Worker (und das Vorschau-System) per ID-Abgleich (TMDB, TVDB, Show-ID) in allen existierenden `tvshow.nfo`-Dateien auf dem NAS. Dadurch wird die Episode im korrekten Ordner einsortiert und die Entstehung von doppelten Serienordnern verhindert.

### 5. Robuste Mediathek-URL-Auflösung (Strang 6)
* **HTTP 308-Redirect-Kompensation:** Ein angepasster Redirect-Handler kompensiert HTTP 308-Weiterleitungen (z. B. bei ZDF-Sendungs-Links) und verhindert Abstürze beim HTML-Scraping.
* **Fallback-Pfad-Heuristik:** Falls eine URL offline ist oder das Scraping fehlschlägt, rekonstruiert eine Heuristik das Topic direkt aus dem URL-Pfad (z. B. `/comedy/heute-show` -> `Heute Show`). Ungültige oder unauflösbare URLs werden sicher abgefangen, statt mit rohen URLs in die Suche zu laufen.

---

## Technische Änderungen & Commits
* Version-Bumps in `Dockerfile`, `gui/core/utils.py` und `package.json` auf `1.1.0`.
* Testabdeckung um umfassende Integrationstests für Pipeline-Bypass und Mediathek-Redirects erweitert (Gesamtanzahl Tests: 296 Passed).
* Ignorieren des `.serena/`-Arbeitsordners in `.gitignore`.
