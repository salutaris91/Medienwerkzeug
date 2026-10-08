# Rohoutput advocatus — Kreativteam-Session 2026-10-06 (Akt 2)

Kontext: Risikoprüfung des Plan-Entwurfs (#46-Clientfix, Namenskonflikt-Serverfix, Version-Bump, neue Tests, ROADMAP-Texte).

Hinweis Claude Code (2026-10-07): Der Text unterhalb der nächsten Linie ist die wörtliche Subagent-Antwort aus der OpenCode-Sitzung (ceo-planner ses_eede285a6ffeLjfbSwIYSoRN4T, Subagent-Sitzung ses_eedd94edaffeVTuRbU1YcCQ1iP; Quelle: opencode export, nur die <task>-Hülle entfernt). Wiederhergestellt nach Alex-Go, weil die zuvor archivierte Fassung vom Moderator bearbeitet worden war.

---

<task_result>
Ich habe alle relevanten Codepfade selbst verifiziert (queue_api.py, series_helper.py, helpers.py, system_api.py, utils.py, mw_metadata.py, app.js, index.html, die drei Testdateien, ROADMAP.md, den Eintrag-Entwurf). Hier der Risikobericht.

---

# ADVOCATUS-RISIKOBERICHT — Plan "ROADMAP #46 Namenskonflikt + Dropdown-Sync"

## Zusammenfassung der Kernprüfung

Die Plan-Beschreibung ist überwiegend **präzise** (Zeilennummern und Verhalten bestätigt). Zwei Punkte sind aber **im Wortlaut der Entscheidungsregel fehlerhaft bzw. unvollständig** und würden das Kernziel (Schleife sicher brechen) für eine realistische Klasse von Ordnernamen verfehlen, sowie das Frontend-Test-Harness für AK6 ist mit der bestehenden Mock-Infrastruktur **nicht umsetzbar**. Details unten.

---

## BEFUNDE nach Schwere

### [kritisch] 1. Normalisierungs-Asymmetrie in Regel B — "adopt NAS name" bricht die Schleife NICHT für bereinigte Ordnernamen

**Ort:** `queue_api.py:758` (Vergleich `nas_match_folder != metadata_show_name`), Regel-Formulierung im Plan.

**Befund:** Der Plan vergleicht laut Alex' Regel den **normalisierten** `nas_show_folder` gegen den **rohen** `nas_match_folder` (und gegen `metadata_show_name`). `nas_match_folder` ist der **rohe** Ordnername aus `os.listdir()` (`find_existing_series_folder_by_id`, `series_helper.py:22`). `clean_series_name_for_fs` (`helpers.py:97-111`) entfernt aber u. a. **trailing `[...]`-Tags** (Zeile 103-107), ersetzt `_` (Zeile 109) und strippt trailing Punkte/Striche. `limit_filename_length` kürzt.

**Konkretes Gegenbeispiel (realistisch, da `mw_metadata.py:398` `[{PROVIDER}]` anhängt):**
- `nas_match_folder = "Yu-Gi-Oh! [TMDB_TV]"` (roh)
- `metadata_show_name = "Yu-Gi-Oh! Duel Monsters"`
- Mismatch feuert: `nas_name="Yu-Gi-Oh! [TMDB_TV]"`, `metadata_name="Yu-Gi-Oh! Duel Monsters"`
- Nutzer klickt **"Ordnername vom NAS übernehmen"** → `nas_show_folder = "Yu-Gi-Oh! [TMDB_TV]"`
- Server: `N(nas_show_folder) = "Yu-Gi-Oh!"` (Tag gestrippt)
- Vergleich gegen **rohen** `nas_match_folder "Yu-Gi-Oh! [TMDB_TV]"` → **ungleich**
- Vergleich gegen `metadata_show_name "Yu-Gi-Oh! Duel Monsters"` → **ungleich**
- ⇒ **Hinweis bleibt → Schleife bleibt** für genau den Button, dessen Zweck es ist, sie zu brechen.

Der "metadata"-Button ist davon nicht betroffen (er setzt den bereits normalisierten `metadata_name`, `N` ist idempotent, also `N(metadata_name)==metadata_show_name` immer wahr). Aber die Regel erfüllt ihr eigenes Akzeptanzkriterium "adopt NAS name bricht die Schleife" nicht für alle Ordnernamen.

**Empfehlung (einzige korrekte Formulierung):** **Beide** Seiten normalisieren. Mit `N(x) = limit_filename_length(clean_series_name_for_fs(str(x).strip()))` gilt: **kein Hinweis, wenn `N(nas_show_folder) in {N(nas_match_folder), metadata_show_name}`** (wobei `metadata_show_name` bereits `= N(show_name)` ist, also kein Doppel-Clean nötig; `N(nas_match_folder)` ist der neue, fehlende Schritt). Damit gilt garantiert:
- adopt NAS name → `N(nas_name) == N(nas_match_folder)` (identische Eingabe) → kein Hinweis ✓
- adopt metadata name → `N(metadata_name) == metadata_show_name` → kein Hinweis ✓
- dritter Name → keiner von beiden → Hinweis ✓

**AK-Ergänzung (zwingend):** Neuer Backend-Test mit **Bracket-Tag-Ordnername** (z. B. `"Show [TMDB_TV]"`), der `nas_show_folder = "Show [TMDB_TV]"` setzt und `assertNotIn("show_name_mismatch", result)` prüft — **plus** Kontroll-Assert, dass dieselbe Fixture **ohne** `nas_show_folder` den Hinweis liefert. Ohne diesen Test wäre Finding 1 unbemerkt und die Schleife würde für diese Namen weiterbestehen.

---

### [wichtig] 2. Leere/None/Nicht-String `nas_show_folder` muss exakt heutiges Verhalten reproduzieren — sonst Regression im Erstaufruf

**Ort:** neues Gate in `queue_api.py:750-762`; Guard-Vorbild `series_helper.py:44`.

**Befund:** Der Erstaufruf der Vorschau hat **kein** `nas_show_folder` (Override-Feld leer, `app.js:4383`). Heute führt das zu "Mismatch feuert, wenn `nas_match_folder != metadata_show_name`". Das neue Gate muss diese Fälle **unverändert** durchreichen, darf aber nicht versehentlich `N(None)`/`N("")` berechnen und gegen etwas vergleichen. Konkret:
- `nas_show_folder = None` (fehlend) → muss heute-Verhalten ergeben (Hinweis falls mismatch).
- `nas_show_folder = ""` oder nur Whitespace → `str(x).strip()` leer → ebenso heute-Verhalten.
- **Nicht-String-Typen aus JSON** (`123`, `{}`, `[]`, `true`): `str()`-Coercion liefert unsinnige Namen (`"123"`, `"{}"`, …). Empfehlung: nur `isinstance(nas_show_folder, str)` und `strip()` nicht leer behandeln; alles andere wie fehlend.

**Empfehlung:** Gate-Guard formulieren als `if isinstance(nas_show_folder, str) and nas_show_folder.strip():` → Override-Vergleich; sonst Fallthrough auf die bestehende `if nas_match_folder and nas_match_folder != metadata_show_name`-Logik. **AK-Ergänzung:** Test "fehlendes/leeres nas_show_folder liefert identisches Ergebnis wie heute" (deckt zugleich Regression gegenüber `test_false_positive_show_name_mismatch_with_different_years` in `test_utils.py:3123` ab, der ohne `nas_show_folder` läuft).

---

### [wichtig] 3. A) `await populateLocalProfilesDropdown()` würde den Verarbeitungsstart blockieren — Fire-and-forget erzwingen; `res.json()`-Parse in den bestehenden try/catch

**Ort:** `app.js:10559-10592` (Profil-Save-Block), `app.js:10596-10597` (closePreviewModal + Prozessstart), `populateLocalProfilesDropdown` `app.js:12385-12414`.

**Befund:**
1. **Blockade:** Der Plan lässt offen, ob `await`. Ein inline-`await populateLocalProfilesDropdown()` **vor** `closePreviewModal()` (10596) würde den kompletten Verarbeitungsstart verzögern/blockieren, wenn `/api/profiles` hängt oder langsam ist. Da `populateLocalProfilesDropdown` einen eigenen try/catch hat und der Verarbeitungsstart laut Plan "in jedem Fall" weiterlaufen soll, ist **nur nicht-awaitende Ausführung** (fire-and-forget) korrekt: `populateLocalProfilesDropdown();` ohne `await`.
2. **JSON-Parse:** `res.json()` (neuer Code) wirft bei ungültigem JSON. Der Parse **muss innerhalb** des bestehenden `try` (10560) liegen, sonst propagiert eine Exception aus dem Handler (unbehandelt) und `closePreviewModal`/Prozessstart wird übersprungen. Konkret: `const response = await fetch(...)`; dann `if (response.ok) { const data = await response.json(); … } else { appendConsoleLog(…) }` — alles im try; der `catch` ergänzt `appendConsoleLog` **und** behält `console.error` (Konsolidieren, nicht zwei Fehlerkanäle mit widersprüchlicher Sichtbarkeit).
3. **Race mit closePreviewModal:** `series-local-profile-select` liegt außerhalb des Preview-Modals (Serien-Formular), daher kein DOM-Verlust beim Schließen — dennoch ist `populateLocalProfilesDropdown` durch `if (!select) return;` (12387) gegen entfernte Elemente abgesichert. Benennen, nicht annehmen.
4. **Restrisiko:** `populateLocalProfilesDropdown` schluckt eigene Fehler still (`console.error` nur, 12412). Folge: neu gespeichertes Profil erscheint ggf. erst nach Reload, ohne Nutzerhinweis. Akzeptabel (kosmetisch), aber explizit dokumentieren.

**Empfehlung:** Erfolgsprüfung mit `await` auf `fetch`+`json` (schnell, lokal), dann **nicht-awaitender** Aufruf von `populateLocalProfilesDropdown()`, dann ungehindert `closePreviewModal()`/Prozessstart. Fehlertext mit "Fehler"/"❌" formulieren, damit `appendConsoleLog` (`app.js:2179`) ihn rot färbt.

---

### [wichtig] 4. D) Frontend-Harness für AK6 kann den `btn-preview-execute`-Handler mit der bestehenden Mock-Basis **nicht** auslösen

**Ort:** `tests/frontend/app_warning.test.js:31-33` (Vorbild `createMockElement.addEventListener`), `app.js:10540` (Handler-Registrierung), `app.js:10541` (`currentPreviewPayload`-Guard).

**Befund:** Das Vorbild-Mock speichert den Klick-Callback **nicht** — `addEventListener(type) { this.__listeners[type] = (…) + 1; }` zählt nur. Damit ist der `btn-preview-execute`-Handler nach dem `eval` **nicht aufrufbar**; AK6 ("kein Dropdown-Refresh bei success:false; Fehlerhinweis via appendConsoleLog") wäre nicht testbar. Zusätzlich:
- `currentPreviewPayload` ist module-scoped (`let`, zugewiesen `app.js:10320`) — muss über einen exponierten Setter gesetzt werden (Muster wie `setNfoAgentScanData` in `app_warning.test.js:113`).
- Der Handler liest `document.querySelectorAll(".preview-cb-*:checked")`, viele `getElementById` (Checkboxen), ruft `closePreviewModal()`, `appendConsoleLog()`, `connectLogStream()` und `fetch("/api/process")` — alles muss gemockt/aufrufbar sein.
- **fetch-Mock muss URL-diskriminierend sein** für `/api/profile` (POST, `{success:true|false}`), `/api/profiles` (GET, `{profiles:[]}`) und `/api/process` (POST) — sonst testet AK6 versehentlich den Dropdown-Lade-Mock (AK5) mit.
- Globaler Zustand `allLocalProfiles` (`app.js:12393`) und DOM-Elemente (`console-body-text`, `series-local-profile-select`) persistieren über Tests im `elements`-Dict → müssen pro Test zurückgesetzt werden.

**Empfehlung:** Im Plan explizit festschreiben: (a) Mock-`addEventListener` **speichert den Callback** (z. B. `this.__listeners[type].push(fn)` oder `.callback = fn`), (b) Setter für `currentPreviewPayload` exportieren, (c) fetch-Mock nach URL routen mit Call-Zählern, (d) `allLocalProfiles`/DOM-State resetten. Alternativ — falls der Handler weiterhin nicht refactorbar ist — AK6 auf das **isolierte** Verhalten reduzieren (Mock direkt auf die neue if/else-Stelle, z. B. über einen exponierten Helfer), und das Trigger-Integration in AK5 nur indirekt absichern. Ohne (a)-(d) ist AK6 nicht umsetzbar bzw. trügerisch grün.

---

### [wichtig] 5. D) Backend AK2-4 drohen trivial-grün zu werden — positive Kontrolle je Test zwingend

**Ort:** `tests/test_utils.py:3047` und `:3123` (Vorbilder).

**Befund:** Risiken, dass ein AK grün wird, ohne die neue Logik zu treffen:
- `find_existing_series_folder_by_id` liefert `None` (Ordner nicht gefunden / ID-Zweig nicht erreicht, z. B. `provider` leer) → `show_name_mismatch` wird nie gesetzt → `assertNotIn` grün, obwohl der Override-Pfad gar nicht lief.
- Der `show_id`/`provider`-Zweig (`queue_api.py:750`) wird bei fehlendem `provider` übersprungen.

**Empfehlung:** Jeder AK trägt **zwei Asserts**: (1) die eigentliche Behauptung (mit `nas_show_folder=X` → kein Hinweis bzw. dritter Name → Hinweis) **und** (2) eine Kontroll-Assert, dass **dieselbe Fixture ohne `nas_show_folder`** den Hinweis liefert (`assertIsNotNone(result.get("show_name_mismatch"))`). Das beweist, dass der Zweig tatsächlich erreicht und der Override wirksam wird. Konkret drei AK-Varianten vorschlagen: adopt-nas (inkl. Bracket-Tag-Fall aus Finding 1), adopt-metadata, dritter Name → Hinweis bleibt.

---

### [kosmetisch] 6. Groß-/Kleinschreibung und Whitespace beim manuellen Override

**Ort:** Vergleich in neuem Gate; `clean_series_name_for_fs` (`helpers.py:97`) normalisiert **nicht** case.

**Befund:** Die Buttons kopieren exakte Strings (case-treu) → kein Problem für Buttons. Aber eine **manuell** eingetippte Variante ("yu-gi-oh!" statt "Yu-Gi-Oh!") gilt nach der Regel als "dritter Name" → Hinweis bleibt. Das ist konsistent mit Alex' Regel, aber ggf. überraschend. **Empfehlung:** bewusst so lassen (kein Case-Folding, da echtes Abweichen sonst verschleiert würde) und im ROADMAP/Entwurf als Verhalten dokumentieren; kein Code nötig.

---

### [kosmetisch] 7. ROADMAP-#64–#66-Texte: Nummernvergabe, Referenzen und Format

**Ort:** `docs/sessions/2026-10-06-roadmap46-namenskonflikt/roadmap-neue-eintraege.md`; `ROADMAP.md` Ende (`:1782-1793`, höchste Nummer 63).

**Befund:** Nummernvergabe korrekt (#64–#66 direkt nach #63), keine Duplikate, Format konsistent zum Existing-Format. Die **Referenzen in #66 sind verifiziert korrekt**: `mw_metadata.py:233` = `f"{title} ({year}) [{country}]"`, `:398` = `f"{r['name']} [{r['provider'].upper()}]"`, `clean_show_name` = `utils.py:23`, `clean_series_name_for_fs` = `helpers.py:97`. Kein Risiko aus den Texten selbst. Hinweis: Der Entwurf referenziert Prozess-Akteure ("repo-operator", "Gate-A2-Worker") — intern konsistent, aber vor Übernahme in die dauerhafte ROADMAP ggf. session-neutral formulieren (rein kosmetisch).

---

## Antworten auf die sieben Prüfpunkte (Kurzfassung)

1. **Asymmetrie:** Siehe Finding 1 — **beide Seiten normalisieren** (`N(nas_match_folder)` ist der fehlende Schritt). Restfälle: leere/None/Nicht-String siehe Finding 2; case siehe Finding 6. Die Schleife bricht garantiert nur mit der Doppel-Normalisierung.
2. **Dritter Name:** Erzeugt **keine** Endlosschleife — die Schleife iteriert ausschließlich über die zwei Buttons, die beide brechen (nach Finding-1-Fix). Dritter Name = persistent korrekter Hinweis, gewollt nach Alex' Regel. Einziger Nebeneffekt: ein "dritter" Name, der normalisiert mit `nas_match_folder` kollidiert (z. B. "Yu-Gi-Oh!" vs. Ordner "Yu-Gi-Oh! [TMDB_TV]"), wird stillschweigend akzeptiert — inhaltlich richtig (effektiv gleicher Zielordner), aber dokumentieren.
3. **A-Fehlerpfad:** `res.json()` muss im bestehenden `try` liegen; `populateLocalProfilesDropdown()` **nicht awaiten** (Fire-and-forget); Race mit closePreviewModal unkritisch (Dropdown außerhalb des Modals + Null-Guard); stilles Scheitern von `populateLocalProfilesDropdown` bleibt Restrisiko (dokumentieren).
4. **Test-Design:** Siehe Findings 4+5 — Harness muss Callbacks speichern, `currentPreviewPayload` exponieren, fetch URL-diskriminierend mocken, State resetten; Backend braucht positive Kontroll-Asserts gegen trivial-grün.
5. **C-Vollständigkeit:** Verifiziert — exakt **10** `?v=93`-Stellen (index.html:2752 + app.js:1-9). Kein Service Worker, keine weitere HTML-Datei, keine weitere `app.js`-Referenz. `style.css?v=47` und `utilities.css?v=1` sind unverändert; `cache_busting.test.js` prüft sie nur auf nicht-leer → bleibt grün. Bump korrekt und vollständig.
6. **Sicherheit/Nebenwirkung:** Neuer Server-Vergleich ist **rein lesend** (String-Vergleich, kein `os.path.join`, keine Datei-IO). Kein neues Pfad-Traversierungs-/Injection-Risiko durch den zusätzlichen Vergleich. Antwort-Schema unverändert (Feld `show_name_mismatch` nur gesetzt/abwesend) → ältere Clients unbeeinträchtigt. **Notiz (außerhalb Scope, vorbestehend):** `nas_show_folder` fließt weiterhin via `resolve_series_folder_name` (`series_helper.py:44-49`) in `dest_show_dir`/später den Prozessor; `clean_series_name_for_fs` strippt **keine** `/`/`..`-Sequenzen — die eigentliche Absicherung passiert erst downstream via `is_path_allowed` (`processor.py:3120`). Kein Blocker für diesen Plan, aber als vorbestehender Befund notieren.
7. **E-Risiken:** Siehe Finding 7 — unkritisch, Referenzen korrekt.

---

## Weitere Notizen (außerhalb Scope, nicht anfassen)

- **[wichtig, vorbestehend]** `app.js:10283` interpoliert `nas_name`/`metadata_name` **ungescaped** in `innerHTML`. Ein Ordnername auf dem NAS (vom Nutzer/über Metadaten steuerbar) mit `<`/`"`/`<img onerror=…>` ergibt **stored XSS**. Nicht Teil dieses Plans, aber ein ROADMAP-Kandidat (Escape via `escapeHTML`/`textContent`). Da Plan E ohnehin ROADMAP-Einträge ergänzt, als zusätzlichen Vorschlag anbieten.
- **[kosmetisch]** `appendConsoleLog` (`app.js:2179`) färbt nur bei Substring "fehler"/"error"/"❌" — der geplante Fehlerhinweis sollte diese Wortmarke enthalten, sonst erscheint er neutral statt rot.

---

## Empfohlene AK-Ergänzungen an den Plan

1. **AK-B1 (neu):** `N(x)`-Normalisierung beider Vergleichsseiten inkl. Bracket-Tag-Fall — `N(nas_show_folder) in {N(nas_match_folder), metadata_show_name}`.
2. **AK-B2 (neu):** Guard für fehlend/leer/Nicht-String `nas_show_folder` = Fallthrough auf heute-Verhalten; Test deckt es ab.
3. **AK-A1 (neu):** `res.json()` im bestehenden try; `populateLocalProfilesDropdown()` nicht-awaitend; Fehlertext mit Rot-Markierung.
4. **AK-Test: Backend** je zwei Asserts (Behauptung + Kontrolle ohne `nas_show_folder`), plus Bracket-Tag-Test.
5. **AK-Test: Frontend** Harness-Voraussetzungen festschreiben (Callback-Speicherung, Setter, URL-routender fetch-Mock, State-Reset).

---

## VERDICT: REVISE

**Einwände (nummeriert):**
1. **[kritisch]** Regel B vergleicht normalisiert gegen rohen `nas_match_folder` — "adopt NAS name" bricht die Schleife nicht für Ordnernamen mit trailing `[...]`-Tag/Underscore (`queue_api.py:758`, `series_helper.py:22`, `helpers.py:103-111`). Fix: beide Seiten normalisieren.
2. **[wichtig]** Gate muss fehlende/leere/Nicht-String `nas_show_folder` exakt als heute-Verhalten durchreichen (`queue_api.py:750-762`, `series_helper.py:44`).
3. **[wichtig]** A) `await populateLocalProfilesDropdown()` inline würde `closePreviewModal`/Prozessstart blockieren; `res.json()` muss im bestehenden try liegen; fire-and-forget erzwingen (`app.js:10559-10597`).
4. **[wichtig]** AK6-Frontend-Harness: bestehendes Mock speichert keinen Klick-Callback → Handler nicht auslösbar; `currentPreviewPayload` nicht exponierbar; fetch-Mock URL-diskriminierend nötig (`app_warning.test.js:31-33`, `app.js:10540-10541`).
5. **[wichtig]** AK2-4 drohen trivial-grün → je Test positive Kontroll-Assert (gleiche Fixture ohne `nas_show_folder` liefert Hinweis) + Bracket-Tag-Test.
6. **[kosmetisch]** Fehlerhinweis in A ohne "Fehler"/"❌"-Marker wird nicht rot gefärbt (`app.js:2179`).
7. **[kosmetisch]** ROADMAP-#66-Referenzen verifiziert korrekt; Session-interne Akteursnamen vor dauerhafter Übernahme ggf. neutralisieren.

**Restrisiken/nicht geprüft:** `resolve_series_folder_name`-Path-Traversal (vorbestehend, downstream via `is_path_allowed` gemildert, außerhalb Scope); stored XSS in `app.js:10283` (vorbestehend). Die eigentliche `/api/process`-Pfadvalidierung wurde für diesen Review nicht end-to-end getestet (nur statisch geprüft).
</task_result>
