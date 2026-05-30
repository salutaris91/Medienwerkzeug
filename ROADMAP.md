# Roadmap – Geplante Erweiterungen

Zentrale Sammelstelle für geplante, noch **nicht umgesetzte** Erweiterungen des
Medienwerkzeugs. Jeder Abschnitt ist ein eigenständiger Plan und kann unabhängig
angegangen werden.

| # | Thema | Status | Aufwand (grob) |
|---|-------|--------|----------------|
| 1 | Echtes Multi-Cloud (mehrere Cloud-Ziele gleichzeitig) | geplant | mittel |
| 2 | Distribution & Bündelung (rclone/ffmpeg/yt-dlp mitliefern) | geplant | mittel–groß |

---

## 1. Echtes Multi-Cloud (Stufe 2)

Erweiterung von „ein NAS + ein Cloud-Ziel" auf **beliebig viele, unabhängig
schaltbare Speicherziele** (NAS, pCloud, Google Drive, OneDrive, Dropbox, S3 …).

### Ausgangslage (nach Stufe 1)
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

### Ziel
Pro Speicherziel ein eigener, unabhängiger Schalter und Zielordner — dynamisch aus
`storage_targets` erzeugt.

### Umzusetzende Änderungen
1. **Job-Parameter-Modell (Backend):** Statt `copy_to_nas`/`copy_to_pcloud` ein
   generisches Modell — pro Ziel `copy_to_<id>` oder eine Liste
   `copy_targets: ["nas","pcloud","gdrive"]`.
   - `gui/workers/processor.py`: Transfer-Schleifen iterieren bereits über
     `storage_targets`; die `t_id == "pcloud"`-Sonderfälle (`explicit_remote_base`,
     Defaults) verallgemeinern.
   - `gui/api/queue_api.py`, `gui/api/youtube_api.py`: Job-Payloads umstellen.
   - `gui/core/transfers.py`: `copy_to_pcloud()`-Wrapper entfernen.
2. **Kategorie-Mapping:** durchgängig `cat["targets"][target_id]` nutzen;
   `nas_sub`/`pcloud_remote` nur noch als Migrations-Fallback.
3. **Frontend:** in den Verarbeitungs-Views (Film/Serie/YouTube) die zwei festen
   Checkboxen durch **dynamisch gerenderte** ersetzen — eine pro aktivem Ziel, plus
   Zielordner-Dropdown pro Ziel. Settings-Editor: `rclone_remote` editierbar,
   Kategorie-Matrix mit Spalte pro Ziel. Optional: `rclone listremotes`-Dropdown und
   „Verbindung testen" via `rclone about`.
4. **Settings-Migration:** bestehende Flags auf das generische Modell migrieren,
   `targets`-Dict für alle Ziele befüllen; vorher Backup von `settings.json`.
5. **Optionale Namens-Bereinigung:** interne pcloud-Etiketten generisch benennen.

### Risiken & Hinweise
- Regressionsrisiko im gut getesteten Einzel-Cloud-Pfad → schrittweise, Tests
  erweitern (Mock-Ziele im kanonischen Modul patchen, siehe REVIEW.md).
- Settings-Migration betrifft echte Nutzerdaten → Backup + idempotente Migration.
- `rclone about` wird nicht von allen Backends unterstützt — die Anzeige fängt das
  bereits ab (Ziel wird übersprungen).

### Empfohlene Reihenfolge
1. Generisches Job-Parameter-Modell (Backend) + Migration + Tests.
2. Frontend: dynamische Ziel-Checkboxen/Dropdowns.
3. Settings-UI: rclone-Remote-Auswahl + „Verbindung testen".
4. Optionale Namens-Bereinigung.

### Aufwand (grob)
Backend ~1–2 Tage, Frontend ~1–2 Tage, Tests/Migration ~1 Tag. Dank rclone-
Abstraktion kein anbieterspezifischer Code nötig.

---

## 2. Distribution & Bündelung (Tool an andere weitergeben)

Ziel: Das Tool so verteilbar machen, dass Empfänger möglichst wenig manuell
installieren müssen. Aktuell werden `ffmpeg`/`ffprobe`, `rclone`, `yt-dlp` per
bloßem Namen aufgerufen (setzen Homebrew-Installation im `PATH` voraus), und das
`.app` nutzt das System-Python mit nutzereigenen site-packages.

### Weg A: Binaries ins .app bündeln (selbstständig)
- Binaries nach `Medienwerkzeug.app/Contents/Resources/bin/` legen.
- **Code-Änderung:** ein Tool-Pfad-Resolver (`tool("rclone")` o. ä.) — erst die
  mitgelieferte Binary, sonst `PATH`. Betrifft ~60 subprocess-Aufrufstellen, daher
  über eine zentrale Helper-Funktion lösen.
- **Python selbst** mit **py2app** oder **PyInstaller** bündeln (Python + pip-Pakete).
- **Stolpersteine:**
  - **Code-Signing & Notarisierung** (Apple Developer ID, ~99 $/Jahr), sonst blockt
    Gatekeeper fremde, unsignierte Binaries.
  - **Größe:** ffmpeg ~70 MB, rclone ~50 MB, yt-dlp ~30 MB.
  - **Architektur:** arm64/Intel (am besten Universal-Binaries).
  - **Lizenzen:** rclone (MIT), yt-dlp (frei) unkritisch; ffmpeg GPL/LGPL → Pflichten.

### Weg B: Beim ersten Start automatisch installieren
- Auf Basis des vorhandenen `/api/check-dependencies`-Endpunkts Fehlendes erkennen
  und via Homebrew installieren (`brew install rclone ffmpeg yt-dlp`) plus
  `pip install -r requirements.txt`.
- **Nachteil:** setzt Homebrew voraus (nicht überall vorhanden, nicht sauber still
  installierbar), braucht Netz + Zustimmung, fragiler.

### Wichtigster Haken (beide Wege)
Den rclone-**Dienst** (Binary) kann man mitliefern, die **Verbindungen** nicht: Die
Cloud-Anbindung beruht auf **OAuth-Tokens pro Nutzer** (nutzereigene `rclone.conf`).
Jeder Empfänger muss einmal `rclone config` für sein eigenes Konto durchlaufen —
Cloud-Zugänge dürfen nicht mitgegeben werden. Der `rclone config`-Flow ließe sich
später in die UI einbetten, die Anmeldung bleibt aber pro Person.

### Empfehlung
- **Saubere Weitergabe:** py2app + gebündelte Binaries + Developer-ID-Notarisierung +
  Tool-Pfad-Resolver. Eigenes, mittelgroßes Distributions-Projekt.
- **Pragmatischer Einstieg:** `check-dependencies` nutzen, um fehlende Tools beim
  Start klar zu melden und eine 1-Klick-Homebrew-Installation anzubieten — schnell
  lauffähig für technisch versierte Empfänger ohne Signing-Aufwand.

### Aufwand (grob)
Pragmatischer Einstieg (Weg B light): ~0,5–1 Tag. Volles signiertes Bundle (Weg A):
mehrere Tage inkl. Build-Pipeline, Tool-Resolver und Notarisierung.
