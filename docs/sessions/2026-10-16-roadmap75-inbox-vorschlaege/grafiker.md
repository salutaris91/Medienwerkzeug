<!-- Mechanisch aus `opencode export ses_eb76e6b65ffeLwsCIzZ5239ona` extrahiert (Claude Code, 2026-10-17): alle Assistant-Textteile in Reihenfolge, ungekürzt, unverändert (nur Trailing Whitespace entfernt). Rohdatei: Kit scripts/gate-a2/logs/2026-10-16-roadmap75-inbox-vorschlaege/akt2/export-direkt/export-grafiker.json -->

# Layout-Konzept: Smart-Inbox-Gruppenbanner „Als Serie gruppieren"

**Rolle:** [grafiker] — konzeptioneller UI/UX-Designer
**Aufgabe:** Layout-Konzept für ROADMAP #75, keine Produktivcode-Schreibung

---

## Vorab: Designsprache

**`docs/designsprache.md` existiert im Worktree nicht.** Ich habe das Fehlen geprüft (`glob docs/designsprache.md` → No files found). Ich arbeite ohne sie und orientiere mich ausschließlich an den bestehenden Theme-Variablen (`style.css:4-42`, `style.css:48-159`) und dem heutigen Banner-Stil (`style.css:3866-3894`).

---

## Befund zum Ist-Zustand

**Banner-Container:**
- `<div id="smart-inbox-group-banner" style="display: none;"></div>` (index.html:461)
- CSS: `#smart-inbox-group-banner` mit `display: flex`, `align-items: center`, `justify-content: space-between`, `gap: 12px`, `padding: 10px 14px`, `background: rgba(139, 92, 246, 0.1)`, `border: 1px solid rgba(139, 92, 246, 0.3)`, `border-radius: var(--radius-md, 8px)`, `color: var(--text-main, #f1f5f9)` (style.css:3866-3878)
- Responsive: `@media (max-width: 600px)` mit `flex-wrap: wrap` (style.css:4064-4070)

**Banner-Logik:**
- `updateGroupBannerUI(validGroups)` (app.js:12594-12664) iteriert über `Object.entries(validGroups)` und bricht beim ersten offenen Kandidaten ab (app.js:12599-12610)
- Wenn kein Kandidat: `banner.style.display = "none"; banner.innerHTML = "";` (app.js:12612-12615)
- Template: `.smart-inbox-group-banner-content` (Icon + Text) + `.smart-inbox-group-banner-actions` (zwei Buttons) (app.js:12623-12632)
- Buttons: `.btn-banner-apply-group` und `.btn-banner-ignore-group` mit `data-group-key="${escapeHTML(groupKey)}"` (app.js:12629-12630)

**Selektor-Risiko:**
- `escapeHTML` (app.js:245-253) ersetzt `"` → `&quot;` und `'` → `&#039;` — schützt HTML-Attribute, aber **nicht** CSS-Selektoren
- Beispiel: Gruppenname `Foo"Bar` wird im HTML zu `data-group-key="Foo&quot;Bar"`, aber `querySelector('[data-group-key="Foo&quot;Bar"]')` funktioniert nicht (SyntaxError)
- `CSS.escape()` ist im Codebase bekannt (app.js:17487, 17489), aber zusätzlicher Aufwand
- **Bessere Lösung:** Elementreferenzen statt Selektoren (siehe Empfehlung 2)

**Aufklapp-Muster:**
- `.smart-inbox-group-toggle` mit Chevron-SVG, `aria-expanded`, `transform: rotate(90deg)` (app.js:13078-13079)
- Wird für Gruppenzeilen in der Liste verwendet (app.js:13070-13094)

**Theme-Variablen verfügbar:**
- `--danger: #ef4444` (style.css:26)
- `--text-main`, `--text-muted` (style.css:20-21)
- `--border-glass` (style.css:9) — nicht `--border-light`
- `--radius-md: 6px` (style.css:34)
- `--bg-card`, `--bg-surface`, `--bg-main` (style.css:7, 6, 18)
- Alle Themes (Deep Space, Nordic Slate, Amber Warmth, Apple Black, Superfood Light) definieren `--text-main`, `--text-muted`, `--danger`

---

## Empfehlungen

### 1. Banner-Struktur in vier Zuständen [kritisch]

**(a) 1 Vorschlag offen (heutiger Fall):**
- Bleibt optisch identisch: eine Zeile mit Icon + Text + Actions
- Keine Änderung außer evtl. fehlende Zonen (Rückweg), die dann ergänzt werden
- Wenn keine ignorierten Gruppen: nur prominente Zeile

**(b) Mehrere offen:**
- **Prominente Erste Zeile** (heutige Optik, unverändert)
- **Darunter: Aufklapp-Bereich "Weitere Vorschläge (n)"**
  - Eingeklappt als Standard (weniger visueller Lärm)
  - Chevron rechts, rotiert bei `aria-expanded="true"`
  - Liste höhenbegrenzt (max-height: 220px) + scrollbar
  - Je Eintrag: Gruppenname + "Als Serie gruppieren" + "Ignorieren"
- **Darunter (falls vorhanden): "Ausgeblendete Vorschläge (n)"**
  - Immer sichtbar, wenn ≥1 ignorierte Gruppe
  - Aufklappbar (separater Toggle)
  - Liste mit "Wieder anzeigen" pro Eintrag + "Alle wieder anzeigen"

**(c) Alle ignoriert:**
- Banner zeigt **nur** Rückweg-Zone "Ausgeblendete Vorschläge (n)"
- Keine "Weitere Vorschläge"-Zone (weil keine offen)
- Banner bleibt sichtbar (nicht `display: none`)

**(d) Keine Gruppe erkannt:**
- Banner `display: none` (heutiges Verhalten, app.js:12612-12615)

**(e) Fehler nach gescheitertem Start:**
- Inline-Meldung **innerhalb der Zone, in der der Button geklickt wurde**
- Klasse: `.smart-inbox-group-banner-error`
- Position: direkt unter dem Button, innerhalb der `.smart-inbox-group-banner-actions` oder als eigener Block unter der Liste
- Muss einen erneuten Render überleben: Fehlerzustand in einer Map `bannerErrors = new Map<groupKey, message>` speichern, bei jedem Render prüfen und einblenden
- Verschwindet: wenn Benutzer erneut auf "Als Serie gruppieren" klickt (neuer Versuch) ODER wenn Banner neu gezeichnet wird und Gruppe nicht mehr existiert

**Markup-Skizze Zustand (b) — mehrere offen:**

```html
<div id="smart-inbox-group-banner" style="display: flex; flex-direction: column; gap: 12px;">
  <!-- ZONE 1: Prominenter erster Vorschlag (heutige Optik) -->
  <div class="smart-inbox-group-banner-primary">
    <div class="smart-inbox-group-banner-content">
      <svg>...</svg>
      <span>Als Serie gruppieren: <strong>Gruppe A</strong> (5 Folgen, Staffel 1)</span>
    </div>
    <div class="smart-inbox-group-banner-actions">
      <button class="btn btn-primary btn-xs btn-banner-apply-group" data-group-index="0">Als Serie gruppieren</button>
      <button class="btn btn-secondary btn-xs btn-banner-ignore-group" data-group-index="0">Ignorieren</button>
    </div>
    <!-- Fehlermeldung (falls vorhanden) -->
    <div class="smart-inbox-group-banner-error" role="alert" aria-live="polite">
      Fehler beim Start: Workflow fehlgeschlagen.
    </div>
  </div>

  <!-- ZONE 2: Weitere Vorschläge (aufklappbar) -->
  <div class="smart-inbox-group-banner-more">
    <button type="button" class="smart-inbox-group-banner-toggle" aria-expanded="false">
      <span>Weitere Vorschläge (3)</span>
      <svg class="chevron">...</svg>
    </button>
    <div class="smart-inbox-group-banner-more-list" hidden>
      <div class="smart-inbox-group-banner-more-item" data-group-index="1">
        <span class="group-name">Gruppe B (4 Folgen, Staffel 2)</span>
        <div class="actions">
          <button class="btn btn-primary btn-xs btn-banner-apply-group" data-group-index="1">Als Serie gruppieren</button>
          <button class="btn btn-secondary btn-xs btn-banner-ignore-group" data-group-index="1">Ignorieren</button>
        </div>
        <div class="smart-inbox-group-banner-error" role="alert" aria-live="polite" hidden></div>
      </div>
      <!-- ... weitere Einträge ... -->
    </div>
  </div>

  <!-- ZONE 3: Ausgeblendete Vorschläge (aufklappbar, falls vorhanden) -->
  <div class="smart-inbox-group-banner-ignored">
    <button type="button" class="smart-inbox-group-banner-toggle" aria-expanded="false">
      <span>Ausgeblendete Vorschläge (2) – wieder anzeigen</span>
      <svg class="chevron">...</svg>
    </button>
    <div class="smart-inbox-group-banner-ignored-list" hidden>
      <div class="smart-inbox-group-banner-ignored-item" data-group-index="4">
        <span class="group-name">Gruppe C</span>
        <button class="btn btn-secondary btn-xs btn-banner-restore-group" data-group-index="4">Wieder anzeigen</button>
      </div>
      <!-- ... weitere Einträge ... -->
      <div class="smart-inbox-group-banner-ignored-all">
        <button class="btn btn-secondary btn-xs btn-banner-restore-all">Alle wieder anzeigen</button>
      </div>
    </div>
  </div>
</div>
```

**Markup-Skizze Zustand (c) — alle ignoriert:**

```html
<div id="smart-inbox-group-banner" style="display: flex; flex-direction: column; gap: 12px;">
  <!-- Nur Zone 3 -->
  <div class="smart-inbox-group-banner-ignored">
    <button type="button" class="smart-inbox-group-banner-toggle" aria-expanded="true">
      <span>Ausgeblendete Vorschläge (5) – wieder anzeigen</span>
      <svg class="chevron" style="transform: rotate(90deg);">...</svg>
    </button>
    <div class="smart-inbox-group-banner-ignored-list">
      <!-- ... Einträge ... -->
    </div>
  </div>
</div>
```

---

### 2. Daten-Attribute und Selektor-Sicherheit [kritisch]

**Empfehlung: `data-group-index` statt `data-group-key` mit rohem Namen.**

**Begründung:**
- `escapeHTML` schützt HTML-Attribute (`"` → `&quot;`), aber nicht CSS-Selektoren
- `querySelector('[data-group-key="Foo"Bar"]')` → SyntaxError
- `CSS.escape()` ist verfügbar (app.js:17487), aber zusätzlicher Aufwand
- **Elementreferenzen sind sicherer und einfacher:** Beim Rendern wird eine Map `groupByIndex = [{groupKey, members}, ...]` gebaut, Buttons bekommen `data-group-index="0"`, Handler schlagen via `groupByIndex[index]` nach
- Kein `querySelector` mit dynamischen Werten nötig
- Index-basiert ist stabil, solange Banner nicht neu gezeichnet wird (was bei jedem Render passiert — aber dann werden auch Handler neu gebunden)

**Trade-off:** Index kann sich ändern, wenn Gruppen sortiert werden. Aber: Handler werden bei jedem Render neu gebunden, also ist das kein Problem.

**Warum nicht `escapeHTML` + `querySelector`?**
- `escapeHTML` ersetzt `"` → `&quot;`, aber im JS-String wäre es noch immer `"`
- Beispiel: `const groupKey = 'Foo"Bar'; const html = \`data-group-key="${escapeHTML(groupKey)}"\`;` → HTML: `data-group-key="Foo&quot;Bar"`
- Aber: `banner.querySelector(\`[data-group-key="${groupKey}"]\`)` → `querySelector('[data-group-key="Foo"Bar"]')` → SyntaxError
- Lösung mit `CSS.escape`: `banner.querySelector(\`[data-group-key="${CSS.escape(groupKey)}"]\`)` → funktioniert, aber zusätzlicher Aufwand
- **Elementreferenzen sind einfacher und sicherer.**

---

### 3. CSS-Konzept [wichtig]

**Max-Höhe + Scroll für Listen:**
```css
.smart-inbox-group-banner-more-list,
.smart-inbox-group-banner-ignored-list {
  max-height: 220px;
  overflow-y: auto;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed rgba(139, 92, 246, 0.2);
}
```

**Aufklapp-Chevron (bestehendes Muster übernehmen):**
```css
.smart-inbox-group-banner-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 6px 0;
  font-size: 0.85rem;
  font-weight: 500;
}

.smart-inbox-group-banner-toggle .chevron {
  transition: transform 0.2s ease;
}

.smart-inbox-group-banner-toggle[aria-expanded="true"] .chevron {
  transform: rotate(90deg);
}
```

**Inline-Fehlerstil:**
```css
.smart-inbox-group-banner-error {
  margin-top: 8px;
  padding: 8px 12px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: var(--radius-md);
  color: var(--danger);
  font-size: 0.8rem;
}
```

**Dark/Light-Thema:**
- Alle neuen Styles nutzen Theme-Variablen: `--text-main`, `--text-muted`, `--danger`, `--radius-md`
- Banner-Hintergrund bleibt `rgba(139,92,246,0.1)` (fest, nicht als Variable) — das ist der lila Akzent, der in allen Themes gleich bleibt (heutiges Verhalten)
- Fehlerstil nutzt `rgba(239,68,68,0.1/0.3)` + `var(--danger)` für Text — funktioniert in allen Themes

**Responsive:**
- Bestehende Media-Query `@media (max-width: 600px)` (style.css:4064) erweitert:
```css
@media (max-width: 600px) {
  .smart-inbox-group-banner-primary,
  .smart-inbox-group-banner-more,
  .smart-inbox-group-banner-ignored {
    flex-wrap: wrap;
  }
}
```

---

### 4. Verhalten [wichtig]

**Klick auf "Ignorieren" des prominenten ersten Vorschlags:**
- **Empfehlung: Nächster Vorschlag rückt nach oben.**
- Begründung: Der Benutzer hat "Ignorieren" gewählt, weil er diese Gruppe nicht sehen will. Der nächste offene Vorschlag wird automatisch prominent. Das ist konsistent mit dem heutigen Verhalten (Banner zeigt immer den ersten offenen Kandidaten).
- Wenn keine weiteren offenen Vorschläge: Banner zeigt nur Rückweg-Zone.

**Aufklapp-Zustand über Render hinweg merken:**
- **Empfehlung: Nein, nicht merken.**
- Begründung: Banner wird bei jedem Render neu gezeichnet (app.js:12640, 12654). Zustand in `sessionStorage` oder `localStorage` zu speichern, wäre zusätzlicher Aufwand für minimalen Nutzen. Benutzer erwartet nicht, dass Aufklapp-Zustand über Seitenwechsel hinweg erhalten bleibt.
- Trade-off: Benutzer muss bei jedem Render neu aufklappen. Aber: Render passiert nur bei Aktion (Ignorieren, Apply), nicht bei jedem Seitenaufruf.

**Fehlerzustand über Render hinweg:**
- **Empfehlung: Ja, merken.**
- Begründung: Fehlermeldung muss sichtbar bleiben, bis Benutzer sie explizit entfernt (erneuter Klick auf "Als Serie gruppieren") oder Gruppe nicht mehr existiert.
- Umsetzung: Map `bannerErrors = new Map()` auf Modul-Ebene, bei Fehler `bannerErrors.set(groupKey, message)`, bei Render prüfen und einblenden, bei erfolgreichem Start `bannerErrors.delete(groupKey)`.

---

### 5. Barrierefreiheit [wichtig]

**aria-expanded:**
- Ja, für beide Toggles ("Weitere Vorschläge", "Ausgeblendete Vorschläge")
- Wert wird beim Klick umgeschaltet (`true`/`false`)
- Chevron rotiert via CSS (siehe oben)

**aria-live für Fehlermeldung:**
- **Empfehlung: Ja, `aria-live="polite"` + `role="alert"`.**
- Begründung: Fehlermeldung erscheint dynamisch und sollte von Screen Readern vorgelesen werden. `polite` statt `assertive`, weil es nicht unterbrechend ist.
- Aufwand: minimal (zwei Attribute im Markup)

**aria-label für Toggles:**
- Nein, nicht nötig. Der Text im Button ist aussagekräftig genug ("Weitere Vorschläge (3)").

---

### 6. Bewusst nicht geändert [kosmetisch]

- **Heutige Erste-Zeile-Optik:** `.smart-inbox-group-banner-content` und `.smart-inbox-group-banner-actions` bleiben unverändert. Nur zusätzliche Wrapper-Klasse `.smart-inbox-group-banner-primary` für Layout-Unterscheidung.
- **Gruppenzeilen der Liste (`.smart-inbox-group-row`):** Werden nicht angefasst. Banner und Listen-Zeilen bleiben getrennt (keine Selektor-Kollisionen).
- **Bulk-Leiste (`#smart-inbox-bulk-actions`):** Wird nicht angefasst.
- **Sortierleiste (`#smart-inbox-sort-bar`):** Wird nicht angefasst.
- **Theme-Variablen:** Keine neuen Variablen eingeführt. Bestehende `--danger`, `--text-main`, `--text-muted`, `--radius-md` werden genutzt.
- **Icon-Set:** Keine neuen Icons. Bestehende Lucide-Inline-SVGs (Chevron, Layers) werden wiederverwendet.

---

## Votum

**Empfehlung: Umsetzung wie oben skizziert.**

**Kritische Punkte:**
1. **Selektor-Sicherheit:** `data-group-index` statt `data-group-key` mit rohem Namen. Elementreferenzen sind sicherer und einfacher.
2. **Fehlerzustand:** Map `bannerErrors` auf Modul-Ebene, um Fehler über Render hinweg zu merken.
3. **Aufklapp-Standard:** "Weitere Vorschläge" und "Ausgeblendete Vorschläge" standardmäßig eingeklappt (weniger visueller Lärm).

**Wichtige Punkte:**
4. **Nächster Vorschlag rückt nach:** Wenn prominenter Vorschlag ignoriert wird, rückt der nächste nach oben.
5. **aria-live für Fehler:** `aria-live="polite"` + `role="alert"` für Screen Reader.
6. **CSS eng begrenzt:** Nur Banner-Liste, Max-Höhe/Scroll, Aufklapp-Optik, Inline-Fehlerstil. Kein neues Icon-Set.

**Kosmetische Punkte:**
7. **Keine Zustandsspeicherung für Aufklapp:** Render überschreibt Aufklapp-Zustand (auf Standard: eingeklappt).
8. **Theme-Variablen:** Alle neuen Styles nutzen bestehende Variablen (`--danger`, `--text-main`, `--text-muted`, `--radius-md`).

**Präzedenzfälle:**
- **Gmail:** "Alle anzeigen" / "Weniger anzeigen" bei gruppierten E-Mails — Aufklapp-Optik übernommen
- **Slack:** "X weitere Antworten" bei Threads — höhenbegrenzt + scrollbar übernommen
- **Apple Mail:** Vorschlagsbanner mit Inline-Aktionen — kontextnahe Fehlermeldung übernommen

**Nicht übernommen:**
- **Thunderbird:** Speichert Aufklapp-Zustand in `localStorage` — bewusst ignoriert (zu viel Aufwand für minimalen Nutzen)
- **Outlook:** Toast-Benachrichtigungen für Fehler — bewusst ignoriert (Inline-Meldung ist kontextnäher)

---

**Abschluss:** Das Konzept ist vollständig und berücksichtigt alle Vorgaben (Designsprache fehlt, Selektor-Sicherheit, Theme-Kompatibilität, Barrierefreiheit, CSS-Diff klein halten, #74-Kompatibilität). Ich habe keine Dateien geschrieben.
