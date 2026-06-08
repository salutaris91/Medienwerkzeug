# After Release Roadmap

Zentrale Sammelstelle für geplante, noch **nicht umgesetzte** Erweiterungen des
Medienwerkzeugs. Jeder Abschnitt ist ein eigenständiger Plan und kann unabhängig
angegangen werden.

Der frühere Release- und Distributionsplan liegt nur noch als historisches
Archiv unter `docs/archive/ROAD_TO_GLORY.md`. Offene Punkte daraus sind hier in
die aktive After-Release-Roadmap übernommen.

| # | Thema | Status | Aufwand (grob) |
|---|-------|--------|----------------|
| 1 | Echtes Multi-Cloud (mehrere Cloud-Ziele gleichzeitig) | geplant | mittel |
| 2 | Distribution & Bündelung (rclone/ffmpeg/yt-dlp mitliefern) | geplant | mittel–groß |
| 3 | KI-Cover- & Logo-Generierung (Gemini/OpenRouter) | geplant | mittel |
| 4 | Selektiver Import für StreamFab-Downloads | erledigt | klein |
| 5 | Angleichung an Metadatendienst (NAS-Renaming-Tool) | erledigt | mittel |
| 9 | Eingebaute Authentifizierung (PIN/Passwort) | erledigt | mittel |
| 10 | Duplikat-Erkennung für Filme | geplant | mittel |
| 11 | Inkrementeller Cache für den Duplikat-Scan | geplant | mittel |
| 12 | Performance-Optimierung für sehr große Serienbibliotheken | geplant | mittel |
| 13 | Komfortablere Health-Quick-Fix-Oberfläche | geplant | klein–mittel |
| 14 | Health-Status-Vertrag & Frontend-Testabdeckung | geplant | klein–mittel |
| 15 | FAQ sprachlich und visuell überarbeiten | erledigt | klein |
| 16 | System Metrics Worker: Thread-Akkumulation verhindern | geplant | klein |
| 17 | NAS-Diagnose-Checkliste auf der Startseite | geplant | klein–mittel |
| 18 | Docker-Image veröffentlichen (GHCR/Docker Hub) | geplant | mittel |
| 19 | Geführter rclone-Web-Flow | geplant | mittel |
| 20 | Web-Upload mit Drag & Drop | geplant | groß |
| 21 | Desktop-App Packaging (pywebview/PyInstaller) | geplant | groß |
| 22 | Update-Hinweise und Release Notes | geplant | klein–mittel |
| 23 | Lizenz- und Drittanbieterhinweise | geplant | klein |
| 24 | API-Key Maskierung UX (Fokus/Editierung-Verhalten) | geplant | klein |
| 25 | TV-Pfad: Angleichung der Untertitel-Erkennung | geplant | klein |
| 26 | FAQ/Dokumentation: Docker-Importquellen und Volume-Mapping beschreiben | geplant | klein |
| 27 | Web-Folder-Picker: Dynamische Titel je nach ausgewählter Kategorie | geplant | klein |
| 28 | Web-Folder-Picker: Layout-Verbreiterung & responsive Anpassungen | geplant | klein |
| 29 | Speicherziel Syncing: Separater Zielordner pro Speicherziel | geplant | klein–mittel |
| 30 | Cloud-Upload (rclone): Status- und Fortschritts-Feedback in der Warteschlange | geplant | klein–mittel |
| 31 | NAS-Downloader-Integration (JDownloader/Download-Backend) | geplant | mittel |
| 32 | Automatische Papierkorb-Leerung unter Docker | geplant | klein–mittel |
| 33 | Automatischer TVDB-Fallback für fehlende TMDB-Plots | geplant | klein |
| 34 | Altersfreigabe-Checks im UI deutlicher erklären | geplant | klein |
| 35 | Premium-Umbenennungsdialog für Health-Fixes mit Metadaten-Lookup | geplant | klein–mittel |
| 36 | Health-Dashboard: Gruppierung, Massen-Fixes (Batch) & Auto-Korrektur | geplant | mittel |

---

## Empfohlene Reihenfolge & Abhängigkeiten (Review vom 07.06.2026)

Grundsatzentscheidungen, die die Reihenfolge prägen:
- **Distributionsweg:** Docker hat Priorität (ist bereits der primäre Kanal,
  siehe #18). Eigenständiges Bundle (#2) und Desktop-App (#21) sind nachgelagert.
- **Downloader-Backend für #31:** JDownloader (verbreitet, gut unterstützt) ist
  die bevorzugte Wahl für die Integration.

### Cluster mit Abhängigkeiten

**Cloud/Speicherziel-Cluster** — #1 zuerst, da es das generische Job- und
Settings-Modell für Speicherziele schafft:
1. **#1** (Echtes Multi-Cloud) — schafft das generische Modell.
2. **#29** (Separater Zielordner pro Speicherziel) überschneidet sich stark mit
   #1, Punkt 3 des Umsetzungsplans dort ("Zielordner-Dropdown pro Ziel",
   "Kategorie-Matrix mit Spalte pro Ziel"). Nach #1 erneut bewerten, ob #29
   noch eigenständige Restarbeit ist oder darin aufgeht — sonst droht doppelte
   Arbeit am selben Settings-Modell.
3. **#19** (Geführter rclone-Web-Flow) und **#30** (Cloud-Upload Status-/
   Fortschritts-Feedback) bauen auf demselben Transfer-Code auf, den #1 umbaut
   (`copy_to_cloud_target`). Beide erst nach #1 angehen, um den Code nicht
   zweimal anzufassen.

**Distributions-Cluster** — Docker zuerst (siehe Grundsatzentscheidung):
1. **#18** (Docker-Image veröffentlichen) — bereits Hauptkanal, moderater
   Aufwand und geringeres Risiko als ein eigenständiges Bundle.
2. **#2** (Distribution & Bündelung) — liefert u. a. den Tool-Pfad-Resolver.
3. **#21** (Desktop-App-Packaging) setzt den Tool-Pfad-Resolver aus #2 voraus
   ("Tool-Pfad-Resolver mit gebündelten oder systemweiten Binaries abstimmen")
   — frühestens nach #2 sinnvoll planbar.
4. **#23** (Lizenz-/Drittanbieterhinweise) hängt davon ab, was am Ende
   tatsächlich gebündelt wird (#2/#18/#21) — vorher recherchiert, droht doppelte
   Arbeit bei Strategiewechseln.
5. **#22** (Update-Hinweise & Release Notes) profitiert von den Versionstags
   und GitHub-Releases, die erst durch #18 entstehen.

**Health/Performance-Cluster** — Vertrag vor UI-Ausbau:
1. **#14** (Health-Status-Vertrag & Frontend-Testabdeckung) zuerst, damit #13
   nicht auf einem noch unstabilen/undokumentierten Status-Vertrag aufbaut und
   später nachgezogen werden muss.
2. **#13** (Komfortablere Health-Quick-Fix-Oberfläche) danach.
3. **#12** (Performance-Optimierung große Serienbibliotheken) — Analyse zuerst,
   wie im Abschnitt selbst beschrieben.
4. **#16** (System Metrics Worker: Thread-Akkumulation) ist ein eigenständiger
   Bugfix mit kleinem Aufwand und kann unabhängig davon jederzeit, auch früher,
   eingeschoben werden.

**Duplikat-Cluster** — Reihenfolge in der Tabelle ist bereits korrekt:
1. **#10** (Duplikat-Erkennung für Filme) zuerst.
2. **#11** (Inkrementeller Cache für den Duplikat-Scan) danach, damit der Cache
   gleich Filme und Serien abdeckt und nicht nachträglich erweitert werden muss.

### Kleine, unabhängige Quick-Wins

Folgende Punkte sind klein, eigenständig und ohne Abhängigkeiten zu größeren
Vorhaben — sie lassen sich jederzeit zwischen den Clustern einschieben, um
früh sichtbaren Fortschritt zu erzielen:
- **#16** (Thread-Akkumulation, s. o.)
- **#24** (API-Key Maskierung UX)
- **#25** (TV-Pfad Untertitel-Erkennung)
- **#26** (FAQ/Doku Docker-Importquellen)
- **#27** und **#28** (Web-Folder-Picker: Titel + Layout) — betreffen dieselbe
  Komponente, sinnvollerweise zusammen umsetzen
- **#33** (TVDB-Fallback)

### Offene Klärungspunkte vor Start

- **#1/#29:** Soll #29 vollständig in #1 aufgehen, oder bleibt ein eigenständiger
  Rest übrig? Erst nach Abschluss von #1 final entscheidbar.
- **#3, #17, #20, #32:** größere, eigenständige Features ohne harte Abhängigkeiten
  zu anderen Punkten — Reihenfolge untereinander richtet sich nach Priorität/
  Nutzen, nicht nach technischen Voraussetzungen.

### Vollständigkeits-Hinweis

Punkt **#25** (TV-Pfad: Angleichung der Untertitel-Erkennung) fehlte bislang in
der Übersichtstabelle, obwohl der zugehörige Abschnitt existierte — wurde
ergänzt.

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

## 9. Eingebaute Authentifizierung (PIN/Passwort)

Für Nutzer, die das Medienwerkzeug als Docker-Container betreiben, aber keinen Reverse-Proxy (wie Traefik oder Nginx) eingerichtet haben, ist das Web-Interface im gesamten LAN offen erreichbar. Dies stellt ein Sicherheitsrisiko für die hinterlegten API-Keys dar.

### Ziel
Eine simple, in Flask integrierte Authentifizierung, die den Nutzer beim ersten Aufruf der Web-UI zwingt, ein Zugangspasswort (oder eine PIN) festzulegen. Danach muss man sich anmelden und die Session wird als Cookie gespeichert.

### Umsetzung
- Speicherung des Passwort-Hashes sicher in der `settings.json`.
- Flask-Middleware (`@app.before_request`), die alle Routen (außer Login und Statics) schützt und bei unautorisierten Anfragen einen 401 Fehler oder Redirect wirft.
- Eine simple, schön gestaltete Login-Seite als Einstiegspunkt im Frontend.

### Aufwand (grob)
~1 Tag. Die Logik für Session-Cookies und Flask-Routen-Schutz ist standardisiert, erfordert aber Anpassungen am Frontend-Routing und API-Verhalten.

---

## 10. Duplikat-Erkennung für Filme

Die globale Duplikat-Erkennung gruppiert aktuell bewusst nur Serienepisoden anhand
von `SxxExx`. Für Filme fehlt eine verlässliche Identitätsregel.

### Ziel
Mehrfach vorhandene Filme erkennen, ohne verschiedene Filme mit ähnlich klingenden
Titeln irrtümlich als Duplikate zu behandeln.

### Umsetzung
- Primär Metadaten-IDs aus vorhandenen NFO-Dateien verwenden (z.B. TMDB-ID).
- Als Fallback normalisierten Titel plus Erscheinungsjahr nutzen.
- Vor Löschvorschlägen Codec, Auflösung, Laufzeit und Dateigröße vergleichen.
- Unsichere Treffer nur als prüfbedürftige Kollision anzeigen.

### Aufwand (grob)
~1–2 Tage inklusive Tests.

---

## 11. Inkrementeller Cache für den Duplikat-Scan

Der Duplikat-Scan läuft derzeit bei jedem Start erneut über alle Serienordner und
führt für Treffer zusätzliche Medienanalysen aus. Er nutzt den schnellen
Health-Cache nicht.

### Ziel
Unveränderte Bibliotheksbereiche überspringen und nur neue oder geänderte Dateien
erneut gruppieren und analysieren.

### Umsetzung
- Eigenen Cache für den Duplikat-Scan verwenden; keine enge Kopplung an den
  Health-Cache.
- Pro Serien- oder Filmordner ein kompaktes Manifest relevanter Videodateien
  speichern (Pfad, Größe, `mtime`).
- Bereits ermittelte Medieninformationen wie Codec, Auflösung und Laufzeit
  wiederverwenden.
- Cache-Treffer und Laufzeit sichtbar ausgeben.

### Aufwand (grob)
~1–2 Tage inklusive Migration und Tests.

---

## 12. Performance-Optimierung für sehr große Serienbibliotheken

Serien bleiben auch mit schnellem Health-Scan spürbar langsamer als Filme, weil
sie viele Staffel- und Episodendateien enthalten. Vor weiteren Optimierungen
sollen Messdaten gesammelt werden.

### Ziel
Die tatsächlichen Engpässe in großen Bibliotheken sichtbar machen und gezielt
optimieren, statt pauschal weitere Caches einzubauen.

### Umsetzung
- Laufzeit, Ordneranzahl, Cache-Treffer und erneute Vollprüfungen pro Kategorie
  protokollieren.
- Erst danach prüfen, ob Staffel-Manifeste, feinere Invalidierung oder eine
  begrenzte Parallelisierung auf dem NAS sinnvoll sind.
- Performance-Test mit repräsentativer großer Serienbibliothek dokumentieren.

### Aufwand (grob)
Analyse ~0,5 Tag; Umsetzung abhängig vom Messergebnis.

---

## 13. Komfortablere Health-Quick-Fix-Oberfläche

Für den Vor-Release reicht es, nach einem Quick-Fix Scrollposition, geöffnete
Gruppen und den sichtbaren Kontext stabil zu halten. Später kann die Bedienung
gezielter modernisiert werden.

### Ziel
Mehrere Bibliotheksprobleme nacheinander beheben, ohne dass die Ergebnisliste
vollständig neu aufgebaut wird oder der Nutzer seine Position verliert.

### Umsetzung
- Behobene Einträge lokal aus der Liste entfernen und Summen aktualisieren.
- Hintergrund-Revalidierung gezielt für den betroffenen Ordner ausführen.
- Optional Undo-Hinweis und Fortschrittsfeedback direkt am Eintrag anzeigen.

### Aufwand (grob)
~0,5–1 Tag.

---

## 14. Health-Status-Vertrag & Frontend-Testabdeckung

Für den Vor-Release reicht eine pragmatische Health-UI-Limitierung mit Backend-
Regressionstest. Eine gründlichere Absicherung der Health-Status-Schnittstelle
und der Frontend-Reaktion kann nach dem Release separat umgesetzt werden.

### Ziel
Der Health-Scan-Status soll einen stabilen, dokumentierten Response-Vertrag
bekommen, damit Frontend und Backend auch bei großen Ergebnislisten, Abbrüchen,
Fehlern und Offline-Zuständen nicht auseinanderlaufen.

### Umsetzung
- JSON-Schema oder strukturierte Contract-Tests für `/api/nas/health-status`
  definieren.
- Health-Status-Zustände explizit abdecken: `idle`, `running`, `done`,
  `cancelled`, `error` und NAS-offline-nahe Fehlerfälle.
- Frontend-Tests für `renderHealthStatus()` ergänzen, insbesondere für das
  500-Befunde-Limit, Gesamtzähler, Cache-Statistik, Abbruchstatus und Fehlertexte.
- Testdaten mit sehr vielen Befunden als Fixture bereitstellen, ohne echte NAS-
  oder Browser-Abhängigkeit.

### Aufwand (grob)
~0,5–1 Tag inklusive Test-Fixtures.

---

## 15. FAQ sprachlich und visuell überarbeiten

Die FAQ-Texte sollen sprachlich sauber auf Deutsch überarbeitet werden. Aktuell
fehlen an mehreren Stellen Umlaute oder wurden durch Umschreibungen wie `Ae`,
`Oe` und `Ue` ersetzt. Zusätzlich wirkt das Fragezeichen-Icon über dem
FAQ-Bereich noch nicht stimmig.

### Ziel
- Deutsche FAQ-Texte vollständig prüfen und fehlende Umlaute korrekt einsetzen.
- Formulierungen überarbeiten, damit die Fragen und Antworten natürlich auf
  Deutsch klingen.
- Gestaltung, Größe und Position des Fragezeichen-Icons prüfen und optisch
  verbessern.

### Aufwand (grob)
Klein: Textkorrektur und eine gezielte visuelle Anpassung im Frontend.

---

## 16. System Metrics Worker: Thread-Akkumulation verhindern

Die Hintergrundberechnung der Speicherauslastung (NAS und Inbox/Outbox) nutzt aktuell einen simplen `threading.Thread`-Wrapper mit `join(timeout)`, um Stale Mounts abzufangen, ohne den gesamten Worker-Loop zu blockieren.

### Ziel
Verhindern, dass sich hängende Daemon-Threads ansammeln, wenn das NAS über viele Stunden offline oder "stale" (eingefroren) ist. Da in jedem 60s-Zyklus ein neuer Timeout-Thread gestartet wird, können diese sich andernfalls langsam akkumulieren.

### Umsetzung
- Umstellung des `get_folder_size_bytes` und `_read_target_storage` Aufrufs auf echte Prozesse via `multiprocessing.Process` oder die Ausführung über `subprocess`.
- Ein echter Prozess kann nach einem Timeout via SIGKILL hart beendet werden, während Python-Threads im Status "D" (Uninterruptible Sleep) systembedingt nicht hart getötet werden können.
- Ggf. Einführung eines Circuit Breakers: Nach 3 gescheiterten Timeouts wird die Speichermessung für X Minuten pausiert, um nicht sinnlos Prozesse/Threads zu starten.

### Aufwand (grob)
~0,5 Tage (Klein). Vor allem Architektur-Tests nötig, um sicherzustellen, dass die Multiprocessing-Aufrufe nicht auf die bestehende Job-Queue oder Gunicorn durchschlagen.

---

## 17. NAS-Diagnose-Checkliste auf der Startseite

Nach der kompakten NAS-Statusanzeige kann die Startseite um eine detaillierte,
aufklappbare Diagnose erweitert werden. Ziel ist mehr Transparenz bei
Netzwerk-, Tailscale-, Docker- und Mount-Problemen, ohne die normale
Startseitenansicht dauerhaft zu überladen.

### Ziel
Der Nutzer soll direkt erkennen können, an welchem Schritt die NAS-Verbindung
scheitert: Konfiguration, IP-Erreichbarkeit, Docker-/Desktop-Laufzeitmodus oder
lokaler Mount.

### Umsetzung
- Die Kachel "Systemverbindungen" erhält ein Info-Symbol oder einen kleinen
  "Details"-Schalter.
- Aufgeklappt erscheint eine Diagnose-Checkliste, zum Beispiel:
  - Einstellungen aktiviert.
  - Einhängepfad konfiguriert.
  - Haupt-IP auf Port 445 erreichbar.
  - Backup-/Tailscale-IP auf Port 445 erreichbar.
  - Netzlaufwerk lokal eingehängt.
- Im Desktop-Modus kann ein "Jetzt mounten"-Button angeboten werden, wenn das
  NAS erreichbar, aber noch nicht eingehängt ist.
- Im Docker-Modus bleiben Mount-Aktionen deaktiviert; die UI erklärt stattdessen,
  dass das NAS außerhalb des Containers als Volume bereitgestellt werden muss.
- Die API muss dafür strukturierte Diagnosedaten liefern, etwa `nas_enabled`,
  `nas_root_configured`, `checked_ips`, `reachable_ip`, `runtime_mode` und
  einen optionalen Fehler- oder Hinweistext.

### Aufwand (grob)
Klein–mittel: Backend-Diagnosevertrag, Frontend-Aufklappbereich und Tests für
Desktop-/Docker-Zustände.

---

## 18. Docker-Image veröffentlichen (GHCR/Docker Hub)

Das Docker-Profil ist der primäre Distributionskanal für NAS- und Server-Nutzer.
Nach dem lokalen Docker-Produktcheck soll das Image öffentlich und versioniert
bereitgestellt werden.

### Ziel
Nutzer können das Medienwerkzeug über ein fertiges Container-Image installieren
und später per `docker compose pull` aktualisieren.

### Umsetzung
- Image unter einem stabilen Namen in GitHub Container Registry oder Docker Hub
  veröffentlichen.
- Tags für Versionen (`v1.0`, `v1.1`, `latest`) definieren.
- `docker-compose.yml` mit klaren Volume-Beispielen und Portainer-/Synology-
  kompatibler Anleitung dokumentieren.
- Kompatibilität mit Portainer, Synology Docker-UI und Unraid testen.

### Aufwand (grob)
Mittel: Registry-Setup, Build-Pipeline, Release-Dokumentation und manuelle Tests
auf einer echten NAS-/Server-Umgebung.

---

## 19. Geführter rclone-Web-Flow

Cloud-Ziele funktionieren über `rclone`, aber der OAuth-Setup-Prozess ist aktuell
terminalnah. Für weniger technische Nutzer braucht es eine geführte Einrichtung
in der Weboberfläche.

### Ziel
Cloud-Remotes wie Google Drive oder pCloud können ohne direkten Terminalkontakt
eingerichtet, getestet und in den Einstellungen ausgewählt werden.

### Umsetzung
- Bestehende rclone-Remotes listen und in der Settings-UI auswählbar machen.
- Geführten Flow für `rclone config` bzw. OAuth-URL, Rückmeldung und
  Verbindungstest entwerfen.
- Fehlerfälle verständlich anzeigen: fehlendes rclone, abgebrochener Login,
  ungültiges Remote, Backend unterstützt `rclone about` nicht.
- Keine OAuth-Tokens im Code oder Repository speichern; Konfiguration bleibt
  nutzer- und installationsspezifisch.

### Aufwand (grob)
Mittel: UI-Flow, sichere Prozesssteuerung, Fehlerbehandlung und Tests mit
gemockten rclone-Antworten.

---

## 20. Web-Upload mit Drag & Drop

Für Nutzer, die keinen NAS-Share am Client eingebunden haben, kann ein Upload
direkt in die Weboberfläche sinnvoll sein. Für große Videodateien ist das ein
eigenständiges Feature.

### Ziel
Dateien und Ordner können über die Weboberfläche in die Inbox hochgeladen werden,
ohne dass der Nutzer vorher ein Netzlaufwerk verbinden muss.

### Umsetzung
- Upload-Dialog mit Drag & Drop, Fortschritt und Abbruchmöglichkeit.
- Chunked Uploads für große Dateien, idealerweise mit Resume nach Abbruch.
- Serverseitige Größenlimits, freie-Speicher-Prüfung und verständliche Fehler.
- Sichere Zielpfad-Auflösung innerhalb der erlaubten Inbox-Roots.
- Tests für unterbrochene Uploads, doppelte Dateinamen, unzulässige Pfade und
  sehr große Dateien.

### Aufwand (grob)
Groß: Frontend-Upload-UX, Backend-Streaming/Chunking, Speicherprüfung und
robuste Fehlerfälle.

---

## 21. Desktop-App Packaging (pywebview/PyInstaller)

Neben Docker soll später eine native Desktop-App möglich sein. Das ist getrennt
von der allgemeinen Tool-Bündelung zu betrachten, weil Fensterintegration,
Signierung und Plattformunterschiede eigene Risiken haben.

### Ziel
Das Medienwerkzeug lässt sich als macOS-/Windows-Desktop-App starten, ohne dass
Nutzer Python oder die Flask-App manuell bedienen müssen.

### Umsetzung
- `pywebview` as natives Fenster über dem bestehenden Flask-Backend prüfen.
- PyInstaller-/py2app-Builds für macOS und Windows aufsetzen.
- Tool-Pfad-Resolver mit gebündelten oder systemweiten Binaries abstimmen
  (`ffmpeg`, `yt-dlp`, `rclone`).
- Plattformhinweise dokumentieren: macOS Gatekeeper, Windows Defender False
  Positives, fehlende Notarisierung ohne Apple Developer Account.

### Aufwand (grob)
Groß: Build-Pipeline, Plattformtests, Signierungs-/Sicherheitsfragen und
Installationsdokumentation.

---

## 22. Update-Hinweise und Release Notes

Updates sollen für Docker- und spätere Desktop-Nutzer klar sichtbar und
nachvollziehbar sein.

### Ziel
Nutzer erkennen, welche Version sie verwenden, ob ein Update verfügbar ist und
was sich zwischen Versionen geändert hat.

### Umsetzung
- Version in UI und API anzeigen.
- Docker-Update-Hinweise dokumentieren (`docker compose pull` und
  `docker compose up -d`).
- Optional gegen GitHub Releases prüfen und "Update verfügbar" in der UI zeigen.
- Release Notes bzw. Changelog pro Version pflegen: neu, geändert, gefixt,
  bekannte Einschränkungen.

### Aufwand (grob)
Klein–mittel: Versionsquelle, UI-Hinweis, GitHub-Release-Abgleich und
Dokumentationsroutine.

---

## 23. Lizenz- und Drittanbieterhinweise

Bei gebündelten Tools oder veröffentlichten Docker-Images müssen Lizenzhinweise
für mitgelieferte Komponenten sauber dokumentiert werden.

### Ziel
Release-Artefakte enthalten nachvollziehbare Hinweise zu Drittanbieter-Tools und
deren Lizenzen.

### Umsetzung
- `LICENSES/` oder eine gebündelte Drittanbieter-Hinweisdatei anlegen.
- Lizenzlage für `ffmpeg` (GPL/LGPL abhängig vom Build), `yt-dlp`, `rclone` und
  relevante Python-/Frontend-Abhängigkeiten prüfen.
- Docker-Image und spätere Desktop-Bundles auf mitgelieferte Binaries abstimmen.
- README-/Release-Hinweise um die Lizenzinformationen ergänzen.

### Aufwand (grob)
Klein: Recherche, Dokumentation und Pflege bei neuen gebündelten Abhängigkeiten.

---

## 24. API-Key Maskierung UX (Fokus/Editierung-Verhalten)

Wenn ein maskierter API-Key (z. B. `****1234`) im Input-Feld vom Benutzer teil-editiert wird (ohne ihn ganz zu löschen oder komplett zu ersetzen), ignoriert das Backend den Wert stillschweigend aufgrund der `is_masked()`-Prüfung. Dies kann zu Verwirrung führen, da der Benutzer denkt, er hätte den Key geändert, dieser aber unverändert bleibt.

### Ziel
Eine sauberere UX beim Editieren maskierter Werte.

### Umsetzung
- Im Frontend beim Fokussieren (`focus`-Event) oder bei der ersten Tastatureingabe (`input`-Event) den maskierten Wert automatisch verwerfen/leeren, um dem Benutzer eine saubere Neueingabe zu ermöglichen.
- Alternativ: Validierung im Frontend einbauen, die verhindert, dass teileditierte Werte, die mit `****` beginnen, abgesendet werden (mit entsprechendem Validierungshinweis).

### Aufwand (grob)
Klein: Reine Frontend-UX-Anpassung in `app.js`.

---

## 25. TV-Pfad: Angleichung der Untertitel-Erkennung

Aktuell unterscheidet sich die Erkennung von Untertiteln in der TV-Vorschau von der des Movie-Pfads.

### Ausgangslage
- Der TV-Pfad findet Untertitel in Unterordnern nur, wenn sie exakt mit dem Dateinamen der Episode beginnen (`sbasename.startswith(base_old)` in [`queue_api.py`](file:///Users/alex/Documents/Medienwerkzeug/gui/api/queue_api.py#L358-L376)).
- Fremd benannte Untertitel (z. B. `ger_forced.sub` in einem Unterordner neben `S01E01.mkv`) werden dadurch im TV-Pfad nicht als solche erkannt und zugeordnet. Sie landen am Ende zwar über die Auffangregel im Serienordner, verlieren aber ihre Sprach-/Forced-Tags.
- Im Movie-Pfad hingegen werden alle Untertitel über `sub_exts` global erfasst und whitelisted.

### Ziel
- Angleichung der TV-Untertitel-Erkennung, sodass auch im TV-Pfad unstrukturierte, aber klar zuzuordnende Untertiteldateien in Unterordnern (z. B. durch Nähe zur Episodendatei) als Untertitel erkannt und mitsamt ihren Suffixen whitelisted werden.

### Aufwand (grob)
Klein: Erweiterung des Suchmusters in der TV-Vorschau (`queue_api.py`).

---

## 26. FAQ/Dokumentation: Docker-Importquellen und Volume-Mapping beschreiben

Für Benutzer, die das Medienwerkzeug in Docker (z. B. auf einem Synology NAS) betreiben, ist die Anbindung von lokalen Import-Quellen (wie StreamFab auf dem Mac) oft eine Stolperfalle. Es soll eine detaillierte FAQ bzw. Anleitung hinzugefügt werden.

### Ziel
Verständliche Erklärung der Ordner-Pfade (Host vs. Container) und wie externe Download-Quellen (z. B. StreamFab auf dem Mac) so konfiguriert werden, dass sie über das NAS in den Docker-Container fließen.

### Umsetzung
- Ergänzung der FAQ in der Web-UI (`index.html`) um einen Eintrag zum Thema "Wie binde ich Import-Quellen in Docker ein?".
- Dokumentation der beiden Lösungswege (A: Download direkt auf das gemountete NAS, B: Zusätzliches Volume-Mapping in `docker-compose.yml`).

### Aufwand (grob)
Klein: Reine Textarbeit in `index.html` und Dokumentations-Update.

---

## 27. Web-Folder-Picker: Dynamische Titel je nach ausgewählter Kategorie

### Ziel
Beim Klick auf die Lupe zur Ordnerauswahl in den Einstellungen soll der Titel des Web-Folder-Picker-Modals kontextsensitiv angepasst werden. Statt des allgemeinen Titels "Ordner auswählen" soll z. B. angezeigt werden: "Ordner für Filme auswählen" oder "Ordner für Serien auswählen" (je nach Kategorie).

### Umsetzung
- Übergabe des Kategorie-Namens oder Typs an `openFolderPicker()`.
- Dynamische Anpassung der Überschrift im HTML-Modal via Javascript beim Öffnen.

### Aufwand (grob)
Klein: Minimale Änderung im Javascript und Modal-DOM.

---

## 28. Web-Folder-Picker: Layout-Verbreiterung & responsive Anpassungen

### Ziel
Das Modal für den Web-Folder-Picker soll auf Bildschirmen mit ausreichendem Platz breiter dargestellt werden, um tiefe Pfadstrukturen und lange Ordnernamen ohne Umbrüche lesbar anzuzeigen.

### Umsetzung
- Anpassung der CSS-Klassen bzw. Inline-Styles für das Modal (`#modal-folder-picker .mw-modal`) in `index.html`.
- Nutzung von flexiblen Breiten (z. B. `max-width: 700px` statt `500px`) und Media Queries für mobile Geräte.

### Aufwand (grob)
Klein: CSS-Stylesheets anpassen.

---

## 29. Speicherziel Syncing: Separater Zielordner pro Speicherziel

### Ziel
Beim Einrichten des Speicherziel-Syncings soll der Benutzer für jedes konfigurierte Speicherziel (z. B. NAS und pCloud) einen individuellen Zielordner festlegen können, anstatt dass ein globaler Ordner oder ein hartkodierter Standardpfad für alle genutzt wird.

### Umsetzung
- Erweiterung des Einstellungs-Modells, sodass Ordner-Pfade pro Speicherziel und Kategorie (Filme/Serien) separat abgespeichert und editiert werden können.
- Anpassung der UI in den Einstellungen, um für jede aktivierte Speicherziel-Spalte ein eigenes Pfad-Eingabefeld (mit Picker) zu rendern.

### Aufwand (grob)
Klein–mittel: UI-Raster-Anpassung und Einstellungs-Struktur-Erweiterung.

---

## 30. Cloud-Upload (rclone): Status- und Fortschritts-Feedback in der Warteschlange

### Ziel
Während der rclone-Übertragung (z. B. zu pCloud) soll der Benutzer in der Warteschlange (Queue-UI) ein klares Feedback und idealerweise einen Fortschritt erhalten. Aktuell ist der Status in der Warteschlange während des Uploads nicht transparent genug oder zeigt den Fortschritt nicht an.

### Umsetzung
- Parsen des stdout von `rclone` (z. B. über `--use-json-log` oder Regex-Matching des normalen Fortschritts-Outputs von rclone).
- Übermittlung des aktuellen Upload-Zustands/Prozentsatzes über den Job-Status in den API-Antworten von `/api/queue`.
- Visuelle Darstellung des Ladefortschritts oder einer aktiven Upload-Animation in der Frontend-Warteschlange.

### Aufwand (grob)
Klein–mittel: Stream-Parsing von rclone und Übertragung an das Frontend.

---

## 31. NAS-Downloader-Integration (JDownloader/Download-Backend)

### Ziel
Für große Downloads soll der Datenweg optional direkt über den NAS-/Docker-Host
laufen, statt über einen am Mac gemounteten Tailscale-/SMB-Ordner:

```text
Internet -> Downloader auf dem NAS -> NAS-Download-Ordner -> Medienwerkzeug
```

Dadurch muss der Mac nicht als Durchleitungsstation dienen
(`Internet -> Mac -> Tailscale/SMB -> NAS`), und lange Downloads bleiben auch
dann stabiler, wenn der Mac schläft, getrennt wird oder die Verbindung schwankt.

### Grundsatz
Medienwerkzeug soll **nicht selbst zum vollwertigen Downloader werden**. Der
Download-Teil bleibt bei einem spezialisierten Dienst wie JDownloader, aria2,
qBittorrent oder SABnzbd. Medienwerkzeug übernimmt die Integration:

- Download-Jobs/Links an das konfigurierte Download-Backend übergeben.
- Status und Zielordner sichtbar machen.
- Fertige Downloads aus einem gemeinsamen NAS-Ordner importieren und in den
  bestehenden Verarbeitungsfluss übernehmen.

### Gewählter Ansatz: JDownloader als separater Docker-Service

JDownloader wurde als bevorzugtes Downloader-Backend festgelegt (verbreitet,
gut unterstützt). Die Schnittstelle bleibt trotzdem generisch genug, um später
weitere Backends zu ermöglichen.

- Optionalen JDownloader-Container in `docker-compose.yml` beschreiben, nicht in
  denselben Container wie Medienwerkzeug packen.
- Gemeinsames Volume definieren, z. B.
  `/volume1/Kino/Downloads:/downloads`.
- Medienwerkzeug-Einstellungen ergänzen:
  - Downloader aktiviert/deaktiviert.
  - Typ: JDownloader oder generisches Download-Backend.
  - Download-Ordner im Container.
  - Verbindungsdaten/API-Konfiguration, falls erforderlich.
- Fertige Downloads über eine Importquelle oder einen speziellen
  Downloader-Import in die Inbox bzw. Verarbeitung übernehmen.

### Risiken & Hinweise
- JDownloader/MyJDownloader-Authentifizierung und API-Zugriff müssen sauber
  behandelt werden; Zugangsdaten gehören in `.env` bzw. sichere Settings.
- Captchas, Hoster-Änderungen, Login-Cookies und Archive bleiben Aufgabe des
  Downloaders, nicht des Medienwerkzeugs.
- Der gemeinsame Download-Ordner muss als Docker-Volume korrekt gemappt sein,
  damit beide Container dieselben Dateien sehen.
- Für andere Backends sollte die Schnittstelle generisch genug bleiben, damit
  später aria2, qBittorrent oder SABnzbd möglich sind.

### Aufwand (grob)
Mittel: Docker-Compose-Erweiterung, Settings-UI, API-Anbindung an ein
Downloader-Backend, Import-/Statuslogik und Dokumentation.

---

## 32. Automatische Papierkorb-Leerung unter Docker

### Ziel
Der Docker-/NAS-Papierkorb (`.medienwerkzeug-trash`) soll optional automatisch
geleert werden, damit Dateien nicht dauerhaft nur in die Quarantäne verschoben
werden. Die Aufbewahrungszeit soll konfigurierbar sein, z. B. 2 Tage, 7 Tage
oder ein eigener Wert.

### Ausgangslage
- Aktuell werden unerwünschte Dateien und gelöschte Medien im Docker-Modus nicht
  endgültig entfernt, sondern in den sicheren Medienwerkzeug-Papierkorb auf dem
  gemappten Volume verschoben.
- Das schützt vor versehentlichem Datenverlust, führt aber dazu, dass alter Müll
  Speicherplatz belegt, bis der Papierkorb manuell geleert wird.

### Umsetzung
- Neue Einstellung für automatische Papierkorb-Leerung:
  - aktiviert/deaktiviert,
  - Aufbewahrungsdauer in Tagen,
  - optionaler Button "Papierkorb jetzt prüfen/leeren".
- Hintergrund-Job oder geplanter Cleanup beim Start, der nur Dateien löscht, die
  älter als die konfigurierte Aufbewahrungsdauer sind.
- Sicherheitsprüfung vor endgültigem Löschen:
  - Der Cleanup darf ausschließlich innerhalb des bekannten
    `.medienwerkzeug-trash`-Ordners arbeiten.
  - Pfade müssen per `realpath`/`commonpath` gegen Symlink- oder
    Pfad-Ausbrüche abgesichert werden.
  - Vor dem Aktivieren sollte ein Schreib- und Löschtest mit einer temporären
    Testdatei prüfen, ob der Container die Dateien wirklich löschen darf.
  - Wenn Rechte fehlen oder der Trash-Pfad nicht eindeutig bestimmbar ist, wird
    nicht gelöscht, sondern sichtbar geloggt/gewarnt.
- Transparenz:
  - Vor einem manuellen Leeren anzeigen, wie viele Dateien und wie viel Speicher
    betroffen wären.
  - Nach jedem Cleanup Anzahl der gelöschten Dateien und Fehler protokollieren.
  - Optional: Dry-Run-Endpunkt für Diagnose und UI-Vorschau.

### Risiken & Hinweise
- Endgültiges Löschen ist irreversibel. Deshalb nur nach explizit aktivierter
  Einstellung und nie außerhalb des Medienwerkzeug-Papierkorbs.
- Docker-PUID/PGID und NAS-Dateirechte können das Löschen verhindern. Das muss
  als eigener Diagnosefall behandelt werden, nicht als stilles Scheitern.
- Bei sehr großen Papierkörben sollte der Cleanup in Batches laufen, damit die
  Web-App nicht blockiert.

### Aufwand (grob)
Klein–mittel: Settings-Erweiterung, Cleanup-Worker, Rechte-/Pfadprüfung,
UI-Vorschau und Tests für Sicherheitsgrenzen.

---

## 33. Automatischer TVDB-Fallback für fehlende TMDB-Plots

### Ziel
Wenn für eine Serie (wie z. B. "H2O - Abenteuer Meerjungfrau") als Metadaten-Anbieter TMDB ausgewählt wird, kann es vorkommen, dass TMDB zwar Episodeninformationen wie Titel und Ausstrahlungsdatum liefert, aber keine Handlungsbeschreibungen (`overview`) gepflegt sind. In solchen Fällen soll das Backend automatisch versuchen, den fehlenden Plot über TVDB nachzuladen.

### Umsetzung
- Innerhalb der Funktionen in `mw_metadata.py` (insbesondere `fetch_episode_nfo_data`) prüfen, ob die von TMDB gelieferte Beschreibung leer ist.
- Ist sie leer, über die TMDB API (z. B. via `/tv/{id}/external_ids`) die verknüpfte `tvdb_id` abrufen.
- Einen Lookup bei TVDB für die entsprechende Serie bzw. Staffel und Episode durchführen.
- Den dort gefundenen Plot nahtlos in das Rückgabe-Ergebnis integrieren.

### Aufwand (grob)
Klein: Erweiterung in `mw_metadata.py` um eine kleine Abfrage der `external_ids` und Aufruf der bereits existierenden TVDB-Methoden als Fallback.

---

## 34. Altersfreigabe-Checks im UI deutlicher erklären

### Ziel
Wenn beim Bibliothekscheck abweichende Altersfreigaben (z. B. Schreibweisen wie `FSK-18` statt `FSK 18`) gemeldet werden, soll für den Benutzer in der UI deutlicher hervorgehoben werden, warum dies geschieht (Formatvereinheitlichung für Filter und Badges, auch wenn Medienserver wie Emby beide Formate lesen können).

### Umsetzung
- Im Frontend bei der Anzeige von `invalid_age_rating`-Hinweisen einen Tooltip oder Info-Text einblenden, der den Hintergrund (Formatvereinheitlichung) erklärt.
- Die Detail-Beschreibung in der Issue-Liste entsprechend verständlich formulieren.

### Aufwand (grob)
Klein: UI-Textänderungen.

---

## 35. Premium-Umbenennungsdialog für Health-Fixes mit Metadaten-Lookup

### Ziel
Der aktuelle Umbenennungs-Quick-Fix im Health-Dashboard nutzt ein einfaches Browser-Eingabefenster (`prompt()`). Dieses soll durch ein stilvolles Medienwerkzeug-eigenes Modal ersetzt werden, das Fehleingaben verhindert, Sicherheits-Bestätigungen verlangt und intelligente Metadaten-Suchen direkt integriert.

### Umsetzung
- **Echtes UI-Modal:** Das standardmäßige JavaScript-Prompt durch ein passendes HTML-Modal ersetzen, welches sich gestalterisch nahtlos in das Medienwerkzeug-Design (Glasmorphismus) einfügt.
- **Sicherheits-Bestätigungsdialog:** Vor dem physischen Umbenennen auf dem NAS wird dem Benutzer eine Vorschau angezeigt ("Sicher? Folgende Dateien werden umbenannt: ..."), um unbeabsichtigte Tippfehler abzufangen.
- **Bereinigter Namensvorschlag:** Vorbefüllung des Eingabefeldes mit einem bereinigten Namensvorschlag (z. B. Punkte durch Leerzeichen ersetzen, Jahr in Klammern setzen), analog zur Logik bei der normalen Metadatensuche.
- **Metadaten-Lookup:** Integration einer Live-Suchmaske für TMDb/TVDB im Modal. Findet der Benutzer den korrekten Titel online, kann er diesen mit einem Klick als Zielnamen für den Umbenennungs-Prozess übernehmen.

### Aufwand (grob)
Klein–mittel: UI-Modal entwerfen, API um eine Bestätigungsvorschau erweitern und Suche im Modal anbinden.

---

## 36. Health-Dashboard: Gruppierung, Massen-Fixes (Batch) & Auto-Korrektur

### Ziel
Bei großen Medienbibliotheken können Hunderte von Health-Warnungen auftreten. Die manuelle Behebung jedes einzelnen Befunds ist extrem zeitaufwendig. Das Dashboard soll durch Gruppierungsfunktionen, Massen-Bearbeitung (Batch-Actions) und eine intelligente Auto-Korrektur erweitert werden, um das Beheben von Massen-Issues drastisch zu beschleunigen.

### Umsetzung
- **Fehler-Gruppierung im UI:** Optionale Umschaltung der Befund-Liste von der pfadbasierten Sortierung hin zu einer Gruppierung nach Fehlertyp (z. B. alle "Ungültige Altersfreigabe" zusammen anzeigen).
- **Massen-Aktionen (Batch-Fixes):** Einführung von Sammel-Aktionen über Checkboxen oder direkt für ganze Fehler-Gruppen (z. B. "Alle FSK-Schreibweisen der Gruppe auf einmal korrigieren").
- **Intelligente Auto-Korrektur (Heuristik):**
  - Automatisches Ersetzen offensichtlicher Schreibfehler (z. B. das Entfernen von Bindestrichen bei `FSK-18` -> `FSK 18` oder Angleichungen von Kleinschreibung).
  - Nur bei nicht eindeutig behebbaren Fehlern (z. B. völlig fehlenden Werten oder unbekannten Ratings) wird der Benutzer zur manuellen Auswahl/Bestätigung aufgefordert.
- **Hintergrund-Batch-Job:** Die Massenänderungen werden asynchron im Hintergrund durchgeführt, um Timeouts bei Hunderten von Dateiänderungen zu verhindern.

### Aufwand (grob)
Mittel: Anpassung der Health-UI (Gruppierungs-Logik, Checkboxen), Backend-Batch-API und Implementierung von Auto-Fix-Heuristiken.
