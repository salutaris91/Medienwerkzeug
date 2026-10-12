# Rohoutput grafiker — Kreativteam 2026-10-12 (Akt 2, Ordner-Folgen)
Hinweis Claude Code (2026-10-12): Mechanisch aus `opencode export ses_ed092b3e0ffe9iDPDyHyWFilqY` (ceo-planner, Akt 2) abgelegt, nicht vom Moderator abgeschrieben (Lehre 59). Einzige Änderung: Trailing Whitespace entfernt. Volle Daten: Kit `scripts/gate-a2/logs/2026-10-12-inbox-ordnerfolgen/export-ceo-planner-akt2.json`.

---

## grafiker: grafiker Ordner-Kästchen UI (Subagent-Sitzung ses_ed08fb8deffeyYHXeyZAlGXais, Status: completed)

<task id="ses_ed08fb8deffeyYHXeyZAlGXais" state="completed">
<task_result>
# Gestaltungskonzept — Akt 2: Einzelvideo-Ordner in der Smart Inbox

## Referenz-Patterns (Präzedenzfälle)

1. **Apple Finder (Liste mit Icons):** Ordner zeigen Ordner-Icon + Name, Dateien zeigen Datei-Icon + Name. Bei gemischten Selektionen bleibt die visuelle Hierarchie klar: Icon-Typ → Name → Meta-Info. *Übernommen:* Ordner-Icon als primärer visueller Anker.
2. **Jellyfin Serien-Bibliothek:** Gruppenzeilen zeigen Serienname + Badge "X Folgen", aufgeklappt sieht man Episodenliste mit SxxExx-Badge + Episodentitel. *Übernommen:* SxxExx-Badge in Monospace, aufgeklappte Mitgliederliste.
3. **Synology Download Station:** Bei Ordnern mit einer Datei zeigt der Tooltip "1 Video in Ordner" — der Nutzer sieht sofort, was verarbeitet wird. *Übernommen:* Explizite Kennzeichnung "1 Video" statt vager "1 Datei(en)".

---

## 1. Zeile eines Einzelvideo-ORDNER-Eintrags

**Konzept:** Die Zeile übernimmt die bestehende `.smart-inbox-item`-Struktur (`app.js:13147–13176`), ergänzt um drei visuelle Differentiatoren:

**Positionierung (von links nach rechts):**
```
[☑] [📁] [Ordnername] [Badge: "Serie"] [Badge: "1 Video"] [Meta: Größe · Datum] [Quarantäne] [Auswählen]
```

**Konkrete Änderungen:**

- **Checkbox** (`app.js:13130–13135`): Sitzt an erster Stelle (vor dem Icon), identisch zu Einzeldateien. `aria-label="Ordner mit einer Folge auswählen"` statt generisch "Auswählen für Serie".
- **Ordner-Icon:** Lucide `folder` (`app.js:2336` hat das SVG bereits), 14×14px, `color: var(--accent)`. Sitzt direkt nach der Checkbox, vor dem Namen. Bei Einzeldateien steht dort `lucide-video`.
- **Name:** Zeigt `item.project` (Ordnername), nicht den internen Dateinamen. Begründung: Der Nutzer sieht in der Inbox den Ordnernamen auf der Festplatte — Konsistenz mit der Finder-Ansicht.
- **Badge "1 Video":** Neues Badge nach dem Typ-Badge (Serie/Film/Doku). Text: `"1 Video"` (nicht "1 Datei(en)" wie bei `app.js:13109`). Style: `background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3);` (grün, analog zu Doku-Badge `app.js:13101`).
- **Tooltip/Hinweis:** `title="Verarbeitet wird: <single_video_relpath>"` auf der gesamten Zeile. Der Nutzer sieht auf Hover, welche Datei im Ordner verarbeitet wird (Transparenz).

**Code-Ansatzpunkt:** `app.js:13126` (Eligibility-Check) erweitern:
```javascript
const isTvSingleFolder = (item.media_type === "tv" && item.is_dir === true && item.video_count === 1 && item.single_video_relpath);
const isTvSingle = (item.media_type === "tv" && item.is_dir === false) || isTvSingleFolder;
```

**Visuelle Hierarchie:** Icon (Ordner vs. Datei) → Name (Ordnername vs. Dateiname) → Badge ("1 Video" vs. "1 Datei(en)"). Drei Ebenen der Differenzierung, ohne neue Farben einzuführen.

---

## 2. Gruppenzeile / gemischte Gruppe (lose Datei + Ordner)

**Konzept:** Die bestehende Gruppenzeile (`app.js:12976–13088`) bleibt strukturell unverändert. Nur die Mitgliederliste (`app.js:13019–13033`) muss zwischen Datei und Ordner unterscheiden.

**Aufgeklappte Mitgliederliste:**

| Mitglied-Typ | Icon | Name | SxxExx-Badge | Größe |
|--------------|------|------|--------------|-------|
| Lose Datei | `lucide-video` | Dateiname (`item.project`) | `S01E01` (aus `item._se`) | `1,2 GB` |
| Ordner (1 Video) | `lucide-folder` | Ordnername (`item.project`) + darunter Dateiname in `text-muted` | `S01E02` (aus `item._se`, extrahiert aus `single_video_query`) | `1,3 GB` |

**Konkrete Änderungen an `app.js:13019–13033`:**

```javascript
item.items.forEach(m => {
    const isFolder = m.is_dir === true;
    const icon = isFolder
        ? '<svg ... lucide-folder ...></svg>'
        : '<svg ... lucide-video ...></svg>';

    const nameHtml = isFolder
        ? `<span style="font-weight: 500;">${escapeHTML(m.project)}</span>
           <span style="font-size: 0.85em; color: var(--text-muted);">${escapeHTML(m.single_video_relpath)}</span>`
        : `<span style="font-weight: 500;">${escapeHTML(m.project)}</span>`;

    memberEl.innerHTML = `
        <div style="display: flex; align-items: center; gap: 8px; overflow: hidden;">
            ${icon}
            <span class="badge-season-episode">${m._se ? m._se.formatted : 'Folge'}</span>
            <div style="display: flex; flex-direction: column; gap: 2px;">
                ${nameHtml}
            </div>
        </div>
        <div style="font-size: 0.8em; color: var(--text-muted); flex-shrink: 0;">
            ${m.total_size ? formatBytes(m.total_size) : ''}
        </div>
    `;
});
```

**SxxExx-Badge für Ordner:** Wird aus `single_video_query` extrahiert (Server-Pipeline liefert bereits den bereinigten Query, Frontend ruft `extractStrictSeasonEpisode(item.single_video_query)` auf). Das Badge sitzt an identischer Position wie bei lose Dateien — visuelle Konsistenz.

**Aggregierte Metrik (Gruppenzeile):** `modified_at` = max aller Mitglieder, `total_size` = Summe. Bleibt unverändert (`app.js:12527–12535`).

---

## 3. Mehrvideo-Ordner (≥2 Videos)

**Empfehlung:** **Kein expliziter Hinweis** im UI.

**Begründung:**
- Mehrvideo-Ordner sind heute schon sichtbar (sie erscheinen in der Inbox mit `video_count: 3` o.ä.).
- Sie haben **kein Checkbox** (Eligibility-Check `app.js:13126` schlägt fehl).
- Ein Tooltip "Nicht wählbar, weil ≥2 Videos" wäre **überflüssige Erklärbarkeit** — der Nutzer sieht das Badge "3 Datei(en)" und versteht implizit: "Oh, der Ordner hat mehrere Videos, deshalb keine Checkbox."
- #71 (volles Aufklapp-UI) wird bewusst nicht gebaut — ein Hinweis "Aufklapp-UI fehlt" wäre technischer Jargon, kein Nutzer-Mehrwert.

**Dissens (falls Alex anderer Meinung):** Falls ein Hinweis gewünscht ist, Textvorschlag:
```
<span class="multi-video-notice" title="Ordner mit mehreren Videos — manuell auswählen">Mehrere Videos</span>
```
Style: `font-size: 0.75em; color: var(--text-muted); font-style: italic;` (dezent, nicht alarmierend).

---

## 4. Film-Ordner ohne SxxExx (F1 abgesagt)

**Zustand:** Bleibt **wie heute** — kein Checkbox, kein Badge "1 Video", keine Sonderbehandlung.

**Begründung für stillen Zustand:**
- Alex hat F1 explizit abgelehnt (Kickoff `docs/sessions/2026-10-12-inbox-ordnerfolgen/00-kickoff.md:80–85`).
- Der Server erkennt solche Ordner als `media_type: "movie"` (`project_api.py:1417–1432`).
- Das Frontend zeigt den Film-Badge "Film erkannt" (`app.js:13093–13095`).
- Die Film-Sperre (`app.js:13139–13145`) greift: "Film (für Serie gesperrt)" + "Als Serie / Folge behandeln"-Link.
- **Kein Widerspruch:** Der Nutzer kann den Film-Ordner per "Als Serie / Folge behandeln" entsperren (bestehender Flow). Eine zusätzliche Kennzeichnung "Ordner mit 1 Video" wäre redundant — der Film-Lock ist bereits das sichtbare Signal.

**Akzeptanz:** Ja, stiller Zustand reicht. Der Nutzer sieht: Ordner-Icon + "Film erkannt" + "Film (für Serie gesperrt)" — das ist hinreichend klar.

---

## 5. Zustände: Auswahl-Set, isProcessing-Guard, Render-Überleben

**Empfehlung:** Schlüssel im `selectedInboxProjects`-Set ist **`item.project`** (Ordnername bei Ordnern, Dateiname bei Dateien).

**Begründung:**
- `selectedInboxProjects` ist ein `Set<string>` (`app.js:12470`), das aktuell `item.project` speichert (`app.js:13196`).
- Bei Ordnern ist `item.project` der Ordnername (z.B. "ThWaDeS11E23").
- Bei Dateien ist `item.project` der Dateiname (z.B. "The.Walking.Dead.S01E01.mkv").
- **Keine Doppel-Nennung:** Ein Ordner und eine Datei können nicht denselben `project`-Wert haben (der Server liefert entweder Ordner oder Datei, nie beides mit identischem Namen — `project_api.py:1315–1346`).

**Fehlerquelle:** Falls der Nutzer **denselben Namen** für einen Ordner und eine Datei verwendet (extrem unwahrscheinlich, aber technisch möglich), kollidiert das Set. **Abhilfe:** Nicht nötig — der Server verhindert diese Kollision nicht explizit, aber in der Praxis tritt sie nicht auf (Inbox-Struktur: entweder `ThWaDeS11E23/` oder `ThWaDeS11E23.mkv`, nie beides).

**isProcessing-Guard:**
- `app.js:13121` prüft `processingSet.has(item.project)`.
- Bei Ordnern: `processingSet` enthält den Ordnernamen (Server verarbeitet den Ordner als Ganzes, `processor.py:870–884`).
- Checkbox wird disabled (`app.js:13133`), visuelle Rückmeldung: `opacity: 0.5; cursor: not-allowed`.
- **Funktioniert für Ordner identisch wie für Dateien** — keine Sonderbehandlung nötig.

**Render/Sortier-Wechsel:**
- `selectedInboxProjects` ist DOM-unabhängig (globales Set, `app.js:12470`).
- `renderSmartInboxList` (`app.js:12952`) liest das Set beim Rendern (`app.js:13132`: `selectedInboxProjects.has(item.project)`).
- **Überlebt Sortier-Wechsel** (sessionStorage-basiert, `app.js:12964–12966`) und Re-Renders (z.B. nach "Ignorieren" einer Gruppe, `app.js:12615`).

**Zähler (Bulk-Leiste):**
- `app.js:12666`: `const count = selectedInboxProjects.size;`
- Text: `"${count} ausgewählt"` (`app.js:12671`).
- **Funktioniert für gemischte Selektion** (Dateien + Ordner) ohne Änderung — das Set zählt Elemente, nicht Typen.

---

## 6. Manuell-Modus-Fallback-Gruppenname (B4 im Kickoff)

**Szenario:** Nutzer wählt 3 Dateien + 2 Ordner per Checkbox → Bulk-Leiste → "Ausgewählte als Serie verarbeiten" → Modal öffnet sich mit leerem Titel → Fallback-Gruppenname wird berechnet.

**Bestehende Logik (`app.js:12706–12708`):**
```javascript
const firstItem = currentSmartInboxRawSuggestions.find(s => s.project === files[0]);
const fallbackName = firstItem ? (firstItem.suggested_query || cleanSeriesName(firstItem.project)) : cleanSeriesName(files[0]);
const groupName = detectManualGroupSeriesName(files, fallbackName);
```

**Problem bei Ordnern:**
- `files[0]` kann ein Ordnername sein (z.B. "ThWaDeS11E23").
- `firstItem.suggested_query` kommt vom Server (`project_api.py:1496`) — bei Ordnern ist das der **Ordnername** (nicht der Dateiname).
- `detectManualGroupSeriesName` (`app.js:12641–12661`) extrahiert Common-Prefix aus den Dateinamen — bei Ordnernamen funktioniert das nicht korrekt (Kickoff B4: "ThWaDeS" statt "The Walking Dead").

**Lösung:** Server liefert additiv `single_video_query` für Ordner (Kickoff Entscheidung 2). Das Frontend nutzt **diesen Wert** statt `suggested_query`:

```javascript
const firstItem = currentSmartInboxRawSuggestions.find(s => s.project === files[0]);
const fallbackName = firstItem
    ? (firstItem.single_video_query || firstItem.suggested_query || cleanSeriesName(firstItem.project))
    : cleanSeriesName(files[0]);
```

**Nutzer sieht im Modal:**
- **Titel-Feld:** `"The.Walking.Dead"` (bereinigt durch `clean_show_name`, `project_api.py:1438–1440`).
- **Provider-Suche:** TMDB/TVDB findet "The Walking Dead" → Nutzer wählt Treffer → `show_name` wird überschrieben (`app.js:3280–3283`).
- **Fallback (kein Provider-Treffer):** `"The.Walking.Dead"` bleibt als manueller Name.

**Visuell im Modal:** Keine Änderung — das Modal zeigt das Titel-Feld wie heute. Der Nutzer merkt nicht, dass der Fallback-Name jetzt aus `single_video_query` kommt (Transparenz statt Komplexität).

---

## 7. Barrierefreiheit / Interaktion

**Klickziel Checkbox vs. Zeile:**
- **Heute:** Klick auf Zeile öffnet Projekt (`app.js:13178–13179`: `configureSmartInboxButton`).
- **Checkbox:** Separates Klickziel (`app.js:13192–13202`: `cb.addEventListener("change")`).
- **Empfehlung:** **Keine Änderung.** Checkbox ist kleines, präzises Klickziel (16×16px, `style.css:3923–3929`). Zeilen-Klick öffnet Projekt (bestehendes Verhalten). Nutzer versteht: Checkbox = Selektion, Zeilen-Klick = Details.
- **Riskant:** Klick auf Zeile → Checkbox togglen? Würde das Projekt-Öffnen brechen. **Nicht umsetzen.**

**aria-Labels:**
- **Checkbox (Datei):** `aria-label="Auswählen für Serie"` (`app.js:13134`).
- **Checkbox (Ordner):** `aria-label="Ordner mit einer Folge auswählen"` (siehe Punkt 1).
- **Gruppenzeile:** `aria-label="Seriengruppe: ${groupKey}"` (bereits vorhanden, `app.js:13001`).
- **Toggle-Button (Aufklappen):** `aria-expanded="true/false"` (bereits vorhanden, `app.js:13001`).

**Tastatur-Navigation:**
- Checkbox ist fokussierbar (Tab-Reihenfolge).
- `focus-visible` style vorhanden (`style.css:3936–3939`).
- Toggle-Button unterstützt Enter/Space (`app.js:13057–13062`).
- **Keine Änderung nötig** — bestehende Barrierefreiheit reicht.

---

## Was ich bewusst NICHT gestalte (Scope-Enge)

1. **#71 Aufklapp-UI für Mehrvideo-Ordner:** Wird explizit nicht gebaut (Kickoff Scope).
2. **Ordner-Aufräumen nach Verarbeitung:** Server-Realität (`processor.py:1084–1091`), aber kein UI-Feedback nötig — der Eintrag verschwindet einfach (video_count 0 → `continue`, `project_api.py:1345–1346`).
3. **F1 Typ-Erkennung für Film-Ordner:** Alex hat abgelehnt (Kickoff `00-kickoff.md:80–85`).
4. **Neue CSS-Klassen für Ordner-Badges:** Ich empfehle, bestehende Klassen wiederverwenden (`.badge-season-episode`, `.smart-inbox-cb`). Nur das "1 Video"-Badge ist neu — aber es kann inline gestylt werden (analog zu Typ-Badges `app.js:13094–13104`).
5. **Server-seitige Änderungen:** Ich gestalte nur das Frontend. Die additiven Felder `single_video_relpath`/`single_video_query` müssen im Server gebaut werden (Kickoff Entscheidung 2), aber das ist nicht Teil dieses Gestaltungsauftrags.

---

## Risiken / Dissens

1. **Verwirrung Ordner vs. Datei:**
   - **Risiko:** Nutzer sieht "ThWaDeS11E23" (Ordnername) und "The.Walking.Dead.S01E01.mkv" (Dateiname) in derselben Gruppe — versteht nicht, warum die Namen unterschiedlich sind.
   - **Abhilfe:** Tooltip auf der Gruppenzeile: `"Gruppe basiert auf Dateinamen"` (dezent, nur bei Hover).
   - **Dissens:** Falls Alex die Tooltip-Idee ablehnt → stiller Zustand. Der Nutzer lernt: "Gruppe = Dateinamen-basiert" aus der Dokumentation.

2. **Doppel-Nennung im Set (theoretisch):**
   - **Risiko:** Ordner "X" und Datei "X" in derselben Inbox → `selectedInboxProjects` kann nicht unterscheiden.
   - **Abhilfe:** Nicht nötig — extrem unwahrscheinlich, Server verhindert es nicht explizit, aber Praxis zeigt: tritt nicht auf.
   - **Falls Alex skeptisch:** Schlüssel ändern auf `${item.is_dir ? 'folder:' : 'file:'}${item.project}`. Aber das bricht Abwärtskompatibilität (bestehende Set-Einträge sind nur `item.project`). **Empfehlung:** Nicht umsetzen, Risiko akzeptieren.

3. **Badge "1 Video" redundant?**
   - **Risiko:** Nutzer sieht "1 Video" und denkt: "Ja, klar, sehe ich doch."
   - **Abhilfe:** Badge trotzdem zeigen — es ist die **Bestätigung**, dass der Ordner wählbar ist (Affordanz). Ohne Badge: Nutzer wundert sich, warum der Ordner eine Checkbox hat.
   - **Dissens:** Falls Alex das Badge ablehnt → entfernen, aber Tooltip "1 Video im Ordner" beibehalten.

---

## Konkrete Textvorschläge (Deutsch)

| Kontext | Text | Stil |
|---------|------|------|
| Badge (Einzelvideo-Ordner) | `"1 Video"` | Grün, analog zu Doku-Badge |
| Tooltip (Zeile) | `"Verarbeitet wird: <single_video_relpath>"` | `title`-Attribut |
| aria-label (Checkbox, Ordner) | `"Ordner mit einer Folge auswählen"` | Accessibility |
| aria-label (Checkbox, Datei) | `"Auswählen für Serie"` | Bestehend, unverändert |
| Mitgliederliste (Ordner) | Ordnername + darunter Dateiname in `text-muted` | Zweizeilig |
| Fehlerfall (kein `single_video_relpath`) | `"Ordner (Datei nicht identifiziert)"` | Roter Text, nur bei Server-Fehler |

---

## Zusammenfassung

**Kernprinzip:** Ordner-Einträge verhalten sich **identisch zu Datei-Einträgen** — gleiche Checkbox-Position, gleiche Gruppen-Logik, gleiche Bulk-Leiste. Einziger Unterschied: **Ordner-Icon + "1 Video"-Badge + Tooltip mit Dateiname**. Diese Minimale Differenzierung reicht, um Verwirrung zu vermeiden, ohne neue UI-Paradigmen einzuführen.

**Nicht gestaltet:** Aufklapp-UI (#71), Typ-Erkennung (F1), Ordner-Aufräumen, Server-Änderungen. Alles außerhalb des Scope.

**Risiken:** Theoretische Set-Kollision (akzeptiert), Badge-Redundanz (akzeptiert), Namens-Verwirrung (Tooltip als Abhilfe).
</task_result>
</task>
