# Rohoutput grafiker — Kreativteam-Session 2026-10-08 (Akt 3, #65)
Hinweis Claude Code (2026-10-08): Mechanisch aus `opencode export ses_ee533a3c8ffesW6v133rMvr61E` (ceo-planner) abgelegt, nur Aufrufe ab dem Akt-3-Auftrag, nicht vom Moderator abgeschrieben (Lehre 59). Einzige Änderung: Trailing Whitespace am Zeilenende entfernt (Pre-Commit-Hook). Volle Prompts und Antworten: Kit `scripts/gate-a2/logs/2026-10-08-roadmap64-65/export-ceo-planner-akt3.json`.

---

## grafiker zu #65 Gruppen-UI (Subagent-Sitzung ses_ee501f9aaffeds9DMq7aBKGIwF, Status: error)

Kein Output. Fehler (wörtlich): Subagent failed (task_id: ses_ee501f9aaffeds9DMq7aBKGIwF): The user rejected permission to use this specific tool call.
Ursache laut stderr: Berechtigungsanfrage `external_directory` headless auto-abgelehnt; der ceo-planner hat den Auftrag danach wiederholt (nächster Abschnitt).

---

## grafiker zu #65 (Wiederholung) (Subagent-Sitzung ses_ee4fe3d32ffeDDWIRs1tqrJERT, Status: completed)

<task id="ses_ee4fe3d32ffeDDWIRs1tqrJERT" state="completed">
<task_result>
# ROADMAP #65: „Als Serie gruppieren" — Konzeptionelle Empfehlungen

> **Bezugsgrundlage:** `docs/designsprache.md` existiert nicht (Bestätigung aus Session 2026-10-08). Konzeption bezieht sich auf Theme-Variablen (`--text-main`, `--text-muted`, `--border-light`, `--accent`) und Inline-Style-Konvention aus `app.js:12278–12303`.

---

## 1. Gruppenzeile — Aufbau & Interaktion

**Empfehlung:** Kompakte Flex-Zeile mit Chevron-Icon, Serienname, Folge-Anzahl, aggregierte Meta. Klick auf gesamte Zeile öffnet Mitgliederliste.

```html
<div class="smart-inbox-group" role="button" aria-expanded="false" tabindex="0"
     style="background: rgba(255,255,255,0.02); border: 1px solid var(--border-light);
            border-radius: 8px; padding: 14px 18px; cursor: pointer; transition: all 0.2s;">
  <div style="display: flex; align-items: center; gap: 12px; flex-grow: 1;">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         stroke-width="2" style="transition: transform 0.2s; flex-shrink: 0;">
      <polyline points="9 18 15 12 9 6"/>
    </svg>
    <div style="display: flex; flex-direction: column; gap: 4px; flex-grow: 1;">
      <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
        <strong style="font-size: 1rem; color: var(--text-main);">Breaking Bad</strong>
        <span style="font-size: 0.75em; padding: 2px 8px; border-radius: 12px;
                     background: rgba(59,130,246,0.15); color: #3b82f6; font-weight: 500;">
          Serie
        </span>
        <span style="font-size: 0.8em; color: var(--text-muted);">11 Folgen</span>
      </div>
      <div style="font-size: 0.8em; color: var(--text-muted);">
        45,2 GB · 03.10.2026
      </div>
    </div>
  </div>
</div>
```

**Interaktion:**
- Chevron rotiert 90° bei `aria-expanded="true"` (CSS `transform: rotate(90deg)`)
- Klick auf Zeile toggle, Enter/Space via Keyboard
- Mitgliederliste direkt unterhalb (kein Overlay)

**Präzedenzfälle:**
| App | Übernommen | Ignoriert |
|-----|------------|-----------|
| **macOS Finder (Liste mit Pfeilen)** | Chevron links, Klick auf Zeile öffnet Unterelemente | Finder nutzt Baumstruktur — wir haben flache Liste mit virtuellen Gruppen |
| **Gmail (Konversationsansicht)** | Kompakte Zeile mit Anzahl-Badge, Klick öffnet Details | Gmail zeigt Preview-Text — wir zeigen aggregierte Meta |
| **Spotify (Album-Tracks)** | Chevron + Titel + Dauer, einklappbar | Spotify nutzt Tabelle — wir nutzen Cards |

---

## 2. Mitglieder-Ansicht — Staffel-Zwischenüberschriften

**Empfehlung PR1:** **Keine** Staffel-Zwischenüberschriften. Folgen sortiert nach `SxxExx` numerisch (S01E01, S01E02, … S05E12). Staffel-Badge pro Zeile.

**Begründung:** 264 Folgen = ~5–11 Staffeln. Zwischenüberschriften erzeugen visuelles Rauschen und vertikale Verschwendung. Das Staffel-Badge pro Folge reicht für Orientierung.

```html
<div class="smart-inbox-group-members" style="margin-top: 8px; padding-left: 28px;
                                                border-left: 2px solid var(--border-light);">
  <div class="smart-inbox-item" style="padding: 10px 14px; display: flex; align-items: center;
                                        gap: 12px; background: rgba(255,255,255,0.01);
                                        border-radius: 6px; margin-bottom: 6px;">
    <span style="font-size: 0.75em; padding: 2px 6px; border-radius: 4px;
                 background: rgba(255,255,255,0.05); color: var(--text-muted); font-weight: 500;">
      S01E01
    </span>
    <span style="font-size: 0.9em; color: var(--text-main); flex-grow: 1;">
      Breaking.Bad.S01E01.720p.mkv
    </span>
    <span style="font-size: 0.8em; color: var(--text-muted);">4,1 GB</span>
  </div>
  <!-- weitere Folgen -->
</div>
```

**Präzedenzfälle:**
| App | Übernommen | Ignoriert |
|-----|------------|-----------|
| **Plex (Staffel-Ansicht)** | Episoden-Liste mit Staffel-Badge, keine Zwischenüberschriften | Plex nutzt Grid-Layout — wir nutzen Liste |
| **Sonarr (Queue)** | Flache Liste mit SxxExx-Badge, numerisch sortiert | Sonarr zeigt Cover-Art — wir haben keine Thumbnails |

---

## 3. Vorschlagskarte „Als Serie gruppieren"

**Empfehlung:** Info-Banner **über** der Sortier-Leiste (index.html:461), nur wenn Auto-Vorschlag vorliegt. Kein Modal, kein Overlay — dezent aber sichtbar.

```html
<div id="smart-inbox-group-suggestion" role="alert"
     style="background: rgba(59,130,246,0.08); border: 1px solid rgba(59,130,246,0.3);
            border-radius: 8px; padding: 12px 16px; margin-bottom: 12px;
            display: flex; align-items: center; justify-content: space-between; gap: 12px;">
  <div style="display: flex; align-items: center; gap: 10px;">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2">
      <rect x="2" y="3" width="20" height="15" rx="2"/>
      <path d="M12 18v4M8 21l8-3"/>
    </svg>
    <div>
      <strong style="font-size: 0.9em; color: var(--text-main);">Breaking Bad</strong>
      <span style="font-size: 0.8em; color: var(--text-muted); margin-left: 6px;">
        11 Folgen erkannt · 5 Staffeln
      </span>
    </div>
  </div>
  <div style="display: flex; gap: 8px;">
    <button class="btn btn-secondary btn-sm" style="padding: 6px 12px; font-size: 11px;">
      Ignorieren
    </button>
    <button class="btn btn-primary btn-sm" style="padding: 6px 12px; font-size: 11px;">
      Als Serie gruppieren
    </button>
  </div>
</div>
```

**Präzedenzfälle:**
| App | Übernommen | Ignoriert |
|-----|------------|-----------|
| **GitHub (Dependabot-Alerts)** | Info-Banner über Liste mit Action-Buttons | GitHub nutzt gelb/warning — wir nutzen blau/info (kein Risiko) |
| **VS Code (Extension-Empfehlungen)** | Dezent aber sichtbar, Bestätigung erforderlich | VS Code nutzt Toast — wir nutzen statischen Banner (persistent bis Aktion) |

---

## 4. Gesperrte Film-Einträge

**Empfehlung:** Tooltip + deaktivierter Button „Als Serie gruppieren" mit Hinweis. Ausnahme-Link darunter (unterstrichen, `var(--text-muted)`).

```html
<div class="smart-inbox-item" style="opacity: 0.6;">
  <!-- normale Item-Struktur -->
  <button disabled title="Filme können nicht gruppiert werden"
          style="padding: 6px 10px; font-size: 11px; opacity: 0.5; cursor: not-allowed;">
    Als Serie gruppieren
  </button>
  <a href="#" class="force-group-link" style="font-size: 0.75em; color: var(--text-muted);
                                              text-decoration: underline; margin-top: 4px;
                                              display: block;">
    Trotzdem als Serie freigeben
  </a>
</div>
```

**Präzedenzfälle:**
| App | Übernommen | Ignoriert |
|-----|------------|-----------|
| **macOS (geschützte Dateien)** | Deaktivierter Button + Tooltip bei Hover | macOS zeigt Schloss-Icon — wir nutzen Text-Tooltip |
| **Figma (Read-only-Layer)** | Deaktiviert + „Override"-Link | Figma nutzt Modal — wir nutzen Inline-Link (weniger Interruption) |

---

## 5. Vorschau-Modal (~264 Zeilen)

**Empfehlung PR1:** **Keine** einklappbaren Staffeln. Modal zeigt alle Folgen in flacher Liste mit Scroll. Checkbox „Alle auswählen" fixiert oben.

**Begründung:** 264 Zeilen = ~800px Höhe. Virtual Scrolling ist Overkill (kein Lazy-Loading nötig). Staffel-Collapsible erhöht Komplexität ohne messbaren UX-Gewinn.

```html
<div style="max-height: 60vh; overflow-y: auto; border: 1px solid var(--border-light);
            border-radius: 6px; padding: 8px;">
  <label style="display: flex; align-items: center; gap: 8px; padding: 8px;
                border-bottom: 1px solid var(--border-light); margin-bottom: 8px;
                font-weight: 600; color: var(--text-main);">
    <input type="checkbox" id="select-all-episodes">
    Alle auswählen (264)
  </label>
  <!-- Folgen-Liste -->
</div>
```

**Präzedenzfälle:**
| App | Übernommen | Ignoriert |
|-----|------------|-----------|
| **Dropbox (Datei-Auswahl)** | Scrollbare Liste + „Alle auswählen"-Checkbox | Dropbox nutzt Virtual Scrolling bei >1000 Dateien — bei 264 nicht nötig |
| **Google Drive (Auswahl-Dialog)** | Flache Liste mit Checkboxen, Scroll | Google Drive nutzt Thumbnails — wir haben keine Preview |

---

## 6. Edge Cases

| Fall | Lösung |
|------|--------|
| **Gruppe mit 1 Folge** | Nicht gruppieren. Auto-Vorschlag nur bei ≥2 Folgen. |
| **Lange Serienamen** | `word-break: break-word; overflow-wrap: break-word;` am `<strong>` (siehe #64-Empfehlung). |
| **Gemischte Inbox (Ordner + Einzeldateien)** | Server-seitige Deduplizierung: Wenn Ordner „Breaking Bad" + Einzeldateien „Breaking Bad S01E01" → Ordner hat Priorität, Einzeldateien werden ignoriert (kein doppelter Vorschlag). |
| **Schmale Bildschirme (<600px)** | Gruppenzeile: Chevron + Name + Badge in Zeile 1, Meta + Buttons in Zeile 2 (`flex-wrap: wrap`). Mitgliederliste: `padding-left: 0` (kein Einzug). |

---

## Entscheidungsvorlage

| Aspekt | Empfehlung | Trade-off/Risiko |
|--------|------------|------------------|
| **Gruppenzeile** | Chevron + Serie-Name + Badge + Meta, Klick auf Zeile toggle | Chevron-Icon braucht 16×16px — minimaler Platzverbrauch |
| **Mitglieder-Ansicht** | Flache Liste, SxxExx-Badge, keine Staffel-Überschriften | Bei >10 Staffeln unübersichtlich — aber PR1-MVP |
| **Vorschlagskarte** | Info-Banner über Sortier-Leiste, blau, Bestätigung erforderlich | Banner braucht ~60px Höhe — vertikal teuer bei leerer Inbox |
| **Film-Sperre** | Deaktivierter Button + Tooltip + „Trotzdem freigeben"-Link | Ausnahme-Link könnte übersehen werden — aber gewollt dezent |
| **Vorschau-Modal** | Flache Liste, Scroll, „Alle auswählen"-Checkbox | Bei 264 Folgen ~800px Höhe — akzeptabel, kein Virtual Scrolling |
| **Edge Cases** | ≥2 Folgen für Auto-Vorschlag, `word-break`, Server-Dedup, `flex-wrap` | Gemischte Inbox braucht Server-Logik — Backend-Aufwand |

**Alex-Entscheidung:** Welche Punkte sollen in PR1 umgesetzt werden? Empfehlung: Alle außer Staffel-Zwischenüberschriften (Punkt 2) und Virtual Scrolling (Punkt 5) — beides kann später ergänzt werden.
</task_result>
</task>
