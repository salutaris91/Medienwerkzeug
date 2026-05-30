# Plan: Echtes Multi-Cloud (Stufe 2)

Status: **geplant, nicht umgesetzt.** Dieser Plan beschreibt, wie das Medienwerkzeug
von „ein NAS + ein Cloud-Ziel" auf **beliebig viele, unabhängig schaltbare
Speicherziele** (NAS, pCloud, Google Drive, OneDrive, Dropbox, S3 …) erweitert wird.

## Ausgangslage (nach Stufe 1)

- Uploads laufen vollständig über **rclone** (`copy_to_cloud_target` in
  `gui/core/transfers.py`). Der Anbieter wird allein durch `rclone_remote` bestimmt
  — backend-neutral. rclone unterstützt ~70 Backends.
- `storage_targets` in `settings.json` ist bereits eine **Liste** beliebiger Ziele
  (id, name, type, root_path, rclone_remote, enabled).
- Die Speicher-Anzeige im Dashboard iteriert die Liste bereits generisch
  (Fallback-Kette, NAS via statvfs, Cloud via `rclone about`).
- Die Settings-UI hat bereits „➕ Neues Speicherziel hinzufügen" und ein
  Kategorie-Mapping, das sich an die aktiven Ziele anpasst.

### Die verbleibende Grenze
Das **Verarbeiten** kennt nur zwei feste Schalter: `copy_to_nas` und
`copy_to_pcloud`. Alle Nicht-NAS-Ziele teilen sich den `copy_to_pcloud`-Flag, und
einige Stellen prüfen fest auf die id `"pcloud"`. Dadurch lässt sich der Cloud-Slot
zwar frei auf einen anderen Anbieter umstellen, aber nicht **pCloud UND Google Drive
gleichzeitig** unabhängig schalten.

## Ziel

Pro Speicherziel ein eigener, unabhängiger Schalter und Zielordner — dynamisch aus
`storage_targets` erzeugt. Der Nutzer kann beliebig viele Ziele anlegen, jeweils ein
rclone-Remote zuordnen und pro Job auswählen, wohin kopiert wird.

## Umzusetzende Änderungen

### 1. Job-Parameter-Modell (Backend)
- Statt `copy_to_nas` / `copy_to_pcloud` ein generisches Modell:
  - Entweder pro Ziel `copy_to_<id>` (bool), oder besser eine Liste
    `copy_targets: ["nas", "pcloud", "gdrive"]`.
- `gui/workers/processor.py`: Die Transfer-Schleifen iterieren bereits über
  `storage_targets`. Die `should_copy`-Logik liest schon `params.get(f"copy_to_{t_id}")`
  zuerst — der Fallback auf `copy_to_pcloud` und die `t_id == "pcloud"`-Sonderfälle
  (z. B. `explicit_remote_base`, `target_id`-Defaults) werden entfernt/verallgemeinert.
- `gui/api/queue_api.py`, `gui/api/youtube_api.py`: Job-Payloads auf das generische
  Modell umstellen (`explicit_pcloud_base` → pro Ziel auflösen).
- `gui/core/transfers.py`: `copy_to_pcloud()`-Wrapper entfernen; durchgängig
  `copy_to_cloud_target(target_id=...)` nutzen.

### 2. Kategorie-Mapping
- Durchgängig `cat["targets"][target_id]` als Pfad pro (Kategorie, Ziel) nutzen.
- `nas_sub` / `pcloud_remote` nur noch als **Migrations-Fallback** behalten.
- `resolve_target_destination` nutzt bereits den `targets`-Dict — beibehalten.

### 3. Frontend
- **Verarbeitungs-Views** (Film/Serie/YouTube): die zwei festen Checkboxen (NAS,
  pCloud) durch **dynamisch gerenderte** Checkboxen ersetzen — eine pro aktivem
  Speicherziel, plus je ein Zielordner-Dropdown pro Ziel.
- **Settings:** der Speicherziel-Editor existiert bereits; sicherstellen, dass er
  `rclone_remote` editierbar macht und die Kategorie-Matrix Spalten pro Ziel zeigt.
- Optional: Dropdown der in rclone konfigurierten Remotes via `rclone listremotes`
  und ein „Verbindung testen" via `rclone about`.

### 4. Settings-Migration
- Bestehende `copy_to_nas`/`copy_to_pcloud`-Defaults in Profilen/Settings auf das
  generische Modell migrieren (z. B. `copy_to_pcloud: true` → `copy_targets`
  enthält die id des bisherigen Cloud-Ziels).
- Kategorien: `targets`-Dict für alle Ziele befüllen (aus `nas_sub`/`pcloud_remote`).
- Vor der Migration ein Backup von `settings.json` anlegen.

### 5. Optionale Namens-Bereinigung
- Interne pcloud-Etiketten generisch benennen (`copy_to_pcloud` → generisch,
  Variable `pcloud_local` → `target_local`, Feld `pcloud_remote` → `cloud_remote`).
- Rein kosmetisch; kann zusammen mit Punkt 1–4 erledigt werden.

## Risiken & Hinweise
- **Regressionsrisiko** im gut getesteten Einzel-Cloud-Pfad → schrittweise umbauen,
  Tests erweitern (Mock-Ziele im kanonischen Modul patchen, siehe REVIEW.md).
- **Settings-Migration** betrifft echte Nutzerdaten → Backup + idempotente Migration.
- **rclone-Voraussetzung:** Jedes Cloud-Ziel braucht ein konfiguriertes rclone-Remote
  (`rclone config`). `rclone about` wird nicht von allen Backends unterstützt — die
  Speicher-Anzeige fängt das bereits ab (Ziel wird übersprungen).

## Empfohlene Reihenfolge
1. Generisches Job-Parameter-Modell + processor/queue/youtube umstellen (Backend),
   mit Migration & erweiterten Tests.
2. Frontend: dynamische Ziel-Checkboxen/Dropdowns in den Verarbeitungs-Views.
3. Settings-UI: rclone-Remote-Auswahl + „Verbindung testen".
4. Optionale Namens-Bereinigung.

## Aufwand (grobe Schätzung)
Mittleres Feature: Backend ~1–2 Tage, Frontend ~1–2 Tage, Tests/Migration ~1 Tag.
Dank rclone-Abstraktion kein anbieter­spezifischer Code nötig.
