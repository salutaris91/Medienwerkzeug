# Medienwerkzeug API-Dokumentation 📡

Diese Datei dokumentiert die REST-Endpunkte des Medienwerkzeug-Backends. Die
Kommunikation erfolgt via JSON.

## Architektur

Das Backend ist eine **Flask-App** (`gui/main.py`), die ihre Endpunkte über
**Blueprints** unter dem Präfix `/api` registriert. Jede Domäne hat ein eigenes
Modul unter `gui/api/`:

| Blueprint | Modul | Zuständigkeit |
|-----------|-------|---------------|
| `system_api` | `gui/api/system_api.py` | Status, Einstellungen, Statistik, Logs, Profile |
| `project_api` | `gui/api/project_api.py` | Inbox-Projekte scannen, bereinigen, Smart Inbox |
| `nas_api` | `gui/api/nas_api.py` | NAS-Serien/-Staffeln, Duplikate, Health-Scan |
| `search_api` | `gui/api/search_api.py` | Metadaten-Suche, Episoden-Matching, Schätzung |
| `queue_api` | `gui/api/queue_api.py` | Job-Queue, Verarbeitung |
| `youtube_api` | `gui/api/youtube_api.py` | YouTube-Download, Schnitt, Abonnements |
| `nas_renamer_api` | `gui/api/nas_renamer_api.py` | NAS-Renaming mit Vorschau, Ausführung und Rollback |

Server-Start und Browser-Öffnung laufen über `gui/main.py`. Lokal läuft die App
auf `http://127.0.0.1:5001`.

> **Hinweis zu Alias-Routen:** Einige Endpunkte existieren in zwei Schreibweisen
> (z. B. `/api/paths-clean` und `/api/paths/clean`) aus Kompatibilitätsgründen.
> Unten ist jeweils die kanonische Variante dokumentiert.

---

## system_api — Status & Konfiguration

### `GET|POST /api/status`
Server- und Inbox-Status. Liefert u. a. NAS-Status, Projektliste sowie die
Ordnergrößen für die Überwachung.
```json
{
  "nas_status": "connected",
  "inbox_path": "…/Medien Input",
  "outbox_path": "…/Medien Output",
  "projects": ["Projekt_1"],
  "streamfab_downloads": [],
  "inbox_size_gb": 1.52,
  "outbox_size_gb": 0.87
}
```

### `GET|POST /api/settings`
Liest (GET) bzw. speichert (POST) die Konfiguration (`settings.json`). 
**Security:** Sensitive Felder (`telegram_token`, `whatsapp_apikey`, `tmdb_api_key`, `tvdb_api_key`) werden beim Lesen maskiert (z. B. `****abcd`). Werden maskierte Werte gepostet, überschreiben diese nicht die echten Credentials im Backend. API-Keys für TMDB/TVDB werden primär über die `gui/.env` Datei verwaltet.

### `POST /api/nas/connect`
Versucht das konfigurierte NAS sofort per SMB einzubinden und aktualisiert den
gecachten NAS-Status. Falls das direkte AppleScript-Mounting fehlschlägt, öffnet
der Server den Finder-Fallback über den konfigurierten Servernamen. Liefert eine
verständliche Meldung, wenn Netzwerk, Tailscale oder die im macOS-Schlüsselbund
gespeicherten Zugangsdaten geprüft werden müssen. Wiederholte Mount-Versuche
werden für fünf Sekunden begrenzt.

### `GET|POST /api/stats`
NAS-Speicherbelegung und Konvertierungs-Statistik (gesparter Platz etc.).

### `GET /api/conversion/recommendations` *(Feature 2)*
Empfohlene Encoding-Einstellungen pro Content-Typ, aus der Konvertierungs-Historie.
```json
{
  "recommendations": { "anime": {"optimal_quality": 55, "avg_ratio": 0.38, "sample_count": 42, "confidence": "high"} },
  "global": { "avg_ratio": 0.48, "total_conversions": 301, "total_saved_bytes": 123456 }
}
```

### `GET|POST /api/profile`, `GET|POST /api/profiles`
Einzel-Profil laden/speichern bzw. alle lokalen Profile auflisten.

### `GET|POST /api/check-dependencies`
Prüft Verfügbarkeit/Versionen externer Tools (`ffmpeg`, `yt-dlp`, `rclone`).

### `GET|POST /api/system-open-folder`
Öffnet einen Ordner im macOS-Finder. Query/Payload: `path` oder `category_id`.

### `GET|POST /api/system-restart`
Startet den Server-Prozess neu.

### `GET /api/logs`
Server-Sent-Events-Stream der Live-Logs.

---

## project_api — Inbox & Projekte

### `GET /api/scan-project?project=<Ordner>`
Scannt einen Inbox-Projektordner nach Videos, Untertiteln, Junk; erkennt Doku und
liefert `suggested_query`. Liest den Parameter aus der **Query** (GET).

### `GET /api/inbox/analyze` *(Feature 1 — Smart Inbox)*
Analysiert alle Inbox-Projekte und liefert Vorschläge mit Typ, Profil-Match,
Codec-Status und Begründungs-Chips (`reasons`).
```json
{
  "suggestions": [{
    "project": "Heroes.S01E05.720p",
    "media_type": "tv",
    "confidence": "high",
    "profile_match": true,
    "suggested_query": "Heroes",
    "video_count": 1,
    "has_inefficient_codec": true,
    "reasons": ["Profil gefunden", "Serie erkannt", "Codec ineffizient (H.265 empfohlen)"]
  }]
}
```

### `GET|POST /api/paths-preview-clean` · `GET|POST /api/paths-clean`
Vorschau bzw. Ausführung der Bereinigung von Inbox/Outbox (Payload: `inbox_files`,
`output_files` als relative Pfade).

### `GET|POST /api/browse-folder`, `/api/list-subfolders`
Dateisystem-Browser für die Pfadauswahl.

### `GET|POST /api/clean-project`, `/api/delete-project`, `/api/split-project-file`
Projekt bereinigen, löschen, Datei aufteilen.

---

## nas_api — NAS-Bibliothek

### `GET|POST /api/nas-series?destination_id=<id|all>`
Listet vorhandene Serien-/Film-Ordner einer Kategorie auf dem NAS (+ Outbox).
Liest `destination_id` aus **Query und Body**.

### `GET|POST /api/nas-seasons?folder=<Show>&destination_id=<id>`
Vorhandene Staffeln + Episodenzahlen einer Show.

### `GET|POST /api/check-nas-duplicate`, `/api/media-compare`, `/api/resolve-duplicate`
Einzel-Duplikat-Prüfung beim Verarbeiten, ffprobe-Vergleich, Auflösung.

### `GET|POST /api/streamfab-import`
Importiert StreamFab-Downloads in die Inbox.

### Feature 3 — Media Health Dashboard
* `POST /api/nas/health-scan` — startet den Bibliotheks-Scan im Hintergrund.
* `GET /api/nas/health-status` — Fortschritt + Ergebnis (gecacht). Issues nach
  Schwere (`critical`/`warning`/`info`): fehlende NFOs/Artwork, Episodenlücken,
  Codec-Inkonsistenz, leere Ordner, kleine Dateien, doppelt verschachtelte
  Filmordner (`nested_duplicate`), kryptische/unbenannte Ordner (`bad_folder_name`),
  Ordner-/Dateiname-Mismatches (`name_mismatch`).
* `POST /api/nas/health-fix` — Quick-Fix für Health-Issues. Actions:
  `flatten` (Verschachtelung auflösen), `rename_folder`, `rename_file`,
  `rename_folder_to_file`, `rename_file_to_folder`, `rename_both`.
  Payload: `{"action": "...", "path": "...", "new_name": "..."}`.
  Nur innerhalb NAS-Root, nie überschreibend.

### Feature 4 — NAS-weite Duplikat-Erkennung
* `POST /api/nas/scan-duplicates` — startet die Erkennung im Hintergrund.
* `GET /api/nas/duplicates` — Gruppen doppelter Episoden + Empfehlung (HEVC >
  Auflösung > Größe) + rückgewinnbarer Platz.
* `POST /api/nas/resolve-duplicate-global` — löscht eine gewählte Datei.
  Payload: `{"path": "<absoluter NAS-Pfad>"}`. **Sicherheit:** nur Videodateien
  unterhalb der NAS-Root werden gelöscht.

### NAS-Renamer
* `GET|POST /api/nas-renamer/preview` — erzeugt eine Dry-Run-Vorschau für
  geplante Episoden-Umbenennungen.
* `POST /api/nas-renamer/apply` — wendet ausgewählte Umbenennungen an und
  schreibt ein Transaktionslog.
* `POST /api/nas-renamer/rollback` — rollt eine gespeicherte Umbenennungs-
  Transaktion zurück.

---

## search_api — Metadaten

### `GET|POST /api/search?type=<movie|tv>&q=<Begriff>`
Sucht Filme/Serien (TMDB/TVDB/TVmaze).

### `GET|POST /api/fetch-show-info`, `/api/fetch-episodes`, `/api/match-episodes`, `/api/series-detect`, `/api/guess-season`
Serien-Details, Episodenlisten, Episoden-Zuordnung, Serien-Erkennung, Staffel-Schätzung.

### `GET|POST /api/estimate-conversion`
Schätzt die Konvertierungs-Ersparnis (Payload: `filenames`, `quality`).

### `GET|POST /api/joke`, `/api/quote`, `/api/toggle-visibility`
UI-Beiwerk und Sichtbarkeits-Toggles.

---

## queue_api — Verarbeitung

### `GET|POST /api/preview-process`
Erzeugt die detaillierte Zuordnungs-Vorschau (Umbenennung/Ziele) vor dem Job.

### `GET|POST /api/process`
Reiht einen Verarbeitungs-Job in die Queue ein (Payload: `media_type`,
`mappings`, Ziel-IDs, `copy_to_nas`/`copy_to_pcloud`, `is_anime` etc.).
```json
{ "status": "ok", "task_id": "<uuid>" }
```

### `GET|POST /api/queue`, `/api/queue-clear`, `POST /api/queue-retry`
Job-Status abrufen, abgeschlossene Jobs leeren, fehlgeschlagenen Job wiederholen.

---

## youtube_api — YouTube

### `GET|POST /api/yt/fetch`, `/api/yt/segments`, `/api/yt/cut-done`, `/api/yt/finalize`
Metadaten lesen, Segmente schneiden, finalisieren/herunterladen.

### `GET|POST /api/youtube/merge`, `/api/youtube/search-parts`
Teile zusammenführen, mehrteilige Videos suchen.

### `GET|POST /api/youtube/subscriptions`
Abonnements lesen/speichern.

### `POST /api/youtube/subscriptions/approve` · `/ignore` · `/check`
Pending-Video freigeben (reiht Download-Job ein), ignorieren, alle Abos prüfen.
