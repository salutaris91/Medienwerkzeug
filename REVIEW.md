# Entwickler- & KI-Review-Richtlinien (REVIEW.md) 🔍🛠️

Dieses Dokument dient als Leitfaden und Onboarding-Hilfe für Entwickler und KIs, die an der Medienwerkzeug-Codebase arbeiten. Es beschreibt die Kernprinzipien der Architektur, Codierungs-Leitplanken und Wartungsvorschriften.

---

## 🏛️ Architektur-Prinzipien

### 1. Minimalistische Abhängigkeiten (Zero-Dependency-Backend)
* **Keine Frameworks:** Das Backend verwendet bewusst **kein** Flask, FastAPI oder Django. Stattdessen wird die Python-Standardbibliothek mit `http.server.ThreadingHTTPServer` genutzt. Dies sorgt für eine extrem schlanke App, die auf jedem macOS-System ohne `pip install` sofort läuft.
* **Externe CLIs:** Für schwere Aufgaben wie YouTube-Downloads und Cloud-Uploads verlässt sich die App auf etablierte System-Tools (`yt-dlp`, `rclone`), die via `subprocess` ausgeführt werden.

### 2. Einfaches Frontend (Vanilla Web)
* Das Frontend befindet sich unter `gui/static/` und besteht aus reinem, modernem Vanilla HTML, CSS (flex/grid) und JavaScript.
* **Kein Build-Schritt:** Es gibt keinen Webpack/Vite/Babel/Tailwind-Build-Schritt. Änderungen an HTML/JS/CSS sind nach einem Browser-Reload sofort aktiv.

### 3. Thread-Sicherheit
* Medienverarbeitungen laufen asynchron im Hintergrund. Die App besitzt einen dedizierten Thread (`job_queue_worker`), der eine `queue.Queue` abarbeitet.
* Alle Zugriffe auf den globalen Zustand der Jobs (`active_jobs`) werden streng über `active_jobs_lock` geschützt.

---

## 🚦 Kritische Coding-Leitplanken (Must-Follow)

### 1. Bereinigung von Namen (Sanitization)
* **Pfadsicherheit:** Ordnernamen, die aus TMDB- oder TVDB-Metadaten generiert werden (z. B. Seriennamen), dürfen keine Zeichen enthalten, die auf Dateisystemen oder Cloud-Remotes ungültig sind (z. B. `/` oder `:`).
* **Funktion:** Verwende für alle Ordnerpfade und Dateinamen die Bereinigung `sanitize_filename(name)` und für Seriennamen zusätzlich `clean_series_name_for_fs(name)` in `gui/server.py`, um ungültige Zeichen sowie suchspezifische Suffixe (wie `(Mediathek Serie aus URL)`) und Sender-Tags (wie `[ARTE]`) zu entfernen.

### 2. Ausgabe-Ordner (Outbox) als Quelle der Wahrheit
* **Kein In-Place-Processing:** Dateien dürfen niemals direkt im Ordner `Medien Input` (Inbox) umbenannt und belassen werden.
* **Ablauf:** 
  1. Zuerst werden die Dateien in den sauber benannten Zielordner in `Medien Output` (Outbox) verschoben.
  2. Falls NAS aktiv ist, wird die Struktur von der Outbox auf das NAS kopiert.
  3. Falls pCloud aktiv ist, wird der Upload ebenfalls performant aus der lokalen Outbox gestartet.
  4. Am Ende wird das temporäre Projektverzeichnis in der Inbox gelöscht.

### 3. Artwork-Synchronisation bei Filmen
* Beim Verarbeiten von Filmen müssen sowohl die generischen Metadaten-Bilder (`poster.jpg`, `fanart.jpg`) als auch die benannten Versionen (`[Filmname]-poster.jpg`, `[Filmname]-fanart.jpg`) im Zielordner existieren. Fehlt eine Variante, muss sie automatisch von der anderen kopiert werden.

### 4. Substring-basierte Kategorie-Zuordnung
* Bei der Auswahl der NAS-Kategorie im Frontend wird oft ein Pfad (z. B. `/Volumes/Kino/Dokus/Einzelne Dokus`) gesendet. Falls kein ID-Treffer in `settings.json` existiert, muss das Backend einen Fallback-Vergleich durchführen, ob ein konfigurierter Kategorie-Pfad (`nas_sub`) im gesendeten Pfad enthalten ist.

### 5. Sprache und Benutzeroberfläche
* Alle für den Nutzer sichtbaren Konsolen-Logs, Benachrichtigungen und UI-Texte werden auf **Deutsch** gehalten.

---

## 📝 Checkliste für Code-Änderungen (Review-Checklist)

1. **Startort des Servers:** Der Server darf ausschließlich aus dem Dokumentenordner `/Users/alex/Documents/Medienwerkzeug/gui/server.py` gestartet werden.
2. **Daemon-Threads:** Alle neu erzeugten Hintergrund-Threads müssen als Daemon initialisiert werden (`daemon=True`), damit der Server beim Beenden nicht blockiert.
3. **Fehlerbehandlung:** APIs dürfen niemals abstürzen oder unvollständige JSONs ausliefern. Fange Ausnahmen (`try-except`) ab und liefere strukturierte Fehlermeldungen an das Frontend zurück.
4. **Keine verwaisten Preview-Daten:** Nach erfolgreicher Vorschau-Erstellung müssen die temporären Zuordnungen sauber gelöscht werden, sobald der eigentliche Job startet.

---

## 🔍 Spezifische Tipps zum Verständnis der App (Onboarding & Navigation)

Wenn du dich als KI oder Entwickler dieser Codebase näherst, gehe am besten in dieser Reihenfolge vor:

### 1. Einstiegspunkt & API-Routing
* Starte bei [gui/server.py](file:///Users/alex/Documents/Medienwerkzeug/gui/server.py). Hier siehst du die HTTP-Endpunkte in `do_GET` und `do_POST`. Jedes Feature (z. B. StreamFab-Import, Film/Serien-Sortierung, YouTube-Schnitt) besitzt einen korrespondierenden `handle_api_*`-Handler.
* Beachte, dass `server.py` nur noch für HTTP-Routing und JSON-Verpackung zuständig ist. Die Logik liegt in den Modulen unter `gui/core/`.

### 2. Der Lebenszyklus eines Medien-Jobs
1. **Frontend-Anfrage:** Der Nutzer löst eine Aktion im UI aus. `gui/static/app.js` sendet einen POST-Request an `/api/process` mit allen Parametern (`media_type`, `mappings`, etc.).
2. **Warteschlange (Queue):** [gui/server.py](file:///Users/alex/Documents/Medienwerkzeug/gui/server.py) ruft `jobs.add_job()` auf. Dadurch wird der Job in die Warteschlange [gui/core/jobs.py](file:///Users/alex/Documents/Medienwerkzeug/gui/core/jobs.py) eingereiht.
3. **Sequentielle Abarbeitung:** Der im Hintergrund laufende Thread `job_queue_worker` holt den Job aus der Queue und ruft die registrierte Worker-Funktion `process_worker` in [gui/core/media.py](file:///Users/alex/Documents/Medienwerkzeug/gui/core/media.py) auf.
4. **Verarbeitung & Synchronisation:** `media.py` führt die Sortierung, Umbennung und NFO-Generierung durch und ruft [gui/core/sync.py](file:///Users/alex/Documents/Medienwerkzeug/gui/core/sync.py) für Kopiervorgänge (NAS/pCloud) auf. Währenddessen meldet ein Progress-Callback den Fortschritt zurück an `jobs.py`.

### 3. Diagnose und Debugging
* **Live-Logs:** Schau dir die Datei `gui/logs/medienwerkzeug.log` an, um Details zu Kopiervorgängen, API-Fehlern oder API-Antworten zu sehen.
* **Unit-Tests:** Führe `python3 -m unittest discover -s tests -p "test_*.py"` aus, um sicherzustellen, dass Hilfsfunktionen (z. B. zur Namensbereinigung) fehlerfrei arbeiten.

---

## 🛠️ Anweisungen zur Pflege & Erweiterung (Maintenance Guide)

Damit das Medienwerkzeug auch langfristig stabil und wartbar bleibt, müssen folgende Richtlinien beachtet werden:

### 1. Sauberkeit der Kern-Module (`gui/core/`)
* **Verantwortlichkeiten trennen:**
  * [utils.py](file:///Users/alex/Documents/Medienwerkzeug/gui/core/utils.py): Reine Hilfsfunktionen (Settings lesen/schreiben, String-Manipulationen, Pfad-Auflösungen). Keine Nebeneffekte.
  * [sync.py](file:///Users/alex/Documents/Medienwerkzeug/gui/core/sync.py): Netzwerk, Mounts, pCloud (rclone), rsync.
  * [jobs.py](file:///Users/alex/Documents/Medienwerkzeug/gui/core/jobs.py): Thread-Steuerung, Warteschlangen, Job-Status.
  * [media.py](file:///Users/alex/Documents/Medienwerkzeug/gui/core/media.py): TMDB/TVDB Metadaten-Handling, NFO-Generierung, Ordnerstruktur-Generierung.
* **Import-Hierarchie einhalten:**
  * `utils.py` darf keine anderen internen Module importieren.
  * `sync.py` und `jobs.py` importieren nur Standard-Module und `utils.py`.
  * `media.py` darf `utils.py`, `sync.py` und `jobs.py` importieren.
  * `server.py` importiert die Core-Module und delegiert an sie.
  * Vermeide zirkuläre Importe unter allen Umständen.

### 2. Änderungen am Frontend
* Änderungen am Layout oder Design müssen stets modern und responsiv gestaltet sein. Verwende reines CSS (kein Tailwind oder externe UI-Frameworks) in [gui/static/style.css](file:///Users/alex/Documents/Medienwerkzeug/gui/static/style.css).
* Neue JavaScript-Funktionen in [gui/static/app.js](file:///Users/alex/Documents/Medienwerkzeug/gui/static/app.js) sollten modular aufgebaut und sauber dokumentiert sein.

### 3. Erweiterung der Testabdeckung
* Jedes Mal, wenn kritische Funktionen in `utils.py` oder `media.py` (wie Pfaderzeugung, Namensbereinigung, etc.) angepasst werden, **müssen** entsprechende Unit-Tests in [tests/test_utils.py](file:///Users/alex/Documents/Medienwerkzeug/tests/test_utils.py) hinzugefügt werden.
* Führe vor jedem Commit/Release die gesamte Testsuite lokal aus.

