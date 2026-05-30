# Entwickler- & KI-Review-Richtlinien (REVIEW.md) 🔍🛠️

Leitfaden und Onboarding-Hilfe für Entwickler und KIs, die an der Medienwerkzeug-
Codebase arbeiten. Beschreibt Architektur, Coding-Leitplanken und Wartung.

---

## 🏛️ Architektur-Prinzipien

### 1. Flask-Backend mit Blueprints
* Das Backend ist eine **Flask-App**. Einstiegspunkt ist
  [gui/main.py](gui/main.py): registriert die Blueprints und startet beim Hochfahren
  die Hintergrund-Threads (`job_queue_worker`, `folder_size_monitor`).
* Die Endpunkte sind nach Domäne in Blueprints unter `gui/api/` aufgeteilt
  (`system_api`, `project_api`, `nas_api`, `search_api`, `queue_api`,
  `youtube_api`). Die HTTP-/JSON-Schicht ist dünn — die Logik liegt in
  `gui/core/` und `gui/workers/`. Endpunkt-Übersicht: siehe [API.md](API.md).
* **Schlanke Abhängigkeiten:** nur Flask/Werkzeug/Flask-Cors (siehe
  `requirements.txt`). Schwere Aufgaben (Download, Upload, Transkodierung) laufen
  über System-Tools (`yt-dlp`, `rclone`, `ffmpeg`) via `subprocess`.

### 2. Einfaches Frontend (Vanilla Web)
* Frontend unter `gui/static/` — reines HTML/CSS/JS, **kein Build-Schritt**.
* `app.js` wird in `index.html` mit Cache-Buster geladen (`app.js?v=N`). Bei
  JS-Änderungen den Wert **erhöhen**, damit der Browser neu lädt.

### 3. Thread-Sicherheit
* Medienjobs laufen asynchron. `job_queue_worker` (in
  [gui/workers/processor.py](gui/workers/processor.py)) arbeitet eine
  `queue.Queue` ab.
* Zugriffe auf den globalen Job-Status (`active_jobs`) werden über
  `active_jobs_lock` geschützt. Neue Hintergrund-Threads immer als `daemon=True`.

---

## 🗂️ Projektstruktur

```
gui/
  main.py            Flask-App, Blueprint-Registration, Server-Start
  mw_metadata.py     TMDB/TVDB/TVmaze-Scraping, NFO-Generierung
  api/               Blueprints (ein Modul je Domäne)
  core/
    helpers.py       Log-Queue, sanitize_*, is_path_allowed, Ordner-Monitor
    media.py         ffprobe, Konvertierungs-Schätzung/-Historie, get_media_info
    transfers.py     NAS-Mount, rsync, rclone, walk_nas_categories
    utils.py         Settings, Profile, Historie-I/O
    notifications.py macOS/Telegram/WhatsApp
    health.py        Feature 3: Media Health Dashboard
    duplicates.py    Feature 4: NAS-weite Duplikat-Erkennung
  workers/
    processor.py     job_queue_worker, process_worker
    youtube_worker.py Abo-Checks, Auto-Download
  static/            Frontend (index.html, app.js, style.css, utilities.css)
  data/              Laufzeitdaten (gitignored): Profile, Historie, Scan-Caches
tests/               Unit-Tests
```

### Test-Kompatibilitäts-Fassaden (wichtig zu wissen)
* [gui/server.py](gui/server.py) ist **kein** laufender Server, sondern eine
  Fassade **nur für die Unit-Tests**: Sie stellt die alte `GUIRequestHandler`-API
  bereit und leitet die Aufrufe über den Flask-Test-Client an die echten
  Endpunkte weiter. Die App selbst importiert `gui/server.py` nicht.
* [gui/api/endpoints.py](gui/api/endpoints.py) ist eine schmale Kompatibilitäts-
  Fassade (re-exportiert `load_settings`/`save_settings`) für dieselben Tests.

---

## 🚦 Kritische Coding-Leitplanken (Must-Follow)

### 1. Bereinigung von Namen (Sanitization)
Aus Metadaten generierte Ordner-/Dateinamen dürfen keine FS-/Cloud-ungültigen
Zeichen (`/`, `:` …) enthalten. Nutze `sanitize_filename(name)` und für
Seriennamen `clean_series_name_for_fs(name)` (in `gui/core/helpers.py`).

### 2. Outbox als Quelle der Wahrheit (kein In-Place-Processing)
Nie direkt in der Inbox umbenennen. Ablauf: Inbox → sauber benannter Ordner in
der **Outbox** → von dort nach NAS (rsync) und/oder pCloud (rclone) → am Ende
das temporäre Inbox-Projekt löschen.

### 3. Artwork bei Filmen
Sowohl generische (`poster.jpg`/`fanart.jpg`) als auch benannte Versionen
(`[Filmname]-poster.jpg` …) müssen im Zielordner existieren; fehlende Variante
aus der anderen kopieren.

### 4. Substring-basierte Kategorie-Zuordnung
NAS-Endpunkte lesen `destination_id` aus **Query und Body**. Fehlt ein ID-Treffer
in `settings.json`, per Fallback prüfen, ob ein konfigurierter `nas_sub` im
gesendeten Pfad enthalten ist.

### 5. Pfad-Sicherheit bei Löschvorgängen
Lösch-Endpunkte (z. B. Duplikat-Auflösung) müssen den Zielpfad gegen die NAS-Root
prüfen (Containment via `os.path.commonpath`) und nur erwartete Dateitypen löschen.

### 6. Sprache
Alle nutzersichtbaren Logs, Benachrichtigungen und UI-Texte auf **Deutsch**.

---

## 📝 Checkliste für Code-Änderungen

1. **Fehlerbehandlung:** Endpunkte dürfen nie abstürzen; `try/except` und
   strukturierte JSON-Fehler zurückgeben.
2. **Daemon-Threads:** neue Hintergrund-Threads mit `daemon=True`.
3. **Cache-Buster:** bei JS-Änderungen `app.js?v=N` in `index.html` erhöhen.
4. **Keine verwaisten Preview-Daten** nach Job-Start.
5. **Mock-Ziele in Tests:** Funktionen im **kanonischen Modul** patchen, in dem
   der Endpunkt/Worker sie aufruft (z. B. `gui.workers.processor.ensure_nas_mounted`),
   nicht auf der `gui/server.py`-Fassade — Re-Bindings propagieren sonst nicht.

---

## 🔍 Onboarding & Navigation

1. **Einstieg/Routing:** Beginne in [gui/main.py](gui/main.py) und den Blueprints
   unter `gui/api/`. Jedes Feature hat einen `handle_api_*`-Endpunkt.
2. **Lebenszyklus eines Jobs:**
   1. Frontend (`app.js`) sendet POST an `/api/process` (queue_api).
   2. Der Job wird in die `job_queue` (in `gui/core/helpers.py`) eingereiht.
   3. `job_queue_worker` (in `gui/workers/processor.py`) holt ihn und ruft
      `process_worker` auf.
   4. `process_worker` sortiert/benennt um, generiert NFOs (über `mw_metadata.py`)
      und kopiert via `gui/core/transfers.py` nach NAS/pCloud; ein Progress-
      Callback meldet den Fortschritt.
3. **Diagnose:** Live-Logs in `gui/logs/medienwerkzeug.log`. Tests mit
   `python3 -m unittest discover -s tests`.

---

## 🛠️ Pflege & Erweiterung

### Verantwortlichkeiten in `gui/core/`
* `utils.py` — reine Hilfsfunktionen (Settings/Profile/Historie), keine
  Nebeneffekte; importiert keine anderen internen Module.
* `helpers.py` — Logging, Sanitize, Pfadprüfung, Ordner-Monitor.
* `transfers.py` — Netzwerk/Mounts/rsync/rclone, `walk_nas_categories`.
* `media.py` — ffprobe, Konvertierungs-Schätzung/-Historie.
* `health.py` / `duplicates.py` — die NAS-Analyse-Features (Hintergrund-Scan +
  Cache in `gui/data/`).
* Zirkuläre Importe vermeiden.

### Frontend
Modern und responsiv, reines CSS in `style.css`/`utilities.css`. Neue JS-Funktionen
modular und dokumentiert in `app.js`.

### Testabdeckung
Bei Änderungen an kritischen Funktionen (Pfaderzeugung, Namensbereinigung,
Empfehlungslogik …) passende Unit-Tests in
[tests/test_utils.py](tests/test_utils.py) ergänzen. Vor jedem Commit die gesamte
Suite ausführen.
