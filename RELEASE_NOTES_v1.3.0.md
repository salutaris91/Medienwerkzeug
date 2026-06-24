# Release Notes — Medienwerkzeug v1.3.0

Dieses Release bringt einen zuverlässigen NAS-Überschreibschutz für Filme (inkl. Plaintext-Medienvergleich), die typisierte Erkennung und UI-Unterstützung von Inbox-Einzeldateien sowie eine stark verbesserte, kontextsensitive Filmsuche, die echte Filmtitel nicht mehr versehentlich beschneidet.

---

## Highlights in v1.3.0

### 1. NAS-Überschreibschutz & Medienvergleich für Filme (#30)
* **Zentraler Schutz vor Überschreiben:** Bei Transfers zu NAS-Zielen wird nun ein opt-in Überschreibschutz aktiviert. Existiert der Zielpfad bereits, wird die vorhandene Datei automatisch in einen Quarantäne-Papierkorb (`.medienwerkzeug-trash`) auf dem NAS verschoben, anstatt sie unwiderruflich zu überschreiben. Schlägt dieses Verschieben fehl, wird der gesamte Transfer abgebrochen.
* **Plaintext-Medienvergleich im UI:** Kollisionen werden nach dem Ermitteln der finalen Dateinamen geprüft. Treten Kollisionen auf, zeigt das UI ein rotes Warnungs-Banner mit einer tabellarischen Gegenüberstellung der Medienparameter (Dateiname, Dateigröße, Auflösung, Video-/Audio-Codec, Bitrate, Dauer sowie eine automatische Qualitäts-Einschätzung) der vorhandenen und der neuen Datei.

### 2. Typisierte Inbox-Einzeldateien (#31)
* **Saubere Unterscheidung:** Einzeldateien in der Inbox werden jetzt typisiert erfasst und nicht mehr als Ordner-Projekte behandelt.
* **UI-Integration:** Im UI werden Einzeldateien durch ein Film-Icon (`🎥`) anstelle eines Ordners dargestellt. Tooltips, Buttons und Bestätigungsdialoge passen sich dynamisch an, um vom "Ordner verschieben" auf "Datei verschieben" umzustellen.
* **Robuster UI-Status:** Das Icon bleibt auch nach Status-Updates (z. B. nach dem Starten einer Verarbeitung) korrekt erhalten, da der Ordnertyp im DOM-Element (`data-is-dir`) mitgeführt wird.

### 3. Kontextsensitive & robuste Filmsuche (#32)
* **Titel-Erhaltung:** Sprach- und Release-Tags (z. B. `german`, `dl`, `1080p`) werden nur noch dann abgeschnitten, wenn sie in einem klaren Release-Kontext stehen. Echte Filmtitel wie *"The French Dispatch"* oder *"The English Patient"* bleiben dadurch vollständig erhalten.
* **Smarte Jahreszahl-Filterung:** Titel, die mit einer Jahreszahl beginnen (z. B. *"2001: Odyssee im Weltraum"*), werden nicht mehr fälschlicherweise beim ersten Jahr abgeschnitten, sondern das System filtert erst am echten Release-Jahr bzw. bei nachfolgenden Scene-Tags.
* **Fallback auf Videodateiname:** Wenn ein Projekt in einem generischen Ordner liegt (z. B. `Downloads`, `Neuer Ordner`, `Film`), nutzt das System automatisch den Namen der darin enthaltenen Videodatei als Suchbegriff.

---

## Technische Änderungen & Commits
* Version-Bumps in `Dockerfile`, `gui/core/utils.py` und `package.json` auf `1.3.0`.
* Umfassende Unit-Tests für Scene-Tag-Filterung, Jahreszahl-Heuristiken, generische Ordnernamen und den Quarantäne-Transferpfad hinzugefügt (`tests/test_movie_processing_fixes.py` und `tests/test_transfers_fallback.py`).
* Whitespace-Bereinigung über das gesamte Diff (`git diff --check` läuft fehlerfrei durch).
* Aktualisierung des Wissensgraphen via Graphify.
