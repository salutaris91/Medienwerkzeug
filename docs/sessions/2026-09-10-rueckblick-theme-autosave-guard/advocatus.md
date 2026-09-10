# Advocatus-Rohoutput — Rückblick-Session Theme-Autosave-Request-Guard (#62)

Session: 2026-09-10, Request-Guard beim Theme-Autosave (Abnahme)
Datum: 10.09.2026
Gegenstand: Roadmap-Item #62, Branch `a2/20260910T064759Z` (nicht gemergt)

> Ungekürzter Rohoutput des advocatus aus der Rückkanal-Konsultation.

---

## Vorbemerkung zur Verifikationstiefe

Im Prüfkontext standen keine Shell-/Bash-Fähigkeiten zur Verfügung. Folgende Behauptungen des Workers konnten daher **nicht eigenständig verifiziert** werden und sind als Restrisiko markiert, nicht als bestätigt:

- `npm run test:frontend` (AK 6: „5 bestehende Tests grün") — nicht ausgeführt.
- Diff-Umfang („ROADMAP.md 4 Zeilen, app.js 13, Testdatei 151 neu") — kein `git diff` möglich.
- „keine Cache-Buster-Änderung in index.html" — `index.html:2716` zeigt aktuell `app.js?v=92`; ob dieser Wert vor dem Branch identisch war, ist ohne Git-Vergleich nicht belegbar.

Alle inhaltlichen Prüfungen basieren auf direktem Code-Lesen der betroffenen Dateien.

---

## Findings nach Schwere

### [kritisch]

Keine.

### [wichtig]

**W1 — Server-seitiges Lost Update bleibt möglich (AbortController ist rein clientseitig).**
`gui/static/app.js:494-498` bricht nur das clientseitige `fetch`-Promise ab. Ist Request 1 (altes Theme) bereits vollständig beim Server eingegangen, führt der Server sein Read-Modify-Write unabhängig vom Abbruch aus. `gui/core/persistence.py:609-624` (`update_settings` → `update_json_file` unter `settings_lock`, `persistence.py:11/310`) garantiert nur die Atomarität des **einzelnen** RMW, nicht die Reihenfolge zweier Requests. Schreiben Request 1 und Request 2 beide `app_theme`, gewinnt der zuletzt serialisierte — das kann der ältere sein (Lost Update).
**Bewertung:** Restrisiko akzeptabel und in `ROADMAP.md:1756-1758` als „praktische Auswirkung heute gering" dokumentiert (localhost, Single-User, `settings_lock` serialisiert, betroffen ist nur das Theme-Feld). Der Guard **reduziert** das Risiko deutlich (Abbruch, bevor Request 2 startet), **beseitigt** es nicht. Festhalten als bewusste, dokumentierte Restgröße — kein Blocker.

**W2 — Test-Mock bildet echtes Browser-Verhalten nur näherungsweise ab.**
`tests/frontend/theme_autosave.test.js:66-71`: `dispatchEvent` awaitet den async-Handler **sequenziell** (`await handler.call(...)`). Im echten Browser wird ein `change`-Handler nicht awaited; das Event feuert synchron, der async-Handler läuft unabhängig weiter. Der Test umgeht das korrekt, indem er beide `dispatchEvent`-Aufrufe **ohne** await startet (`:337`, `:345`) und so die parallele Interleaving-Struktur nachbildet; die Promise-Verkettung wird nur zum deterministischen Abwarten genutzt. Die Assertions sind belastbar (siehe W2-Fazit unten), aber der Test prüft ein **Modell** des Browser-Verhaltens, nicht das Verhalten selbst. Ein Fehler in einer echten Browser-fetch-Implementierung (z. B. reject mit anderem Error-Typ bei abort) wäre nicht abgedeckt.

**W3 — String-Marker-Extraktion ist strukturell fragil.**
`tests/frontend/theme_autosave.test.js:94-98`: `startMarker` (`const themeSelect = …`) und `endMarker` (`loadStatus();` per `indexOf`) extrahieren den Code-Ausschnitt. Aktuell korrekt: der erste `loadStatus();` nach `:479` steht in `app.js:547`, dazwischen liegt nur `setInterval(loadStatus, 6000)` (`:556`, enthält `loadStatus,` ohne `();`) — der extrahierte Ausschnitt (`app.js:479-546`) ist vollständig und syntaktisch selbsttragend. **Aber:** Wird künftig ein weiteres `loadStatus();` zwischen den Markern eingefügt (z. B. im themeSelect-Block), extrahiert der Test einen unvollständigen Ausschnitt und bricht still. Dies ist exakt die bereits im advocatus-Review zu #60 als „größte strukturelle Schwachstelle" benannte Stelle (`docs/sessions/2026-09-08-theme-autosave-rueckblick/advocatus.md:35`). Kein aktueller Bug, aber Wartbarkeitsrisiko.

### [kosmetisch]

**K1 — `signal.aborted`-Zweig ohne `AbortError`-name wird nicht separat getestet.**
`app.js:534` prüft `e.name === "AbortError" || signal.aborted`. Beide Tests decken nur den `name`-Treffer ab (`theme_autosave.test.js:308-311` setzt explizit `abortErr.name = 'AbortError'`; `:398-399` ebenso). Der Pfad „fetch rejected mit generischem Error, aber `signal.aborted === true`" ist ungetestet. Funktional korrekt, nur Testlücke.

**K2 — Behauptung „Module-lokales themeSaveController" ist ungenau.**
`app.js:481` deklariert `let themeSaveController = null;` **innerhalb** des `if (themeSelect) { … }`-Blocks, also block-lokal, nicht module-lokal. Funktional identisch, da der `change`-Handler als Closure darauf zugreift. Reine Begriffsungenauigkeit in der Umsetzungsbeschreibung.

**K3 — `currentSettings.app_theme` wird vor dem try mutiert und bleibt bei Abbruch stehen.**
`app.js:500` setzt `currentSettings.app_theme = newTheme` **vor** `fetch`. Bei Abbruch bleibt der Wert auf dem zuletzt **gewählten** (nicht zwangsläufig serverseitig **gespeicherten**) Theme. Das ist UI-konsistent (die Anzeige folgt der Nutzerwahl), kann aber bei serverseitigem Lost Update (W1) temporär vom Serverstand abweichen — bis zum nächsten Reload. Kein Bug.

**K4 — `then`-Zweig prüft nicht auf `signal.aborted`.**
`app.js:526-532` (`if (!response.ok)`) behandelt den Fehler ohne Abbruch-Check. Theoretisch könnte ein abgebrochener, aber bereits resolved Request mit `ok:false` den Hinweis setzen. Praktisch nicht erreichbar: der `then`-Zweig läuft als Microtask unmittelbar nach `resolve` ab — bevor ein Nutzer-Event (und damit `abort()` in Handler B) als Macrotask intervenieren kann. Einzige Ausnahme wären fetch-Implementierungen, die trotz Abort resolved (z. B. Cache-Fall). Kein realer Bug, nur fehlende defensive Härtung.

---

## Prüfschwerpunkte im Detail (mit Datei:Zeile)

### 1. AbortError-Erkennung — robust genug?
`app.js:534`: `if (e && (e.name === "AbortError" || signal.aborted)) return;`
- **`e.name === "AbortError"`** deckt DOMException mit Namen ab (Standard-Browserverhalten). ✓
- **`signal.aborted`** deckt den Fall ab, dass die fetch-Implementierung einen anderen Fehler wirft, das Signal aber bereits abgebrochen ist. ✓
- **Falschmaskierung echter Fehler:** Ein echter Netzwerkfehler von Request 1 wird dann als Abbruch maskiert, wenn das Signal *zwischenzeitlich* abgebrochen wurde (Nutzer hat bereits weitergewechselt). Das ist semantisch korrekt: Für ein verworfene Theme soll kein Hinweis erscheinen. Kein Bug.
- **Abbruch nach `response.ok`-Prüfung:** Da der `then`-Zweig als Microtask unmittelbar nach `resolve` läuft, kann kein `abort()` (Macrotask) dazwischengreifen. Siehe K4.
- **Fazit:** Robust genug; Restlücke nur theoretisch (K4), Rest-Testlücke (K1).

### 2. Server-seitige Reihenfolge / Lost Update
Siehe W1. `gui/api/system_api.py:82-128` (POST `/api/settings`) ruft `update_settings(mutate)` (`:121-128`); `mutate` schreibt `data[k] = v` für alle übergebenen Felder inkl. `app_theme`. `persistence.py:609-624` serialisiert über `settings_lock`, garantiert aber keine Request-Reihenfolge. Restrisiko vorhanden, akzeptabel begründet.

### 3. Testqualität
- **Mock-Verhalten:** nähert Browser an (W2); Assertions belastbar.
- **`firstChangePromise`-Abarbeitung:** `theme_autosave.test.js:354` (`await firstChangePromise`) erzwingt die Abarbeitung der Abort-Rejection — würde der erste Handler die Rejection nicht korrekt per `catch`/`return` schlucken, hinge der Test (Timeout). Damit ist die Abort-Abarbeitung indirekt, aber wirksam geprüft. ✓
- **Marker-Mechanismus:** aktuell korrekt, fragil (W3).
- **Belastbarkeit:** Guard-Test prüft konkret 2 Requests, `signal[0].aborted === true`, kein Hinweis, kein `console.error` — deckt AK 1+2 ab. ✓

### 4. Regressionen
- **Code nach try/catch:** Keiner. Der Handler endet bei `app.js:544`; der `return` (`:535`) beendet die async-Funktion ohne übersprungenen Folgecode. Kein `finally` nötig (kein Cleanup). ✓
- **`currentSettings`-Mutation:** siehe K3 (konsistent).
- **Haupt-Save-Pfad (`app.js:9842`):** liest `document.getElementById("settings-app-theme")?.value` unabhängig vom Autosave — kein Konflikt. ✓
- **loadSettings/Theme-Restore (`app.js:8483-8486`):** `setInputVal` (`:8413-8416`) setzt nur `el.value`, **kein** `change`-Event → kein Autosave-POST beim initialen Laden. Keine Regression. ✓
- **Doppelter abort bei bereits abgeschlossenem Request:** `abort()` auf bereits resolved Signal ist ein No-op. Harmlos. ✓

### 5. Scope-Treue
- Keine Anzeichen von Änderungen an anderen `fetch`-Aufrufen; der Guard ist isoliert auf den `themeSelect`-Block (`app.js:479-545`).
- Keine Cache-Buster-Änderung nachweisbar verifizierbar (siehe Vorbemerkung); `index.html:2716` unverändert gelesen.
- Diff-Umfang ohne `git diff` nicht verifizierbar (siehe Vorbemerkung).

---

## AK-Abgleich

| AK | Beschreibung | Beleg | Status |
|----|-------------|-------|--------|
| 1 | zweiter Wechsel bricht erste Anfrage ab | `app.js:494-498`; Test `:339-351` | erfüllt |
| 2 | Abbruch zeigt KEINEN Hinweis | `app.js:533-536`; Test `:356-363` | erfüllt |
| 3 | `response.ok==false` zeigt Hinweis | `app.js:526-532`; Test `:111-172` | erfüllt |
| 4 | echter Netzwerkfehler im catch zeigt Hinweis | `app.js:537-541`; Test `:174-224` | erfüllt |
| 5 | nach Erfolg kein Hinweis | `app.js:487-490` (Reset zu Beginn) + `ok`-Pfad ohne Fehler; Test `:226-278` | erfüllt |
| 6 | bestehende Tests bleiben grün | nicht ausgeführt (kein Shell-Zugriff) — **nicht verifiziert** | offen |

---

## Fazit

Die Umsetzung ist funktional korrekt, minimal-invasiv und scope-treu. Alle fünf inhaltlich prüfbaren Akzeptanzkriterien (AK 1–5) sind im Code erfüllt und durch die drei neuen Tests (`theme_autosave.test.js:289-385`, `:387-429`, `:431-438`) abgedeckt; die fünf Bestandstests sind unverändert vorhanden. Der AbortError-Check (`e.name === "AbortError" || signal.aborted`) ist robust gegen beide Abbruch-Signaturen. Das server-seitige Lost-Update bleibt als bewusst dokumentiertes Restrisiko bestehen (W1), ist für localhost/Single-User/Theme-Feld akzeptabel. Die Testmechanik ist eine Näherung des Browser-Verhaltens (W2) und strukturell fragil (W3) — kein Blocker, aber für langfristige Wartbarkeit relevant.

Vor einem Merge empfehle ich lediglich, AK 6 (`npm run test:frontend`) real auszuführen und den Git-Diff-Umfang zu bestätigen (beides im Prüfkontext mangels Shell-Zugriff nicht möglich).

VERDICT: APPROVE

## Einwandliste

1. `[wichtig]` W1 — Server-seitiges Lost Update bleibt möglich (`app.js:494-498`, `persistence.py:609-624`). Restrisiko, bewusst dokumentiert; keine Änderung zwingend.
2. `[wichtig]` W2 — Test-Mock (`theme_autosave.test.js:66-71`) awaitet den async-Handler sequenziell und bildet echtes Browser-Verhalten nur näherungsweise ab.
3. `[wichtig]` W3 — String-Marker-Extraktion (`theme_autosave.test.js:94-98`) bricht still bei künftiger Einfügung eines `loadStatus();` zwischen den Markern.
4. `[kosmetisch]` K1 — `signal.aborted`-Pfad ohne `AbortError`-name ungetestet.
5. `[kosmetisch]` K2 — „module-lokal" ungenau; tatsächlich block-lokal (`app.js:481`).
6. `[kosmetisch]` K3 — `currentSettings.app_theme` wird vor dem try mutiert (`app.js:500`); konsistent, kann temporär vom Serverstand abweichen.
7. `[kosmetisch]` K4 — `then`-Zweig (`app.js:526-532`) prüft nicht auf `signal.aborted`; praktisch nicht erreichbar.

## Restrisiken / nicht ausgeführte Prüfungen

- `npm run test:frontend` (AK 6) nicht ausgeführt.
- `git diff` / Branch-Umfang (Scope-Treue, Cache-Buster, Zeilenanzahl) nicht verifizierbar.
- Kein End-to-End-Test gegen einen echten Browser/fetch-Stack; Abdeckung beruht auf Mock-Modell.
