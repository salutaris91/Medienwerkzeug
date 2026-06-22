# Quarantänebereinigung (Docker-Papierkorb) - Version 3 (Kopie für das Repository)

Implementierung einer automatischen und manuellen Quarantäne- und Papierkorb-Leerung im Docker-Modus (Roadmap-Punkt 32). Dies betrifft die in den Mountpoints generierten `.medienwerkzeug-trash`-Verzeichnisse.

## User Review Required

> [!IMPORTANT]
> **Sicherheits- und Berechtigungsgrenzen (Symlinks & Verzeichnisse):**
> - Ein Symlink im Trash, der auf ein externes Verzeichnis verweist (z. B. `/outside`), darf beim Löschen **nicht** aufgelöst werden (kein `realpath` auf dem Symlink selbst), da dies sonst den externen Pfad löschen würde. 
> - Stattdessen wird der Pfad des Symlinks selbst per `abspath` und `commonpath` gegen den Trash-Ordner validiert und anschließend direkt mit `os.unlink` (bzw. `os.remove`) entfernt.
> - Echte Verzeichnisse werden per `os.path.realpath` validiert und mittels `shutil.rmtree` gelöscht (mit Deaktivierung von Symlink-Verfolgungen während der Rekursion).

> [!IMPORTANT]
> **Stale-NAS Schutz & Timeouts:**
> - Da Netzwerk-Mounts hängen können, wird der Statistik-Scan und der Vorab-Löschcheck vollständig über den isolierten `storage_probe.py` Subprocess abgewickelt.
> - Ein synchroner Dry-Run blockiert den Flask-Hauptprozess höchstens bis zum konfigurierten Timeout (z. B. 10s).
> - Falls das physische Löschen im Hintergrund-Thread aufgrund eines toten Mounts hängen bleibt (stuck state), wird das UI nach einer Zeitspanne (z. B. 5 Minuten Inaktivität) einen entsprechenden Stuck-Warnhinweis anzeigen.

> [!IMPORTANT]
> **Concurrency & Mehrfachausführung:**
> - Es darf niemals mehr als ein aktiver Löschlauf parallel ausgeführt werden. 
> - Ist `TRASH_CLEANUP_STATUS["running"] == True`, wird jeder erneute Löschversuch an `POST /api/system/trash/cleanup` sofort mit `HTTP 409 (Conflict)` abgelehnt.

## Open Questions

Keine. Alle Review-Punkte wurden eingearbeitet.

---

## Proposed Changes

### 1. Core-Erweiterung & Sicherheitsfunktionen (Backend)

#### [MODIFY] [persistence.py](file:///Users/alex/Documents/Medienwerkzeug/gui/core/persistence.py)
- **Erweiterung der Standardeinstellungen (`DEFAULT_SETTINGS`):**
  - Hinzufügen von `"trash_auto_empty": False`
  - Hinzufügen von `"trash_retention_days": 7`

#### [MODIFY] [utils.py](file:///Users/alex/Documents/Medienwerkzeug/gui/core/utils.py)
- **Konsolidierung der allowed roots (`get_allowed_roots()`):**
  - Diese Funktion wird in `utils.py` implementiert, um zirkuläre Importe zu vermeiden.
  - Sie ermittelt alle konfigurierten Verzeichnisse aus `settings.json`:
    - `inbox_dir`
    - `outbox_dir`
    - `nas_root`
    - `storage_targets` (Felder `root_path` oder `path`)
    - `import_sources` (Unterstützung für Strings und Dictionaries)
    - `local_download_folders` (neu aufgenommen)

#### [MODIFY] [helpers.py](file:///Users/alex/Documents/Medienwerkzeug/gui/core/helpers.py)
- **Sicherheits-Check:** `is_path_allowed(target_path)` nutzt die konsolidierte `get_allowed_roots()` aus `utils.py`.

#### [MODIFY] [trash.py](file:///Users/alex/Documents/Medienwerkzeug/gui/core/trash.py)
- **Implementierung des Cleaners:**
  - `get_trash_stats()`:
    - Nutzt `get_allowed_roots()`, findet die Mountpoints und ruft `storage_probe.py` im Modus `trash_stats` auf.
    - Cacht die Werte im RAM, damit `/api/system/trash/stats` sofort antwortet.
  - `empty_trash_async(retention_days=None, dry_run=False)`:
    - Prüft den Concurrency-Status. Wenn `TRASH_CLEANUP_STATUS["running"] == True`, wird eine Exception geworfen.
    - Setzt den globalen `TRASH_CLEANUP_STATUS` auf `running: True`, `started_at` auf den aktuellen Timestamp und startet einen Thread für das physische Löschen.
  - **Präziser Lösch-Algorithmus (im Thread):**
    - Vorab-Schreibtest: Legt eine Dummy-Datei im Trash an und löscht sie.
    - Iteration über Ordner im Format `YYYY-MM-DD_HH-MM-SS`.
    - Für jedes Element (Datei, Verzeichnis oder Symlink):
      1. Falls es sich um einen Symlink handelt (geprüft mit `os.path.islink` oder `lstat`):
         - Validiere den Pfad des Links selbst mittels `os.path.abspath` und `os.path.commonpath` gegen den Trash-Ordner.
         - Wenn gültig, lösche ihn direkt per `os.unlink`. Das Ziel des Symlinks wird niemals verfolgt oder gelöscht.
      2. Falls es sich um ein echtes Verzeichnis handelt:
         - Validiere den realen Pfad mittels `os.path.realpath` und `os.path.commonpath`.
         - Wenn gültig, lösche es per `shutil.rmtree`.
      3. Falls es sich um eine reguläre Datei handelt:
         - Validiere den pfad und lösche per `os.remove`.
    - Aktualisiert `TRASH_CLEANUP_STATUS` mit `finished_at`, `deleted_count`, `error_count` und `last_error` und setzt `running: False`.

#### [MODIFY] [storage_probe.py](file:///Users/alex/Documents/Medienwerkzeug/gui/workers/storage_probe.py)
- **Erweiterung um Modus `trash_stats`:**
  - Aufruf: `python storage_probe.py trash_stats <trash_path>`
  - Scannt den Trash-Ordner ohne Symlinks zu folgen.
  - Gibt `{"bytes": total_bytes, "count": total_files}` als JSON aus.
  - Wird vom Flask-Prozess mit einem 10-Sekunden-Timeout aufgerufen, um stale Mounts abzufangen.

---

### 2. API-Erweiterung & Hintergrund-Thread

#### [MODIFY] [system_api.py](file:///Users/alex/Documents/Medienwerkzeug/gui/api/system_api.py)
- **Globale Variable:** `TRASH_CLEANUP_STATUS` im RAM.
- **Routen:**
  - `GET /api/system/trash/stats`: Gibt die gecachten Papierkorb-Statistiken zurück.
  - `GET /api/system/trash/cleanup-status`: Gibt `TRASH_CLEANUP_STATUS` zurück.
  - `POST /api/system/trash/cleanup`: Triggert den Cleanup-Lauf.
    - Parameter: `dry_run` (boolean) und `retention_days` (optional).
    - Falls bereits ein Lauf aktiv ist (`TRASH_CLEANUP_STATUS["running"] == True`), wird `HTTP 409 (Conflict)` mit `{"status": "already_running"}` zurückgegeben.
    - Falls `dry_run=true`, wird der Scan synchron ausgeführt (mit 10s Timeout) und die Liste der Löschkandidaten sofort zurückgegeben.
    - Falls `dry_run=false`, wird die Löschung asynchron angestoßen und `{"status": "started"}` zurückgegeben. Das UI pollt danach `/api/system/trash/cleanup-status`.

#### [MODIFY] [main.py](file:///Users/alex/Documents/Medienwerkzeug/gui/main.py)
- **Hintergrund-Thread:** Startet den periodischen `trash_cleaner_worker` (alle 12 Stunden), der bei `trash_auto_empty` abgelaufene Dateien bereinigt und stündlich die Statistik im RAM aktualisiert.

---

### 3. Frontend-UI Integration

#### [MODIFY] [index.html](file:///Users/alex/Documents/Medienwerkzeug/gui/static/index.html)
- Im Tab "Docker & Hardware" fügen wir eine neue Sektion "Papierkorb & Quarantäne (Docker)" ein:
  - Checkbox: "Automatische Quarantäne-Bereinigung aktivieren"
  - Eingabe: "Aufbewahrungsdauer (Tage)"
  - Bereich für manuelle Aktionen:
    - Statusanzeige: "Größe: X MB / Dateianzahl: Y"
    - Button "Papierkorb prüfen" (Dry-Run Vorschau der abgelaufenen Dateien)
    - Button "Abgelaufene jetzt löschen" (Löst asynchrones Löschen aus)
  - Fortschrittsanzeige für den asynchronen Löschlauf.
  - **Stuck-Warnhinweis:** Wenn der Status `running` länger als 5 Minuten aktiv ist, zeigt das UI einen gelben Warnhinweis an ("Löschvorgang läuft ungewöhnlich lange. Möglicherweise blockiert ein Netzwerk-Mount.").

#### [MODIFY] [app.js](file:///Users/alex/Documents/Medienwerkzeug/gui/static/app.js)
- Bindet die neuen Einstellungs-Felder an das Laden und Speichern an.
- Implementiert Klick-Handler für "Prüfen" und "Löschen".
- Pollt `/api/system/trash/cleanup-status` während des Löschvorgangs, um Fortschritt und Fehler anzuzeigen.

---

## Verification Plan

### Automated Tests
- Neue Testdatei [test_trash_cleaner.py](file:///Users/alex/Documents/Medienwerkzeug/tests/test_trash_cleaner.py):
  1. **Symlink-Ausbruchsschutz:** Ein Symlink im Trash, der auf `/etc` oder `/outside` zeigt, wird gelöscht, ohne das Ziel anzufassen.
  2. **Grenzwerte-Test:** Blockiert Pfade außerhalb des `.medienwerkzeug-trash` Verzeichnisses.
  3. **storage_probe Integration:** Verifiziert, dass der `trash_stats` Modus von `storage_probe.py` korrekte Bytes und Anzahl liefert.
  4. **Retention-Dauer:** Verifiziert, dass Dateien vor dem Ablaufdatum erhalten bleiben und danach gelöscht werden.
  5. **Dry-Run:** Stellt sicher, dass bei `dry_run=True` keine realen Löschungen stattfinden.
  6. **Concurrency-Schutz:** Startet zwei simulierte Bereinigungen parallel und stellt sicher, dass die zweite mit einer Exception/Fehlermeldung abgelehnt wird.
  7. **Async-Status:** Verifiziert, dass der Status `running` korrekt auf `True` und danach `False` gesetzt wird.

### Manual Verification
1. Starten der App im Docker-Modus.
2. Löschen einer Testdatei.
3. Öffnen des Docker-Tabs im Frontend: Anzeige von Dateigröße und Anzahl verifizieren.
4. "Papierkorb prüfen" klicken und Liste der abgelaufenen Testdateien verifizieren.
5. Manuelles Löschen auslösen und Polling-Fortschritt im UI beobachten.
