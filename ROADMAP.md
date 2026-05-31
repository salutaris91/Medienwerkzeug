# Roadmap – Geplante Erweiterungen

Zentrale Sammelstelle für geplante, noch **nicht umgesetzte** Erweiterungen des
Medienwerkzeugs. Jeder Abschnitt ist ein eigenständiger Plan und kann unabhängig
angegangen werden.

| # | Thema | Status | Aufwand (grob) |
|---|-------|--------|----------------|
| 1 | Echtes Multi-Cloud (mehrere Cloud-Ziele gleichzeitig) | geplant | mittel |
| 2 | Distribution & Bündelung (rclone/ffmpeg/yt-dlp mitliefern) | geplant | mittel–groß |
| 3 | KI-Cover- & Logo-Generierung (Gemini/OpenRouter) | geplant | mittel |
| 4 | Selektiver Import für StreamFab-Downloads | erledigt | klein |
| 5 | Angleichung an Metadatendienst (NAS-Renaming-Tool) | erledigt | mittel |
| 6 | Server-genaue Artwork-Prüfung (Emby/Jellyfin/Plex) | geplant | klein |
| 7 | Inkrementeller Health-Scan (Timestamp-Cache) | geplant | klein |

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

---

## 3. KI-Cover- & Logo-Generierung (Bilderstellung)

Automatische Generierung von Postern, Fanart (Hintergründen) und transparenten Logos für Medien, zu denen es in den offiziellen Datenbanken (TMDb, TVDb) keine Einträge gibt (z. B. eigene Aufnahmen, seltene Dokumentationen oder YouTube-Downloadelemente).

### Brainstorming & API-Vergleich
Für die Bilderstellung stehen primär zwei flexible APIs zur Verfügung:

1. **Gemini API (Imagen 3)**:
   - **Vorteile**: Direkt über Googles Gemini-Infrastruktur nutzbar. Imagen 3 ist hervorragend darin, Text in Bildern korrekt zu rendern (essentiell für Filmtitel auf Postern). Sehr hohe Ästhetik und schnelle Reaktionszeit.
   - **Nachteile**: Keine native Generierung von transparenten PNGs (muss per Post-Processing gelöst werden).
2. **OpenRouter API (FLUX.1 / SD3)**:
   - **Vorteile**: Zugriff auf FLUX.1 (Schnell/Dev/Pro), das aktuell weltbeste Bildmodell für Typografie (Schriftzug-Rendering) und Realismus. Teilweise sehr günstige oder kostenfreie Test-Modelle verfügbar.
   - **Nachteile**: Zusätzlicher Account nötig; Latenz kann je nach Modell schwanken.

### Technische Umsetzung (Stufenplan)

#### 1. Backend-Modul (`gui/core/image_generator.py`)
- Kapselung der API-Aufrufe (Gemini API Key / OpenRouter Key in `.env` laden).
- **Poster (2:3)**: Standard-Auflösung 1000x1500 px. Prompt-Struktur: `Movie poster for [Title], [Genre], high quality, cinematic style, 2:3 aspect ratio`.
- **Fanart (16:9)**: Standard-Auflösung 1920x1080 px (ohne Text). Prompt-Struktur: `Atmospheric background scene for [Title], movie landscape, high resolution, no text, 16:9 aspect ratio`.
- **Clearlogo (Transparentes PNG)**:
  - Generierung des Titelschriftzugs: `The text "[Title]" in a stylized, modern/clean movie title font, centered on a solid pitch-black background, high contrast, isolated`.
  - **Post-Processing (Python/PIL)**: Ein kleines Skript konvertiert den schwarzen Hintergrund programmgesteuert in Transparenz (Alpha-Kanal Thresholding) und speichert das Ergebnis als transparentes `logo.png` (bzw. `clearlogo.png`).

#### 2. Frontend-Integration
- Wenn bei der Suche nach Filmen/Serien keine Ergebnisse gefunden werden (oder manuell gewählt), wird eine Option **🎨 Cover & Artworks generieren** eingeblendet.
- Der Nutzer kann den Standard-Prompt per Freitext verfeinern (z. B. "Stil: Anime" oder "Stil: 80er Jahre Retro").
- Nach Fertigstellung (ca. 5–15 Sek.) werden die Bilder in einer kleinen Vorschau-Galerie angezeigt und können per Haken für die Verarbeitung übernommen werden.

### Aufwand (grob)
Backend-Logik & Post-Processing ~1 Tag, Frontend-UI (Prompt-Eingabe, Galerie) ~1 Tag. Ein extrem lohnenswertes Feature für eine vollständig runde Medienbibliothek.

---

## 4. Selektiver Import für StreamFab-Downloads

Ermöglicht es dem Benutzer, beim Importieren von Downloads (z. B. aus StreamFab) gezielt auszuwählen, welche Ordner/Dateien in die Inbox übernommen werden sollen, anstatt blind alle importierten Elemente zu verschieben.

### Ziel
Verhinderung des Imports von unerwünschten Begleitdateien (wie Logos, Postern, Trailern oder NFOs) oder das Zurücklassen bestimmter Download-Projekte in der Importquelle.

### Technische Umsetzung (Stufenplan)
1. **Import-Preview API:**
   - Ein neuer API-Endpunkt `/api/streamfab/preview` scannt die konfigurierten `import_sources` und liefert eine Liste der gefundenen Projektordner und Einzeldateien zurück (analog zur Inbox-Struktur).
2. **Benutzeroberfläche:**
   - Beim Klick auf den Import-Button auf der Startseite (oder in der Navigationsleiste) öffnet sich ein Auswahldialog (Modal).
   - In diesem Dialog werden alle importfähigen Projekte mit Checkboxen aufgelistet (standardmäßig alle ausgewählt).
   - Der Benutzer kann einzelne Ordner oder unerwünschte Dateitypen (z. B. Bilder oder Begleitdateien) abwählen.
3. **Selektiver Import-Prozess:**
   - Der Post-Request `/api/streamfab-import` wird um einen Parameter `selected_items` erweitert.
   - Der Backend-Worker verschiebt nur die vom Benutzer ausgewählten Dateien/Ordner in das Medien-Input-Verzeichnis.

### Aufwand (grob)
Backend-Logik & API ~0,5 Tage, Auswahldialog-UI ~0,5 Tage. Sehr nützlich, um die Inbox direkt beim Import sauber zu halten.

---

## 5. Angleichung an Metadatendienst (NAS-Renaming-Tool)

Ermöglicht es dem Benutzer, einen bereits existierenden Serienordner auf dem NAS zu scannen, mit dem Metadatendienst (z.B. TMDB/TVDB) abzugleichen und alle darin enthaltenen Staffeln und Episodendateien automatisch nach dem einheitlichen Namensschema zu benennen und mit Status-Badges zu versehen.

### Ziel
Nachträgliches Aufräumen und Angleichen älterer Serien-Bibliotheken, bei denen sich die Benennung unterscheidet (z. B. durch einen Wechsel des Metadatendienstes, unterschiedliche historische Benennungskonventionen in verschiedenen Staffeln oder fehlerhafte Sonderzeichen).

### Optionen zur Umsetzung und Machbarkeit

| Option | Beschreibung | Vorteile | Nachteile | Aufwand (grob) |
|---|---|---|---|---|
| **Option A: In-Place Renaming direkt auf dem NAS (Empfohlen)** | Das Tool arbeitet direkt auf dem gemounteten NAS-Laufwerk. Es benennt die Dateien um und schreibt die lokalen `.nfo`-Dateien neu. | • Extrem schnell (nur `os.rename`-Aufrufe)<br>• Keine Netzwerk- oder lokale Plattenlast | • Potenziell destruktiv bei Fehlern<br>• Kritisch bei Verbindungsabbrüchen | ~4,5 Tage |
| **Option B: Über die Inbox (Import & Re-Process)** | Die Dateien werden virtuell in den Inbox-Verarbeitungsprozess kopiert, dort umbenannt und wieder zurückgeschrieben. | • Nutzt die bereits vollständig getestete Pipeline<br>• Sehr sicher (nicht-destruktiv) | • Extrem langsam (Kopieren von Gigabytes über WLAN/Netzwerk)<br>• Benötigt viel temporären Speicher | ~1 Tag |
| **Option C: Hybrid-Lösung (Skript-Generierung)** | Das Backend scannt die Dateien und generiert ein eigenständiges Python- oder Shell-Skript im Serienordner, das der Benutzer nach Kontrolle manuell starten kann. | • Maximale Transparenz für versierte Nutzer<br>• Ausführung außerhalb der Web-App | • Unbequem für normale Endnutzer (Terminal-Nutzung erforderlich) | ~2 Tage |

### Zwingende Sicherheitsmaßnahmen (für Option A)

Da In-Place-Operationen auf einem NAS ein Risiko für Datenverlust bergen, müssen folgende Mechanismen implementiert werden:

1. **Zwingender Dry-Run (Trockenlauf):**
   - Es wird vor jeder Änderung eine vollständige Liste aller geplanten Renames und Dateianpassungen im Frontend visualisiert.
   - Der Benutzer muss jede Änderung explizit bestätigen oder kann einzelne Dateien vom Prozess ausschließen.

2. **NFO-Backup-Strategie:**
   - Vor dem Ändern oder Überschreiben einer `.nfo`-Datei (z.B. `tvshow.nfo` oder `episode.nfo`) wird eine Kopie mit der Endung `.nfo.bak` im selben Verzeichnis angelegt.
   - Tritt beim Schreiben ein Fehler auf, wird das Backup sofort wiederhergestellt.

3. **Automatischer Rollback-Pfad (Transaktionsprotokoll):**
   - Das Backend schreibt vor der Ausführung eine JSON-Transaktionsdatei (z.B. `rename_transaction_[timestamp].json`) in ein internes Anwendungsdatenverzeichnis.
   - Diese Datei speichert ein Mapping: `{"alt/pfad/datei.mkv": "neu/pfad/datei.mkv"}`.
   - Sollte der Umbenennungsprozess fehlschlagen oder der Benutzer die Änderungen rückgängig machen wollen, kann über einen Button „Rückgängig machen“ diese Liste rückwärts abgearbeitet werden.

4. **Lock- und Berechtigungs-Prüfung:**
   - Vor dem Start des Prozesses wird auf Schreibberechtigungen im gesamten Serienordner geprüft.
   - Für jede Datei wird verifiziert, ob sie durch andere Prozesse blockiert oder geöffnet ist (z. B. durch Leseversuche oder Schreibzugriffe).

5. **In-Place Ordnerverschiebung & Restrukturierung:**
   - Erfordert die Angleichung eine Änderung des Serien-Hauptordnernamens (z. B. Verschiebung von `Show Alt` zu `Show Neu`), wird dies ebenfalls direkt in-place auf dem NAS via `os.rename` durchgeführt. Da dies auf demselben Volume geschieht, erfolgt die Verschiebung augenblicklich und erzeugt keine Netzwerklast.
   - Neue Staffel- oder Special-Unterordner werden automatisch angelegt.
   - Solche Pfad- und Ordneränderungen werden vollständig im Transaktionsprotokoll erfasst, damit das Rollback auch die Ordnerstruktur fehlerfrei wiederherstellen kann.

### Technische Umsetzung (Stufenplan für Option A)

1. **Bibliotheks-Scraper & ID-Lookup:**
   - Scannt einen ausgewählten Show-Ordner auf dem NAS nach Episodendateien (Videos, Untertitel, NFOs).
   - Liest die ID (z.B. TMDB-ID) aus der vorhandenen `tvshow.nfo` aus und lädt die aktuellen Metadaten des Anbieters.
   - Analysiert die vorhandenen Dateien und extrahiert Staffel- und Episodennummern.
2. **Preview & Abgleich-UI:**
   - Zeigt dem Benutzer eine Gegenüberstellung in einer Tabelle: *Aktueller Dateiname* vs. *Vorgeschlagener Metadaten-Name*.
   - Nutzt Badges zur Statusanzeige:
     - `Passt bereits` (Grün): Dateiname entspricht der Konvention.
     - `Abweichung` (Gelb): Der Episodentitel oder die Schreibweise weicht ab (z.B. Schreibfehler oder anderer Metadatendienst). Umbenennung empfohlen.
     - `Kein Treffer` (Rot): Episode kann nicht im Metadatendienst gefunden werden (Benutzer muss manuell zuordnen).
3. **Massen-Renamer & Rollback:**
   - Führt die Umbenennungen im Hintergrund aus und aktualisiert die lokalen `.nfo`-Dateien. Generiert bei Erfolg ein Transaktionsprotokoll und bietet in der UI die Option eines sofortigen Rollbacks an.

### Aufwand (grob)
- **Backend-Abgleich-Logik, NFO-Backups & Rollback-Engine**: ~2,5 Tage.
- **Frontend-UI (Vorschau-Tabelle, Badges, Fortschrittsbalken, Rollback-Button)**: ~1,5 Tage.
- **Sicherheits-Validierung & Tests**: ~0,5 Tage.
- **Gesamtaufwand**: ~4,5 Tage (Mittel).

---

## 6. Server-genaue Artwork-Prüfung (Emby / Jellyfin / Plex)

Aktuell prüft der Bibliotheks-Check nur „liegt **irgendein** Bild im Ordnerbaum?"
(`_has_any_artwork` in `gui/core/health.py`, rekursiv). Das beseitigt Fehlalarme,
sagt aber nichts darüber aus, ob die für den genutzten Medienserver *relevanten*
Artworks vorhanden und korrekt benannt sind.

### Ziel
Differenzierte Meldungen pro Artwork-Typ, abgestimmt auf den **konfigurierten
Medienserver**. In den Einstellungen wählt der Nutzer einmal seinen Server
(Emby / Jellyfin / Plex); der Check validiert dann **exakt gegen dessen
Konvention** — keine Fehlmeldung für Bildtypen, die der gewählte Server gar nicht
verwendet (z. B. `clearlogo` bei Plex).

### Konventionen je Server (jeweils neben der Videodatei bzw. im Medienordner)

**Emby & Jellyfin** (Jellyfin ist ein Emby-Fork → identisch):

| Bildtyp | Erkannte Dateinamen |
|---|---|
| Poster | `poster.jpg`, `folder.jpg`, `cover.jpg`, `<name>.jpg`, `movie.jpg`, `default.jpg` |
| Hintergrund (Fanart) | `fanart.jpg`, `backdrop.jpg`, `<name>-fanart.jpg` |
| Logo | `clearlogo.png`, `logo.png` |
| Banner | `banner.jpg` |
| Disc | `discart.png`, `disc.png` |
| Clearart | `clearart.png` |
| Thumb | `thumb.jpg`, `landscape.jpg` |

**Plex** (setzt aktivierten „Local Media Assets"-Agenten voraus; kennt nativ
**kein** Logo/Clearart/Disc):

| Bildtyp | Erkannte Dateinamen |
|---|---|
| Poster | `poster.jpg`, `folder.jpg`, `cover.jpg`, `<name>.jpg`, `movie.jpg`, `default.jpg`, `show.jpg` |
| Hintergrund (Art) | `fanart.jpg`, `art.jpg`, `background.jpg`, `backdrop.jpg` |
| Banner | `banner.jpg` |
| Theme (optional) | `theme.mp3` |

### Umzusetzende Änderungen
- **Settings:** neues Feld `media_server` (Default `"emby"`; Werte
  `emby` | `jellyfin` | `plex`) in `gui/core/utils.py:load_settings()` + Auswahl in
  der Settings-UI.
- **Konventions-Tabelle** als Daten-Map im Code (pro Server: Bildtyp → Namensliste +
  Severity). Emby und Jellyfin teilen sich denselben Eintrag.
- `_has_any_artwork` zu einer typbewussten Prüfung erweitern (z. B.
  `_artwork_status(path, server) -> {"poster": bool, "fanart": bool, ...}`),
  rekursiv, Dateinamen case-insensitiv, `<name>` = Stem der Videodatei.
- Getrennte Issues mit passender Severity (fehlendes **Poster** = `warning`,
  Fanart/Logo/Banner = `info`), statt der einen Sammelmeldung „kein Artwork".
  Nur Bildtypen prüfen, die der gewählte Server kennt.
- Für Serien zusätzlich season-/episodenbezogene Artworks erwägen
  (`season01-poster.jpg` etc.) — optional.

### Aufwand (grob)
~0,5–1 Tag Backend (Konventions-Map + Setting + typbewusster Check) + kleine
Frontend-Anpassung (Server-Auswahl in Settings, differenzierte Issue-Anzeige).

---

## 7. Inkrementeller Health-Scan (Timestamp-Cache)

Der Health-Scan prüft aktuell bei jedem Durchlauf alle ~240 Ordner vollständig,
einschließlich ffprobe-Codec-Stichproben. Das dauert über eine Minute. Bei
Folge-Scans sind aber typischerweise nur wenige Ordner verändert worden.

### Ziel
Ordner, die beim letzten Scan fehlerfrei waren und seitdem nicht verändert wurden,
überspringen. Folge-Scans sollen in Sekunden statt Minuten abschließen.

### Konzept: Timestamp-basierter Skip
Pro gescanntem Ordner wird ein Cache-Eintrag gespeichert:

```json
{
  "path": "/Volumes/Kino/Filme/Blade.Runner.2049",
  "mtime": 1780123456.0,
  "status": "clean",
  "scan_version": 2
}
```

Beim nächsten Scan wird pro Ordner geprüft:
1. Existiert ein Cache-Eintrag für diesen Pfad?
2. Ist die aktuelle `mtime` (via `os.stat`) identisch mit dem gespeicherten Wert?
3. War der Status `"clean"` (keine Issues)?
4. Stimmt die `scan_version` mit der aktuellen überein?

Nur wenn alle vier Bedingungen erfüllt sind, wird der Ordner übersprungen.
Andernfalls wird er vollständig neu gescannt und der Cache aktualisiert.

**Warum `scan_version`:** Wenn neue Check-Typen hinzukommen (wie zuletzt
`nested_duplicate`, `bad_folder_name`, `name_mismatch`), muss die Version
hochgezählt werden, damit alle Ordner einmalig gegen die neuen Regeln geprüft
werden — auch wenn sich ihr Inhalt nicht geändert hat.

**Warum `mtime` ausreicht:** Sobald eine Datei im Ordner hinzugefügt, umbenannt
oder gelöscht wird, aktualisiert das Dateisystem die `mtime` des übergeordneten
Verzeichnisses automatisch. Für tiefere Änderungen (z.B. in Unterordnern) wird
die maximale `mtime` über `os.walk` ermittelt.

### Umzusetzende Änderungen
- **Cache-Datei** (`health_folder_cache.json`) neben der bestehenden
  `health_scan_cache.json` in `gui/data/`.
- **`_check_movie` / `_check_series_show`:** Vor dem Prüfen den Cache
  konsultieren; nach dem Prüfen den Cache aktualisieren.
- **`_run_health_scan`:** Übersprungene Ordner in der Fortschrittsanzeige
  als „(cached)" kennzeichnen; am Ende die Anzahl übersprungener Ordner loggen.
- **UI:** Optionaler Button „Voll-Scan erzwingen" der den Cache ignoriert.

### Alternativer Ansatz (Reserve): Zweistufiger Scan
Falls der Timestamp-Ansatz nicht zuverlässig genug ist (z.B. bei NAS-Dateisystemen
mit ungenauer mtime-Granularität), könnte alternativ ein zweistufiger Scan
implementiert werden: Stufe 1 prüft nur Dateinamen und Ordnerstruktur (instant),
Stufe 2 (ffprobe/Dateigrößen) nur bei geänderten Ordnern oder auf Knopfdruck.

### Aufwand (grob)
~0,5 Tage. Hauptarbeit ist die Cache-Logik mit Version-Tracking; die Integration
in den bestehenden Scan-Flow ist minimal.
