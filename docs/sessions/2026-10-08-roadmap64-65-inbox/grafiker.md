# Rohoutput grafiker — Kreativteam-Session 2026-10-08 (Akt 2)
Hinweis Claude Code (2026-10-08): Mechanisch aus `opencode export ses_ee533a3c8ffesW6v133rMvr61E` (ceo-planner) abgelegt, nicht vom Moderator abgeschrieben (Lehre 59). Je Abschnitt: Auftragsbeschreibung, Subagent-Sitzung, dann die wörtliche Subagent-Antwort. Einzige Änderung: Trailing Whitespace am Zeilenende entfernt (Pre-Commit-Hook); sonst unverändert. Volle Prompts und Antworten: Kit `scripts/gate-a2/logs/2026-10-08-roadmap64-65/export-ceo-planner.json`.

---

## grafiker zu #64 Sortier-UI (Subagent-Sitzung ses_ee526865dffeJ0jrzSbePJ8mHy, Status: error)

Kein Output. Fehler (wörtlich): Subagent failed (task_id: ses_ee526865dffeJ0jrzSbePJ8mHy): The user rejected permission to use this specific tool call.
Ursache laut stderr: Berechtigungsanfrage `external_directory (/Users/alex/Documents/Medienwerkzeug/*)` headless auto-abgelehnt; der ceo-planner hat den Auftrag danach wiederholt (nächster Abschnitt).

---

## grafiker zu #64 (Wiederholung) (Subagent-Sitzung ses_ee5245faffferxo331eFD12Ejg, Status: completed)

<task id="ses_ee5245faffferxo331eFD12Ejg" state="completed">
<task_result>
# Rohoutput grafiker — Kreativteam-Session 2026-10-08 (ROADMAP #64)

> **Bezugsgrundlage:** `docs/designsprache.md` existiert im Worktree nicht (Bestätigung aus den Vorläufer-Sessions 2026-09-03 und 2026-10-06). Diese Konzeption bezieht sich auf die Theme-Variablen in `gui/static/style.css` (Deep-Space-Default: `--bg-card #18181b`, `--border-glass #27272a`, `--text-main #f8fafc`, `--text-muted #94a3b8`, `--accent #2563eb`, `--radius-lg 10px`, `--radius-sm 4px`) und die Inline-Style-Konvention in `app.js:12278–12303`.

---

## 1. Sortier-Steuerung — drei Varianten

### Variante A: Sortier-Leiste (empfohlen)

Dünne Trenn-Leiste zwischen Abschnittstitel und Liste. Drei klickbare Label-Buttons `Name | Datum | Größe`, aktives Feld hervorgehoben mit Pfeil-Indikator (▲/▼).

```html
<!-- HTML-Mockup: Sortier-Leiste, eingefügt zwischen index.html:459 (BEREINIGEN-Row) und :461 (#smart-inbox-list) -->
<div id="smart-inbox-sort-bar" role="toolbar" aria-label="Sortierung"
     style="display: flex; align-items: center; gap: 4px; padding: 6px 0; margin-bottom: 8px;
            border-bottom: 1px solid var(--border-light); font-size: 0.8em;">
  <span style="color: var(--text-muted); margin-right: 4px; font-weight: 500;">Sortieren:</span>
  <button data-sort="name" aria-sort="ascending"
    style="background: rgba(255,255,255,0.08); color: var(--text-main); border: none; border-radius: 4px;
           padding: 4px 10px; cursor: pointer; font-size: inherit; font-weight: 600; min-height: 28px;
           display: inline-flex; align-items: center; gap: 4px;">
    Name <span aria-hidden="true">▲</span>
  </button>
  <button data-sort="date"
    style="background: transparent; color: var(--text-muted); border: none; border-radius: 4px;
           padding: 4px 10px; cursor: pointer; font-size: inherit; min-height: 28px;
           display: inline-flex; align-items: center; gap: 4px;">
    Datum
  </button>
  <button data-sort="size"
    style="background: transparent; color: var(--text-muted); border: none; border-radius: 4px;
           padding: 4px 10px; cursor: pointer; font-size: inherit; min-height: 28px;
           display: inline-flex; align-items: center; gap: 4px;">
    Größe
  </button>
</div>
```

**Empfehlung: Variante A.** Begründung:

- **Affordanz-Kongruenz:** Die Einträge sind Flex-Zeilen mit links-bündiger Informationshierarchie (Name → Meta → Aktionen). Eine horizontale Leiste bildet dieselbe Lesrichtung ab und signalisiert „Spalten" — ohne eine Tabelle vorzutäuschen, die es visuell nicht gibt.
- **Entdeckung:** Alle drei Optionen sind sofort sichtbar (keine versteckte Dropdown). Das ist entscheidend, weil Sortierung ein *sekundäres* Feature ist — niemand soll erst klicken müssen, um zu sehen, dass es existiert.
- **Weißraum-Ökonomie:** 28px Höhe + 8px Margin = minimaler vertikaler Footprint. Die bestehende `border-bottom: 1px solid var(--border-light)`-Sprache wird aufgegriffen (index.html:436, 452).

### Variante B: Kompakt-Dropdown

```html
<!-- Alternative: Dropdown statt Leiste -->
<select id="smart-inbox-sort-select" aria-label="Sortierung"
  style="background: var(--bg-input); color: var(--text-main); border: 1px solid var(--border-glass);
         border-radius: var(--radius-sm); padding: 4px 8px; font-size: 0.8em; min-height: 28px;">
  <option value="name-asc">Name (A → Z)</option>
  <option value="name-desc">Name (Z → A)</option>
  <option value="date-asc">Datum (älteste zuerst)</option>
  <option value="date-desc">Datum (neueste zuerst)</option>
  <option value="size-asc">Größe (kleinste zuerst)</option>
  <option value="size-desc">Größe (größte zuerst)</option>
</select>
```

**Bewusst abgelehnt.** Das `<select>`-Element verbirgt den aktuellen Zustand hinter einem Klick — der Nutzer sieht nicht, *wonach* sortiert ist, ohne das Dropdown zu öffnen. Zudem bricht ein nativer `<select>` visuell mit der Dark-UI (Browser-Default-Styling auf macOS/Windows), was entweder theme-spezifisches CSS oder ein Custom-Dropdown erfordert — beides Scope-Creep.

### Variante C: Sortier-Chips/Pills

```html
<!-- Alternative: Chip-Pills -->
<div style="display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 8px;">
  <button style="background: rgba(59,130,246,0.15); color: #3b82f6; border: 1px solid rgba(59,130,246,0.3);
                 border-radius: 12px; padding: 3px 12px; font-size: 0.75em; cursor: pointer;">
    Name ▲
  </button>
  <button style="background: rgba(255,255,255,0.03); color: var(--text-muted); border: 1px solid var(--border-glass);
                 border-radius: 12px; padding: 3px 12px; font-size: 0.75em; cursor: pointer;">
    Datum
  </button>
  <button style="background: rgba(255,255,255,0.03); color: var(--text-muted); border: 1px solid var(--border-glass);
                 border-radius: 12px; padding: 3px 12px; font-size: 0.75em; cursor: pointer;">
    Größe
  </button>
</div>
```

**Bewusst abgelehnt.** Die Pill-Form (`border-radius: 12px`) konkurriert mit den Typ-Badges (Film/Serie/Doku, identisches Styling `app.js:12286`). Zwei Elemente mit gleicher visueller Sprache an unterschiedlichen Stellen erzeugen Hierarchie-Noise. Die Type-Badges sind *klassifizierend*, die Sort-Chips wären *funktional* — diese Unterscheidung geht visuell verloren.

### Präzedenzfälle

| App/Pattern | Übernommen | Bewusst ignoriert |
|---|---|---|
| **macOS Finder (Liste)** | Klickbare Spaltenköpfe mit ▲/▼-Indikator, eine Spalte aktiv, Klick wechselt Richtung. *Übernommen:* Das Ein-Spalte-aktiv-Prinzip und die Pfeilrichtung. | Finder nutzt echte Tabellenspalten mit fester Breite — unsere Einträge sind Cards, also keine Spaltenköpfe, sondern eine Toolbar. |
| **GitHub Pull-Request-Liste** | Sort-Leiste als kompakte Button-Gruppe über der Liste (`Sort ▾`-Dropdown *plus* sichtbarer aktiver Wert). *Übernommen:* Trennung „Sortier-Toolbar" von der Liste via `border-bottom`. | GitHub kombiniert Dropdown + Label — zu komplex für drei Felder. Bei uns reichen drei Buttons. |
| **Spotify Playlist** | Klickbare Spaltenüberschriften (#, Title, Date Added, Duration) mit ▲-Indikator. *Übernommen:* Die `font-size: 0.8em`-Skalierung und `color: var(--text-muted)` für inaktive Labels. | Spotify hat echte Tabellenzellen — siehe Finder. |

---

## 2. Datums- und Größenanzeige pro Eintrag

### Empfehlung: Metazeile nach „N Datei(en)", Mittelpunkt-Trennzeichen

Heutige erste Zeile (app.js:12284–12288):
```
<strong>Name</strong> [Badge] N Datei(en)
```

Zielstruktur:
```
<strong>Name</strong> [Badge] N Datei(en) · 12,4 GB · 03.10.2026
```

**Konkrete Umsetzung** (app.js:12287 ersetzen/erweitern):

```javascript
// Hilfsfunktionen (einmalig definieren, z.B. am Dateianfang oder als Utility)
function formatFileSize(bytes) {
    if (bytes == null || bytes < 0) return "";
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + " MB";
    return (bytes / (1024 * 1024 * 1024)).toFixed(1) + " GB";
}

function formatGermanDate(isoOrTimestamp) {
    if (!isoOrTimestamp) return "";
    const d = new Date(typeof isoOrTimestamp === "number" ? isoOrTimestamp * 1000 : isoOrTimestamp);
    if (isNaN(d.getTime())) return "";
    return d.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" });
    // ergibt "03.10.2026"
}

// In der Render-Schleife (app.js:12287 ersetzen):
const metaParts = [`${item.video_count} Datei(en)`];
if (item.size != null) metaParts.push(formatFileSize(item.size));
if (item.date) metaParts.push(formatGermanDate(item.date));
const metaText = metaParts.join(` <span style="color: var(--text-muted);">·</span> `);

// Im HTML-Template:
`<span style="font-size: 0.8em; color: var(--text-muted);">${metaText}</span>`
```

**Begründung der Reihenfolge:**

1. **N Datei(en)** — bleibt zuerst, weil es direkt zum Projektnamen gehört (ist die häufigste Information, immer vorhanden).
2. **Größe** — vor Datum, weil sie für die Sortierentscheidung „lohnenswert?" relevanter ist (große Projekte = langer Download/Verarbeitung).
3. **Datum** — zuletzt, weil es die am wenigsten action-relevante Information ist (Alter des Projekts, nicht der Dateien).

**Trennzeichen `·` (U+00B7):** Etabliert in der bestehenden UI als Separator-Konvention (app.js nutzt bereits `gap`-basierte Trennung, aber für Text-Segmente in einer Zeile ist der Mittelpunkt das typografisch korrekte Zeichen — kein Pipe `|`, kein Bindestrich). `color: var(--text-muted)` für das Trennzeichen selbst, damit es gegenüber den Werten zurücktritt.

**Fallback:** Wenn `item.size` oder `item.date` vom Server `null`/`undefined` sind, wird das Segment übersprungen — kein leeres `· ·`, kein „—".

---

## 3. Zustände & A11y

### Visuelle Zustände der Sortier-Buttons

| Zustand | `background` | `color` | Pfeil | Sonstiges |
|---|---|---|---|---|
| **Inaktiv** | `transparent` | `var(--text-muted)` | keiner | — |
| **Hover** | `rgba(255,255,255,0.05)` | `var(--text-muted)` | keiner | `transition: background 0.15s` |
| **Aktiv (asc)** | `rgba(255,255,255,0.08)` | `var(--text-main)` | `▲` nach Label | `font-weight: 600` |
| **Aktiv (desc)** | `rgba(255,255,255,0.08)` | `var(--text-main)` | `▼` nach Label | `font-weight: 600` |
| **Fokus (Keyboard)** | wie aktiv + | — | — | `outline: 2px solid var(--accent); outline-offset: 2px` |

### A11y-Anforderungen

- **`<button>`-Elemente**, kein `<span onclick>` — bereits im Mockup (Abschnitt 1) so vorgesehen.
- **`aria-sort="ascending"` / `"descending"`** am *aktiven* Button. Inaktive Buttons haben kein `aria-sort` (nicht `"none"` — das ist laut W3C ARIA 1.2 nur für Tabellenspalten definiert).
- **`aria-label`** am Toolbar-Container: `aria-label="Sortierung der Inbox-Projekte"`.
- **Mindestklickfläche:** `min-height: 28px` + `padding: 4px 10px` ergibt effektiv ~28×60px — über WCAG 2.5.5 (44×44px empfohlen, 28px Höhe ist akzeptabel für Text-Buttons in Toolbars, vgl. GitHub/Spotify).
- **Keyboard:** Tab-Reihenfolge: Sortier-Leiste → erste Inbox-Zeile → zweite … (native Tab-Order, kein `tabindex` nötig). Enter/Space auf Sortier-Button triggert Sortierung.

### Umschalt-Logik

```
Klick auf inaktiven Button → aktiv, Richtung asc, alle anderen inaktiv
Klick auf bereits aktiven Button → Richtung wechselt (asc ↔ desc)
```

### Session-Persistenz

```javascript
// Speichern
sessionStorage.setItem("smart-inbox-sort", JSON.stringify({ field: "name", direction: "asc" }));
// Lesen
const saved = JSON.parse(sessionStorage.getItem("smart-inbox-sort") || "null");
```

Key: `smart-inbox-sort`. Default (kein Eintrag): `{ field: "name", direction: "asc" }` — alphabetisch aufsteigend ist die mental erwartete Default-Reihenfolge für eine Projektliste.

---

## 4. Edge Cases visuell

### Leere Liste

Die Sortier-Leiste wird **nur gerendert, wenn `suggestions.length > 0`** (app.js:12253). Bei leerer Liste bleibt der bestehende Leerzustand (app.js:12322) unverändert — kein orphaned Sort-Bar über der „Keine verarbeitbaren Film-…" Nachricht.

### Lange Projektnamen (Wrap)

Bestehendes Problem: `app.js:12284` hat `flex-wrap: wrap` auf der Name-Zeile, aber der `<strong>`-Name selbst hat kein Wrap-Verhalten. Lösung:

```css
/* inline am <strong>: */
word-break: break-word;
overflow-wrap: break-word;
min-width: 0;  /* erlaubt Flex-Child zu schrumpfen */
```

Die Metazeile (`N Datei(en) · 12,4 GB · 03.10.2026`) bricht natural mit `flex-wrap: wrap` in die zweite Zeile, wenn der Name zu lang ist. Die Reasons-Badges rutschen entsprechend nach unten — bestehendes Verhalten bleibt intakt.

### Schmaler Bildschirm (< 600px)

Die Sortier-Leiste nutzt `flex-wrap: wrap` (bereits im Toolbar-Container über `flex-wrap: wrap` an index.html:428 angelegt). Bei < 400px Breite:

```
Sortieren:
[Name ▲] [Datum] [Größe]
```

…bricht in eine eigene Zeile. Kein horizontales Scrollen.

### Verarbeitungs-Hervorhebung (app.js:2465–2471)

Die Cyan-Border (`rgba(0, 229, 255, 0.3)`) und das Cyan-Background (`rgba(0, 229, 255, 0.03)`) werden am **Item-Div** gesetzt (app.js:12275–12276), nicht an der Sortier-Leiste. Die Sortierung ändert nur die *Reihenfolge* der Item-Divs im DOM — die `updateSmartInboxProcessingState`-Logik (app.js:2460–2471) iteriert über `[data-project]`-Attribute und ist damit reihenfolge-unabhängig. **Keine Änderung nötig.**

### Sortierung während Verarbeitung

Wenn ein Projekt den Verarbeitungsstatus wechselt, während die Liste sortiert ist, bleibt die Sortierung erhalten. `updateSmartInboxProcessingState()` ändert nur Border/Background/Disabled-State, nicht die DOM-Reihenfolge. Passt.

---

## 5. Bewusst NICHT

| Nicht enthalten | Begründung |
|---|---|
| **Keine neue CSS-Datei** | Die gesamte Sortier-Leiste + Zustände lassen sich als Inline-Styles (app.js-Konvention) umsetzen. Einzige Ausnahme: `:hover`/`:focus`-Pseudoklassen brauchen entweder `style.css` (~10 Zeilen) oder JS-Event-Listener. Empfehlung: **`style.css` minimal erweitern** (Hover/Focus für `.smart-inbox-sort-btn`), weil JS-Hover-Listener teurer und fehleranfälliger sind. |
| **Keine neuen Icons** | ▲/▼ sind Unicode-Zeichen (U+25B2/U+25BC), keine Lucide-SVGs nötig. Die Sortier-Pfeile sind *funktionale Indikatoren*, nicht dekorative Icons — Unicode ist hier semantisch korrekt und spart ~200 Bytes pro Pfeil. |
| **Keine Mehrfachsortierung** | Ein Feld aktiv gleichzeitig — ausreichend für drei Sortierdimensionen. Shift-Klick-Multisort ist ein Power-User-Feature ohne erkennbaren Bedarf in einer Projektliste. |
| **Kein Drag-to-Reorder** | Gehört zu ROADMAP #20, ist explizit ausgelagert. Die Sortier-Leiste blockiert diese Erweiterung nicht — ein späteres Drag-Handle links an jeder Zeile ist kompatibel. |
| **Kein Custom-Dropdown** | Variante B bewusst abgelehnt (siehe Abschnitt 1). |
| **Keine Server-Sortierung** | Die Liste hat typischerweise < 50 Einträge. Client-Sortierung (Array.sort + DOM-Rebuild) ist unter 1 ms — Server-Roundtrip wäre UX-Verschlechterung. |
| **Keine Animation der Sortier-Reihenfolge** | FLIP-Animationen für DOM-Reordering sind visuell nett, aber bei < 50 Einträgen und Inline-Styles unverhältnismäßig komplex. Einfaches `innerHTML`-Rebuild reicht. |

---

**Zusammenfassung (Entscheidungsvorlage):**

| Aspekt | Empfehlung |
|---|---|
| Steuerungs-UI | Variante A: Sortier-Leiste mit drei `<button>`-Labels |
| Meta-Anzeige | `N Datei(en) · 12,4 GB · 03.10.2026` (Mittelpunkt-Trenner, Fallback bei fehlenden Werten) |
| Richtungs-Indikator | ▲/▼ Unicode nach dem aktiven Label, `font-weight: 600` + `var(--text-main)` |
| Persistenz | `sessionStorage` Key `smart-inbox-sort`, Default `name/asc` |
| style.css | Minimal: ~10 Zeilen Hover/Focus für `.smart-inbox-sort-btn` |
| A11y | `<button>`, `aria-sort`, `aria-label` am Toolbar, Fokus-Ring `2px solid var(--accent)` |
</task_result>
</task>
