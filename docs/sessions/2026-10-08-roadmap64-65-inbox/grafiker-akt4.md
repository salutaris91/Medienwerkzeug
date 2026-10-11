# Rohoutput grafiker — Kreativteam 2026-10-08 (Akt 4, #65)
Hinweis Claude Code (2026-10-09): Mechanisch aus `opencode export ses_ee2dc847cffeefAVh2xzGtKoRQ` (ceo-planner, Akt 4b–4d im #65-Worktree) abgelegt, nicht vom Moderator abgeschrieben (Lehre 59). Einzige Änderung: Trailing Whitespace entfernt. Der in Akt 4c hängengebliebene plan-reviewer-Aufruf (Subagent-Sitzung ses_ee2c4d97bffe3qpBcSH5O8ZJ1P, Modell-Stream abgerissen, von Claude Code beendet) hat keinen Output und erscheint hier nicht. Volle Daten: Kit `scripts/gate-a2/logs/2026-10-08-roadmap64-65/export-akt4.json`.

---

## grafiker: Kästchen-UI Inbox (Subagent-Sitzung ses_ee2d12723ffealf5s7nIWVB1aE, Status: completed)

<task id="ses_ee2d12723ffealf5s7nIWVB1aE" state="completed">
<task_result>
# Konzeption: Checkbox-Auswahl + Sammel-Knopf für „Als Serie gruppieren"

> **Bezugsgrundlage:** `docs/designsprache.md` existiert nicht (Bestätigung aus `grafiker-akt3.md:19`). Konzeption bezieht sich auf Theme-Variablen (`--text-main`, `--text-muted`, `--border-light`, `--accent`) und Inline-Style-Konvention aus `app.js:12450–12475`.

---

## a) Positionierung von Checkbox und Sammel-Knopf

### Empfehlung: Checkbox **links vor dem Projektnamen**, Sammel-Knopf in **eigener Aktionsleiste zwischen Sortier-Leiste und Liste**

**Checkbox in der Zeile:**

```html
<div class="smart-inbox-item" data-project="Breaking.Bad.S01E01"
     style="background: rgba(255,255,255,0.02); border: 1px solid var(--border-light);
            border-radius: 8px; padding: 14px 18px; display: flex; align-items: center;
            justify-content: space-between; gap: 16px;">

  <!-- CHECKBOX: ganz links, vor dem Content-Block -->
  <input type="checkbox" class="smart-inbox-checkbox"
         aria-label="Breaking Bad S01E01 zur Serien-Gruppierung auswählen"
         style="width: 18px; height: 18px; cursor: pointer; flex-shrink: 0;
                accent-color: var(--accent, #00e5ff);">

  <!-- Bestehender Content-Block (unverändert) -->
  <div style="display: flex; flex-direction: column; gap: 6px; flex-grow: 1;">
    <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
      <strong style="font-size: 1rem; color: var(--text-main);">Breaking.Bad.S01E01</strong>
      <span style="font-size: 0.75em; padding: 2px 8px; border-radius: 12px;
                   background: rgba(139,92,246,0.15); color: #8b5cf6;">Serie</span>
      <span style="font-size: 0.8em; color: var(--text-muted);">1 Datei(en) · 4,1 GB · 03.10.2026</span>
    </div>
    <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-top: 4px;">
      <!-- reasons -->
    </div>
  </div>

  <!-- Bestehende Buttons (unverändert) -->
  <div style="display: flex; align-items: center; gap: 8px;">
    <button class="btn btn-danger btn-sm btn-delete-smart">Quarantäne</button>
    <button class="btn btn-select-smart">Auswählen</button>
  </div>
</div>
```

**Sammel-Knopf in eigener Leiste (erscheint nur bei ≥1 Auswahl):**

```html
<div id="smart-inbox-bulk-actions" role="toolbar"
     style="display: none; align-items: center; justify-content: space-between;
            gap: 12px; padding: 10px 14px; margin-bottom: 12px;
            background: rgba(0,229,255,0.05); border: 1px solid rgba(0,229,255,0.2);
            border-radius: 6px;">

  <div style="display: flex; align-items: center; gap: 10px;">
    <span id="smart-inbox-selection-count" style="font-size: 0.85em; color: var(--text-main); font-weight: 500;">
      3 Einträge ausgewählt
    </span>
  </div>

  <div style="display: flex; gap: 8px;">
    <button id="smart-inbox-clear-selection" class="btn btn-secondary btn-xs"
            style="padding: 4px 10px; font-size: 11px;">
      Auswahl aufheben
    </button>
    <button id="smart-inbox-group-selected" class="btn btn-primary btn-sm"
            style="padding: 6px 12px; font-size: 11px; font-weight: 500;">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
        <rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>
      </svg>
      Ausgewählte als Serie gruppieren
    </button>
  </div>
</div>
```

**Position im DOM (index.html, nach `#smart-inbox-sort-bar`, vor `#smart-inbox-list`):**

```html
<div id="smart-inbox-sort-bar" role="toolbar">...</div>

<!-- NEU: Bulk-Aktionsleiste -->
<div id="smart-inbox-bulk-actions" role="toolbar" style="display: none;">...</div>

<div id="smart-inbox-list" style="display: flex; flex-direction: column; gap: 12px;"></div>
```

**Begründung:**
- **Checkbox links** (nicht rechts bei den Buttons): Trennung von „Auswahl" und „Aktion". Präzedenz Gmail/Outlook: Checkbox links, Action-Buttons rechts.
- **Bulk-Leiste zwischen Sortier-Leiste und Liste** (nicht in der Sortier-Leiste selbst, nicht im Banner):
  - Sortier-Leiste ist für Sortierung — Aktions-Knopf würde die Affordanz verwässern.
  - Banner ist für Auto-Vorschläge — manueller Sammel-Knopf gehört nicht dort hin.
  - Eigene Leiste: klarer visueller Schnitt, erscheint nur bei Bedarf (keine permanente Belegung).
- **Präzedenzfälle:**
  - **Gmail (Konversationsansicht):** Checkbox links in jeder Zeile, Bulk-Aktionsleiste erscheint über der Liste bei Auswahl.
  - **Outlook (E-Mail-Liste):** Identisch — Checkbox links, „Löschen/Verschieben"-Leiste bei ≥1 Auswahl.
  - **macOS Finder (Listenansicht):** Checkbox links, Action-Buttons rechts.

---

## b) Verhältnis der drei Auswahl-Ebenen

### Empfehlung: **Klare Hierarchie mit Vorrang-Regeln, Mischzustände sichtbar aber nicht blockierend**

**Drei Ebenen:**

1. **Auto-Gruppe** (Banner bestätigt): Server hat `suggested_query` erkannt, Frontend zeigt Banner „Breaking Bad — 11 Folgen erkannt". Klick auf „Als Serie gruppieren" → alle 11 Einträge werden zur Gruppenzeile.
2. **Manuelle Checkbox-Auswahl**: Nutzer wählt 3–5 Einträge per Checkbox, klickt „Ausgewählte als Serie gruppieren".
3. **„Trotzdem freigeben"**: Film-Eintrag (media_type: „movie") wird per Ausnahme-Link ankreibar.

**Vorrang-Regeln:**

| Zustand | Verhalten |
|---------|-----------|
| **Eintrag ist Teil einer bestätigten Auto-Gruppe** | Checkbox ist **nicht einzeln ankreibar** — die ganze Gruppe wird als Einheit behandelt. Gruppenzeile hat stattdessen einen „Als Serie verarbeiten"-Button. |
| **Eintrag ist Teil eines Auto-Vorschlags (Banner noch nicht bestätigt)** | Checkbox ist **sichtbar aber deaktiviert** mit Tooltip „Auto-Vorschlag bestätigen oder ignorieren". Verhindert Mischzustände. |
| **Eintrag ist „trotzdem freigegebener" Film-Eintrag** | Checkbox ist **aktiv**, Eintrag kann mit anderen manuell gruppiert werden. Visueller Hinweis: Border-Farbe ändert sich leicht (siehe d). |
| **Manuell ausgewählte Einträge + Auto-Gruppe existieren parallel** | Erlaubt. Nutzer kann Auto-Gruppe ignorieren und stattdessen manuell auswählen. |

**Mischzustände und ihre Sichtbarkeit:**

```html
<!-- Auto-Gruppe (bereits bestätigt) — keine Einzel-Checkboxes -->
<div class="smart-inbox-group" aria-expanded="false">
  <div style="display: flex; align-items: center; gap: 12px;">
    <svg><!-- chevron --></svg>
    <strong>Breaking Bad</strong>
    <span style="font-size: 0.75em; padding: 2px 8px; border-radius: 12px;
                 background: rgba(139,92,246,0.15); color: #8b5cf6;">Serie</span>
    <span style="font-size: 0.8em; color: var(--text-muted);">11 Folgen</span>
  </div>
  <button class="btn btn-primary btn-sm">Als Serie verarbeiten</button>
</div>

<!-- Auto-Vorschlag (Banner noch nicht bestätigt) — Checkbox deaktiviert -->
<div class="smart-inbox-item" data-project="Better.Call.Saul.S01E01">
  <input type="checkbox" disabled
         title="Auto-Vorschlag bestätigen oder ignorieren"
         style="opacity: 0.4; cursor: not-allowed;">
  <div style="flex-grow: 1;">
    <strong>Better.Call.Saul.S01E01</strong>
    <!-- ... -->
  </div>
</div>

<!-- „Trotzdem freigegebener" Film-Eintrag — Checkbox aktiv, Border-Hinweis -->
<div class="smart-inbox-item" data-project="The.Rock.1996"
     style="border: 1px solid rgba(245,158,11,0.3);">
  <input type="checkbox" class="smart-inbox-checkbox"
         style="accent-color: #f59e0b;">
  <div style="flex-grow: 1;">
    <strong>The.Rock.1996</strong>
    <span style="font-size: 0.75em; padding: 2px 8px; border-radius: 12px;
                 background: rgba(59,130,246,0.15); color: #3b82f6;">Film</span>
    <span style="font-size: 0.75em; color: #f59e0b; margin-left: 6px;">
      ✓ Als Serie freigegeben
    </span>
  </div>
</div>
```

**Begründung:**
- **Auto-Gruppe hat Vorrang**: Wenn der Server eine Gruppe erkannt hat und der Nutzer bestätigt hat, ist die Gruppe eine Einheit. Einzelne Checkboxes würden die Kohärenz brechen.
- **Auto-Vorschlag (unbestätigt) sperrt Checkbox**: Verhindert, dass Nutzer Teile der vorgeschlagenen Gruppe manuell auswählen und damit den Auto-Vorschlag untergraben.
- **„Trotzdem freigegebener" Film-Eintrag ist sichtbar**: Border-Farbe (amber/orange) signalisiert „hier wurde eine Regel bewusst gebrochen". Kein Modal, kein Popup — dezent aber erkennbar.
- **Präzedenzfälle:**
  - **Google Photos (Alben):** Auto-erkannte Gesichter/Orte sind Gruppen, manuelle Auswahl ist parallel möglich.
  - **Apple Music (Playlists):** Auto-Playlists (z.B. „Neu gemischt") sind unveränderlich, manuelle Playlists sind editierbar.

---

## c) Zustände und Grenzen

### Empfehlung: **Pragmatische MVP-Lösung, komplexe Fälle als Nachzug dokumentieren**

| Fall | Lösung | Begründung |
|------|--------|------------|
| **Checkbox bei `isProcessing`** | `disabled` + `opacity: 0.5` + `cursor: not-allowed` | Konsistent mit Quarantäne-Button (app.js:12468). Verhindert Auswahl während Verarbeitung. |
| **„Alle auswählen" bei 264 Einträgen** | **NICHT in PR1**. Stattdessen: Bulk-Leiste hat nur „Auswahl aufheben" + „Als Serie gruppieren". | „Alle auswählen" bei 264 Einträgen wäre ein unbeabsichtigter Massen-Job. Nutzer soll bewusst einzeln auswählen. Nachzug: „Alle Serien-Einzeldateien auswählen"-Button als separater, expliziter Button (nicht Checkbox). |
| **Zähler „N ausgewählt"** | In der Bulk-Leiste: `<span id="smart-inbox-selection-count">3 Einträge ausgewählt</span>` | Sofortige Rückmeldung, kein Raten. |
| **Verhalten beim Re-Render (Auswahlverlust?)** | **sessionStorage für Auswahl** (Key: `smart-inbox-selection`, Value: JSON-Array von `data-project`). Bei Re-Render: Checkboxes werden wieder gesetzt. | Sortier-Leiste nutzt bereits sessionStorage (app.js:12309–12334). Konsistentes Pattern. Verhindert Frustration bei Sortier-Wechsel. |
| **Tastatur/Screenreader** | `<label>` um Checkbox oder `aria-label` auf Checkbox. `tabindex="0"` auf Checkbox. Enter/Space toggle. | WCAG 2.1 Level A. Checkbox ist interaktives Element, muss fokussierbar sein. |
| **Schmale Screens (<600px)** | Checkbox bleibt links (18×18px, `flex-shrink: 0`). Bulk-Leiste: `flex-direction: column`, Buttons untereinander. | Bestehende `flex-wrap: wrap`-Konvention (index.html:428) wird fortgeführt. |

**HTML-Skizze für Checkbox mit Label (a11y):**

```html
<label style="display: inline-flex; align-items: center; cursor: pointer;">
  <input type="checkbox" class="smart-inbox-checkbox"
         data-project="Breaking.Bad.S01E01"
         aria-label="Breaking Bad S01E01 zur Serien-Gruppierung auswählen"
         style="width: 18px; height: 18px; cursor: pointer; accent-color: var(--accent, #00e5ff);">
</label>
```

**JavaScript-Logik (skizziert, nicht implementiert):**

```javascript
// sessionStorage speichern/laden
function saveSmartInboxSelection() {
  const selected = Array.from(document.querySelectorAll('.smart-inbox-checkbox:checked'))
    .map(cb => cb.dataset.project);
  sessionStorage.setItem('smart-inbox-selection', JSON.stringify(selected));
  updateBulkActionBar();
}

function restoreSmartInboxSelection() {
  const saved = JSON.parse(sessionStorage.getItem('smart-inbox-selection') || '[]');
  document.querySelectorAll('.smart-inbox-checkbox').forEach(cb => {
    if (saved.includes(cb.dataset.project)) {
      cb.checked = true;
    }
  });
  updateBulkActionBar();
}

function updateBulkActionBar() {
  const count = document.querySelectorAll('.smart-inbox-checkbox:checked').length;
  const bulkBar = document.getElementById('smart-inbox-bulk-actions');
  const countSpan = document.getElementById('smart-inbox-selection-count');

  if (count > 0) {
    bulkBar.style.display = 'flex';
    countSpan.textContent = `${count} Einträge ausgewählt`;
  } else {
    bulkBar.style.display = 'none';
  }
}
```

---

## d) Ausweich-Link „Trotzdem als Serie freigeben"

### Empfehlung: **Inline-Link unter dem Button-Bereich, bewusste Entscheidung durch expliziten Klick**

**Position und Text:**

```html
<div class="smart-inbox-item" data-project="The.Rock.1996" data-media-type="movie">
  <!-- Content -->
  <div style="display: flex; flex-direction: column; gap: 6px; flex-grow: 1;">
    <div style="display: flex; align-items: center; gap: 10px;">
      <strong>The.Rock.1996</strong>
      <span style="font-size: 0.75em; padding: 2px 8px; border-radius: 12px;
                   background: rgba(59,130,246,0.15); color: #3b82f6;">Film</span>
    </div>
  </div>

  <!-- Buttons + Ausweich-Link -->
  <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 6px;">
    <div style="display: flex; gap: 8px;">
      <button class="btn btn-danger btn-sm btn-delete-smart">Quarantäne</button>
      <button class="btn btn-select-smart" disabled
              title="Filme können nicht als Serie verarbeitet werden">
        Auswählen
      </button>
    </div>

    <!-- Ausweich-Link -->
    <a href="#" class="force-series-exception-link"
       style="font-size: 0.75em; color: var(--text-muted); text-decoration: underline;
              cursor: pointer; transition: color 0.2s;"
       title="Diesen Film-Eintrag explizit für Serien-Gruppierung freigeben">
      Trotzdem als Serie freigeben
    </a>
  </div>
</div>
```

**Bestätigungscharakter:**

Der Link ist **unterstrichen** und in `var(--text-muted)` — nicht prominent, aber sichtbar. Klick öffnet **kein Modal**, sondern schaltet den Eintrag sofort um:

```javascript
// Skizziert, nicht implementiert
document.addEventListener('click', (e) => {
  if (e.target.classList.contains('force-series-exception-link')) {
    e.preventDefault();
    const item = e.target.closest('.smart-inbox-item');
    const project = item.dataset.project;

    // sessionStorage: freigegebene Filme
    const exceptions = JSON.parse(sessionStorage.getItem('series-exceptions') || '[]');
    if (!exceptions.includes(project)) {
      exceptions.push(project);
      sessionStorage.setItem('series-exceptions', JSON.stringify(exceptions));
    }

    // UI-Update: Checkbox erscheint, Border-Farbe ändert sich
    renderSmartInboxItemAsException(item);
  }
});
```

**Zustand nach Klick:**

```html
<!-- Nach Klick auf „Trotzdem als Serie freigeben" -->
<div class="smart-inbox-item" data-project="The.Rock.1996"
     style="border: 1px solid rgba(245,158,11,0.3); background: rgba(245,158,11,0.02);">

  <!-- Checkbox erscheint -->
  <input type="checkbox" class="smart-inbox-checkbox"
         style="accent-color: #f59e0b;">

  <div style="display: flex; flex-direction: column; gap: 6px; flex-grow: 1;">
    <div style="display: flex; align-items: center; gap: 10px;">
      <strong>The.Rock.1996</strong>
      <span style="font-size: 0.75em; padding: 2px 8px; border-radius: 12px;
                   background: rgba(59,130,246,0.15); color: #3b82f6;">Film</span>
      <!-- Neuer Hinweis -->
      <span style="font-size: 0.75em; color: #f59e0b; font-weight: 500;">
        ✓ Als Serie freigegeben
      </span>
    </div>
  </div>

  <!-- Buttons bleiben, aber „Auswählen" ist jetzt aktiv -->
  <div style="display: flex; gap: 8px;">
    <button class="btn btn-danger btn-sm btn-delete-smart">Quarantäne</button>
    <button class="btn btn-select-smart">Auswählen</button>
  </div>
</div>
```

**Begründung:**
- **Text „Trotzdem als Serie freigeben"**: Explizit, keine Abkürzung. Signalisiert „das ist die Ausnahme, nicht die Regel".
- **Position unter den Buttons**: Nicht im Weg, aber sichtbar. Nutzer muss aktiv nach unten schauen.
- **Kein Modal**: Bestätigung durch expliziten Klick auf den Link (nicht durch „Sind Sie sicher?"). Das ist bewusste Entscheidung, nicht Versehen.
- **Visueller Hinweis (Border + Badge)**: Amber/orange signalisiert „hier wurde eine Regel gebrochen". Konsistent mit Warning-Farben (siehe `--danger` in style.css).
- **sessionStorage**: Freigabe gilt für die Browser-Sitzung. Bei Reload bleibt sie erhalten.
- **Präzedenzfälle:**
  - **macOS (geschützte Dateien „trotzdem öffnen"):** Inline-Link, kein Modal.
  - **Figma (Read-only-Layer „Override"):** Inline-Link, sofortige Umschaltung.

---

## e) MVP-Abgrenzung: Was ist PR1-würdig?

### Empfehlung: **Fokus auf Kern-Flow, komplexe Fälle als ROADMAP dokumentieren**

**PR1-würdig (muss rein):**

| Feature | Begründung |
|---------|------------|
| **Checkbox pro Serien-Einzeldatei** | Kern-Feature. Ohne Checkbox keine manuelle Gruppierung. |
| **Bulk-Leiste mit Zähler + Sammel-Knopf** | Notwendig für UX. Nutzer muss sehen, was er ausgewählt hat. |
| **„Trotzdem als Serie freigeben" (pro Eintrag)** | Alex-Entscheidung „1–3 wie empfohlen". Ausnahme muss pro Eintrag funktionieren. |
| **Checkbox disabled bei `isProcessing`** | Konsistenz mit Quarantäne-Button. Verhindert Race-Conditions. |
| **sessionStorage für Auswahl** | Verhindert Frustration bei Sortier-Wechsel. Bestehendes Pattern (#64). |
| **Tastatur/Screenreader (Label, aria)** | WCAG 2.1 Level A. Nicht verhandelbar. |
| **Visueller Hinweis für „trotzdem freigegebener" Film-Eintrag** | Border-Farbe + Badge. Signalisiert Regel-Ausnahme. |

**NICHT PR1-würdig (ROADMAP):**

| Feature | Begründung |
|---------|------------|
| **„Alle auswählen" bei 264 Einträgen** | Risiko: unbeabsichtigter Massen-Job. Nachzug: expliziter Button „Alle Serien-Einzeldateien auswählen" (nicht Checkbox). |
| **Mischzustands-Visualisierung (Auto-Gruppe + manuelle Auswahl)** | Komplexität sprengt PR1. Regel: Auto-Gruppe hat Vorrang, Checkbox deaktiviert. Einfacher als alle Kombinationsfälle zu visualisieren. |
| **sessionStorage für „trotzdem freigegebener" Film-Einträge** | Kann später ergänzt werden. PR1: Freigabe gilt nur für aktuelle Session. |
| **Bulk-Leiste für Auto-Gruppen** | Auto-Gruppen haben eigenen „Als Serie verarbeiten"-Button. Bulk-Leiste ist nur für manuelle Auswahl. |
| **Komplexe Mischzustände (Film + Serie in einer manuellen Gruppe)** | Erlaubt, aber nicht explizit visualisiert. Nutzer sieht an den Badges, was er ausgewählt hat. |

**Begründung für Abgrenzung:**
- **PR1 muss funktionieren**: Checkbox + Sammel-Knopf + Ausnahme-Link sind der Kern-Flow. Alles andere ist Komfort.
- **Komplexität kontrollieren**: Mischzustände, „Alle auswählen", sessionStorage für Ausnahmen — das sind Edge-Cases, die PR1 nicht blockieren.
- **ROADMAP als Sicherheitsnetz**: Alles, was nicht in PR1 kommt, wird in ROADMAP.md dokumentiert (siehe ADR-65-6 für #68).

---

## Zusammenfassung der Empfehlungen

| Frage | Empfehlung | Trade-off/Risiko |
|-------|------------|------------------|
| **a) Positionierung** | Checkbox links vor Projektnamen, Bulk-Leiste zwischen Sortier-Leiste und Liste | Bulk-Leiste braucht ~50px Höhe — erscheint nur bei Auswahl |
| **b) Drei Ebenen** | Auto-Gruppe hat Vorrang, Auto-Vorschlag sperrt Checkbox, „trotzdem freigegebener" Film ist sichtbar (amber) | Mischzustände sind einfach geregelt, aber nicht alle Kombinationsfälle visualisiert |
| **c) Zustände/Grenzen** | Checkbox disabled bei `isProcessing`, kein „Alle auswählen" in PR1, sessionStorage für Auswahl, a11y mit Label/aria | „Alle auswählen" fehlt — Nachzug als expliziter Button |
| **d) Ausweich-Link** | Inline-Link unter Buttons, Text „Trotzdem als Serie freigeben", visueller Hinweis (amber Border + Badge) | Kein Modal — bewusste Entscheidung durch Klick, nicht durch Bestätigung |
| **e) MVP-Abgrenzung** | Kern-Flow (Checkbox + Bulk-Leiste + Ausnahme-Link) in PR1, komplexe Fälle in ROADMAP | Komfort-Features fehlen — aber Kern-Flow funktioniert |

**Alex-Entscheidung:** Welche Punkte sollen in PR1 umgesetzt werden? Empfehlung: Alle unter „PR1-würdig" — das ist der Kern-Flow. Alles andere kann später ergänzt werden.
</task_result>
</task>
