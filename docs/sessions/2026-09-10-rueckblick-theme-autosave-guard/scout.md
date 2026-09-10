# Scout-Rohoutput — Rückblick-Session Theme-Autosave-Request-Guard (#62)

## Session: 2026-09-10, Request-Guard beim Theme-Autosave (Abnahme)

**Datum:** 10.09.2026

> Ungekürzter Rohoutput des scout aus der Rückkanal-Konsultation (Abnahme Branch `a2/20260910T064759Z`, Roadmap-Item #62).

---

## Kurzeinschätzung

Die Umsetzung von #62 ist sauber und minimal: AbortController module-lokal geführt, Abort-Fang breit genug (`e.name === "AbortError" || signal.aborted`), Fehlerhinweis wird zu Handler-Beginn resettet, Tests decken alle Akzeptanzkriterien ab. Das Bemerkenswerte ist nicht die Umsetzung selbst, sondern dass sie ein Muster etabliert, das an **mindestens 5 weiteren Stellen** in `app.js` fehlt oder inkonsistent ist. Der größte Hebel liegt nicht in einem Wrapper, sondern in der Angleichung des AbortError-Fangs an die bereits robustere Theme-Variante.

---

## Chancen und Anschlussideen

### 1. AbortError-Fang in 4 Such-Handlern ist weniger robust als im Theme-Handler

**Beobachtung:**

Der neue Theme-Handler fängt Abbrüche mit einer breiten Prüfung:

```
app.js:534  if (e && (e.name === "AbortError" || signal.aborted)) {
```

Die vier bestehenden Such-Handler nutzen nur den engen Check:

```
app.js:3187  if (e.name === 'AbortError') return;  // searchSeries
app.js:4231  if (e.name === 'AbortError') return;  // searchMovie
app.js:4860  if (e.name === 'AbortError') return;  // searchYtMovie
app.js:4941  if (e.name === 'AbortError') return;  // searchYtSeries
```

Zusätzlich fehlt bei den Such-Handlern der `e &&`-Null-Check. Wenn `e` aus irgendeinem Grund `null`/`undefined` wäre, würde `e.name` werfen statt still zu returnen.

**Nutzen:** Robustheit gegen Browser-Engines, die bei `fetch`-Abort einen Fehler mit anderem `name` werfen (bekanntes Problem in älteren WebKit-Versionen), und Schutz gegen `TypeError` bei unerwarteten Error-Objekten. `signal.aborted` ist der zuverlässigere Indikator, weil er direkt am Controller hängt.

**Aufwand:**
- KI: ~5 Minuten (4 Zeilen ändern, je 1 Testfall pro Handler wäre optional).
- Menschlicher Engpass: Review, ob die breitere Prüfung in den Such-Handlern Seiteneffekte hat (z.B. ob ein gewollter Abort dort jemals eine Fehlermeldung zeigen soll — aktuell: nein, beide Pfade returnen still).

**Alex-Entscheidung nötig?** Ja — weil es eine bewusste Ausweitung des Guards an 4 Stellen ist, nicht nur eine mechanische Kopie.

---

### 2. `saveAllSubscriptions()` — Autosave ohne Request-Guard

**Beobachtung:**

Der `change`-Handler der Subscription-Toggles (`app.js:5614–5624`) ist `async` und ruft bei jedem Toggle `saveAllSubscriptions()` auf:

```js
// app.js:5614
switchInput.addEventListener("change", async (e) => {
    const isEnabled = e.target.checked;
    sub.enabled = isEnabled;
    statusText.textContent = isEnabled ? "Aktiv" : "Aus";
    updateBadge(isEnabled);
    await saveAllSubscriptions();        // ← POST ohne Guard
    renderSubscriptionsList();
});
```

`saveAllSubscriptions()` selbst (`app.js:5919–5934`) macht ein `POST /api/youtube/subscriptions` ohne AbortController, ohne Signal, ohne Race-Behandlung:

```js
// app.js:5919
async function saveAllSubscriptions() {
    try {
        const response = await fetch("/api/youtube/subscriptions", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ subscriptions: currentSubscriptions })
        });
        if (!response.ok) { throw new Error("Fehler beim Speichern"); }
        ...
    } catch (e) {
        console.error("Error saving subscriptions:", e);
        alert("Fehler beim Speichern der Abonnements!");
    }
}
```

Schnelles Umschalten mehrerer Toggles erzeugt mehrere parallele POSTs. Der letzte `alert()` bei Fehler blockiert zusätzlich die UI. Die Funktion wird außerdem aufgerufen von `app.js:5645` (Delete-Button, Quarantäne) und `app.js:6224` (nach Abo-Hinzufügung) — beide sind Einzelaufrufe, aber der Toggle-Handler ist ein Rapid-Fire-Risiko.

**Nutzen:** Verhindert Race Conditions (ältere Antworten können neuere überschreiben), eliminiert potenzielle Doppel-Alerts, und bringt Konsistenz mit dem Theme-Pattern.

**Aufwand:**
- KI: ~15 Minuten (AbortController in `saveAllSubscriptions` einbauen oder im Handler führen, AbortError still behandeln).
- Menschlicher Engpass: Review + Entscheidung, ob der `alert()` bei Fehler bestehen bleiben soll oder durch ein subtileres Feedback ersetzt wird (separates Thema, nicht Teil dieses Guards).

**Alex-Entscheidung nötig?** Ja — Scope-Frage: nur Guard, oder gleich den `alert()` durch ein inline-Error-Element ersetzen?

---

### 3. Gemeinsame Hilfsfunktion `guardedAutosave()` — noch verfrüht, aber absehbar

**Beobachtung:**

Das Muster wiederholt sich strukturell:
1. AbortController-Variable führen
2. Bei neuem Trigger: alten Controller abbrechen
3. Neuen Controller erstellen, Signal an `fetch` übergeben
4. Im catch: `AbortError`/`signal.aborted` still behandeln
5. Echte Fehler melden

Aktuell gibt es **2 Stellen** mit diesem vollständigen Muster (Theme-Handler + potenziell Subscriptions nach Idee 2) und **4 Stellen** mit dem Teil-Muster (Such-Handler: Guard + Abort-Fang, aber kein Error-Element).

**Nutzen bei einer Hilfsfunktion:** Weniger Code-Duplikation, einheitliches Abort-Verhalten, ein einziger Ort für Änderungen am Pattern (z.B. wenn später ein Debounce dazukommt).

**Trade-off / warum ich es noch nicht empfehle:**
- Bei nur 2 vollständigen Instanzen ist ein Wrapper Over-Engineering.
- Die Kontexte sind unterschiedlich: Theme hat ein Error-Element, Such-Handler schreiben in `innerHTML`, Subscriptions nutzen `alert()`. Ein Wrapper müsste diese Unterschiede absorbieren, was ihn komplexer macht als das inline-Pattern.
- Empfehlung: **Beobachten.** Wenn eine dritte Stelle dazukommt (z. B. ein weiteres Autosave-Feld in den Settings), dann extrahieren.

**Aufwand (falls später gebaut):**
- KI: ~30 Minuten (Wrapper + Migration der bestehenden Stellen + Tests).
- Menschlicher Engpass: Design-Entscheidung, wie der Wrapper Error-Reporting und Abort-Signalisierung handhabt.

**Alex-Entscheidung nötig?** Nicht jetzt. Erst relevant, wenn Idee 2 umgesetzt ist und eine dritte Stelle identifiziert wird.

---

### 4. Test-Infrastruktur: String-Marker-Extraktion funktioniert, aber Marker sind implizite Verträge

**Beobachtung:**

Die Testdatei `tests/frontend/theme_autosave.test.js:94–101` extrahiert den Handler-Code per String-Marker aus `app.js`:

```js
const startMarker = 'const themeSelect = document.getElementById("settings-app-theme");';
const startIndex = appJsContent.indexOf(startMarker);
const endIndex = appJsContent.indexOf('loadStatus();', startIndex);
const themeHandlerCode = appJsContent.substring(startIndex, endIndex);
```

Das ist ein bestehendes Muster (nicht neu durch #62). Die `assert.ok(startIndex !== -1)`-Prüfungen fangen ab, wenn Marker verschwinden. Aber:

- Der End-Marker `'loadStatus();'` ist generisch — wenn vor dem Theme-Block ein weiteres `loadStatus();` eingefügt würde, wäre die Extraktion falsch.
- Änderungen am Theme-Handler-Code müssen wissen, dass sie innerhalb dieses Marker-Fensters liegen.

**Nutzen der Dokumentation:** Wenn jemand den Theme-Block refaktoriert oder verschiebt, weiß er/sie (oder die KI), dass die Marker in der Testdatei mitgezogen werden müssen.

**Aufwand:**
- KI: ~5 Minuten (ein Kommentar in `app.js` oberhalb des Theme-Blocks, der auf die Test-Marker verweist).
- Menschlicher Engpass: keiner.

**Alex-Entscheidung nötig?** Nein — reine Dokumentationsergänzung, aber sehr niedrig priorisiert.

---

## Zusammenfassung und Priorisierung

| # | Idee | Nutzen | Aufwand (KI) | Engpass | Entscheidung? |
|---|------|--------|--------------|---------|---------------|
| 1 | AbortError-Guard angleichen (4 Such-Handler) | Robustheit | ~5 min | Review | Ja |
| 2 | `saveAllSubscriptions()` Guard | Race-Condition-Schutz | ~15 min | Review + Alert-Frage | Ja |
| 3 | Hilfsfunktion `guardedAutosave()` | Duplikation reduzieren | ~30 min | Design-Entscheidung | Noch nicht |
| 4 | Marker-Kommentar in app.js | Wartbarkeit | ~5 min | keiner | Nein |

**Meine Empfehlung für die Reihenfolge:** Idee 1 (kleinster Hebel, größte Konsistenzwirkung) → Idee 2 (echter Bug-Schutz) → Idee 4 (Doku, nebenbei) → Idee 3 (wenn dritte Stelle kommt).
