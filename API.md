# Medienwerkzeug API-Dokumentation 📡

Diese Datei dokumentiert alle REST-Endpunkte des Medienwerkzeug-HTTP-Servers. Die Kommunikation erfolgt ausschließlich via JSON.

---

## 📥 GET Endpunkte

### 1. Status & Inbox (`GET /api/status`)
Gibt den aktuellen Status des Servers sowie die Inhalte des Import-Ordners (`Medien Input`) zurück.
* **Response (JSON):**
  ```json
  {
    "status": "ok",
    "inbox": [
      {
        "name": "Film_Projektordner_1",
        "is_dir": true,
        "files": ["video.mkv", "subtitle.srt"]
      }
    ]
  }
  ```

### 2. Ordner-Browser (`GET /api/browse-folder`)
Ermöglicht das Durchsuchen des lokalen Dateisystems (für die Pfadauswahl in den Einstellungen).
* **Query-Parameter:**
  * `path` (optional): Der zu durchsuchende absolute Pfad. Wenn leer, wird das Benutzer-Heimatverzeichnis (`~`) gelistet.
* **Response (JSON):**
  ```json
  {
    "current_path": "/Users/alex",
    "folders": ["Desktop", "Documents", "Downloads"]
  }
  ```

### 3. Projekt-Dateiscan (`GET /api/scan-project`)
Scannt einen spezifischen Ordner in der Inbox nach Videos, Untertiteln und unbenötigten Dateien (Junk).
* **Query-Parameter:**
  * `project`: Name des Projektordners in der Inbox.
* **Response (JSON):**
  ```json
  {
    "videos": ["film.mkv"],
    "subs": ["film.srt"],
    "junk": ["unused.txt", "banner.jpg"]
  }
  ```

### 4. Metadaten-Suche (`GET /api/search`)
Sucht nach Filmen oder Serien auf TMDB bzw. TVDB.
* **Query-Parameter:**
  * `type`: Typ der Suche (`movie` oder `tv`).
  * `q`: Der Suchbegriff.
* **Response (JSON):** Liste gefundener Einträge mit IDs, Titeln, Veröffentlichungsdaten und Cover-Pfaden.

### 5. Serien-Details (`GET /api/fetch-show-info`)
Ruft Detailinformationen zu einer TVDB-Serien-ID ab.
* **Query-Parameter:**
  * `id`: TVDB Serien-ID.
* **Response (JSON):** Details zur Serie (Episodenanzahl, Staffeln etc.).

### 6. Episoden-Liste (`GET /api/fetch-episodes`)
Ruft alle Episoden einer bestimmten Staffel einer TVDB-Serie ab.
* **Query-Parameter:**
  * `id`: TVDB Serien-ID.
  * `season`: Staffelnummer (z. B. `1`).
* **Response (JSON):** Liste der Episoden mit Episodennummern und Titeln.

### 7. YouTube-Metadaten (`GET /api/yt/fetch`)
Liest über `yt-dlp` Metadaten einer YouTube-URL ein.
* **Query-Parameter:**
  * `url`: YouTube Video- oder Playlist-URL.
* **Response (JSON):** Titel, Beschreibung, Thumbnail-URL und Videoliste.

### 8. Job-Warteschlange (`GET /api/queue`)
Gibt den Status aller aktuellen und abgeschlossenen Hintergrund-Jobs zurück.
* **Response (JSON):**
  ```json
  {
    "jobs": {
      "job_1716300000": {
        "status": "running|completed|error",
        "progress": 50,
        "message": "Kopiere nach NAS...",
        "params": {}
      }
    }
  }
  ```

### 9. Einstellungen abrufen (`GET /api/settings`)
Gibt die aktuelle Konfiguration zurück.
* **Response (JSON):** JSON-Inhalt der `settings.json`.

### 10. Ordner im Finder öffnen (`GET /api/system/open-folder`)
Öffnet einen Ordnerpfad auf dem macOS-System im Finder.
* **Query-Parameter:**
  * `path`: Absoluter Ordnerpfad, der geöffnet werden soll.
* **Response (JSON):** Statusmeldung oder Fehlermeldung bei Problemen.

### 11. Witz des Tages (`GET /api/joke`)
Gibt einen zufälligen Flachwitz für Modals und Toast-Einblendungen zurück.
* **Response (JSON):** `{"joke": "Flachwitz..."}`

### 12. YouTube-Abonnements abrufen (`GET /api/youtube/subscriptions`)
Gibt alle eingetragenen YouTube-Kanäle und Playlist-Abonnements zurück.
* **Response (JSON):** `{"subscriptions": [...]}`

---

## 📤 POST Endpunkte

### 1. Vorschau der Bereinigung (`POST /api/preview_clean`)
Zeigt vorab, welche Junk-Dateien gelöscht werden würden.
* **Payload (JSON):**
  ```json
  {
    "project": "Projektname"
  }
  ```
* **Response (JSON):** Liste der zu löschenden Dateien.

### 2. Projekt bereinigen (`POST /api/clean-project`)
Löscht Junk-Dateien aus einem Projektordner in der Inbox.
* **Payload (JSON):**
  ```json
  {
    "project": "Projektname"
  }
  ```

### 3. Vorschau der Verarbeitung (`POST /api/preview_process`)
**Wichtig für die Bestätigung:** Generiert eine detaillierte Zuordnungsliste, welche Dateien wie umbenannt und wohin verschoben/kopiert/hochgeladen werden.
* **Payload (JSON):** Enthält Metadaten-Mappings, Typ (`movie`/`tv`), Zielordner und IDs.
* **Response (JSON):**
  ```json
  {
    "dest_preview": "NAS: /Volumes/Kino/Filme/Film (2026)",
    "video_mappings": [{"old": "temp.mkv", "new": "Film (2026).mkv"}],
    "subs": [{"old": "temp.srt", "new": "Film (2026).srt"}],
    "junk": ["junk.txt"]
  }
  ```

### 4. Verarbeitung starten (`POST /api/process`)
Reiht einen neuen Job in die Warteschlange ein, um die Dateien umzubenennen, in die Outbox zu verschieben und die NAS/pCloud-Synchronisation anzustoßen.
* **Payload (JSON):** Ähnlich wie `preview_process`, zusätzlich mit ausgewählten Dateilisten (Checkboxen aus dem Frontend).
* **Response (JSON):**
  ```json
  {
    "status": "ok",
    "task_id": "job_1716300000"
  }
  ```

### 5. YouTube-Verarbeitung finalisieren (`POST /api/yt/finalize`)
Startet den finalen YouTube-Download und die Sortierung.
* **Payload (JSON):** YouTube-URL, Zielordner-Details, Qualitätsstufe etc.
* **Response (JSON):** Statusmeldung und Task-ID.

### 6. Einstellungen speichern (`POST /api/settings`)
Speichert geänderte Einstellungen.
* **Payload (JSON):** Gesamtes neues Einstellungs-JSON-Objekt.

### 7. YouTube-Abonnements speichern (`POST /api/youtube/subscriptions`)
Aktualisiert die Liste aller YouTube-Kanäle und Playlist-Abonnements.
* **Payload (JSON):** `{"subscriptions": [...]}`
* **Response (JSON):** `{"status": "success"}`

### 8. YouTube-Abonnements prüfen (`POST /api/youtube/subscriptions/check`)
Triggert im Hintergrund die manuelle Überprüfung aller aktiven YouTube-Abonnements auf neue Videos.
* **Response (JSON):** `{"status": "success", "message": "Überprüfung gestartet"}`
