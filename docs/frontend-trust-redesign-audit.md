# Frontend Trust Redesign Audit

## Ziel

Das Medienwerkzeug soll erwachsener, ruhiger und vertrauenswuerdiger wirken.
Der Schwerpunkt liegt nicht auf einem dekorativen Redesign, sondern auf einem
Trust-Redesign: Nutzer sollen vor jeder riskanten Dateiaktion verstehen, was
passiert, was bereits passiert ist, was fehlschlug und was sicher wiederholt
werden kann.

Medienwerkzeug ist eine Vorbereitungs- und Ordnungszentrale vor Plex,
Jellyfin oder Emby. Die Oberflaeche muss daher eher wie ein Datei-, Sync- und
Wartungswerkzeug wirken als wie ein spielerisches Dashboard.

## Scope dieser Planungsphase

Diese Datei beschreibt den Audit- und Umsetzungsrahmen fuer den ersten
Frontend-Design-Pass.

Enthalten:

- visuelle Probleme und Zielrichtung
- Priorisierung der wichtigsten UX-Flows
- Copy- und Terminologie-Regeln
- erste umsetzbare Phase ohne komplette Neuentwicklung
- Akzeptanzkriterien fuer Review und Umsetzung

Nicht enthalten:

- direkte UI-Implementierung
- neues Framework
- vollstaendige Informationsarchitektur
- Aenderungen an Backend-Verhalten oder Dateioperationen

## Leitprinzipien

1. **Boring trust vor wow UI.**
   Dateioperationen brauchen Vorhersagbarkeit, nicht Effektstaerke.

2. **Farbe ist Status, nicht Dekoration.**
   Akzentfarben markieren Primaeraktion, Erfolg, Warnung oder Gefahr.

3. **Jede riskante Aktion braucht Konsequenzklarheit.**
   Buttons sollen sagen, was sie tun: "Vorschau erstellen",
   "143 Aenderungen anwenden", "3 Duplikate in Quarantaene verschieben".

4. **Technische Begriffe werden uebersetzt.**
   Begriffe wie `nas_root`, `rclone`, Outbox oder Manifest duerfen vorkommen,
   brauchen aber eine kurze nutzerorientierte Erklaerung an der Stelle, an der
   sie entscheidungsrelevant sind.

5. **Dekoration darf Status nicht uebertoenen.**
   Glows, Glas, Parallax, Radialverlaeufe und Emoji-Icons muessen zuruecktreten,
   sobald Nutzer Pfade, Konflikte, Risiken oder Fehler lesen sollen.

## Sichtbare Problemfelder

### Visuelle Sprache

Aktuell wirkt die Default-Oberflaeche stark nach generischem KI-Dashboard:

- dunkles Glassmorphism
- Pink/Violett-Gradienten
- Glow- und Light-Cone-Effekte
- grosse, dekorative Cards
- viele Emoji-Icons in Navigation, Buttons und Ueberschriften
- spielerische Elemente wie Witz/Quote in einem operativen Werkzeug

Zielrichtung:

- matte, opake Flaechen
- reduzierte Schatten
- 1px-Borders statt Glasrahmen
- kleinere Radien
- ein konsistentes Icon-Set statt Emojis
- klare Status-Chips fuer `queued`, `running`, `done`, `warning`,
  `failed`, `conflict`, `skipped`
- Pfade und Logs in Monospace

### Informationsdichte

Viele Bereiche sind card-lastig. Fuer Dateioperationen braucht die App mehr
scanbare Listen, Tabellen, Zusammenfassungen und Detailbereiche.

Beispiele:

- Rename-/Move-Vorschau als Vorher/Nachher-Tabelle
- Queue-Jobs als kompakte Zeilen mit expandierbaren Details
- Health- und Duplikatbefunde mit Grund, Risiko und empfohlener Aktion
- Sync-Ziele mit Richtung, letztem Erfolg, Schreibtest und Konfliktpolitik

### Terminologie

Die App mischt derzeit Metaphern, technische Begriffe und Produktmarketing.
Das erschwert Vertrauen.

Zu pruefen:

| Aktueller Begriff | Problem | Moegliche Richtung |
| --- | --- | --- |
| Sendezentrale | metaphorisch, nicht eindeutig | Import & Vorschau, Transferzentrale, Arbeitsbereich |
| Werkzeuge | sehr allgemein | Wartung, Batch-Aktionen |
| Bibliothek | kann mit Plex/Jellyfin-Bibliothek kollidieren | Bibliothekspruefung, NAS-Wartung |
| Outbox | erklaerungsbeduerftig | Outbox beibehalten, aber als lokaler Zwischenordner erklaeren |
| nas_root | technisch | NAS-Stammverzeichnis (`nas_root`) |
| rclone Remote | technisch | rclone-Remote mit Ein-Satz-Erklaerung |

Die finalen Begriffe sollen erst nach dem Flow-Audit festgelegt werden, damit
keine bestehende Nutzerlogik versehentlich verschleiert wird.

## Priorisierte Audit-Flows

### 1. Erstkonfiguration

Fragen:

- Versteht der Nutzer den Unterschied zwischen Quelle, Inbox, Outbox,
  NAS-Ziel und Cloud-Ziel?
- Sind Docker-Pfade und Host-Pfade eindeutig erklaert?
- Sind Lese-/Schreibrechte sichtbar pruefbar?
- Ist klar, welche Werte optional sind?
- Gibt es eine sichtbare Rueckmeldung fuer ungespeicherte Aenderungen?

Erwartete Verbesserungen:

- klare Gruppen: Quellen, Arbeitsordner, Ziele & Sync, System, Sicherheit
- Test-Buttons fuer Verbindung, Lesen, Schreiben
- kurze Erklaerung technischer Felder direkt im Kontext
- keine horizontal abgeschnittenen Settings-Tabs

### 2. Import / Metadaten / Vorschau / Ausfuehrung

Fragen:

- Sieht der Nutzer, welche Dateien erkannt wurden?
- Ist sichtbar, welcher Metadatentreffer warum gewaehlt wurde?
- Sind niedrige Treffer-Sicherheiten markiert?
- Kann der Nutzer einzelne Dateien ausschliessen?
- Ist vor der Ausfuehrung klar, welche Dateien verschoben, umbenannt,
  geloescht, uebersprungen oder kopiert werden?

Erwartete Verbesserungen:

- Vorher/Nachher-Tabelle fuer Pfade
- Zusammenfassung: Anzahl Moves, Renames, Kopien, Loeschungen, Konflikte
- Filter: alle, geaendert, Konflikte, niedrige Sicherheit, Fehler
- finales Bestaetigungsmodal mit konkreten Zahlen

### 3. Queue / Fehler / Retry

Fragen:

- Ist klar, ob ein Job nichts, alles oder nur teilweise erledigt hat?
- Ist sichtbar, ob ein Retry sicher ist?
- Sind Fehler handlungsorientiert beschrieben?
- Kann der Nutzer Logdetails sehen, ohne die Hauptansicht zu verlieren?

Erwartete Verbesserungen:

- Status-Chips statt nur farbiger Hervorhebung
- expandierbare Jobdetails
- Logauszug pro Job
- Anzeige: "Sicher wiederholbar", "Manuelle Pruefung noetig",
  "Teilweise abgeschlossen"

### 4. NAS / pCloud / rclone Sync

Fragen:

- Ist die Sync-Richtung eindeutig?
- Ist klar, ob ueberschrieben oder geloescht wird?
- Gibt es eine Simulation / Dry-Run-Moeglichkeit?
- Sind letzter Erfolg, freier Speicher und Schreibzugriff sichtbar?

Erwartete Verbesserungen:

- Richtung: Quelle -> Ziel
- Konfliktpolitik: ueberspringen, behalten, automatisch umbenennen,
  ueberschreiben, abbrechen
- Verbindungstest und Schreibtest
- letzter erfolgreicher Sync-Zeitpunkt

### 5. Health Scan / Duplikate / Wartung

Fragen:

- Ist sichtbar, warum ein Befund gemeldet wurde?
- Sind Schweregrad und Risiko klar?
- Ist die empfohlene Aktion reversibel?
- Wird Quarantaene bevorzugt statt endgueltigem Loeschen?

Erwartete Verbesserungen:

- Befundgrund: Dateiname, Metadaten, Groesse, Dauer, ffprobe, NFO, Artwork
- Schweregrad: Hinweis, Warnung, kritisch
- Aktion mit Verb + Objekt
- vor Anwendung Zusammenfassung der Folgen

## Copy-Regeln

### Buttons

Buttons sollen Verb + Objekt nennen.

| Vermeiden | Besser |
| --- | --- |
| Start | Scan starten |
| Fix | Befund beheben |
| Senden | Zu NAS synchronisieren |
| Speichern | Einstellungen speichern |
| Ausfuehren | 143 Aenderungen anwenden |

### Warnungen

Warnungen sollen Ursache, Folge und naechsten Schritt nennen.

Muster:

> Zielpfad existiert bereits. Diese Datei wuerde nicht ueberschrieben, sondern
> uebersprungen. Pruefe den Konflikt oder waehle eine andere Konfliktregel.

### Technische Begriffe

Technische Begriffe sollen beim ersten Auftreten kurz aufgeloest werden.

Beispiele:

- `NAS-Stammverzeichnis (nas_root)`: Basisordner auf dem NAS, in den
  Medienwerkzeug fertige Medien schreibt.
- `rclone-Remote`: benannte rclone-Verbindung fuer Cloud- oder NAS-Sync,
  z. B. `pcloud:`.
- `Outbox`: lokaler Zwischenordner fuer fertig vorbereitete Dateien, bevor
  sie auf Speicherziele kopiert werden.

## Erste Umsetzungsphase: Trust-first Reskin

Diese Phase ist bewusst begrenzt und soll ohne Frameworkwechsel machbar sein.

### Aufgaben

1. Design Tokens beruhigen
   - Default-Theme auf neutrale, matte Flaechen umstellen
   - Pink/Violett-Gradienten als Default entfernen
   - Statusfarben semantisch definieren
   - Radius und Schatten reduzieren

2. Dekorative Effekte reduzieren
   - Radial-Hintergruende entfernen oder stark abdunkeln
   - Glow- und Light-Cone-Hover deaktivieren
   - Parallax-/3D-Effekte aus operativen Cards entfernen

3. Emojis aus Primaer-Navigation und Hauptaktionen entfernen
   - konsistentes Icon-Set vorbereiten
   - Texte beibehalten, Icons nur ergaenzend nutzen
   - besonders riskante Aktionen nicht ueber Icons allein kommunizieren

4. Konsole beruhigen
   - dauerhaft sichtbare Konsole weniger dominant machen
   - Zielbild: Bottom Drawer mit Statusindikator
   - Auto-Fokus auf Fehler erst in spaeterer Phase

5. Settings-Tabs reparieren
   - horizontalen Ueberlauf entfernen
   - fuer viele Kategorien besser vertikale Navigation oder scrollbare Tabs
   - Erklaertexte pro Gruppe schaerfen

## Akzeptanzkriterien fuer Review

Ein erster Design-Pass gilt nur dann als reviewbar, wenn:

- alle Primaer-Navigations-Emojis ersetzt oder entfernt sind
- Default-Theme nicht mehr von Pink/Violett-Glow dominiert wird
- Statusfarben semantisch erkennbar sind
- keine Hauptfunktion durch rein dekorative Hovereffekte schlechter lesbar wird
- Settings-Tabs auf Desktop nicht abgeschnitten wirken
- riskante Primaerbuttons klarer benannt sind oder als offene Folgeaufgabe
  dokumentiert bleiben
- Screenshots von Dashboard, Einstellungen, Vorschau/Queue und Bibliothek
  vorliegen
- mindestens `npm run test:frontend` und ein statischer Check der betroffenen
  JS-Dateien gelaufen sind, falls JavaScript geaendert wurde

## Offene Entscheidungen vor Code

1. Soll `Sendezentrale` als Markenbegriff bleiben oder durch einen wörtlicheren
   Arbeitsbereich ersetzt werden?
2. Welches Icon-Set wird verwendet: Lucide, Tabler, Heroicons oder Inline-SVGs?
3. Soll der erste Pass nur das Default-Theme aendern oder alle Themes
   konsolidieren?
4. Wird die Konsole im ersten Pass nur optisch reduziert oder schon als Drawer
   umgesetzt?
5. Soll "Witz des Tages" aus operativen Flows entfernt, in Darstellung
   versteckt oder komplett ausgebaut werden?

## Empfohlene Reihenfolge

1. Trust-first Reskin vorbereiten und in Screenshots pruefen.
2. Copy-/Terminologie-Audit fuer Navigation und riskante Buttons.
3. Vorschau- und Queue-Flows als naechste Trust-Komponenten ueberarbeiten.
4. Erst danach groessere Informationsarchitektur-Entscheidungen treffen.
