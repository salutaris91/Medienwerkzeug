<!-- Mechanisch aus `opencode export ses_eafa26390ffe6b5c7yV6t27Lma` extrahiert (Claude Code, 2026-10-18): alle Assistant-Textteile in Reihenfolge, ungekürzt, unverändert (nur Trailing Whitespace entfernt). Rohdatei: Kit-Worktree clever-mclaren-94c19f scripts/gate-a2/logs/2026-10-18-roadmap74-kette/akt2/export-grafiker-eafa26390ffe.json -->

Ich prüfe zuerst das Arbeitsverzeichnis und die Designsprache als „Grundgesetz".



**`docs/designsprache.md` existiert nicht im Arbeitsverzeichnis.** Ich arbeite ohne sie und stütze mich auf bestehende Patterns, Theme-Variablen und die referenzierten Vorlagen-Sessions.

Nun lese ich den verifizierten Code-Stand und vorherige Grafiker-Sessions als Kontext:



Jetzt lese ich die bestehende CSS-Klasse für Fehler, die Button-Definitionen und die vorherigen Grafiker-Sessions:



Jetzt lese ich die konkreten CSS-Definitionen und die anderen Grafiker-Sessions der letzten Woche:



Let me also check the bulk bar CSS and the existing group row structure more closely:



Jetzt habe ich den vollständigen Kontext. Hier ist die Strukturanalyse und meine konkreten Layout-Vorschläge.

---

# Layout-Konzept: Staffel-Schnellauswahl + Fehleranzeigen (E1/E2/E3)

> **Bezugsgrundlage:** `docs/designsprache.md` existiert im Worktree nicht (geprüft via `glob`). Konzeption bezieht sich auf Theme-Variablen (`style.css:4–42`), die Inline-Style-Konvention (`app.js:13273`, `:13289`, `:13300`) und bestehende Klassen (`.btn-xs :1783`, `.btn-sm :629`, `.smart-inbox-group-banner-error :3977`).

---

## 1. Gruppenkopf mit Staffel-Knopf-Reihe

### Empfehlung: Variante (b) — eigene zweite Zeile unter dem headerDiv

**Begründung der Varianten-Abwägung:**

| Variante | Vorteil | Nachteil |
|---|---|---|
| **(a) Rechter Block mit flex-wrap** | Minimaler DOM-Change | Bei 11 Staffeln + „Alle" + „Auswählen"→13 Knöpfe wrapt der ganze rechte Block; der „Auswählen"-Knopf rutscht unter die Titelzeile → Hierarchie-Bruch. Der rechte Block (`:13300`) ist heute `align-items: center; gap: 8px` ohne wrap — ein Wrap würde die vertikale Mitte zur Titelzeile zerstören. |
| **(b) Eigene Zeile** | Klare Trennung: Zeile 1 = Identität + Primäraction, Zeile 2 = Filter/Navigation. Extremfall (11+1 Knöpfe) hat eigenen Raum, ohne den Header zu stressen. | +4 Zeilen cssText, ein `createElement` mehr. |
| **(c) Mischform** | — | Kombiniert die Nachteile beider Varianten ohne klaren Gewinn. |

**Empfehlung: Variante (b).** Die zweite Zeile bildet eine **funktionale Hierarchie**: Header = „Was ist das + Hauptaktion", Staffelzeile = „Wähle den Bereich". Das ist dasselbe Pattern wie bei macOS Finder (Kopfzeile = Name + Meta, Toolbar darunter = Aktions-Buttons) oder Plex (Serien-Header + Staffel-Row darunter).

### DOM-Struktur (nur bei ≥ 2 Staffeln):

```
groupDiv (flex column, gap 10px) — unverändert
├── headerDiv (flex row, space-between) — unverändert
│   ├── linker Block (Chevron + Titel + Badge + Meta) — unverändert
│   └── rechter Block: NUR „Auswählen" (btn-sm, umbenannt)
├── ★ seasonBar (flex row, wrap) — NEU, nur bei ≥ 2 Staffeln
│   ├── btn „Staffel 1 (12)"   [btn-xs, sekundär]
│   ├── btn „Staffel 2 (15)"   [btn-xs, sekundär]
│   ├── ...
│   ├── btn „Staffel 11 (8)"   [btn-xs, sekundär]
│   └── btn „Alle Staffeln (173)" [btn-xs, primär-leicht]
├── ★ errorDiv (smart-inbox-group-banner-error) — NEU, bei Fehler
└── membersDiv — unverändert
```

### CssText-Snippets (1:1 übernehmbar):

**seasonBar-Container** (neues Div, eingefügt zwischen `headerDiv` und `membersDiv`):

```javascript
// Nur rendern wenn uniqueSeasons.length >= 2
const seasonBar = document.createElement("div");
seasonBar.className = "smart-inbox-group-seasons";
seasonBar.style.cssText = "display: flex; flex-wrap: wrap; align-items: center; gap: 6px; padding-top: 4px; border-top: 1px dashed rgba(139, 92, 246, 0.15);";
```

**Staffel-Einzelknopf** (sekundär, `btn-xs`):

```javascript
const seasonBtn = document.createElement("button");
seasonBtn.type = "button";
seasonBtn.className = "btn btn-secondary btn-xs";
seasonBtn.setAttribute("data-group-key", escapeHTML(item.group_key));
seasonBtn.setAttribute("data-season", String(season));
seasonBtn.style.cssText = "white-space: nowrap;";
seasonBtn.textContent = `Staffel ${season} (${count})`;
```

**„Alle Staffeln"-Knopf** (primär-leicht, `btn-xs`, mit zap-Icon):

```javascript
const allBtn = document.createElement("button");
allBtn.type = "button";
allBtn.className = "btn btn-primary btn-xs";
allBtn.setAttribute("data-group-key", escapeHTML(item.group_key));
allBtn.setAttribute("data-season", "all");
allBtn.style.cssText = "white-space: nowrap;";
allBtn.innerHTML = `<span style="display:inline-flex; align-items:center; gap:4px;"><svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="height: 12px; width: 12px;"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>Alle Staffeln (${total})</span>`;
```

**Knopf-Reihenfolge:** Staffel-Knöpfe aufsteigend numerisch (1, 2, 3, …), „Alle Staffeln" **rechts** am Ende. Begründung: „Alle" ist die Summe der Einzeloptionen — links würde es wie ein „Reset" wirken, rechts steht es als „alles zusammen" natural am Schluss (Präzedenzfall: macOS Finder-Tagfilter, Plex „All Seasons" rechts).

**Knopfgröße: `btn-xs`** (2px 6px, 11px Font, 4px Radius). Begründung: Bei 11+1 Knöpfen in einer Zeile würde `btn-sm` (4px 10px, 12px) die Zeile unnötig breit und hoch machen. `btn-xs` hält die Zeile kompakt und signalisiert „diese Knöpfe sind untergeordnet zum Hauptknopf ‚Auswählen'" (Hierarchie: Primäraction `btn-sm` > Sekundärfilter `btn-xs`).

### Sichtbarer Extremfall (11 Staffeln, 173 Folgen):

```
┌─────────────────────────────────────────────────────────────────────────┐
│ ▷  Breaking Bad  [Serie (Gruppe)]  173 Folgen · 845,2 GB · 18.10.2026   │
│                                                          [⚡ Auswählen] │
│ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  │
│ [Staffel 1 (12)] [Staffel 2 (15)] [Staffel 3 (13)] [Staffel 4 (13)]    │
│ [Staffel 5 (16)] [Staffel 6 (16)] [Staffel 7 (16)] [Staffel 8 (14)]    │
│ [Staffel 9 (16)] [Staffel 10 (14)] [Staffel 11 (8)]  [⚡ Alle (173)]   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Präzedenzfälle

| App/Pattern | Übernommen | Bewusst ignoriert |
|---|---|---|
| **Plex (Serien-Detail)** | Staffel-Filter als horizontale Button-Reihe unter dem Serien-Header, „All Episodes" rechts am Ende, `btn-xs`-kompakt. | Plex nutzt ein Dropdown bei >20 Staffeln — bei max. 11 ist die flache Reihe übersichtlicher (kein Klick nötig). |
| **Apple TV+ (Staffelauswahl)** | Kompakte Pill-Buttons, aktive Staffel hervorgehoben. | Apple nutzt ein vertikales Sidebar — zu viel Platz für eine Inline-Gruppe. |
| **macOS Finder (Tag-Filter)** | Horizontale Tag-Chips unter der Pfadzeile, wrapping bei Überlauf. | Finder nutzt Checkbox-Pills — unsere Knöpfe sind *exklusiv* (eine Staffel pro Klick), nicht *kombinierbar*, also anderer Interaktionsmodus. |

---

## 2. Visuelle Unterscheidung „Alle" vs. „Staffel N"

### Empfehlung: Primär vs. Sekundär, Icon nur bei „Alle"

| Aspekt | Staffel N (k) | Alle Staffeln (n) |
|---|---|---|
| **Klasse** | `btn btn-secondary btn-xs` | `btn btn-primary btn-xs` |
| **Hintergrund** | `rgba(255,255,255,0.05)` (style.css:625) | `var(--primary)` (bestehende btn-primary) |
| **Textfarbe** | `var(--text-main)` | weiß (btn-primary-default) |
| **Icon** | keins (reiner Text) | ⚡ zap-SVG (12×12, links vom Text) |
| **Wortlaut** | `Staffel N (k)` | `Alle Staffeln (n)` |

**Begründung:**
- **Kontrast-Hierarchie:** Primär (blau, Icon) = „startet den Workflow mit allen Folgen". Sekundär (grau, kein Icon) = „startet den Workflow mit dieser einen Staffel". Der visuelle Kontrast signalisiert sofort: „Alle" ist die Hauptaktion, Einzelstaffeln sind die Filter.
- **Icon-Ökonomie:** Das ⚡-SVG steht bereits am heutigen „Auswählen"-Knopf (`:13302`). Es als „Workflow-Start"-Signal nur beim Alle-Knopf zu behalten (und bei den Staffel-Knöpfen wegzulassen) erzeugt eine klare Ikonografie: ⚡ = „alles starten", kein ⚡ = „Teilbereich".
- **Bewusst ignoriert:** Variante mit farbigen Staffel-Badges (je Staffel eine andere Farbe) — zu viel visueller Lärm bei 11 Staffeln, und die Farbe hätte keine semantische Bedeutung.

---

## 3. Banner-Hinweis für Mehrstaffel-Gruppen

### Wortlaut-Vorschläge (drei Optionen, Alex entscheidet an FP2)

**Kontext:** Nach dem Klick auf „Als Serie gruppieren" bei ≥ 2 Staffeln verschwindet der Banner, die Gruppenzeile erscheint in der Liste mit den neuen Staffel-Knöpfen. Der Hinweis muss **vor** dem Klick erklären, was danach passiert.

**Option A (direkt, handlungsorientiert):**

> „Bei Serien mit mehreren Staffeln erscheint in der Liste eine Auswahl nach Staffel – kein automatischer Start."

**Option B (knapper, mit Gedankenstrich):**

> „Mehrere Staffeln erkannt – nach dem Gruppieren wählst du in der Liste eine einzelne Staffel oder startest alle."

**Option C (zweiteilig, mit Vorschau-Pfeil):**

> „Gruppen mit mehreren Staffeln starten nicht automatisch. Nach dem Gruppieren findest du in der Liste die Staffel-Auswahl ▷"

### Empfehlung: Option B

**Begründung:**
- **Option A** ist korrekt, aber „kein automatischer Start" formuliert negativ (was nicht passiert, statt was passiert).
- **Option B** ist kompakt, erklärt den *Grund* („Mehrere Staffeln erkannt") und die *Folge* („wählst du … eine einzelne Staffel oder startest alle") in einem Satz. Der Gedankenstrich (U+2013) trennt Ursache und Wirkung typografisch korrekt.
- **Option C** mit „▷"-Pfeil ist visuell nett, aber der Pfeil ist mehrdeutig (zeigt er auf die Liste? Auf die Staffel-Knöpfe?). In einer reinen Textumgebung ohne visuelle Verankerung verwirrt er mehr als er hilft.

### Platzierung

**Empfehlung: Als zweizeiliger Hinweis im Banner-Content-Span**, direkt nach dem bestehenden Content-Text:

```html
<div class="smart-inbox-group-banner-content">
    <svg><!-- layers-icon --></svg>
    <span>
        Als Serie gruppieren: <strong>Breaking Bad</strong> (173 Folgen, Staffeln 1, 2, …, 11)
        <span style="display: block; font-size: 0.85em; color: var(--text-muted); margin-top: 2px;">
            Mehrere Staffeln erkannt – nach dem Gruppieren wählst du in der Liste eine einzelne Staffel oder startest alle.
        </span>
    </span>
</div>
```

**Begründung der Platzierung:**
- **Im Banner-Text** (nicht als separater Block darunter): Der Hinweis gehört semantisch zur Aktion — er modifiziert das Versprechen des Buttons. Ein separater Block (z.B. eigene `div` unter dem Banner) würde wie eine unabhängige Meldung wirken und leicht übersehen.
- **`display: block; margin-top: 2px`**: Die zweite Zeile rückt visuell unter den Haupttext, bleibt aber innerhalb desselben `<span>`. `font-size: 0.85em` + `color: var(--text-muted)` signalisieren „Erläuterung, nicht Haupttext" (Hierarchie).
- **Nur bei ≥ 2 Staffeln:** Bei Einzel-Staffel-Gruppen erscheint der Hinweis nicht (bisheriges Verhalten bleibt: „gruppieren + sofort starten").

### Button-Wortlaut-Änderung (bei ≥ 2 Staffeln)

Der Banner-Button heißt heute „Als Serie gruppieren". Bei ≥ 2 Staffeln sollte er **identisch** bleiben — denn der Hinweis-Text erklärt ja, was danach passiert. Eine Änderung zu „Gruppieren" (ohne „Als Serie") wäre inkonsistent mit dem Einzel-Staffel-Fall.

**ABER:** Der „Auswählen"-Knopf in der Gruppenzeile (`:13302`) muss umbenannt werden (siehe Kickoff E1-F3). Empfehlung:

| Staffelzahl | Banner-Button | Gruppenzeile (rechter Block) |
|---|---|---|
| 1 Staffel | „Als Serie gruppieren" (unverändert) | „Auswählen" → **„Starten"** (knapp, eindeutig) |
| ≥ 2 Staffeln | „Als Serie gruppieren" (unverändert) | „Auswählen" → **„Starten"** (öffnet nicht mehr automatisch; Nutzer sieht Staffel-Knöpfe) |

---

## 4. Position der E2-Inline-Fehlermeldung

### 4a. Gruppenzeile

**Eine Meldung pro Gruppe**, nicht pro Staffel-Knopf. Begründung: Die Fehlerquelle ist der Workflow-Start (Sperre `groupWorkflowRunning`, Server-Fehler), nicht die einzelne Staffel. Eine Gruppe = ein Fehlerzustand.

**Position im groupDiv:** Direkt **nach der seasonBar**, **vor dem membersDiv**:

```
groupDiv
├── headerDiv
├── seasonBar (★ neu)
├── errorDiv  (★ neu, nur bei Fehler)
└── membersDiv
```

**CssText-Snippet:**

```javascript
// Nach seasonBar einfügen, nur wenn groupRowErrors.has(item.group_key)
const errorDiv = document.createElement("div");
errorDiv.className = "smart-inbox-group-banner-error";
errorDiv.setAttribute("role", "alert");
errorDiv.setAttribute("aria-live", "polite");
errorDiv.textContent = bannerApplyErrors.get(item.group_key); // oder neue Map groupRowErrors
// Kein eigenes cssText nötig — die Klasse in style.css:3977 liefert bereits:
// color: var(--danger); background: rgba(239,68,68,0.1);
// border: 1px solid rgba(239,68,68,0.3); border-radius: var(--radius-md);
// padding: 6px 10px; font-size: 0.8rem
```

**Falls keine seasonBar existiert** (Einzel-Staffel-Gruppe, aber Fehler): errorDiv direkt nach headerDiv.

### 4b. Bulk-Leiste

**Position:** Innerhalb des `innerHTML`-Templates (`:12909–12917`), als **eigene Zeile zwischen `.smart-inbox-bulk-info` und `.smart-inbox-bulk-buttons`** — aber nur bei Fehler.

**Template-Skizze:**

```javascript
const bulkError = bulkBarError  // Modul-Variable (ein String, kein Map — Bulk-Leiste wird neu gebaut
    ? `<div class="smart-inbox-group-banner-error" role="alert" aria-live="polite" style="width: 100%;">${escapeHTML(bulkBarError)}</div>`
    : "";

bulkBar.innerHTML = `
    <div class="smart-inbox-bulk-info">
        <span id="smart-inbox-bulk-count">${count} ausgewählt</span>
    </div>
    ${bulkError}
    <div class="smart-inbox-bulk-buttons">
        <button class="btn btn-secondary btn-xs" id="btn-bulk-deselect">Auswahl aufheben</button>
        <button class="btn btn-primary btn-xs" id="btn-bulk-group-series">Ausgewählte als Serie verarbeiten</button>
    </div>
`;
```

**CssText am Fehler-Div:** `style="width: 100%;"` — erzwingt eigene Zeile im bestehenden `justify-content: space-between`-Flex-Layout (`style.css:3992`). Die Fehlermeldung spannt die volle Breite zwischen Info und Buttons, visuell als eigene Zeile.

**Alternative (kompakter):** Fehler-Div **nach** `.smart-inbox-bulk-buttons`, als dritter Flex-Partner. Nachteil: Bei `justify-content: space-between` würde der Fehler zwischen Info und Buttons gequetscht. Die `width: 100%`-Lösung erzwingt den Zeilenumbruch sauberer.

---

## 5. E3-Timeout-Meldung im Suchbereich

### Empfehlung: Bestehendes Muster erweitern, keine neue Zeile

Heute (`:3212`):
```javascript
resultsContainer.innerHTML = `<p class="text-center text-danger">Suchfehler: ${e.message || e}</p>`;
```

**Vorschlag für Timeout-Fall:**

```javascript
// Im Timeout-Zweig (didTimeout === true):
resultsContainer.innerHTML = `
    <p class="text-center text-danger">
        Suchfehler: Zeitüberschreitung nach 30 Sekunden.
    </p>
    <p class="text-center" style="color: var(--text-muted); font-size: 0.85em; margin-top: 4px;">
        Bitte Suche erneut starten – bei anhaltendem Problem Provider-Verbindung prüfen.
    </p>
`;
```

**Begründung:**
- **Bestehendes Muster beibehalten** (`p.text-center.text-danger`): Der Nutzer erkennt sofort „das ist eine Fehlermeldung im Suchbereich". Keine neue CSS-Klasse, kein anderes Layout.
- **Zweite Zeile als Hinweis** (`var(--text-muted)`, `font-size: 0.85em`): „Bitte Suche erneut starten" ist die Handlungsaufforderung. „Provider-Verbindung prüfen" gibt eine Diagnose-Perspektive. Die `margin-top: 4px` hält die beiden Absätze visuell zusammen (Gruppierung).
- **Kein „erneut versuchen"-Button:** Die Suche wird über verschiedene Wege gestartet (manuell, Workflow-Ende, Auto-Suche) — ein Button im Suchergebnis-Bereich wäre kontextuell falsch. Der Hinweis „bitte erneut starten" reicht; der Nutzer klickt dann auf „Suchen" im Serien-Dialog.
- **Kein separater Timeout-Stil:** `text-danger` reicht. Ein Icon (⏱️) wäre Scope-Creep (keine neuen Icons).

---

## Zusammenfassung (Entscheidungsvorlage)

| Aspekt | Empfehlung | Alex-Entscheidung |
|---|---|---|
| **Staffel-Knopf-Platzierung** | Variante (b): eigene Zeile unter headerDiv, `flex-wrap: wrap`, `gap: 6px` | offen |
| **Knopfgröße** | `btn-xs` für Staffel + Alle; `btn-sm` nur für „Starten" | offen |
| **Reihenfolge** | Staffel 1, 2, …, N, dann „Alle Staffeln" rechts | offen |
| **„Alle" vs. „Staffel N"** | Alle = `btn-primary` + ⚡-Icon; Staffel = `btn-secondary` + kein Icon | offen |
| **Banner-Hinweis** | Option B: „Mehrere Staffeln erkannt – nach dem Gruppieren wählst du in der Liste eine einzelne Staffel oder startest alle." | **FP2** |
| **Hinweis-Platzierung** | Im Banner-Content-Span, zweite Zeile, `var(--text-muted)` | offen |
| **„Auswählen" → „Starten"** | Ja, umbenennen (FP1-Beschluss) | offen |
| **E2 Gruppenzeile** | 1 Meldung pro Gruppe, nach seasonBar, `div.smart-inbox-group-banner-error` | offen |
| **E2 Bulk-Leiste** | `width: 100%`-Div zwischen Info und Buttons | offen |
| **E3 Timeout** | `p.text-center.text-danger` + zweite Zeile `var(--text-muted)` mit Handlungsaufforderung | offen |

### Präzedenzfälle gesamt

| App/Pattern | Übernommen | Bewusst ignoriert |
|---|---|---|
| **Plex (Serien-Detail)** | Staffel-Filter als kompakte Button-Reihe unter dem Header, „All" rechts. | Dropdown bei >20 Staffeln — bei max. 11 unnötig. |
| **Gmail (Konversationsansicht)** | Inline-Fehlermeldung direkt unter dem Aktionsbereich, `role="alert"`. | Toast-Benachrichtigungen — zu flüchtig für Workflow-Fehler. |
| **GitHub (Dependabot-Alerts)** | Fehler als farbiger Inline-Block mit `border-radius` und dezentem Hintergrund. | Collapse/Expand für Fehler — bei einer Meldung pro Gruppe overkill. |

---

Ich habe keine Dateien geschrieben. Keine `style.css`-Änderung vorgeschlagen. Cache-Buster: nur `app.js v103→v104` (10 Stellen in `index.html`).
