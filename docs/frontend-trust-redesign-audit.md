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

Wichtig: Die erste Umsetzungsphase reduziert vor allem visuelles Misstrauen.
Echter Operations-Trust entsteht erst in den nachfolgenden Flow-Phasen durch
bessere Vorschau-, Konflikt-, Retry-, Sync- und Fehlerlogik. Ein ruhigeres
Design darf deshalb nicht als geloestes Sicherheits- oder Verstaendlichkeits-
problem verkauft werden.

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

Fuer Phase 1 gilt: Der Begriff `Sendezentrale` wird noch nicht umbenannt. Die
Terminologie-Frage wird explizit auf den Copy-/Flow-Audit vertagt, damit der
erste Branch nicht zugleich ein Navigations- und Mental-Model-Refactor wird.

## Phase-1-Entscheidungen

Diese Entscheidungen gelten fuer den ersten Umsetzungsbranch, damit ein Worker
nicht zwischen kleinen Produktfragen haengen bleibt:

| Thema | Entscheidung fuer Phase 1 |
| --- | --- |
| Icon-Set | Lucide-Stil als Zielrichtung; bevorzugt inline/static SVGs ohne neuen Build-Schritt. Externe Abhaengigkeiten nur nach separater Freigabe. |
| `Sendezentrale` | Nicht in Phase 1 umbenennen; spaeter im Terminologie-Audit entscheiden. |
| Themes | Default-Theme beruhigen. Bestehende Themes nicht loeschen und keine Settings-Migration ohne eigene Entscheidung. |
| Konsole | Nur optisch beruhigen. Kein Bottom-Drawer-Umbau in Phase 1. |
| Witz/Quote | Aus operativen Flows heraushalten. Die endgueltige Entfernung oder Verschiebung bleibt eine eigene Entscheidung. |
| JavaScript | Phase 1 ist primaer CSS/HTML. JS nur minimal anfassen, wenn Icons, Settings-Tabs oder reine Anzeigezustaende es zwingend brauchen. |

## Scope-Inventar fuer Phase 1

Der erste Worker soll in diesen Bereichen starten und den Scope nicht ohne
Ruecksprache ausweiten:

| Bereich | Primaere Dateien / Anker | Phase-1-Ziel |
| --- | --- | --- |
| Design Tokens | `gui/static/style.css` (`:root`, Theme-Bloecke, `--primary`, `--accent`, `--accent-gradient`, `--accent-glow`, `--bg-card`, `--bg-glass`) | Default-Theme neutralisieren, Statusfarben semantisch halten. |
| Dekorative Effekte | `gui/static/style.css` (`radial-gradient`, `backdrop-filter`, `.card::before`, `.interactive-card`, Hover/Glow-Regeln) und vereinzelte Inline-Styles in `index.html` / `app.js` | Glows, Radialverlaeufe und Light-Cone-Hover aus operativen Bereichen entfernen oder stark reduzieren. |
| Primaer-Navigation | `gui/static/index.html` (`master-btn-home`, `nav-youtube-downloader`, `nav-tools-dashboard`, `nav-dashboard`, `nav-library`, `nav-settings-dashboard`, `nav-queue-dashboard`, `nav-faq`) | Emoji-Icons ersetzen oder entfernen, Textlabels beibehalten. |
| Primaeraktionen | `gui/static/index.html`, dynamische Buttontexte in `gui/static/app.js` | Riskante oder zentrale Buttons von Emoji + vagem Verb auf klare Verb-Objekt-Texte bringen. |
| Settings-Tabs | `gui/static/index.html` (`settings-tabs-nav`, `settings-tab-btn`) und `gui/static/app.js` (`settingsTabButtons`) | Ueberlauf beseitigen, ohne Settings-IA neu zu bauen. |
| Konsole | `gui/static/index.html` (`app-console`, `console-header-toggle`) und `gui/static/app.js` (`applyConsoleVisibility`, `appendConsoleLog`) | Nur visuell weniger dominant machen; kein neues Drawer-Verhalten. |
| Statusanzeigen | `gui/static/style.css` (`.status-badge`, `.status-indicator`, `.dep-card.status-*`) und Queue-Rendering in `gui/static/app.js` | Farben/Labels an Statusmodell angleichen, Farbe nie als alleinigen Statustraeger verwenden. |

Nicht Teil von Phase 1:

- neue Preview-Tabellen
- neuer Queue-Detailmodus
- neuer Sync-Dry-Run
- neuer Confirm-Dialog-Standard
- Umbau der gesamten Informationsarchitektur
- Entfernen bestehender Themes oder Migration gespeicherter Theme-Werte

## Statusmodell

Farbe darf nie der einzige Statustraeger sein. Jeder Status braucht mindestens
Textlabel plus Form/Icon/Symbol. Die genauen Farben werden in den Design Tokens
definiert; diese Tabelle legt die Semantik fest.

| Status | Bedeutung | Visuelle Rolle | Erlaubte Standardaktion |
| --- | --- | --- | --- |
| `queued` | Job ist eingereiht, aber noch nicht gestartet. | neutraler Chip, Uhr/Queue-Symbol, Label "Wartet" | Job ansehen, ggf. abbrechen falls unterstuetzt |
| `running` | Job oder Scan laeuft gerade. | Primaer/Info-Chip, dezente Aktivitaetsanzeige, Label "Laeuft" | Details ansehen, abbrechen falls sicher unterstuetzt |
| `done` | Vorgang ist abgeschlossen ohne bekannte Warnungen. | Success-Chip, Label "Abgeschlossen" | Ergebnis ansehen, Log oeffnen |
| `warning` | Vorgang ist nutzbar, aber mit pruefbeduerftigen Hinweisen. | Warning-Chip, Label "Warnung" | Hinweise pruefen, ggf. trotzdem fortfahren |
| `failed` / `error` | Vorgang ist fehlgeschlagen. | Danger-Chip, Label "Fehlgeschlagen" | Fehlerdetails ansehen, Retry nur bei ausgewiesener Sicherheit |
| `conflict` | Ziel, Zuordnung oder Datei kollidiert mit bestehendem Zustand. | Warning/Danger je Risiko, Label "Konflikt" | Konfliktregel waehlen, nicht automatisch ueberschreiben |
| `skipped` | Element wurde bewusst uebersprungen. | neutraler Muted-Chip, Label "Uebersprungen" | Grund ansehen, bei Bedarf erneut auswaehlen |
| `partial` | Vorgang ist teilweise abgeschlossen. | Warning-Chip, Label "Teilweise abgeschlossen" | Details und Log pruefen, Retry-Sicherheit anzeigen |

Phase 1 muss dieses Modell noch nicht vollstaendig in allen Flows umsetzen,
aber neue oder angepasste Statusanzeigen sollen nicht dagegen arbeiten.

## Risk-Action-Policy

Riskante Aktionen werden nach Folge und Reversibilitaet gestaffelt. Diese
Policy dient als Copy- und Button-Leitplanke.

| Aktion | Risiko | Mindestanforderung an UI/Copy |
| --- | --- | --- |
| Vorschau / Scan / Test | niedrig, keine Dateioperation | Neutraler oder primaerer Button mit Verb + Objekt, z. B. "Scan starten", "Verbindung testen". |
| Speichern von Einstellungen | mittel, veraendert zukuenftiges Verhalten | Button "Einstellungen speichern"; bei sensiblen Settings klare Erfolg-/Fehler-Rueckmeldung. |
| Verschieben / Umbenennen | hoch, veraendert Dateien und Pfade | Vor Ausfuehrung Zusammenfassung mit Anzahl und Ziel; Button nennt konkrete Aktion, z. B. "143 Aenderungen anwenden". |
| Loeschen / Quarantaene | hoch bis kritisch | Quarantaene bevorzugen; Danger-Stil; Folgen klar benennen; keine humorvolle oder dekorative Sprache. |
| Ueberschreiben | kritisch | Nie als stiller Default; Konflikt sichtbar machen; explizite Entscheidung oder Confirm-Modal erforderlich. |
| Retry | variabel | Label muss zeigen, ob Retry sicher ist. Bei Teilabschluss: "Manuelle Pruefung noetig" statt blindem Primaerbutton. |
| Sync zu NAS/Cloud | hoch, externe Ziele und potenziell grosse Datenmengen | Richtung Quelle -> Ziel, Konflikt-/Overwrite-Verhalten und letzter Zustand muessen sichtbar sein. |

Button-Hierarchie:

- Primaer: naechster sicherer Standardschritt.
- Sekundaer: Navigation, Details, Abbrechen, Testen.
- Warning: fortfahren trotz Risiko oder pruefbeduerftiger Zustand.
- Danger: Loeschen, Ueberschreiben, irreversible oder schwer rueckgaengige Aktionen.

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
Sie ist eine visuelle und copy-nahe Beruhigung, kein Flow-Umbau.

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
   - keine neue Drawer-Interaktion in Phase 1
   - Auto-Fokus auf Fehler erst in spaeterer Phase

5. Settings-Tabs reparieren
   - horizontalen Ueberlauf entfernen
   - fuer viele Kategorien besser vertikale Navigation oder scrollbare Tabs
   - Erklaertexte pro Gruppe schaerfen

6. Riskante Buttontexte im sichtbaren Bestand schaerfen
   - Emoji aus zentralen Primaeraktionen entfernen
   - Buttons mit Verb + Objekt benennen
   - Loeschen/Ueberschreiben nicht wie normale Primaeraktionen stylen

## Akzeptanzkriterien fuer Review

Ein erster Design-Pass gilt nur dann als reviewbar, wenn:

- alle Primaer-Navigations-Emojis ersetzt oder entfernt sind
- Default-Theme nicht mehr von Pink/Violett-Glow dominiert wird und matte,
  opake Flaechen als Grundsprache nutzt
- Statusfarben semantisch erkennbar sind und Status nie nur ueber Farbe
  kommuniziert wird
- keine Hauptfunktion durch rein dekorative Hovereffekte schlechter lesbar wird
- Settings-Tabs auf Desktop nicht abgeschnitten wirken
- riskante Primaerbuttons klarer benannt sind oder mit konkreter Folgeaufgabe
  im Abschluss dokumentiert bleiben
- die Konsole optisch beruhigt ist, ohne neues Drawer-Verhalten einzufuehren
- Baseline- und Nachher-Screenshots von Dashboard, Einstellungen,
  Vorschau/Queue und Bibliothek vorliegen
- mindestens je ein Nachher-Screenshot oder reproduzierbarer Zustand fuer
  Normalzustand, Warning, Failed/Error, Conflict und Partial/Skipped vorliegt,
  sofern diese Zustaende lokal erreichbar sind
- mindestens `npm run test:frontend` und ein statischer Check der betroffenen
  JS-Dateien gelaufen sind, falls JavaScript geaendert wurde
- Kontrast und Touch-/Klickziele in den geaenderten Bereichen grob gegen
  WCAG-AA-Erwartungen geprueft wurden

## Vertagte Entscheidungen

Diese Fragen sind wichtig, aber nicht Teil des ersten Reskin-Branches:

1. Wird `Sendezentrale` dauerhaft als Markenbegriff behalten oder ersetzt?
2. Braucht die App langfristig mehrere Themes oder ein einziges ausgereiftes
   Default-Theme plus optionalen Light/Dark-Modus?
3. Wird die Konsole spaeter als Bottom Drawer, dedizierter Logbereich oder
   Job-Detailansicht umgesetzt?
4. Wird "Witz des Tages" komplett entfernt, nur in einen nicht-operativen
   Bereich verschoben oder als optionale Einstellung beibehalten?
5. Welche Vorschau- und Queue-Komponenten werden in Phase 2 zuerst
   produktionstauglich gemacht?

## Empfohlene Reihenfolge

1. Trust-first Reskin vorbereiten und in Screenshots pruefen.
2. Copy-/Terminologie-Audit fuer Navigation und riskante Buttons.
3. Vorschau- und Queue-Flows als naechste Trust-Komponenten ueberarbeiten.
4. Erst danach groessere Informationsarchitektur-Entscheidungen treffen.
