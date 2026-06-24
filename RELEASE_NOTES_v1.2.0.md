# Release Notes — Medienwerkzeug v1.2.0

Dieses Release bringt eine verfeinerte TV-Untertitel-Zuordnung (inkl. einer neuen Walk-Up-Pfaddistanz-Heuristik) sowie deutliche Verbesserungen am Web-Folder-Picker (Breiten-Layout und dynamische Titel je nach Kategorie).

---

## Highlights in v1.2.0

### 1. TV-Pfad Untertitel-Erkennung (#25)
* **Lockeres Matching:** Die strenge Bindung an `basename.startswith(...)` in `queue_api.py` wurde für Untertitel gelockert. Fremd benannte Untertitel (z.B. `ger_forced.sub` in einem Unterordner neben `S01E01.mkv`) werden jetzt sicher zugeordnet, wenn es keine Mehrdeutigkeiten mit anderen Videos im selben Ordner gibt.
* **Walk-Up-Pfaddistanz-Heuristik:** Ein übergeordnetes Video im Projekt-Root (oder in einem übergeordneten Ordner) darf Untertitel aus Unterordnern nur dann matchen, wenn kein anderer Ordner mit eigener Videodatei dazwischen liegt. Das verhindert Fehlzuordnungen von Subfolders (z. B. `Bonus/ger_forced.sub`) an das Root-Video.
* **Erhöhte Transparenz:** Nicht zuordenbare oder mehrdeutige lose Untertitel (wie `Extra/loose.srt` bei mehreren Videos) werden in der Vorschau-API nun explizit als `junk` klassifiziert, um den Anwender im UI zu informieren.

### 2. Dynamische Titel im Web-Folder-Picker (#27)
* **Kategoriebezogene Titel:** Die Lupe zur Ordnerauswahl übergibt nun den Namen der Kategorie. Das Modal zeigt daraufhin dynamisch an, wofür der Ordner gewählt wird (z. B. **"📂 Ordner für Serien auswählen"** oder **"📂 Ordner für Filme auswählen"**), was die Benutzerführung verbessert.

### 3. Layout-Verbreiterung im Web-Folder-Picker (#28)
* **Responsiver Platzgewinn:** Die maximale Breite des Picker-Modals in `index.html` wurde von `500px` auf `700px` (90% Viewport-Breite) erhöht. Dies erleichtert das Navigieren und Lesen langer, verschachtelter Verzeichnispfade auf Desktop- und Tablet-Monitoren.

---

## Technische Änderungen & Commits
* Version-Bumps in `Dockerfile`, `gui/core/utils.py` und `package.json` auf `1.2.0`.
* Testabdeckung in `tests/test_fix_series_queue_and_naming.py` um umfassende Integrationstests für das Subtitle-Matching (Root- vs. Subfolder-Divergenz, Verschachtelungstiefe und Ambivalenzvermeidung) erweitert.
* Bereinigung aller trailing whitespaces über das gesamte Diff hinweg (`git diff --check` ist vollständig fehlerfrei).
* Synchronisation des Wissensgraphen via Graphify.
