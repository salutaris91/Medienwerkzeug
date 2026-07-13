# Medienwerkzeug vor dem NAS-Update mit OrbStack testen

Dieses Runbook beschreibt die lokale Akzeptanzumgebung für macOS. Sie verwendet
dieselbe Docker-Laufzeit wie das NAS, aber ausschließlich synthetische
Testdaten. Das NAS wird weder verbunden noch eingebunden.

## Wann du dieses Runbook verwendest

- vor dem Merge eines Feature-Branches: aktuellen Quellcode lokal bauen und testen;
- nach dem Merge: das von GitHub Actions veröffentlichte Image separat testen;
- vor einem NAS-Update: prüfen, ob genau dieses Registry-Image startfähig ist.

Die Umgebung eignet sich für UI-, Metadaten-, NFO-, FSK- und Health-Scan-Tests.
Die mitgelieferten `.mkv`-Dateien sind Textplatzhalter und deshalb nicht für
Transcoding- oder Wiedergabetests geeignet. Dafür kopierst du eigene unkritische
Testmedien ausschließlich nach `.runtime-test/media-run/`.

## Das mentale Modell

| Begriff | Bedeutung |
| --- | --- |
| Image | Unveränderliches Paket aus Anwendung, Python und Systemwerkzeugen. |
| Container | Laufende Instanz eines Images. Sie ist jederzeit ersetzbar. |
| Bind-Mount | Explizit freigegebener Host-Ordner, den der Container sehen darf. |
| `config` | Persistente Testeinstellungen; überlebt Container-Neustarts. |
| `media-run` | Beschreibbare Wegwerfkopie der Testbibliothek. |
| Fixture | Versionierte, unveränderte Ausgangsbibliothek für einen Reset. |

OrbStack stellt auf dem Mac den Docker-Daemon bereit. `docker compose` liest
`compose.orbstack.yml`, erstellt den Container und bindet genau zwei lokale
Ordner ein:

```text
.runtime-test/config    -> /config
.runtime-test/media-run -> /media
```

Es gibt keinen Mount auf `/Volumes`, keine SMB-Verbindung und keinen Zugriff auf
deine NAS-Mediathek. Die Weboberfläche ist nur auf dem eigenen Mac unter
<http://127.0.0.1:5812> erreichbar.

Die Compose-Datei verwendet bewusst `linux/amd64`: GitHub Actions veröffentlicht
das derzeitige NAS-Image für diese Architektur und der Dockerfile enthält die
Intel-VAAPI-Treiber des NAS. Auf einem Apple-Silicon-Mac emuliert OrbStack AMD64.
Das ist etwas langsamer als ein nativer ARM64-Build, prüft dafür aber dieselbe
Plattform, die anschließend produktiv eingesetzt wird.

## Voraussetzungen

1. OrbStack ist installiert und gestartet.
2. Im Terminal funktionieren `docker info` und `docker compose version`.
3. Du befindest dich im Medienwerkzeug-Repository oder im Feature-Worktree.

Der zentrale Einstiegspunkt ist immer:

```bash
scripts/orbstack-test.sh help
```

## Einmalige Initialisierung

```bash
scripts/orbstack-test.sh init
```

Dabei entstehen ausschließlich gitignorierte Laufzeitdateien unter
`.runtime-test/`. Existierende Testmedien werden nicht überschrieben.

## Test 1: aktuellen Feature-Branch bauen

```bash
scripts/orbstack-test.sh reset
scripts/orbstack-test.sh build
scripts/orbstack-test.sh start
```

Was im Hintergrund geschieht:

1. `reset` ersetzt nach Bestätigung nur `media-run` durch die Fixture.
2. `build` baut den aktuellen Git-Stand als `medienwerkzeug:orbstack-local`.
3. Branch und Commit werden als Container-Metadaten gespeichert.
4. `start` startet dieses vorhandene Image ohne einen versteckten Neubau.
5. Der Smoke-Test ruft `/api/healthz` und `/api/system/capabilities` auf und
   verlangt `runtime=docker`.

Öffne danach <http://127.0.0.1:5812>. Konfiguriere in der Anwendung nur Pfade
unter `/media`. Für die Fixture sind das insbesondere `/media/Filme` und
`/media/Serien`.

## Empfohlene manuelle Prüfung

1. Einrichtungsdialog und Startseite öffnen.
2. `/media/Filme` und `/media/Serien` als Testbibliothek konfigurieren.
3. Health-Scan ausführen.
4. Prüfen, dass fehlende und ungültige FSK-Werte sowie die fehlende
   `tvshow.nfo` erkannt werden.
5. Einen einzelnen FSK-Wert und anschließend Staffel-/Serien-Scope testen.
6. Kontrollieren, dass nur Dateien in `.runtime-test/media-run` geändert wurden.
7. Container stoppen und erneut starten; Einstellungen müssen erhalten bleiben.
8. `reset` ausführen; die Medien müssen wieder dem Ausgangszustand entsprechen,
   während die Konfiguration erhalten bleibt.

Status und Logs:

```bash
scripts/orbstack-test.sh status
scripts/orbstack-test.sh logs
```

## Test 2: veröffentlichtes Image nach dem Merge

Warte zuerst, bis der Docker-Publish-Workflow für `main` erfolgreich war. Dann:

```bash
scripts/orbstack-test.sh reset
scripts/orbstack-test.sh release
scripts/orbstack-test.sh status
```

`release` zieht standardmäßig
`ghcr.io/salutaris91/mediawerkzeug:main`, startet es ohne lokalen Build und
führt denselben Smoke-Test aus. Ein anderes Tag oder ein Digest kann explizit
übergeben werden:

```bash
scripts/orbstack-test.sh release ghcr.io/salutaris91/mediawerkzeug@sha256:DEIN_DIGEST
```

Für die endgültige NAS-Freigabe ist ein Digest besser als nur `main`, weil er
ein unveränderliches Image eindeutig bezeichnet.

## Stoppen, Zurücksetzen und Aufräumen

Nur den Testcontainer stoppen:

```bash
scripts/orbstack-test.sh stop
```

Testmedien wiederherstellen:

```bash
scripts/orbstack-test.sh reset
```

Für automatisierte lokale Abläufe ist die ausdrückliche Bestätigung möglich:

```bash
scripts/orbstack-test.sh reset --yes
```

`reset` verändert nicht `.runtime-test/config`. Ein vollständiges Löschen der
lokalen Runtime ist absichtlich nicht automatisiert. Dadurch kann kein zu weit
gefasster Cleanup-Befehl versehentlich andere Daten entfernen.

## Fehlerdiagnose

### `Docker is unavailable`

Starte OrbStack und prüfe:

```bash
docker info
docker context show
```

### Anwendung wird nicht gesund

```bash
scripts/orbstack-test.sh status
scripts/orbstack-test.sh logs
```

Der Compose-Healthcheck wartet auf `/api/healthz`. Häufige Ursachen sind ein
fehlgeschlagener Build, nicht beschreibbare Testordner oder ein bereits belegter
Port `5812`.

### Port `5812` ist belegt

Stoppe zunächst nur eine eventuell ältere Medienwerkzeug-Testinstanz:

```bash
scripts/orbstack-test.sh stop
```

Ändere nicht spontan die produktive Compose-Datei. Eine dauerhafte Portänderung
gehört in `compose.orbstack.yml` und in dieses Runbook.

## Freigabegrenze zum NAS

Ein erfolgreicher lokaler Test aktualisiert das NAS nicht. Erst nach deiner
expliziten Freigabe wird auf dem NAS das bereits veröffentlichte Image gezogen.
Die produktiven Deployment-Schritte bleiben von dieser Testumgebung getrennt.
