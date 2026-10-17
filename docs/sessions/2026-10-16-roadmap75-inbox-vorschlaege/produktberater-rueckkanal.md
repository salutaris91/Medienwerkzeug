<!-- Mechanisch aus `opencode export ses_eb48dde5dfferQ4YLeD4UC00RF` extrahiert (Claude Code, 2026-10-17, Rückkanal): alle Assistant-Textteile in Reihenfolge, ungekürzt, unverändert (nur Trailing Whitespace entfernt). Rohdatei: Kit scripts/gate-a2/logs/2026-10-16-roadmap75-inbox-vorschlaege/rueckkanal/export-direkt/export-produktberater.json -->

# Produktberatung: ROADMAP #75 — Inbox-Gruppen-Banner

## 1. BEDIENTAUGLICHKEIT: Eingeklappte Zonen nach jedem Render

**Position: Akzeptabel für den Realbetrieb (1–3 Gruppen), aber mit einer Nuance.**

Der Code zeigt: Nach jedem `renderSmartInboxList`-Aufruf (also nach jedem Ignorieren/Wiederanzeigen) werden beide Zonen zwangsweise eingeklappt (`app.js:12777`, `:12791`). Das Briefing Abschnitt 4 hat "merkenden Aufklapp-Zustand" und "Auto-Aufklappen ab n ≥ 3" bewusst verworfen.

**Für den Hauptuse-case (1–3 Gruppen) ist das tragbar**, weil:
- Zone 1 (prominenter Vorschlag) immer sichtbar ist — das ist der Hauptarbeitspfad
- Zone 2 wird nur bei ≥2 offenen Gruppen relevant, und dann sind es meist 1–2 Einträge
- Der Nutzer hat ein klares mentales Modell: "Ich muss die Liste aufklappen, um weitere zu sehen"

**Aber: Bei sequentiellem Ignorieren in Zone 2 ist es Reibung.** Wenn der Nutzer in Zone 2 drei Gruppen nacheinander ignoriert, muss er Zone 2 drei Mal wieder aufklappen. Das sind 3 zusätzliche Klicks.

**Meine Position gegen das Briefing:** Ich würde eine **minimale Verbesserung** vorschlagen, die NICHT "merkender Aufklapp-Zustand über Reload" ist, sondern **nur innerhalb der aktuellen Session**: Wenn der Nutzer in Zone 2 einen Ignorieren-Klick macht, könnte man die Zone 2 offen lassen (nicht komplett neu rendern mit Einklappen, sondern nur das eine Element entfernen). Das wäre eine eng begrenzte Änderung, die die Reibung nimmt, ohne die Komplexität des "merkenden Zustands über Reload" einzuführen.

**Trade-off:** Das Briefing hat das verworfen, weil es "Sonderfall-Logik im Diff für marginalen Gewinn" nennt. Ich sehe das anders: Es ist kein marginaler Gewinn, wenn der Nutzer 3× statt 1× aufklappen muss. Aber: Alex hat das entschieden, und die aktuelle Lösung ist **nicht kaputt**, nur suboptimal.

**Empfehlung:** Aktuelle Lösung akzeptieren, aber als ROADMAP-Punkt für später notieren: "Zone 2/3 bleiben innerhalb der Session offen, wenn der Nutzer darin arbeitet" (nicht über Reload, nur innerhalb der aktuellen Interaktion).

---

## 2. UX-EDGE: Ignorierte UND angewendete Gruppe in Zone 3

**Position: Das ist eine echte UX-Schwäche, die der Nutzer nicht versteht.**

**Szenario:**
1. Nutzer ignoriert Gruppe A → erscheint in Zone 3 "Ausgeblendete Vorschläge (1)"
2. Nutzer wendet Gruppe A über den Bulk-Weg an (oder sie wird anderweitig angewendet)
3. Gruppe A ist **immer noch in Zone 3** (weil der localStorage-Key noch existiert)
4. Nutzer klickt "Wieder anzeigen" → Gruppe A **verschwindet komplett**, ohne als Vorschlag aufzutauchen

**Warum das verwirrt:** Der Nutzer erwartet: "Wieder anzeigen" = "taucht wieder als Vorschlag auf". Stattdessen: "taucht nirgendwo auf". Die technische Begründung ("durch Semantik erledigt", Briefing Abschnitt 4) ist korrekt: Nach dem Re-Render ist die Gruppe in `appliedInboxGroups`, also wird sie weder in `openGroups` noch in `ignoredGroups` einsortiert (`app.js:12661`). Aber der Nutzer versteht das nicht.

**Das Briefing verwirft die "explizite bereits-angewendet-Prüfung"** mit der Begründung, die Semantik erledige das. Aber die Semantik erledigt es nur **technisch**, nicht **für den Nutzer nachvollziehbar**.

**Meine Position:** Das ist eine **echte Lücke**, keine Wunschliste. Drei Optionen:

**(a) Explizite Prüfung (bevorzugt):** Zone 3 zeigt nur ignorierte Gruppen, die **nicht bereits angewendet** sind. Wenn eine Gruppe ignoriert UND angewendet ist, wird der localStorage-Key automatisch entfernt (still, ohne Meldung). Das ist die sauberste Lösung und kostet ~3 Zeilen Code.

**(b) Button-Text ändern:** Statt "Wieder anzeigen" → "Aus Liste entfernen". Das signalisiert: "Die Gruppe wird aus der Zone 3 entfernt", nicht "Die Gruppe taucht wieder als Vorschlag auf". Aber das ist irreführend, weil der Button ja tatsächlich `clearInboxGroupIgnored` aufruft.

**(c) Kurze Meldung nach dem Klick:** "Diese Gruppe wurde bereits angewendet und wird nicht mehr als Vorschlag angezeigt." Das ist ein Flickwerk.

**Empfehlung:** Option (a) ist die sauberste. Ich würde das als **kleinen Nachbesserungspunkt** vor dem Merge einbringen, nicht als Blocker, aber als "sollte behoben werden". Der Code ist trivial:

```javascript
// In updateGroupBannerUI, Zeile 12657-12664:
for (const [groupKey, members] of entries) {
    const isIgnored = isInboxGroupIgnored(groupKey);
    const isApplied = appliedInboxGroups.has(groupKey);

    if (isIgnored && !isApplied) {
        ignoredGroups.push({ groupKey, members });
    } else if (!isIgnored && !isApplied) {
        openGroups.push({ groupKey, members });
    }
    // Wenn isIgnored && isApplied: Key still entfernen
    if (isIgnored && isApplied) {
        clearInboxGroupIgnored(groupKey);
    }
}
```

Das kostet ~5 Zeilen, verhindert die Verwirrung, und ist konsistent mit der Semantik ("Zone 3 zeigt nur ignorierte, nicht-angewendete Gruppen").

---

## 3. CHANCEN und FOLGE-FEATURES (5, priorisiert)

### 3.1 #74-Kompatibilität sicherstellen (Prio: hoch)

**Bezug:** #74 Staffel-Schnellauswahl ist die nächste Kette.

**Was #75 vorbereiten sollte:** Der aktuelle Code nutzt `.smart-inbox-group-banner-*`-Klassen, was gut getrennt ist von `.smart-inbox-group-row` (die #74 anfassen wird). Keine IDs/Klassen-Kollisionen. Der Banner beeinflusst nicht die Gruppenzeile.

**Was #75 NICHT verbauen sollte:** Der Banner sollte keine Logik einführen, die die Gruppenzeile (`.smart-inbox-group-row`) beeinflusst oder mit ihr interagiert. Die aktuelle Implementierung ist sauber getrennt.

**Aufwand:** Kein zusätzlicher Aufwand — bereits gegeben.

### 3.2 Automatisches Zurückholen bei neuen Folgen (Prio: mittel)

**Bezug:** Alex Q1=C — "diese Kette speichert/wertet nichts dafür", aber das JSON-Format `{"ignored": true}` ist erweiterbar.

**Natürlicher nächster Schritt:** Beim Ignorieren die aktuelle Folgenzahl speichern (`{"ignored": true, "episodeCount": 17}`) und beim nächsten Erkennen prüfen, ob neue Folgen dazugekommen sind. Wenn ja: automatisch zurückholen ODER einen Hinweis zeigen ("3 neue Folgen verfügbar — wieder anzeigen?").

**Was FRÜHVERKÜPFT wäre:** Jetzt schon die Logik einzubauen, die "neue Folgen" erkennt und automatisch zurückholt. Das widerspricht Q1=C ("diese Kette speichert nichts dafür"). Der richtige Zeitpunkt ist **nach** #74, wenn die Staffel-Schnellauswahl funktioniert und Alex den Live-Betrieb mit #75 evaluiert hat.

**Aufwand:** Mittel (~50 Zeilen, JSON-Format erweitern, Prüfroutine beim Erkennen).

### 3.3 Zeitliches Ignorieren (Prio: niedrig)

**Bezug:** Erweiterung des JSON-Formats.

**Idee:** "Ignorieren für 7 Tage" statt "dauerhaft ignorieren". Das JSON würde erweitert: `{"ignored": true, "until": "2026-10-24"}`. Beim Render wird geprüft, ob das Datum überschritten ist — wenn ja, automatisch zurückholen.

**Nutzen:** Hilft, wenn der Nutzer weiß: "In einer Woche kommen neue Folgen, dann will ich die Gruppe wiedersehen." Verhindert, dass ignorierte Gruppen ewig in Zone 3 liegen.

**Aufwand:** Niedrig (~20 Zeilen, Datum prüfen, automatisches Zurückholen).

### 3.4 Gruppen-Details im Banner (Prio: niedrig)

**Bezug:** Entscheidungsunterstützung.

**Idee:** Im Banner nicht nur "17 Folgen, Staffel 1–11" anzeigen, sondern auch "Staffel 11: 5 Folgen" (aufgeschlüsselt nach Staffeln). Das hilft dem Nutzer zu entscheiden: "Will ich die Gruppe jetzt ignorieren, oder nur Staffel 11 auswählen?"

**Nutzen:** Erleichtert die Entscheidung, besonders bei großen Gruppen (Live-Fall: 173 Ordner, 11 Staffeln).

**Aufwand:** Niedrig (~10 Zeilen, Staffeln aufschlüsseln im Template).

### 3.5 Bulk-Ignorieren (Prio: niedrig)

**Bezug:** Symmetrie zu "Alle wieder anzeigen".

**Idee:** Ein Button "Alle ignorieren" in Zone 2, der alle offenen Vorschläge auf einmal ignoriert.

**Nutzen:** Wenn der Nutzer die Inbox aufräumen will und alle Vorschläge erstmal weghaben möchte.

**Aufwand:** Niedrig (~5 Zeilen, Button + Handler).

**Aber:** Das ist ein Sonderfall-Use-case. Die aktuelle Lösung (einzeln ignorieren) reicht für 1–3 Gruppen. Ich würde das **nicht** priorisieren.

---

## 4. FEHLENDE TEXTE/BUTTONS/ZUSTÄNDE

### 4.1 Erklärung, was "Ignorieren" bedeutet (echte Lücke)

**Problem:** Der Nutzer könnte denken, "Ignorieren" = "dauerhaft weg". Aber es ist umkehrbar. Ein kurzer Tooltip oder eine einmalige Erklärung wäre hilfreich.

**Vorschlag:** Ein einmaliger Tooltip beim ersten Hover über "Ignorieren": "Die Gruppe wird ausgeblendet, kann aber über 'Ausgeblendete Vorschläge' wieder angezeigt werden."

**Aufwand:** Niedrig (~5 Zeilen, `title`-Attribut oder einmaliger Tooltip).

### 4.2 NAS-Sicht (echte Lücke, wenn Alex beide Geräte nutzt)

**Problem:** Das Feature ist rein client-seitig (localStorage). Wenn Alex auf dem NAS ignoriert und dann lokal die Inbox öffnet, sieht er die ignorierten Gruppen nicht (und umgekehrt).

**Frage:** Nutzt Alex beide Geräte aktiv für die Inbox? Wenn ja, ist das eine echte Lücke. Wenn nein (nur NAS oder nur lokal), ist es irrelevant.

**Lösung (falls nötig):** Server-seitiger Ignorier-Zustand (neuer Endpunkt, Payload in `settings.json`). Das ist aber ein größerer Eingriff und widerspricht der "reinen Client-Änderung" (Briefing Abschnitt 4).

**Empfehlung:** Erst klären, ob Alex beide Geräte nutzt. Wenn ja: ROADMAP-Punkt für später. Wenn nein: keine Aktion.

### 4.3 Multi-Tab-Verhalten (keine echte Lücke, nur bekanntes Verhalten)

**Problem:** Wenn Tab A und Tab B offen sind, und der Nutzer ignoriert in Tab A, sieht Tab B die Änderung erst nach Reload.

**Das ist bekanntes localStorage-Verhalten** und kein Bug. Der Nutzer wird das nicht als Problem wahrnehmen, weil er die Inbox selten in mehreren Tabs gleichzeitig nutzt.

**Keine Aktion nötig.**

---

## GESAMT-EINSCHÄTZUNG

**Abnahme aus Nutzersicht: JA, mit einer Einschränkung.**

**Begründung:**
- Der Hauptuse-case (1–3 Gruppen, ignorieren und zurückholen) ist gut bedienbar.
- Zone 1 (prominenter Vorschlag) ist immer sichtbar — das ist der Hauptarbeitspfad.
- Zone 2/3 sind klar strukturiert und folgen etablierten Mustern (Gmail, Slack).
- Die Fehlerbehandlung (Inline-Meldung, Rücknahme bei Fehler) ist solide.

**Einschränkung:**
- Der Edge-Fall "ignoriert UND angewendet" (Frage 2) ist verwirrend und sollte vor dem Merge behoben werden (kleine Nachbesserung, ~5 Zeilen).
- Die eingeklappten Zonen nach jedem Render (Frage 1) sind suboptimal, aber nicht kaputt — kann als ROADMAP-Punkt für später notiert werden.

**Empfehlung:**
1. Edge-Fall "ignoriert UND angewendet" vor dem Merge beheben (kleine Nachbesserung, siehe Frage 2).
2. "Zone 2/3 bleiben innerhalb der Session offen" als ROADMAP-Punkt für später notieren.
3. Automatisches Zurückholen bei neuen Folgen als ROADMAP-Punkt für nach #74 notieren.
4. NAS-Sicht erst klären (nutzt Alex beide Geräte?).

**Insgesamt:** Der Patch ist aus Nutzersicht **abnahmefähig**, wenn der Edge-Fall (Frage 2) behoben wird. Die anderen Punkte sind Verbesserungen für später, keine Blocker.
