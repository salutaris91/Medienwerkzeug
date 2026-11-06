# Beitrag des Grafikers: Film-Assistent Wizard (4 Schritte)

**Rolle:** Grafiker (UI/UX) im Kreativteam · 2026-11-06

> Archivierungsvermerk (Orchestrator, 2026-11-06): Die Rohübermittlung enthielt denselben Beitrag zweimal — vorangestellt ein abgeschnittener Block (abriss in Abschnitt 4), danach der vollständige Durchlauf. Archiviert wird der vollständige Durchlauf inhaltlich unverändert; der Doppelblock war ein Übermittlungsartefakt ohne eigenen Inhalt. Keine redaktionellen Änderungen am Text.

**Referenz:** `docs/designsprache.md` existiert nicht im Arbeitsverzeichnis → Bearbeitung ohne Grundgesetz, basierend auf verifiziertem Design-System (style.css, utilities.css, index.html).

---

## 1. Schritt-Layout: Modal-Rahmen und Fortschrittskopf

### ASCII-Skizze des Wizard-Modals

```
┌─────────────────────────────────────────────────────────────────────┐
│  ╔═══════════════════════════════════════════════════════════════╗   │
│  ║  Film 2 von 5: Der Pate                            [× Schließen] ║
│  ║  ─────────────────────────────────────────────────────────── ║   │
│  ║                                                               ║   │
│  ║  ●─────●─────○─────○   ← Fortschrittsbahn (4 Schritte)       ║   │
│  ║  1     2     3     4                                         ║   │
│  ║  Quelle  Meta  Bild  Ergebnis                                ║   │
│  ║                                                               ║   │
│  ║  ┌─────────────────────────────────────────────────────────┐ ║   │
│  ║  │                                                         │ ║   │
│  ║  │  [AKTUELLER SCHRITT-INHALT]                             │ ║   │
│  ║  │  - Max. 1 Viewport-Höhe, kein Scroll im Idealfall       │ ║   │
│  ║  │  - Overflow-y: auto nur als Notausgang                  │ ║   │
│  ║  │  - Padding: 24px (konsistent mit .mw-modal)             │ ║   │
│  ║  │                                                         │ ║   │
│  ║  │                                                         │ ║   │
│  ║  └─────────────────────────────────────────────────────────┘ ║   │
│  ║                                                               ║   │
│  ║  [← Zurück]                      [Weiter →] [Überspringen]  ║   │
│  ╚═══════════════════════════════════════════════════════════════╝   │
└─────────────────────────────────────────────────────────────────────┘
```

### Dimensionsbudget

- **Modal-Breite:** `max-width: 960px` (zwischen NFO-Agent 900px und Onboarding 620px; genug Raum für Artwork-Raster in Schritt 3)
- **Modal-Höhe:** `max-height: 90vh`, Content-Bereich `flex: 1` mit `overflow-y: auto`
- **Schritt-Inhalt:** Ziel = 1 Viewport ohne Scroll; bei 1080p-Bildschirm ≈ 600–700px Content-Höhe verfügbar
- **Zeilenschema:** Header (Fortschrittskopf) 80px, Content flexibel, Footer (Navigation) 64px → bei 90vh = 972px bleiben 828px für Content

### Fortschrittskopf: Empfehlung „Punkte mit Beschriftung"

**Entscheidung:** Punkt-Indikator mit Zahlen + kurze Labels darunter, **nicht** Fortschrittsbalken, **nicht** reiner Text „Schritt 2 von 4".

**Begründung:**
- **Präzedenz Emby Setup-Wizard:** Nutzt nummerierte Punkte mit Labels („Welcome → Library → Users → Finish") — etabliertes Pattern für Medien-Tools, Alex kennt es.
- **Präzedenz Stripe Checkout:** Mehrstufige Formulare mit Punkt-Indikator + Labels, weil es Orientierung gibt („Wo bin ich?") und Kontext („Was kommt noch?") ohne kognitiven Overhead.
- **Trade-off:** Fortschrittsbalken wäre kompakter, aber bei nur 4 Schritten zu grob (25%-Sprünge). Reiner Text „Schritt 2 von 4" spart Platz, gibt aber kein visuelles Fortschrittsgefühl.

**Umsetzung:** Bestehende `.step-dot`-Klasse aus Onboarding (style.css:2753) wiederverwenden, aber mit Labels erweitern. Aktiver Punkt: `var(--accent)` + Glow, abgeschlossene: `var(--success)`, zukünftige: `var(--border-glass)`.

### „Film X von N"-Ebene (ROADMAP #69)

**Platzierung:** Direkt über dem Schritt-Indikator, linksbündig, eigene Hierarchie-Ebene.

**Design:**
- **Typografie:** `font-size: 0.85em`, `font-weight: 600`, `color: var(--text-main)`
- **Icon:** Film-Clapper (Lucide `film`) links, `color: var(--accent)`
- **Separator:** 1px `border-bottom: var(--border-light)` darunter, 12px Margin zum Schritt-Indikator

**Begründung:** Serien-Ebene darf nicht mit 4 Schritten konkurrieren — ist Kontext, nicht Navigation. Deshalb visuell untergeordnet (kleiner, keine Affordanz), aber klar lesbar. Emby zeigt bei Multi-Selection ebenfalls „X von Y" als Kontext-Badge, ohne es in die Schritt-Navigation zu integrieren.

### Neue CSS-Klassen (Schritt 1)

```
.mw-wizard-overlay          — Overlay (Wiederverwendung .mw-modal-overlay Pattern)
.mw-wizard                  — Modal-Container (max-width 960px, Flex-Spalte)
.mw-wizard-header           — Fixer Kopfbereich (Film X von N + Schritt-Indikator)
.mw-wizard-series-context   — „Film X von N"-Zeile
.mw-wizard-steps            — Punkt-Indikator-Container (Flex, Gap 24px)
.mw-wizard-step             — Einzelner Punkt (Kreis + Label)
.mw-wizard-step.active      — Aktueller Schritt
.mw-wizard-step.completed   — Abgeschlossener Schritt
.mw-wizard-step-line        — Verbindungslinie zwischen Punkten
.mw-wizard-content          — Scrollbarer Hauptbereich (flex: 1, overflow-y: auto)
.mw-wizard-footer           — Fixer Fußbereich (Navigation-Buttons)
```

**Aufwand:** **Klein** — bestehende Modal-Struktur wird erweitert, Schritt-Indikator ist Adaption des Onboarding-Patterns.

---

## 2. Schritt 2: Metadaten-Vergleich mit Provider-Badges

### Layout-Konzept: Kompakt-Karten statt Tabelle

**Problem:** Tabelle mit 5 Spalten (Feld | TMDb | TVDB | OMDB | Aktuell) würde bei 6 Feldern (Titel, Jahr, Plot, FSK, Genre, Originaltitel) zu breit und unleserlich.

**Lösung:** Vertikale Feld-Karten, jede Karte zeigt das Feld + alle Provider-Badges horizontal.

### ASCII-Skizze einer Feld-Karte

```
┌─────────────────────────────────────────────────────────────┐
│  Titel                                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │ TMDb     │  │ TVDB     │  │ OMDB     │                  │
│  │ Der Pate │  │ Der Pate │  │ The God- │                  │
│  │     ✓    │  │          │  │  father  │                  │
│  └──────────┘  └──────────┘  └──────────┘                  │
│  [Übernehmen: TMDb]                                         │
└─────────────────────────────────────────────────────────────┘
```

### Provider-Badge-Design

**Größe:** 120px breit × 60px hoch, `border-radius: var(--radius-md)`

**Zustände:**
- **Mit Wert:** `background: var(--bg-surface)`, `border: 1px solid var(--border-light)`, Wert in `var(--text-main)`, Provider-Name in `var(--text-muted)` (klein, oben links)
- **Ohne Wert:** `background: var(--bg-base)`, `border: 1px dashed var(--border-glass)`, Text „TMDb: keine Daten" in `var(--text-muted)`
- **Ausgewählt (Feld wird aus dieser Quelle übernommen):** `border: 2px solid var(--accent)`, `box-shadow: 0 0 12px var(--accent-glow)`, kleiner Haken-Icon (Lucide `check`) oben rechts

**Klick-Interaktion:** Klick auf Badge = Feld aus dieser Quelle übernehmen. Badge wird visuell aktiviert (siehe „Ausgewählt"). Mehrere Badges pro Feld möglich (z. B. Titel aus TMDb, Jahr aus OMDB).

**Farben über Variablen:**
- Badge-Hintergrund: `var(--bg-surface)` (dunkle Themes) bzw. `var(--bg-card)` (superfood-light)
- Badge-Border: `var(--border-light)`
- Badge-Text: `var(--text-main)` für Wert, `var(--text-muted)` für Provider-Label
- Auswahl-Hervorhebung: `var(--accent)` + `var(--accent-glow)`

**Kontrast-Check superfood-light:** `var(--bg-surface)` ist `#f4e6da` (hell), `var(--text-main)` ist `1b3456` (dunkelblau) → Kontrast 9.2:1, WCAG AAA bestanden.

### Kompakt-Layout für 5 Felder + Plot

**Anordnung:** 2-Spalten-Grid für kompakte Felder (Titel, Jahr, FSK, Genre, Originaltitel), Plot als volle Breite darunter.

```
┌──────────────────────┬──────────────────────┐
│  Titel               │  Jahr                │
│  [Badges...]         │  [Badges...]         │
├──────────────────────┼──────────────────────┤
│  FSK                 │  Genre               │
│  [Badges...]         │  [Badges...]         │
├──────────────────────┴──────────────────────┤
│  Originaltitel                              │
│  [Badges...]                                │
├─────────────────────────────────────────────┤
│  Plot (Zusammenfassung)                     │
│  ┌─────────────────────────────────────────┐│
│  │ TMDb: Ein Mafiaboss...                  ││
│  │ TVDB: Die Geschichte...                 ││
│  └─────────────────────────────────────────┘│
│  (max. 3 Zeilen, Rest scrollbar oder „...") │
└─────────────────────────────────────────────┘
```

**Plot-Sonderbehandlung:** Plot ist lang → Textarea-ähnliche Darstellung, max. 3 Zeilen sichtbar, Rest via `overflow-y: auto` scrollbar. Badge-Klick = kompletter Plot aus dieser Quelle übernehmen.

### Neue CSS-Klassen (Schritt 2)

```
.mw-wizard-metadata         — Container für Feld-Karten (Grid, 2 Spalten)
.mw-wizard-field            — Einzelne Feld-Karte
.mw-wizard-field-label      — Feld-Name (z. B. „Titel")
.mw-wizard-field-badges     — Badge-Container (Flex, wrap)
.mw-wizard-provider-badge   — Einzelne Provider-Badge
.mw-wizard-provider-badge.selected — Aktive Auswahl
.mw-wizard-provider-badge.empty    — Keine Daten verfügbar
.mw-wizard-provider-name    — Provider-Label (klein, oben)
.mw-wizard-provider-value   — Wert (haupt, unten)
.mw-wizard-plot-field       — Plot-Sektion (volle Breite, Textarea-Style)
```

**Aufwand:** **Mittel** — neues Karten-Layout, aber keine komplexen Interaktionen. Badge-Zustände sind überschaubar.

---

## 3. Schritt 3: Artwork-Auswahl (Poster + Fanart)

### Raster-Layout: Emby-ähnliche Kacheln

**Präzedenzfall Emby/Jellyfin:** Beide zeigen Poster in responsivem Grid mit 2:3-Aspect-Ratio, Auswahl-Indikator als Ring oder Haken-Overlay. Plex nutzt ähnliche Kacheln mit subtiler Hover-Animation.

**Übernommen:**
- Poster-Größe: 185px breit × 278px hoch (TMDb `w185`-Variante), Hover-Effekt mit `transform: translateY(-2px)`
- Auswahl-Ring: 3px `border: var(--accent)` + `box-shadow: 0 0 16px var(--accent-glow)`
- Haken-Overlay: Lucide `check`-Icon, weiß, unten rechts, `background: var(--accent)`, `border-radius: 50%`

**Bewusst ignoriert:**
- Emby's kontextuelle Menüs (Rechtsklick auf Poster) — für Ein-Nutzer-Tool zu komplex, Auswahl per Klick reicht.
- Plex's automatische Vorauswahl — Alex will explizite Kontrolle (ROADMAP #51).

### Poster-Raster (2D vs. 3D)

**Empfehlung:** 2D-Poster (flach), **kein** 3D-Effekt mit Schatten/Perspektive.

**Begründung:**
- 3D-Poster (mit Perspektive) wirken zwar dynamisch, aber sie verfälschen das Artwork und machen Details schlechter erkennbar.
- Emby/Jellyfin zeigen Poster standardmäßig 2D, 3D nur als optionale Ansicht.
- 2D ist schneller zu rendern (kein CSS-Transform-Overhead) und theme-neutral.

**Grid-Spec:**
- `display: grid`, `grid-template-columns: repeat(auto-fill, minmax(185px, 1fr))`
- `gap: 16px`
- Max. 4 Spalten bei 960px Modal-Breite (4 × 185px + 3 × 16px = 788px, passt)

### Fanart-Raster

**Größe:** 300px breit × 169px hoch (16:9, TMDb `w300`-Variante)

**Grid:** `grid-template-columns: repeat(auto-fill, minmax(300px, 1fr))`, max. 2 Spalten bei 960px

**Layout-Wechsel:** Tab- oder Toggle-Switch zwischen „Poster" und „Fanart" oberhalb des Rasters, um vertikalen Platz zu sparen. Nicht beide Raster gleichzeitig anzeigen (würde zu lang werden).

### Zustände und Ladeindikatoren

**Zustände:**
1. **Lädt:** Skeleton-Loader (graue Box mit `animation: pulse 1.5s infinite`), Aspect-Ratio beibehalten
2. **Geladen:** Bild mit `object-fit: cover`, `border-radius: var(--radius-md)`
3. **Ausgewählt:** Siehe Auswahl-Ring oben
4. **Kein Artwork gefunden:** Placeholder-Kachel mit Lucide `image-off`-Icon, Text „Kein Poster verfügbar", `background: var(--bg-base)`, `border: 1px dashed var(--border-glass)`
5. **Abwahl:** Klick auf ausgewähltes Poster = Auswahl aufheben. Ring verschwindet, Haken-Overlay verschwindet.

### Theme-Kontrast (alle 5 Themes)

**Kritische Themes:**
- **superfood-light:** `var(--bg-surface)` ist `#f4e6da` (hell), Poster-Border `var(--border-light)` ist `rgba(27, 52, 86, 0.12)` → subtil, aber sichtbar. Auswahl-Ring `var(--accent)` ist `#f08aa0` (pink) → hoher Kontrast, gut sichtbar.
- **amber-warmth:** `var(--bg-surface)` ist `#1f1410` (dunkelbraun), `var(--accent)` ist `#d97706` (amber) → Auswahl-Ring leuchtet, gut sichtbar. Skeleton-Loader `var(--bg-base)` ist `#120c0a` → ausreichend Kontrast zu `var(--bg-surface)`.

**Prüfliste als Akzeptanzkriterium:**
- [ ] Alle 5 Themes visuell getestet (Poster-Raster mit 4+ Kacheln)
- [ ] Auswahl-Ring in allen Themes mindestens 3:1 Kontrast zu Hintergrund
- [ ] Skeleton-Loader in allen Themes sichtbar (nicht unsichtbar)
- [ ] Placeholder-Kachel („Kein Artwork") in allen Themes erkennbar
- [ ] Haken-Overlay (weiß) auf allen Themes lesbar (ggf. Schatten hinzufügen)

### Neue CSS-Klassen (Schritt 3)

```
.mw-wizard-artwork          — Container (Tab-Toggle + Raster)
.mw-wizard-artwork-tabs     — Tab-Switcher (Poster | Fanart)
.mw-wizard-artwork-tab      — Einzelner Tab
.mw-wizard-artwork-tab.active — Aktiver Tab
.mw-wizard-artwork-grid     — Raster-Container (Grid)
.mw-wizard-artwork-tile     — Einzelne Kachel (Poster oder Fanart)
.mw-wizard-artwork-tile.selected — Ausgewählt (Ring + Haken)
.mw-wizard-artwork-tile.loading  — Ladezustand (Skeleton)
.mw-wizard-artwork-tile.empty    — Kein Artwork (Placeholder)
.mw-wizard-artwork-image    — <img>-Element (object-fit: cover)
.mw-wizard-artwork-check    — Haken-Overlay (Position: absolute, bottom-right)
.mw-wizard-artwork-skeleton — Skeleton-Loader (Pulse-Animation)
```

**Aufwand:** **Mittel** — Raster-Layout ist Standard, aber Ladezustände und Theme-Tests benötigen Zeit.

---

## 4. Schritt 4: Ergebnis-Zusammenfassung (kompakt statt Listenwand)

### Problem der heutigen Checkbox-Listen

Aktuell werden Renames, Untertitel, Junk-Dateien etc. als lange Checkbox-Listen dargestellt → visuell überwältigend, keine Hierarchie, Nutzer verliert den Überblick.

### Lösung: Zusammenklappbare Gruppen mit Zählern

**Präzedenzfall macOS Finder „Informationen":** Zeigt Datei-Eigenschaften als zusammenklappbare Sektionen (Allgemein, Name & Erweiterung, Kommentare). Reduziert Komplexität, ohne Info zu verstecken.

**Präzedenzfall Notion Database-Views:** Gruppiert Eigenschaften nach Kategorien, jede Gruppe mit Zähler („3 Felder geändert"). Kompakt, aber vollständig.

### ASCII-Skizze der Ergebnis-Zusammenfassung

```
┌─────────────────────────────────────────────────────────────┐
│  ┌───────────────────────────────────────────────────────┐  │
│  │  📁 Zielpfad: /NAS/Filme/Der Pate (1972)             │  │
│  │  🎬 Der Pate (1972)                                   │  │
│  │  [Poster-Vorschau 80×120]                             │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Umbenennungen (3)                              [▼]   │  │
│  │  ├─ film.mkv → Der Pate (1972).mkv                   │  │
│  │  ├─ subtitle.srt → Der Pate (1972).de.srt            │  │
│  │  └─ cover.jpg → folder.jpg                           │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Untertitel (2)                                 [▼]   │  │
│  │  ├─ Deutsch (SRT)                                     │  │
│  │  └─ Englisch (SRT)                                    │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Junk-Dateien (5)                               [▼]   │  │
│  │  ├─ thumbs.db, desktop.ini, ...                       │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Qualität & Conversion                          [▼]   │  │
│  │  ├─ H.265: Ja (bereits konvertiert)                  │  │
│  │  └─ Qualität: 1080p → 1080p (keine Änderung)         │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Design-Details

**Kernbotschaft oben:**
- Zielpfad, Filmtitel, Poster-Vorschau (80×120px) in einer Karte mit `background: var(--bg-surface)`, `border: 1px solid var(--border-light)`, `padding: 16px`
- Poster rechts oder links (Flex-Layout), Titel `font-size: 1.1em`, `font-weight: 600`

**Zusammenklappbare Gruppen:**
- **Header:** Gruppen-Name + Zähler in Klammern (z. B. „Umbenennungen (3)"), Chevron-Icon rechts (Lucide `chevron-down` / `chevron-right`)
- **Zustand geschlossen:** Nur Header sichtbar, `background: var(--bg-surface)`, `border: 1px solid var(--border-light)`, `padding: 12px 16px`
- **Zustand offen:** Header + Liste darunter, `border-radius: var(--radius-md)`, `margin-bottom: 12px`
- **Liste:** Max. 5 Einträge sichtbar, Rest scrollbar (`max-height: 200px`, `overflow-y: auto`)

**Standard-Zustand:**
- Gruppen mit ≤3 Einträgen: standardmäßig offen
- Gruppen mit >3 Einträgen: standardmäßig geschlossen (verhindert Listenwand)

**Interaktion:** Klick auf Header = Gruppe ein/ausklappen. Animation: `max-height` + `opacity` über 200ms (CSS-Transition).

### Neue CSS-Klassen (Schritt 4)

```
.mw-wizard-result           — Container für Ergebnis-Zusammenfassung
.mw-wizard-result-summary   — Kernbotschaft-Karte (Zielpfad, Titel, Poster)
.mw-wizard-result-poster    — Poster-Vorschau (80×120px)
.mw-wizard-result-group     — Zusammenklappbare Gruppe
.mw-wizard-result-group-header — Gruppen-Header (Name + Zähler + Chevron)
.mw-wizard-result-group-header.collapsed — Geschlossener Zustand
.mw-wizard-result-group-content — Gruppen-Inhalt (Liste)
.mw-wizard-result-item      — Einzelner Listeneintrag
.mw-wizard-result-chevron   — Chevron-Icon (Rotation bei Toggle)
```

**Aufwand:** **Mittel** — Collapse-Logik ist Standard, aber viele Gruppen + Listen erfordern sorgfältige Struktur.

---

## 5. Navigation und Zustände

### Zurück/Weiter-Logik

**Standard-Navigation:**
- **Schritt 1 → 2:** „Weiter"-Button aktiv, wenn Quelle gewählt (Suche abgeschlossen oder ID eingegeben)
- **Schritt 2 → 3:** „Weiter"-Button aktiv, wenn mindestens 1 Feld übernommen (nicht alle Badges leer)
- **Schritt 3 → 4:** „Weiter"-Button **immer aktiv** (Artwork optional, ROADMAP #51)
- **Schritt 4:** „Bestätigen"-Button statt „Weiter" (finaler Schritt)

**„Überspringen"-Button:**
- Nur in Schritt 2 und 3 sichtbar (Schritt 1 und 4 sind Pflicht)
- Position: rechts neben „Weiter"-Button, `btn-secondary`-Style
- Klick = aktueller Schritt wird übersprungen, Standard-Werte werden übernommen (Schritt 2: alle Felder aus TMDb, Schritt 3: erstes Poster)
- **Visueller Hinweis:** Tooltip bei Hover: „Überspringen verwendet Standard-Werte"

**„Zurück"-Button:**
- In Schritt 2, 3, 4 sichtbar (nicht in Schritt 1)
- Position: links, `btn-secondary`-Style
- Klick = vorheriger Schritt, alle Eingaben bleiben erhalten

### Fokus-Management

**Bei Schritt-Wechsel:**
- Fokus automatisch auf erstes interaktives Element des neuen Schritts (Schritt 1: Suchfeld, Schritt 2: erste Badge-Gruppe, Schritt 3: erste Poster-Kachel, Schritt 4: „Bestätigen"-Button)
- `element.focus()` nach Render-Completion (JavaScript)

**Bei Modal-Öffnung:**
- Fokus auf Suchfeld (Schritt 1)
- Tab-Navigation zyklisch innerhalb des Modals (Trap Focus, siehe bestehendes Onboarding-Pattern)

### Verhalten bei Abbruch mitten im Wizard

**Szenario:** Nutzer schließt Modal via „×"-Button oder Escape-Taste in Schritt 2.

**Empfehlung:** Bestätigungs-Dialog („Änderungen verwerfen?") nur wenn bereits Eingaben gemacht wurden (Schritt > 1 und mindestens 1 Feld bearbeitet). Sonst sofort schließen.

**Dialog-Design:**
- **Overlay:** `rgba(0,0,0,0.6)` + `backdrop-filter: blur(4px)` (bestehendes `.mw-modal-overlay` Pattern)
- **Modal:** `max-width: 450px`, `padding: 24px`, 2 Buttons: „Verwerfen" (`btn-danger`) + „Weiter bearbeiten" (`btn-primary`)
- **Text:** „Möchtest du den Assistenten wirklich abbrechen? Nicht gespeicherte Änderungen gehen verloren."

### Fehlerdarstellung

**Fehler-Szenarien:**
1. **Provider down (TMDb/TVDB/OMDB antwortet nicht):**
   - **Inline-Fehler:** Badges mit `border: 1px dashed var(--danger)`, Text „TMDb: nicht erreichbar" in `var(--danger)`
   - **Banner oben:** `background: rgba(239, 68, 68, 0.1)`, `border-left: 3px solid var(--danger)`, Text „Einige Provider sind nicht erreichbar. Du kannst trotzdem fortfahren."
   - **Retry-Button:** Kleiner Button rechts im Banner, `btn-secondary btn-xs`

2. **NAS hängt beim Ähnliche-Titel-Scan (Schritt 1):**
   - **Timeout nach 10s:** Banner mit „Scan dauert länger als erwartet" + „Abbrechen"-Button
   - **Progress-Indicator:** Spinner-Icon + „Ähnliche Titel werden gesucht..." (Text ändert sich nach 5s zu „Noch suchen...")

3. **Artwork lädt nicht (Schritt 3):**
   - **Placeholder-Kachel:** Siehe Schritt 3, Zustand 4
   - **Retry pro Kachel:** Klick auf Placeholder = erneuter Ladeversuch

**Allgemeine Fehler-Styles:**
- **Banner:** `padding: 12px 16px`, `border-radius: var(--radius-md)`, `margin-bottom: 16px`
- **Warnung:** `background: rgba(245, 158, 11, 0.1)`, `border-left: 3px solid var(--warning)`, `color: var(--warning)`
- **Fehler:** `background: rgba(239, 68, 68, 0.1)`, `border-left: 3px solid var(--danger)`, `color: var(--danger)`

---

## 6. Theme-Strategie

### Grundsatz: Nur CSS-Variablen + neue Klassen

**Regel:** Keine `inline-style`-NN-Klassen mehr erzeugen (wie im NFO-Agent-Modal). Alle neuen Styles via `mw-wizard-*`-Klassen in `style.css` oder `utilities.css`.

**Begründung:**
- `inline-style`-NN-Klassen sind nicht theme-fähig (hartcodierte Farben)
- Wartbarkeit: CSS-Variablen ermöglichen Theme-Wechsel ohne Code-Änderung
- Konsistenz: Bestehende Patterns (`.mw-modal`, `.btn`, `.step-dot`) nutzen bereits Variablen

### Hardcoded-Farben im NFO-Agent-Modal (Mitwander-Bedarf)

**Betroffene Stellen (index.html:3163):**
```
background: rgba(30, 30, 45, 0.95)  → ersetzen durch var(--bg-card)
backdrop-filter: blur(10px)         → beibehalten (theme-neutral)
```

**Betroffene Stellen (index.html:3189, 3193, 3218):**
```
background: rgba(0,0,0,0.2)         → ersetzen durch var(--bg-input)
background: rgba(30,30,45,1)        → ersetzen durch var(--bg-input)
```

**Migration:** Wenn der Wizard gebaut wird, sollte der NFO-Agent-Modal **mitmigriert** werden (gleiche CSS-Variablen-Strategie). Aufwand: **klein** (5–10 Farbwerte ersetzen).

### Prüfliste: Alle 5 Themes visuell

**Akzeptanzkriterium:** Jede neue Wizard-Komponente muss in allen 5 Themes visuell getestet werden:
- [ ] theme-deep-space (Standard-Dunkel)
- [ ] theme-nordic-slate (Blau-Dunkel)
- [ ] theme-amber-warmth (Braun-Dunkel)
- [ ] theme-apple-black (Schwarz)
- [ ] theme-superfood-light (Hell)

**Test-Szenarien:**
- Schritt-Indikator (aktive/abgeschlossene/zukünftige Punkte)
- Provider-Badges (mit/ohne Wert, ausgewählt)
- Poster-Raster (geladen, Skeleton, Placeholder, ausgewählt)
- Ergebnis-Gruppen (geschlossen/offen)
- Fehler-Banner (Warnung, Fehler)

**Kritische Themes:**
- **superfood-light:** Hell → dunkle Texte, helle Hintergründe. Kontrast prüfen!
- **amber-warmth:** Braun → warme Farben, `var(--accent)` ist amber. Auswahl-Ring muss leuchten!

---

## 7. Offene Design-Fragen an Alex

### Frage 1: Schritt-Indikator-Style

**Empfehlung:** Punkt-Indikator mit Zahlen + Labels (siehe Skizze oben).

**Alternative:** Fortschrittsbalken (visuell ruhiger, aber bei 4 Schritten zu grob).

**Alex-Entscheidung:** Punkt-Indikator oder Fortschrittsbalken?

---

### Frage 2: Artwork-Tab vs. beide Raster gleichzeitig

**Empfehlung:** Tab-Switcher zwischen „Poster" und „Fanart" (spart vertikalen Platz, verhindert Scrollen).

**Alternative:** Beide Raster untereinander (mehr Überblick, aber riskiert Scrollen).

**Alex-Entscheidung:** Tab-Switcher oder beide Raster sichtbar?

---

### Frage 3: „Überspringen"-Button in Schritt 2 und 3

**Empfehlung:** „Überspringen"-Button in Schritt 2 (Standard: alle Felder aus TMDb) und Schritt 3 (Standard: erstes Poster oder kein Artwork).

**Alternative:** Kein „Überspringen", Nutzer muss explizit wählen.

**Alex-Entscheidung:** „Überspringen" erlauben oder Pflicht-Auswahl?

---

### Frage 4: Fehlerdarstellung bei Provider-Ausfall

**Empfehlung:** Inline-Fehler (Badges mit `var(--danger)`) + Banner oben („Einige Provider nicht erreichbar").

**Alternative:** Nur Banner oben, Badges bleiben neutral.

**Alex-Entscheidung:** Inline-Fehler + Banner oder nur Banner?

---

### Frage 5: Abbruch-Dialog nur bei Änderungen oder immer?

**Empfehlung:** Bestätigungs-Dialog nur, wenn bereits Eingaben gemacht wurden (Schritt > 1 und mindestens 1 Feld bearbeitet).

**Alternative:** Immer Dialog zeigen (einfacher zu implementieren, aber nervig bei versehentlichem Öffnen).

**Alex-Entscheidung:** Dialog nur bei Änderungen oder immer?

---

## Zusammenfassung: Aufwandsschätzung pro Schritt

| Schritt | Aufwand | Begründung |
|---------|---------|------------|
| **Schritt 1 (Layout + Fortschrittskopf)** | **Klein** | Bestehende Modal-Struktur wird erweitert, Schritt-Indikator ist Adaption des Onboarding-Patterns. |
| **Schritt 2 (Metadaten-Vergleich)** | **Mittel** | Neues Karten-Layout, Badge-Zustände sind überschaubar, aber 6 Felder + Plot erfordern sorgfältige Struktur. |
| **Schritt 3 (Artwork-Auswahl)** | **Mittel** | Raster-Layout ist Standard, aber Ladezustände (Skeleton, Placeholder) und Theme-Tests (5 Themes) benötigen Zeit. |
| **Schritt 4 (Ergebnis-Zusammenfassung)** | **Mittel** | Collapse-Logik ist Standard, aber viele Gruppen + Listen erfordern sorgfältige Struktur. |
| **Navigation + Zustände** | **Klein** | Fokus-Management und Abbruch-Dialog sind Standard-Patterns. |
| **Theme-Strategie** | **Klein** | Nur CSS-Variablen + neue Klassen, keine komplexen Theme-spezifischen Anpassungen. |

**Gesamtaufwand:** **Mittel** (ca. 2–3 Tage für Implementierung + Testing in allen 5 Themes).

---

## Präzedenzfälle und Referenzen

### Übernommen aus bestehenden Patterns

1. **Onboarding-Wizard (style.css:2692–2807):** Schritt-Indikator mit `.step-dot`-Klassen wird für Wizard-Fortschrittskopf adaptiert.
2. **NFO-Agent-Modal (index.html:3162–3259):** Modal-Struktur (`.mw-modal-overlay`, `.mw-modal`) wird für Wizard-Overlay wiederverwendet.
3. **Fallback-Poster (style.css:2810–2845):** Placeholder-Kachel-Design wird für Artwork-Schritt adaptiert.

### Präzedenzfälle aus anderen Apps

1. **Emby Setup-Wizard:** Punkt-Indikator mit Labels für mehrstufige Konfiguration → übernommen für Wizard-Fortschrittskopf.
2. **Stripe Checkout:** Mehrstufige Formulare mit Punkt-Indikator + Labels → übernommen für Orientierung und Kontext.
3. **macOS Finder „Informationen":** Zusammenklappbare Sektionen → übernommen für Ergebnis-Zusammenfassung (Schritt 4).

### Bewusst ignoriert

1. **Emby's kontextuelle Menüs (Rechtsklick auf Poster):** Zu komplex für Ein-Nutzer-Tool, Auswahl per Klick reicht.
2. **Plex's automatische Vorauswahl:** Alex will explizite Kontrolle (ROADMAP #51), keine Auto-Auswahl.
3. **Jellyfin's 3D-Poster-Effekte:** Verfälschen das Artwork, 2D ist theme-neutral und schneller zu rendern.

---

**Ende des Grafiker-Beitrags.**
