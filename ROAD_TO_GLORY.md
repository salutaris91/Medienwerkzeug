# Road to Glory – Release & Distribution Plan

Dieser Plan (die "Road to Glory") skizziert den Weg, um das Medienwerkzeug von einem für dich optimierten, lokalen Skript in eine weitergebbare, robuste App zu verwandeln, die auch bei Dritten (ohne technische Vorkenntnisse) einwandfrei läuft.

---

## Distributions-Strategie

Das Medienwerkzeug wird über **zwei Kanäle** verteilt — mit identischem Code:

### Primär: Docker (für NAS/Server-Nutzer)
Die Zielgruppe betreibt bereits Medienserver (Emby, Jellyfin, Plex) auf NAS-Systemen. Docker ist dort Standard (Synology, Unraid, TrueNAS bieten Docker-UIs). Ein `Dockerfile` + `docker-compose.yml` ist der schnellste und stabilste Weg zum Release.

- Alle Dependencies (Python, Flask, ffmpeg, yt-dlp, rclone) sind im Image enthalten
- Kein "funktioniert auf meinem Rechner"-Problem
- Updates = neues Image pullen
- Die App läuft direkt neben den Medien — kein SMB-Mounting vom Laptop nötig
- Zugriff über den Browser im LAN (`http://nas-ip:5811`)

**Workflow für Nutzer:** Downloads (z.B. via yt-dlp) gehen direkt auf einen NAS-Share, der als Netzlaufwerk am PC eingebunden ist. Der Docker-Container hat den gleichen Ordner als Volume gemountet und sieht neue Dateien sofort. So funktionieren alle NAS-Medien-Workflows (Sonarr, Radarr etc.).

### Sekundär: Desktop-App (für Nutzer ohne NAS)
Für Nutzer, die das Tool lokal auf dem Mac oder PC nutzen wollen, wird eine native Desktop-App gebaut:

- **pywebview** öffnet ein natives Fenster mit System-WebView (WebKit auf Mac, Edge WebView2 auf Windows) — kein Browser-Feeling, kein Chromium-Ballast
- **PyInstaller** bündelt Python + Flask + pywebview in eine `.app` (macOS) bzw. `.exe` (Windows)
- Flask startet im Hintergrund, pywebview zeigt die UI im nativen Fenster
- Für den Nutzer sieht es aus wie jede andere Desktop-App (eigenes Dock-Icon, Cmd+Q zum Schließen, kein URL-Balken)

```
┌─────────────────────────────────────────────┐
│              Identischer Code               │
│         Flask-Backend + Web-Frontend        │
└──────────┬──────────────────┬───────────────┘
           │                  │
     ┌─────▼─────┐    ┌──────▼───────┐
     │  Docker    │    │  Desktop     │
     │  Container │    │  pywebview   │
     │            │    │  + PyInstaller│
     │  NAS/Server│    │  .app / .exe │
     │  → Browser │    │  → natives   │
     │    Zugriff │    │    Fenster   │
     └────────────┘    └──────────────┘
```

---

## 1. Bewertung der aktuellen Roadmap (Was muss vorher fertig werden?)

Bevor wir das Tool an andere verteilen, sollten folgende Punkte der **aktuellen** Roadmap zwingend abgeschlossen sein:

1. **Priorität 1: Lade-Indikator für Inbox-Projekte in Bearbeitung** (Erledigt)
   - **Warum:** Für Erstnutzer ist es absolut kritisch zu sehen, ob das System im Hintergrund arbeitet, sonst klicken sie mehrfach und erzeugen Fehler oder Queue-Staus.
2. **Priorität 2: Server-genaue Artwork-Prüfung** (Erledigt)
   - **Warum:** Andere Nutzer setzen oft Emby oder Plex ein. Wenn das Medienwerkzeug hier falsche Warnungen ausgibt (weil es aktuell sehr tolerant prüft), führt das zu Support-Fragen.
3. **Priorität 3: Inkrementeller Health-Scan** (Erledigt)
   - **Warum:** Gerade bei großen externen Bibliotheken dauern vollständige Scans extrem lange. Ein Caching ist zwingend nötig für eine flüssige User Experience.
4. **Nice-to-Have: Echtes Multi-Cloud**
   - **Warum:** Wäre als "1.0 Feature" cool, kann aber notfalls auch per Update (`1.1`) nachgereicht werden. Google Drive wird aktuell schon unterstützt (Nutzer kann `gdrive:` statt `pcloud:` eintragen). Was fehlt, ist nur die gleichzeitige Nutzung beider Dienste mit getrennten Schaltern.

*(Punkte wie die KI-Covergenerierung können warten und als Features in späteren Updates verkauft werden).*

---

## 2. Road to Glory – Der Weg zum Public Release

### Phase 0: Pre-Release Features (Aus der alten Roadmap)
*Diese Punkte müssen als Fundament fertiggestellt werden, bevor die eigentliche Distribution-Härtung beginnt.*

#### 1. Lade-Indikator für Inbox-Projekte (Erledigt)
Aktuell ist auf dem Startbildschirm (Inbox) nicht ersichtlich, ob ein erkanntes Projekt bereits vom Backend verarbeitet wird. Dies führt zu Unsicherheit und potenziell fehlerhaften Mehrfach-Klicks.
- **Ziel:** Eine visuelle Rückmeldung in der Inbox implementieren (analog zum kreisenden Lade-Symbol der Projektordner in der linken Seitenleiste).
- **Umsetzung:** Die ID des aktuell verarbeiteten Projekts wird über die bestehende SSE-Verbindung (Server-Sent Events) oder den Status-Endpunkt an das Frontend kommuniziert. Das entsprechende Projekt-Kärtchen erhält ein Loading-Icon und der Bearbeiten-Button wird deaktiviert.

#### 2. Server-genaue Artwork-Prüfung (Emby / Jellyfin / Plex) (Erledigt)
Der aktuelle Bibliotheks-Check prüft lediglich, ob *irgendein* Bild im Ordner liegt. Da Dritte andere Medienserver nutzen könnten, führt das zu falschen oder nervigen Warnungen.
- **Ziel:** Differenzierte Meldungen pro Artwork-Typ, exakt abgestimmt auf den konfigurierten Medienserver.
- **Umsetzung:** Ein neues Feld `media_server` in den Einstellungen (Emby, Jellyfin, Plex). Der Health-Scan validiert gegen eine Konventions-Tabelle. Es werden getrennte Issues ausgegeben (z.B. fehlendes Poster = warning, fehlendes Banner = info).

#### 3. Inkrementeller Health-Scan (Timestamp-Cache) (Erledigt)
Der Health-Scan prüft aktuell bei jedem Durchlauf alle Ordner vollständig, inklusive rechenintensiver `ffprobe`-Codec-Stichproben. Bei großen NAS-Bibliotheken dauert dies extrem lange.
- **Ziel:** Ordner, die beim letzten Scan fehlerfrei waren und seitdem nicht verändert wurden, überspringen. Folge-Scans sollen in Sekunden statt Minuten abschließen.
- **Umsetzung:** Pro gescanntem Ordner wird ein Caching-Eintrag (`health_folder_cache.json`) mit dem letzten Änderungsdatum (`mtime` via `os.stat`) und einer Regel-Version (`scan_version`) gespeichert.

---

### Zwischenphase: Der "Hard-Cut" & Testplan
*Nachdem Phase 0 abgeschlossen ist, legen wir einen bewussten Stopp ein, um die Stabilität der aktuellen App zu sichern, bevor wir das Fundament für den Release umbauen.*

#### Phase 0.5: Härtung & UX-Optimierungen (Feedback aus der Verifizierung)
Bevor wir den `release`-Branch abzweigen, werden folgende Verbesserungen direkt auf `main` umgesetzt:
1. **Artwork-Validierung & Cache-Korrektheit:** (Erledigt)
   - Nummerierte Artwork-Varianten nur entsprechend der Konvention des gewählten Medienservers akzeptieren (z.B. Jellyfin-Backdrops `backdrop-1.jpg` und `backdrop2.jpg`; Plex-Fanarts `fanart-1.jpg`).
   - Die Fehlermeldung neutral zu "Hintergrundbild fehlt" vereinheitlichen.
   - Den Hybrid-Cache-Zustand um alle tatsächlich geprüften Kerndateien erweitern: NFO, Video sowie serverabhängige Poster, Backdrops, Logos und Banner. Dadurch bleiben gelöschte Artworks auch dann erkennbar, wenn das NAS den Ordner-`mtime` nicht zuverlässig aktualisiert.
2. **Hybrid- und Deep-Dive-Cache sauber trennen:**
   - `hybrid_state` und `deep_hash` separat speichern, damit ein Deep-Dive-Lauf den schnellen Folgescan nicht unnötig invalidiert.
   - Laufzeit und Cache-Statistik anzeigen: Treffer, erneute Prüfungen wegen Änderungen und erneute Prüfungen wegen bekannter Issues. Bekannte Issues werden bewusst erneut vollständig geprüft; bei fehlerreichen Bibliotheken bleibt der Folgescan daher erwartbar langsamer.
3. **Race-Condition beim Smart-Inbox-Profil-Laden beheben:**
   - Profil, finale NAS-Kategorie und vorhandenen NAS-Ordner geordnet ermitteln und anschließend die Staffelanzeige aktualisieren.
   - Veraltete Staffel-Requests per Request-ID oder `AbortController` ignorieren, damit eine später eintreffende alte Antwort keine korrekte Anzeige überschreibt.
4. **Health-Scan nach Bibliothekskategorien trennen:** Auswahl einer oder mehrerer konfigurierter Kategorien (z.B. nur Filme oder nur Serien), um Laufzeit und Testergebnisse gezielt beurteilen zu können.
5. **Health-Scan sicher abbrechbar machen:** Abbruch über `threading.Event` und UI-Button. Das Abbruchsignal auch in längeren Unterordner- und Serien-Schleifen prüfen und den Status sichtbar auf `cancelled` setzen.
6. **Quick-Fix-Kontext erhalten:** Nach Aktionen wie "Verschachtelung auflösen" oder "Ordner umbenennen" den sichtbaren Kontext anhand eines stabilen Issue-Schlüssels wiederherstellen. Scrollposition und geöffnete Ergebnisgruppen sollen erhalten bleiben; wenn möglich, wird nur der behobene Eintrag entfernt.
7. **Default-leerer Medienserver:** Neue Nutzer müssen den Medienserver explizit wählen. Ein Scan ohne Auswahl wird bereits am API-Endpunkt mit verständlicher Fehlermeldung abgelehnt, bevor NAS-Mount und Scan-Thread gestartet werden.
8. **Dateinamen zentral bereinigen:** Manuelle Namen aus Quick-Fixes und dem NAS-Renaming-Tool vor `os.rename()` zentral validieren und für das Zieldateisystem bereinigen (z.B. `:` und `?`), damit Sonderzeichen nicht zu Abbrüchen führen.
9. **Ausblendbare Konsole:** Die Konsole am unteren Bildschirmrand standardmäßig ausblenden und über einen "Debug-Modus"-Schalter in den Einstellungen optional aktivierbar machen.

#### 1. Der Hard-Cut (Git-Branching)
Um deinen täglichen Workflow nicht zu stören, wird die Weiterentwicklung über **Git-Branches** getrennt — nicht über eine physische Ordner-Kopie (die würde innerhalb von Tagen auseinanderlaufen):
- **`main`-Branch** = dein täglicher Workflow. Läuft unverändert und stabil weiter.
- **`release`-Branch** = hier passiert die gesamte Release-Härtung (ab Phase 1). Wird von `main` abgezweigt.
- **Bugfixes auf `main`** werden per `git merge main` in den Release-Branch übernommen — ein Befehl statt manuelles Kopieren zwischen zwei Ordnern.
- Beide Branches können parallel laufen (verschiedene Ports), aber es gibt nur **ein** Repository — kein Synchronisations-Problem.

#### 2. Der Testplan (Qualitätssicherung vor dem Branch)
Bevor wir den Release-Branch abzweigen, stellen wir sicher, dass das Fundament absolut fehlerfrei ist.

**Automatisierte Tests (als echte Testdateien, nicht nur Prosa):**
- `test_utils.py` — bestehende Unit-Tests laufen fehlerfrei durch.
- `test_health_scan.py` *(neu)* — Der inkrementelle Health-Scan liest und schreibt die Caching-Dateien (`health_folder_cache.json`) korrekt. Zweiter Durchlauf überspringt unveränderte Ordner.
- `test_artwork_validation.py` *(neu)* — Die Server-genaue Artwork-Prüflogik wirft die korrekten Warnungen pro Medienserver-Typ (simuliert mit Dummy-Pfaden).
- `test_api_endpoints.py` *(neu)* — Keine Regressionen in der API (Endpoints antworten weiterhin wie erwartet, auch bei fehlerhaften Payloads).
- Cache-Grenzfälle ergänzen: gelöschtes Backdrop bei unverändertem Ordner-`mtime`, getrennte Hybrid-/Deep-Dive-Zustände und verständlicher Fehler bei leerem Medienserver.
- Artwork-Konventionen ergänzen: gültige und ungültige nummerierte Varianten pro Medienserver.
- Smart-Inbox ergänzen: veraltete NAS-Staffelantwort darf eine neuere Auswahl nicht überschreiben.
- Dateinamen-Bereinigung ergänzen: manuelle Namen mit illegalen Zeichen werden sichtbar und deterministisch bereinigt.

**Was du (der Nutzer) manuell testest:**
- **Der Lade-Indikator:** Starte einen echten Job in der Inbox und prüfe, ob der Startbildschirm das Lade-Symbol anzeigt und der Bearbeiten-Button deaktiviert ist.
- **NAS-Belastung:** Führe den Health-Scan zweimal auf deinem NAS aus. Der zweite Durchlauf sollte nun extrem schnell (in Sekunden) abgeschlossen sein, da das Timestamp-Caching greift.
- **Täglicher Workflow:** Lade eine Datei über StreamFab herunter und jage sie durch das System. Funktioniert das Umbenennen, Verschieben und Hochladen in die Cloud noch exakt wie gestern?

*Erst wenn du auf diese drei Punkte dein "Go" gibst, zweigen wir den Release-Branch ab und starten Phase 1.*

---

### Phase 1: Code-Härtung & Robustheit
*Alles, was der Code braucht, um bei Dritten zuverlässig zu laufen.*

#### 1.1 Default-Pfade neutralisieren
Aktuelle Defaults im Code (wie `~/pCloud Drive`) müssen leer sein. **Wichtig:** Deine eigenen Einstellungen in der `settings.json` bleiben davon völlig unberührt! Wir ändern nur die Fallbacks für *neue* Nutzer.

#### 1.2 Cross-Platform-Weichen (Mac / Windows / Linux)
- Ist der Nutzer auf Mac: `osascript` (Finder)
- Ist er auf Windows: native Windows-Pfade (`os.startfile` für Explorer, `win10toast` für Benachrichtigungen)
- Ist er im Docker/Linux: keine Desktop-Integrationen nötig, nur CLI-Fallbacks

#### 1.3 `.env`-Handling & Settings-UI
Die Einstellungs-Seite wird um Felder für TMDB/TVDB API-Keys erweitert. Das Backend speichert diese unsichtbar in der `.env`-Datei, sodass der Nutzer nie eine Textdatei anfassen muss.

#### 1.4 Error-Logging & Crash Recovery
- **Strukturiertes Logging** in eine rotierende Log-Datei (nicht nur Konsole) — damit Fehler bei Dritten nachvollziehbar sind.
- **"Bug melden"-Button** in der UI, der relevante Logs anonymisiert exportiert.
- **Crash Recovery für Jobs:** Wenn die App abstürzt während ein Job in `jobs_state.json` auf `in_progress` steht, muss beim Neustart erkannt und bereinigt werden (Status zurücksetzen auf `failed` oder `pending`, nicht auf ewig hängen bleiben).

#### 1.5 Settings-Versionierung & Migration
- Ein `version`-Feld in `settings.json` und `jobs_state.json`.
- Bei App-Updates, die das Schema ändern, läuft eine Migrationsfunktion, die alte Settings automatisch ins neue Format überführt. Ohne das brechen Updates bei bestehenden Nutzern.

#### 1.6 Threadsichere Datei-Schreibvorgänge
`jobs_state.json` und `settings.json` müssen atomar geschrieben werden (Write → Temp-File → `os.rename`), damit bei Stromausfällen oder Neustarts keine korrupten JSON-Dateien entstehen.

#### 1.7 Aktionslog & Undo-Fähigkeit
Wenn die App eine Datei umbenennt, verschiebt oder Ordnerstrukturen anlegt, muss jede Aktion in einem **Aktionslog** (`action_log.json`) protokolliert werden:
- Was wurde gemacht (rename, move, create_folder)
- Quellpfad → Zielpfad
- Zeitstempel
- Zugehöriger Job/Projekt

Das Log ermöglicht:
- **Fehler nachvollziehen:** Wenn ein Nutzer meldet "meine Datei ist weg", kann man im Log nachschauen wohin sie verschoben wurde.
- **Undo (v1.1):** Später kann daraus ein "Rückgängig"-Button gebaut werden, der die letzte Aktion oder den letzten Job zurückrollt.
- Für v1.0 reicht das Log als passive Absicherung — der Undo-Button ist kein Release-Blocker.

---

### Phase 2: Sicherheit & Zugriffskontrolle

#### 2.1 Authentifizierung (LAN-Sicherheit)
Die App läuft als Flask-Server und ist im LAN erreichbar. Ohne Schutz kann jeder im Netzwerk die App steuern und API-Keys einsehen.
- **Für v1.0:** Wir verzichten zunächst auf eine eingebaute Authentifizierung, um den Start so simpel wie möglich zu halten. Stattdessen kommt ein unübersehbarer **Warnhinweis** in die Dokumentation: *"Bitte nur im sicheren Heimnetzwerk betreiben oder hinter einen Reverse-Proxy (Traefik/Nginx) klemmen."*
- **Später (After Release Roadmap):** Eine eingebaute Authentifizierung (Passwort/PIN) wird nachgeliefert.

#### 2.2 API-Key-Schutz
Die Settings-API darf API-Keys nur maskiert zurückgeben (`TMDB_KEY: "****abcd"`). Vollständige Keys werden nur geschrieben, nie gelesen.

---

### Phase 3: Onboarding & First-Time User Experience
*Was sieht der Nutzer beim allerersten Start? Diese Phase kommt VOR dem Packaging, damit der Wizard getestet werden kann, bevor die App eingepackt wird.*

#### 3.1 Onboarding-Wizard
Beim ersten Öffnen darf nicht direkt das leere Dashboard erscheinen. Es muss ein Willkommens-Wizard (Setup) kommen:
1. **Willkommen & Opt-In:** Vorstellung des Tools. Optionales Feld für die E-Mail-Adresse des Nutzers (zur Newsletter-Anmeldung/Updates) und eine Checkbox für anonyme Telemetrie (Nutzungsdaten wie OS, verarbeitete Job-Zahlen zur Verbesserung des Tools; standardmäßig aktiv mit klarem Opt-Out).
2. **API-Keys abfragen:** TMDB-Key eintragen.
3. **Medienserver auswählen:** Emby, Jellyfin oder Plex.
4. **Speicherziele konfigurieren:** NAS-Pfad / lokaler Pfad.
5. **Inbox/Outbox Ordner festlegen:** Pfade für Quell- und Zielordner.

#### 3.2 Telemetrie & Opt-In-Handling (Backend)
- **Schnittstelle:** Einrichten einer minimalen Anbindung an einen Telemetriedienst (z. B. PostHog, Mixpanel oder ein einfacher eigener Cloudflare Worker/Serverless Endpoint), der anonymisierte Events sammelt.
- **Opt-Out-Flag:** Ein `telemetry_enabled`-Schalter in `settings.json`, der auch im Einstellungs-Tab der UI jederzeit deaktiviert werden kann.
- **E-Mail-Übertragung:** Wenn der Nutzer seine E-Mail eingibt, wird diese einmalig an deine zentrale E-Mail-Erfassungsstelle (z. B. SendGrid, Mailchimp oder einen einfachen Webhook) geschickt.

> **Prioritäts-Hinweis:** Die E-Mail-Erfassung wird realistisch nur 5–15 % Conversion erreichen — NAS-Nutzer klicken erfahrungsgemäß "Überspringen". Der eigentliche Wert liegt in der **anonymen Telemetrie** (aktive Installationen, OS-Verteilung, Feature-Nutzung). Diese liefert die harten Zahlen zur App-Akzeptanz. Den E-Mail-Flow daher schlank halten und den Hauptaufwand in die Telemetrie-Anbindung stecken.

#### 3.3 Fallback-Artworks
Wenn keine Cover gefunden werden, generische (aber hübsche) Platzhalter im Design anzeigen.

#### 3.4 In-App-Hilfe
Eine kurze, nutzerfreundliche Hilfe direkt in der App (Tooltips, FAQ-Seite). Kein externes Wiki nötig für den Anfang.

---

### Phase 4: Testing & Stabilität (Quality Assurance)
*Die Utils sind gut getestet (`test_utils.py`), aber die Backend-Logik ist blind.*

#### 4.1 Flask-Endpoint-Tests
End-to-End Tests für die Flask-Endpunkte. Was passiert bei defekten Payloads, fehlenden Feldern, ungültigen Pfaden?

#### 4.2 Mock-Tests für externe Systeme
- NAS-Mounting: Was passiert, wenn SMB fehlschlägt?
- Cloud-Uploads: Was passiert bei rclone-Timeouts?
- API-Ausfälle: Was passiert, wenn TMDB/TVDB nicht erreichbar ist?

#### 4.3 Performance-Grenzen prüfen
- Wie verhält sich die App bei 10.000+ Medien-Einträgen? Gibt es Paginierung?
- NAS über SMB kann langsam sein — Timeouts und Retry-Logik einbauen.
- Mindestanforderungen dokumentieren (RAM, Speicher, Python-Version).

---

### Phase 5: Packaging & Distribution

#### 5.1 Docker-Image (Primärer Kanal – Ziel für v1.0)
- `Dockerfile` auf Basis eines schlanken Python-Images (z.B. `python:3.12-slim`)
- `ffmpeg`, `yt-dlp`, `rclone` werden per `apt-get` / `pip` im Image installiert
- `docker-compose.yml` mit sinnvollen Defaults und kommentierten Volume-Mounts
- Kompatibilität mit Portainer, Synology Docker-UI und Unraid Community Apps testen
- **Rclone-Setup UI:** Der rclone OAuth-Login (aktuell Terminal-basiert) muss im Frontend als geführter Web-Flow nachgebaut werden, damit Nutzer sich über die Browser-UI mit Google Drive/pCloud verbinden können.
- **Web-UI Upload-Button (Ziel v1.1):** Für Nutzer, die ihren NAS-Share nicht als Netzlaufwerk auf dem PC eingebunden haben, wird ein Upload-Button (inkl. Drag & Drop) eingebaut. **Achtung:** Für Videodateien (2-10 GB) braucht das Chunked Uploads, Fortschrittsanzeige und Resume bei Abbruch — das ist ein eigenständiges Feature, kein Einzeiler. Für v1.0 reicht der Verweis auf den NAS-Share als Netzlaufwerk; der Upload-Button kommt in v1.1.

#### 5.2 Desktop-App (Sekundärer Kanal – Ziel für v1.1)
- **pywebview** als natives Fenster (System-WebView, kein Chromium)
- **PyInstaller** bündelt Python + Flask + pywebview + Binaries in `.app` / `.exe`
- **yt-dlp Update-Button** in der UI (`yt-dlp -U`). ffmpeg und rclone bekommen Updates über neue App-Versionen.
- **Pfad-Resolver (`tool()`):** Zentrale Funktion, die für subprocess-Aufrufe primär die mitgelieferten Binaries nutzt, bevor sie auf den System-Path zurückfällt.

#### 5.3 Code-Signing & Gatekeeper (macOS)
Da ein Apple Developer Account 99$/Jahr kostet, verzichten wir vorerst auf die Notarisierung. Stattdessen klare Anleitung: Beim ersten Start *Rechtsklick → Öffnen* oder in *Systemeinstellungen → Datenschutz & Sicherheit* auf "Dennoch öffnen" klicken.

**Hinweis Windows:** PyInstaller-Builds erzeugen regelmäßig Virus-Fehlalarme bei Windows Defender (False Positives). Das ist ein bekanntes Problem und muss in der Release-Dokumentation adressiert werden.

#### 5.4 Lizenzhinweise
`ffmpeg` steht unter GPL/LGPL. Wenn Binaries mitgeliefert werden (Desktop-App) oder im Docker-Image enthalten sind, muss eine `LICENSES/`-Datei mit den entsprechenden Lizenztexten beigelegt werden. Gilt auch für yt-dlp (Unlicense) und rclone (MIT).

#### 5.5 Auto-Updater
- **Docker:** Nutzer pullt einfach das neue Image (`docker-compose pull && docker-compose up -d`). Ein Hinweis in der UI, wenn eine neue Version auf GitHub/Docker Hub verfügbar ist.
- **Desktop:** Prüfung gegen GitHub Releases API. "Update verfügbar"-Button in der UI mit Link zum Download.

---

### Phase 6: Dokumentation & Release

#### 6.1 README aktualisieren
- Aktuelle pip-Abhängigkeiten korrekt auflisten (Flask, Werkzeug, Flask-Cors etc. — die README behauptet aktuell fälschlich, es gäbe keine)
- Installationsanleitung für Docker und Desktop getrennt
- Systemanforderungen (Mindest-RAM, Speicher, unterstützte OS-Versionen)

#### 6.2 Docker Hub / GitHub Container Registry
Image unter einem sauberen Namen veröffentlichen. Tags für Versionen (`v1.0`, `latest`).

#### 6.3 Release Notes
Changelog pro Version. Was ist neu, was ist gefixt, was ist breaking.

---
