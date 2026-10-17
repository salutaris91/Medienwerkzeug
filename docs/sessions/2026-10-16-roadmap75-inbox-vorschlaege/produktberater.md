<!-- Mechanisch aus `opencode export ses_eb76ec0dfffeONdGMrazWGwFjD` extrahiert (Claude Code, 2026-10-17): alle Assistant-Textteile in Reihenfolge, ungekürzt, unverändert (nur Trailing Whitespace entfernt). Rohdatei: Kit scripts/gate-a2/logs/2026-10-16-roadmap75-inbox-vorschlaege/akt2/export-direkt/export-produktberater.json -->

## Position

Das Design trifft Alex' Kernbedürfnis (alle Vorschläge sehen + Rückweg nach Ignorieren), aber die dreistufige Struktur (prominent + aufklappbar + ausgeblendet) ist eine Komplexitätsstufe mehr als nötig. Eine flache Liste aller offenen Vorschläge mit je "Gruppieren"/"Ignorieren" plus einem separaten Bereich "Ignorierte (n)" wäre direkter und leichter verständlich — die bindenden Vorgaben 1–3 sind jedoch gesetzt, daher bewerte ich nur die Ausgestaltung innerhalb dieses Rahmens. Die Wortwahl sollte konsistent "Ignorieren" verwenden (Alex' Zitat, aktiver und ehrlicher als "Ausblenden"), der aufklappbare Bereich standardmäßig eingeklappt sein (selten genutzt), und der prominente erste Vorschlag bleibt fix — kein Nachrücken, weil das die Position des Banners springen ließe und Nutzer verwirrte.

---

## Findings

**1. [wichtig] Wortlaut "Ignorieren" vs. "Ausblenden" — Inkonsistenz in den Vorgaben**

Vorgabe 1 nutzt "Ignorieren" (Button-Text), Vorgabe 3 nutzt "Ausgeblendete Vorschläge" (Rückweg-Label). Das ist inkonsistent und verwirrt Nutzer: "Ignoriere ich etwas oder blende ich es aus?"

**Empfehlung:** Durchgehend "Ignorieren" verwenden.
- Button: **"Ignorieren"** (Alex' Zitat, aktive Entscheidung, ehrlich)
- Rückweg-Label: **"Ignorierte Vorschläge (n) – wieder anzeigen"** (statt "Ausgeblendete")
- Begründung: "Ausblenden" suggeriert temporäre Sichtbarkeit (wie ein Filter), "Ignorieren" ist eine bewusste Entscheidung gegen den Vorschlag. Alex' Zitat nutzt "Ignorieren", der bestehende Code nutzt "Ignorieren" — brechen wir das nicht.

**2. [wichtig] Aufklapp-Zustand: standardmäßig eingeklappt**

Bei 0–2 offenen Vorschlägen (plausible Faustzahl für die meisten Inbox-Situationen) braucht es keinen ausgeklappten Bereich. Der Live-Fall mit 173 Ordnern ist EINE Gruppe, nicht 173 Vorschläge. Realistisch sind 1–3 Serien gleichzeitig in der Inbox, selten mehr.

**Empfehlung:** "Weitere Vorschläge (n)" standardmäßig **eingeklappt**, wenn n ≤ 2. Erst ab n ≥ 3 automatisch aufklappen (oder immer eingeklappt lassen, Nutzerentscheidung via localStorage). Begründung: Der prominente erste Vorschlag ist der wichtigste, alles andere ist "nice-to-have" — aufklappen soll der Nutzer bewusst.

**3. [wichtig] Prominenter erster Vorschlag: kein Nachrücken**

Wenn der erste Vorschlag ignoriert wird, darf der nächste **nicht** automatisch nachrücken. Das würde das Banner springen lassen und Nutzer verwirren ("Wo ist mein Vorschlag hin?").

**Empfehlung:** Nach "Ignorieren" des ersten Vorschlags bleibt das Banner in der Position, zeigt aber den nächsten offenen Vorschlag als neuen "ersten" — **ohne Animation oder Sprung**. Der Nutzer sieht: "Okay, der nächste Vorschlag ist dran." Das ist vorhersehbar und ruhig.

**4. [kosmetisch] Inline-Fehlertext beim gescheiterten Start**

Vorgabe 6 verlangt Inline-Meldung + console.error. Der Wortlaut sollte konkret und handlungsorientiert sein.

**Empfehlung:**
```
"Gruppierung konnte nicht gestartet werden. Bitte erneut versuchen oder Seite neu laden."
```
Begründung: Kein technischer Jargon, klare Handlungsoption (erneut versuchen), keine Schuldzuweisung. `console.error` liefert die Details für Entwickler.

**5. [wichtig] Edge-Fall: "Wieder anzeigen" eines bereits angewendeten Vorschlags**

Kann das auftreten? Ja: Nutzer ignoriert Gruppe A, wendet sie später manuell über einen anderen Weg an (z. B. Bulk-Aktion), klickt dann "Wieder anzeigen". Die Gruppe ist dann doppelt: einmal angewendet, einmal wieder sichtbar.

**Empfehlung:** Beim "Wieder anzeigen" prüfen, ob die Gruppe bereits in `appliedInboxGroups` ist. Falls ja: nicht wieder anzeigen, sondern still entfernen (oder Hinweis: "Diese Gruppe wurde bereits angewendet"). Begründung: Doppelte Anzeige verwirrt, stiller Remove ist sicherer.

**6. [kosmetisch] Verwaiste Schlüssel: Nutzer sieht sie nicht — ist das ok?**

Ja, das ist ok. Vorgabe 2 sagt explizit: "Zähler/Rückweg nur für AKTUELL erkannte Gruppen; verwaiste Schlüssel stören nicht." Das ist richtig: Wenn eine Serie längst verarbeitet ist und der Schlüssel noch in localStorage liegt, soll der Nutzer ihn nicht sehen. Das ist kein Bug, sondern Feature.

**Empfehlung:** Keine Änderung. Verwaiste Schlüssel sind unsichtbar und stören nicht. Optional:ROADMAP-Punkt für "localStorage aufräumen" (sehr niedrig priorisiert).

**7. [wichtig] Überflüssige Komplexität — bewusst OUT halten**

Folgende Features gehören **nicht** in diese Kette:
- **Toast-Systeme** (Vorgabe 6: Inline-Meldung, keine neue Bibliothek)
- **Filter/Suchfeld im Banner** (überflüssig, Banner ist klein)
- **Multi-Select** ("alle ignorieren" / "alle wieder anzeigen" ist schon drin, aber keine individuelle Auswahl mehrerer Vorschläge)
- **Drag-and-drop** zum Umsortieren
- **Automatisches Zurückholen bei neuen Folgen** (Vorgabe 4: eigener ROADMAP-Punkt)
- **Folgenzahl beim Ignorieren speichern** (Vorgabe 4: Speicherformat darf es nicht verbauen, aber diese Kette speichert/wertet nichts dafür)

**Empfehlung:** Diese Features explizit im Briefing als "OUT" listen, damit der Worker sie nicht "einfach mal" einbaut.

**8. [wichtig] AKs aus Nutzersicht: PFLICHT vs. nice-to-have**

**PFLICHT** (ohne diese ist das Feature unvollständig):
- Mehrere Gruppen erreichbar (mindestens 2–3 im Test)
- Ignorieren beliebiger Vorschlag (nicht nur erster)
- Persistenz nach Reload (localStorage, nicht sessionStorage)
- Einzeln wiederanzeigen
- Alle wiederanzeigen
- Zähler nur aktuelle Gruppen (verwaiste Schlüssel zählen nicht)
- Rückweg bleibt sichtbar, wenn alle Vorschläge ignoriert sind
- Alte sessionStorage ignoriert (keine Migration)
- Sonderzeichen-Gruppenname (`"`, `'`, `<`, `&`) funktioniert in Anzeige, Apply, Ignorieren, Wiederanzeigen
- Fehlerfall: Inline-Meldung + console.error, `appliedInboxGroups` zurückgenommen
- Speicher verweigert (localStorage disabled): graceful degradation, kein Crash

**nice-to-have** (können später kommen):
- Automatische Sortierung der "Weitere Vorschläge"-Liste (z. B. nach Folgenzahl)
- Animation beim Auf-/Zuklappen
- Tooltip bei "Ignorieren" ("Dieser Vorschlag wird ausgeblendet und kann später wieder angezeigt werden")
- Tastaturkürzel für "Ignorieren" / "Wieder anzeigen"

**Empfehlung:** PFLICHT-AKs alle in dieser Kette umsetzen, nice-to-have explizit als "OUT" oder ROADMAP listen.

**9. [kosmetisch] Höhenbegrenzung/Scrollbar für "Weitere Vorschläge"**

Vorgabe 1 sagt "höhenbegrenzt/scrollbar". Bei 10+ Vorschlägen wird die Liste sonst endlos.

**Empfehlung:** Max-Höhe ca. 300–400px (5–7 Vorschläge sichtbar), dann scrollbar. Begründung: Banner soll nicht die ganze Inbox überdecken.

**10. [wichtig] Speicherformat: Erweiterungsoffen, aber nicht vorbelegen**

Vorgabe 4 sagt: "Speicherformat darf eine spätere Erweiterung (z. B. Folgenzahl beim Ignorieren) nicht verbauen, aber diese Kette speichert/wertet nichts dafür."

**Empfehlung:** Speicherformat als JSON-Objekt statt einfacher String:
```javascript
// Statt: localStorage.setItem('smart-inbox-ignore-group-' + groupKey, 'true');
// Besser: localStorage.setItem('smart-inbox-ignore-group-' + groupKey, JSON.stringify({ ignored: true, timestamp: Date.now() }));
```
Begründung: Erlaubt spätere Erweiterung (z. B. `followCount: 5`) ohne Breaking Change. Diese Kette schreibt nur `{ ignored: true }`, aber das Format ist offen.

---

## Votum

**APPROVE mit Auflagen:** Das Design ist richtig, aber die Wortlaut-Inkonsistenz ("Ignorieren" vs. "Ausgeblendete") muss bereinigt werden (Finding 1), der aufklappbare Bereich standardmäßig eingeklappt sein (Finding 2), und der Edge-Fall "Wieder anzeigen eines bereits angewendeten Vorschlags" muss abgefangen werden (Finding 5). Die überflüssige Komplexität (Finding 7) muss explizit im Briefing als "OUT" gelistet werden, damit der Worker sie nicht einbaut. Speicherformat erweiterungsoffen gestalten (Finding 10), aber nicht vorbelegen.
