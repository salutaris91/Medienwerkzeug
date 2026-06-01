# Entwickler-Wiki

Dieses Wiki ergänzt die nutzerorientierte [README](../../README.md) und die
[API-Dokumentation](../../API.md). Es dient als Einstieg in den Codebestand:
Welche Module gibt es, wie laufen wichtige Vorgänge ab und an welchen Stellen
sind Änderungen besonders sensibel?

## Orientierung

| Seite | Inhalt |
|-------|--------|
| [Architektur](architecture.md) | Schichten, Verzeichnisse und zentrale Abhängigkeiten |
| [Verarbeitungsablauf](processing-flow.md) | Vom Inbox-Projekt über die Queue bis zu Outbox und Speicherzielen |
| [API und Frontend](api-and-frontend.md) | Flask-Blueprints, REST-Kommunikation und Vanilla-JS-Oberfläche |
| [NAS, Health und Duplikate](nas-health-and-duplicates.md) | Bibliotheksprüfung, Duplikat-Erkennung und NAS-Renaming |
| [Einstellungen und Speicherziele](settings-and-storage.md) | Konfiguration, Zielauflösung und zentrale Settings-Abhängigkeit |

## Schnelleinstieg

- Anwendung starten: `python3 gui/main.py`
- Tests ausführen: `python3 -m unittest discover -s tests -b`
- REST-Endpunkte nachschlagen: [API.md](../../API.md)
- Wissensgraph und automatisches Wiki aktualisieren: `scripts/refresh_graphify.sh`
- Graph gezielt abfragen: `graphify query "<Frage>"`

## Wichtige Einstiegspunkte im Code

| Datei | Rolle |
|-------|------|
| `gui/main.py` | Flask-App, Blueprint-Registrierung und Hintergrund-Threads |
| `gui/workers/processor.py` | Queue-Verarbeitung und Medien-Workflows |
| `gui/core/utils.py` | Einstellungen, Profile und gemeinsame Hilfsfunktionen |
| `gui/core/transfers.py` | NAS-Mount, `rsync`, `ffmpeg`, `yt-dlp` und Cloud-Transfer |
| `gui/static/app.js` | Frontend-Zustand, API-Aufrufe und UI-Interaktionen |

## Wissensgraph richtig einordnen

Der automatisch erzeugte Graph unter `graphify-out/` ist ein Analysewerkzeug,
kein Ersatz für dieses Wiki. Er enthält neben Anwendungscode auch Dokumentation
und Projektregeln. Dadurch können Community-Grenzen und isolierte Knoten
inhaltliches Rauschen enthalten. Für konkrete Fragen sind gezielte Befehle wie
`graphify query`, `graphify explain` und `graphify path` hilfreicher als der
vollständige Graphbericht.

Die sprechenden Namen der Graphify-Communities liegen versioniert in
`docs/graphify-community-labels.json`. Nach Änderungen am Code aktualisiert
`scripts/refresh_graphify.sh` den lokalen Graphen und erzeugt HTML sowie das
automatische Wiki neu. `graphify-out/` bleibt weiterhin lokal und wird nicht
committed.
