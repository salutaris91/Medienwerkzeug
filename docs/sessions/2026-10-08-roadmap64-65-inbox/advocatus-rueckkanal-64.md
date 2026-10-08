# Rohoutput advocatus — Rückkanal-Abnahme #64, 2026-10-08

Hinweis Claude Code (2026-10-08): Mechanisch aus `opencode export ses_ee4eb3d2effef4wJApV8gwohQt` (ceo-planner, Rückkanal-Sitzung) abgelegt, nicht vom Moderator abgeschrieben (Lehre 59). Einzige Änderung: Trailing Whitespace am Zeilenende entfernt (Pre-Commit-Hook). Volle Prompts und Antworten: Kit `scripts/gate-a2/logs/2026-10-08-roadmap64-65-nachbesserung/export-rueckkanal.json`.

---

## advocatus: neue Risiken #64 (Subagent-Sitzung ses_ee4e87f5affekLfYUoIBFpNKTP, Status: completed)

<task id="ses_ee4e87f5affekLfYUoIBFpNKTP" state="completed">
<task_result>
## Advocatus-Befund — ROADMAP #64 (Head `1c8f7ad`, schreibgeschützt geprüft)

Ich habe den implementierten Code gelesen (`project_api.py:1299–1507`, `app.js:12259–12497`, `index.html:461–466`, `style.css:3835–3863`, beide Testdateien, `helpers.py:514–549`, `media.py:256–262`, `welcome.js`, `index.html:2758`/`app.js:6`).

**Kernaussage vorweg:** Ich finde **keinen neuen [kritisch]- oder [wichtig]-Abnahme-Blocker.** Die Substanz liegt in genau **einer** realen semantischen Kollision ([wichtig], aber dokumentiert → Backlog) plus einigen [kosmetisch]/Test-Robustheits-Punkten. Viele der im Briefing als Verdacht benannten Punkte sind nach Codeprüfung **entkräftet** (unten aufgeführt).

---

### A) Für Abnahme relevant — blockiert die Abnahme NICHT

Keine kritischen/wichtigen Blocker gefunden. Es existiert aber ein Punkt, der vor dem Merge bewusst abgewogen werden sollte (kein Code-Fix nötig, nur eine Entscheidung):

**A1. [wichtig] Semantik-Kollision „Größe": `total_size` (nur Videos) vs. `inbox_size_gb` (alle Dateien)**
- **Ort:** `project_api.py:1362–1373` (`total_size = sum(st.st_size)` nur über `video_files`, also nur `video_exts`) gegenüber `helpers.py:535–549` (`get_folder_size_bytes`, zählt **alle** nicht-versteckten Dateien außer Symlinks) bzw. `helpers.py:514–530` (`get_dir_size_gb`), die das Dashboard-`inbox_size_gb` speisen (`app.js:11986`).
- **Begründung:** Zwei verschiedene „Größen"-Begriffe. Der Sortier-Button „Größe" und die Meta-Zeile `formatBytes(item.total_size)` zeigen nur die Video-Summe; der Dashboard-Kopf zeigt die Gesamtgröße des Ordners (inkl. `.nfo`, `.srt`, `.jpg`, `extras/`-Unterordner). Die Summe der Listenwerte bleibt daher systematisch unter der Kopf-Gesamtgröße.
- **Repro-Gedanke:** Inbox-Ordner mit `film.mkv` (10 GB) + `extras/behind-the-scenes.mov` (2 GB, `.mov` ist zwar Video, aber z. B. `.iso`/`.vob`/große `.nfo` nicht) → Smart-Inbox zeigt „Größe 10 GB", Dashboard-Kopf „12 GB".
- **Einordnung:** Semantik ist in `API.md:142–143` und ADR-64-1 explizit so festgelegt („nur Videodateien") — also **kein unentdeckter Bug, sondern bewusste, aber aus UI-Sicht mehrdeutige** Entscheidung. Empfehlung: Label präzisieren (z. B. Tooltip „Videogröße") oder im Backlog dokumentieren, aber **kein Abnahme-Blocker**.

---

### B) ROADMAP-/Backlog-relevant (keine Abnahme-Relevanz)

**B1. [kosmetisch] `patch("os.stat")` global — latente Test-Nebenwirkung über `os.path.*`**
- **Ort:** `tests/test_inbox_suggestions.py:124` und `:153`.
- **Begründung:** `os.path.exists`, `os.path.isdir`, `os.path.getsize` delegieren intern an `os.stat` (über `genericpath`). Der globale Patch fängt also potenziell auch diese Aufrufe ab. **Aktuell harmlos**, weil (a) `get_video_codec` (`media.py:256–262`) über `subprocess`/ffprobe geht und **nicht** `os.stat` nutzt, und (b) kein gepatchter Pfad mit dem Mock-Schlüssel (`"S01E02"`) im Code-Pfad via `exists`/`isdir` geprüft wird. Es ist aber eine tickende Falle für künftige Erweiterungen: Sobald ein anderer Aufrufer im selben `with`-Block `os.path.exists` auf eine Datei mit dem Mock-Schlüssel prüft, wird der Test still falsch. Empfehlung (Backlog): enger patchen (nur `os.stat` für den relevanten Pfad) oder Mock auf `st_size`/`st_mtime`-Attribut-Ebene.

**B2. [kosmetisch] Cache-Globals Typ-Inkonsistenz: `_inbox_cache = {}` (dict) vs. Liste**
- **Ort:** `project_api.py:1174` (initial `{}`) gegenüber `:1504` (`_inbox_cache = suggestions`, Liste).
- **Begründung:** Das initiale `{}` wird zur Laufzeit nie zurückgegeben (`_inbox_cache_time = 0` → `now - 0 > 30`), also **kein Crash**. Aber es ist ein latenter Code-Smell: Jede künftige Stelle, die `_inbox_cache` als Liste liest (`len(...)`, Iteration), würde bei der Initialisierung überraschen. Zudem wird der Cache beim frühen `return []` (`:1310–1311`, fehlende/leere Inbox) **weder gelesen noch geschrieben** — jeder Request bei unkonfigurierter Inbox lädt `load_settings()` + `os.path.exists()` neu. Beides vorbestehend, durch #64 nur „berührt", nicht verursacht. Trivialer Fix (`= []`), aber kein Abnahme-Kriterium.

**B3. [kosmetisch] AK6-Testzeitstempel ist praktisch TZ-stabil**
- **Ort:** `tests/frontend/inbox_sort.test.js:426/433` (`1760000000` → erwartet `"09.10.2025"`).
- **Begründung:** `1760000000` = **09.10.2025, 08:53:20 UTC** — weit weg von Mitternacht. Der Test kippt nur in Zonen ≤ UTC-10 (z. B. Hawaii, UTC-10 → 22:53 am 08.10.). In UTC (GitHub-Actions-CI) und Berlin/CEST (Alex' Mac) ist er grün. **Kein reales Risiko**, nur als Restunsicherheit notiert.

**B4. [kosmetisch] `total_size = 0` bei lauter unlesbaren Dateien wird als „0 Bytes" angezeigt (nicht „unbekannt")**
- **Ort:** `project_api.py:1501` (`total_size: 0` bei allen `OSError`) → `app.js:12435–12436` (`formatBytes(0)` → „0 Bytes").
- **Begründung:** Ein Ordner mit unlesbaren Dateien erscheint in der Liste als „N Datei(en) · 0 Bytes" und sortiert bei „Größe ↑" ganz nach oben — obwohl die tatsächliche Größe unbekannt ist. AK2 legt genau das fest (fehlerhafte Datei zählt als 0), also spec-konform, aber UX-irreführend. `modified_at` verhält sich anders (wird `null` → ans Ende). Asymmetrie: Größe „0" sortiert oben, Datum „null" sortiert unten.

**B5. [Backlog] #65-Interaktion: `data-project` + `deleteProject(item.project)` vs. Pseudo-Gruppen**
- **Ort:** `app.js:12452` (`setAttribute("data-project", item.project)`) und `:12485` (`deleteProject(item.project)`).
- **Begründung:** Das #65-Briefing plant Pseudo-Einträge (Gruppen) mit synthetischem `project` = Gruppenname. Zwei Kollisionsflächen: (a) Ein Gruppenname, der zufällig einem realen Ordner gleicht, würde `deleteProject` auf den falschen Pfad lenken; (b) der Lösch-Button in `renderSmartInboxList` wird für jeden Eintrag generiert — Gruppen dürften keinen „Quarantäne"-Button tragen. Das ist #65-Scope, nicht #64, aber als Interaktions-Risiko für die nächste Stufe festzuhalten.

---

### Entkräftete Prüfpunkte (keine Findings)

- **eval-Testmuster** (`inbox_sort.test.js:220`): etabliertes Muster (wie `app_warning.test.js`), kein neues Risiko.
- **`sortInboxSuggestions`-Kopie via Spread** (`app.js:12264`): `[...items].sort()` kopiert flach, sortiert nur die Kopie; `currentSmartInboxRawSuggestions` bleibt unverändert — kein Mutation-Risiko.
- **`localeCompare` bei langen Listen** (`app.js:12267`): bei Inbox-typischen Größen (<100 Einträge) irrelevant; `sort` ist ohnehin O(n log n).
- **`int(max(mtime))` Rundung** (`project_api.py:1373`): Sekundenauflösung für Sortierung/Anzeige ausreichend; Truncation der Bruchteile unkritisch.
- **API-Kompatibilität älterer Clients** (`welcome.js:16–18`): `fetchSmartInboxSuggestions` reicht JSON durch, keine Feld-Annahmen; `modified_at`/`total_size` sind rein additiv (auch `null`/`0` dokumentiert). Kein Breaking.
- **Deployment-Cache-Buster:** korrekt synchron erhöht — `index.html:2758` → `app.js?v=95`, `app.js:6` → `./js/welcome.js?v=95`. Kein Misch-Versions-Risiko über den JS-Buster.
- **XSS:** `project`, `suggested_query`, `reasons` werden durchgängig `escapeHTML`-escaped (`app.js:12432/12457/12473`); `media_type` aus kontrolliertem Set. Kein Fund.

---

### Restunsicherheiten (was ich nicht prüfen konnte)

- **Keine Testausführung:** Ich habe `pytest` und `npm run test:frontend` **nicht** ausgeführt (schreibgeschützt, keine Befehlsausführung in dieser Prüfung). Die Aussagen zu TZ-Stabilität (B3) und Test-Nebenwirkungen (B1) beruhen auf Code-Analyse, nicht auf realer Laufzeit.
- **Kein Webzugriff / keine Live-NAS-Verifikation:** Deployment-/Cache-Verhalten (A1, Buster) nur statisch aus dem Code abgeleitet.
- **ROADMAP/API.md nicht vollständig auf bereits notierte `total_size`-Semantik geprüft** — falls die Kollision (A1) dort schon dokumentiert ist, reduziert sich ihr Neuigkeitswert entsprechend.

**Gesamturteil:** Keine neuen Blocker. Abnahme nicht blockiert durch die neuen Funde; A1 ist eine bewusst zu treffende Produktentscheidung (Label-Klarheit), B1–B5 sind Backlog-/Robustheits-Punkte ohne Merge-Relevanz.
</task_result>
</task>
