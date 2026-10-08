# Rohoutput plan-reviewer — Runde 1 (2026-10-06, Akt 2)

Geprüft: docs/sessions/2026-10-06-roadmap46-namenskonflikt/briefing.md (Entwurf v1).

Hinweis Claude Code (2026-10-07): Der Text unterhalb der nächsten Linie ist die wörtliche Subagent-Antwort aus der OpenCode-Sitzung (ceo-planner ses_eede285a6ffeLjfbSwIYSoRN4T, Subagent-Sitzung ses_eedcec876ffeTQX5Vvg1Zxok85; Quelle: opencode export, nur die <task>-Hülle entfernt). Wiederhergestellt nach Alex-Go, weil die zuvor archivierte Fassung vom Moderator bearbeitet worden war.

---

<task_result>
Alle Verifikationen sind abgeschlossen. Hier der Prüfbericht.

---

# Plan-Review: `briefing.md` (ROADMAP #46 + Namenskonflikt-Bugfix)

**Geprüft:** Formalia (8 Ritual-Vorgaben), Dissens-Abgleich gegen `advocatus.md` / `produktberater.md` / `grafiker.md` / `roadmap-neue-eintraege.md` / `00-kickoff.md`, und Stichproben aller Code-Behauptungen gegen den echten Code (read-only, keine Befehle).

## Formale Ritual-Prüfung

| # | Vorgabe | Ergebnis |
|---|---------|----------|
| 1 | Frontmatter exakt | ✅ Zeilen 1–8: `kind: plan`, `status: draft`, `approved_by: alex`, Platzhalter für `approved_on`/`approval_quote` (kein erfundener Freigabetext), `source: roadmap#46` |
| 2 | AK-Abschnitt | ✅ `## 3. Akzeptanzkriterien` (Z. 52), AK0–AK12 ausführbar formuliert |
| 3 | status: draft | ✅ |
| 4 | Dissens-Pflicht | ⚠️ formal erfüllt (alle 7 advocatus-Einwände, beide produktberater-Änderungen, grafiker-⚠️ zugeordnet) — **aber** die Auflösung des grafiker/advocatus-Dissenses ruht auf einer falschen Code-Behauptung (Finding 1) und produktberater-Änderung 1 ist nur teilweise aufgegangen (Finding 3) |
| 5 | Alex-Entscheidungen korrekt | ✅ (a) ADR 3 ist eine treue Präzisierung: selbst verifiziert, dass der rohe Vergleich den NAS-Button für Bracket-Tag-Ordner nicht entlastet (`N("Yu-Gi-Oh! [TMDB_TV]") = "Yu-Gi-Oh!"` ≠ roh); die Grenzfall-Konsequenz ist dokumentiert und Alex zur Kenntnis gegeben (Abschn. 8.2). (b) AK6/AK8 korrekt. (c) #64/#65/#66-Texte wortgleich gegen den Entwurf verifiziert (alle Alex-Elemente vorhanden), #67 klar als „nur mit Alex-Freigabe" markiert, Entry-Texte frei von Akteursnamen (Akteursnamen nur im nicht übernommenen Kopf) |
| 6 | Auftrags-Grenzen | ✅ keine Änderung an `clean_show_name` (utils.py:23), `clean_series_name_for_fs` (helpers.py:97), Suchlabels (mw_metadata.py:233/:398), `resolve_series_folder_name` (series_helper.py:35); keine Server-Änderung für #46; keine Migration; bestehende Tests nur ergänzen; Worker fasst briefing/ROADMAP/STAND/VERLAUF nicht an; `.env` nie |
| 7 | Git-Preflight | ✅ formal vollständig: wörtliche Ausgabe (Branch `feat/roadmap-46-namenskonflikt`, HEAD 3522ef2, untracked nur Session-Ordner), kein main, kein Commit ohne Alex-Go, Ausführung über repo-operator, kein `git add -A`, Beifang benannt |
| 8 | Lizenz/Referenzen | ✅ Abschnitt 7 vorhanden und vollständig; kein Third-Party-Code/Asset; grafikers UX-Referenzen korrekt als rein qualitativ deklariert; keine unklaren Lizenzen |

## Inhaltliche Code-Prüfung (eigene Verifikation)

**Bestätigt (Auswahl):** `app.js:10569` fetch ohne `response.ok` (Ergebnis komplett ignoriert) · `populateLocalProfilesDropdown` app.js:12385 mit eigenem try/catch (12389–12413) · Auto-Scroll app.js:2189–2190 · `system_api.py:230-240` (HTTP 200 + `{"success": false}`; 400 bei fehlenden Parametern) · `queue_api.py` Routen 19–20, `nas_show_folder` 407, resolve 412–421, Mismatch-Block 749–762, `metadata_show_name` 756 · `series_helper.py:44-46` = N() exakt, `find_existing_series_folder_by_id` liefert rohen `os.listdir`-Namen (Z. 22) · Buttons 10286–10313 (10298 `nas_name`, 10312 `metadata_name`, je `openPreviewModal`), POST 10260, XSS-Stelle 10283 · **exakt 10** `?v=93`-Stellen selbst gezählt (index.html:2752 + app.js:1–9), `style.css?v=47`/`utilities.css?v=1` unverändert, kein Service Worker, `cache_busting.test.js` erzwingt Gleichheit · `test_utils.py:3047/3123` senden kein `nas_show_folder` (Klasse ab Z. 18) — mit ADR 3/AK 9 (Guard-Fallthrough) bleibt ihr Verhalten unverändert, AK1 hält · `app_warning.test.js:31-33` zählt nur (Callbacks werden nicht gespeichert), `:113` Setter-Muster — Harness-Kritik des Briefings ist zutreffend · ROADMAP.md endet bei #63 (Z. 1782, Dateiende 1793) · `processor.py:3120` `is_path_allowed` (Risiko-Notiz 3 korrekt) · `package.json` `test:frontend` existiert.

**Widerlegt:** Die Behauptung „❌ sichert Rot-Einfärbung via `app.js:2179`" (AK7) — siehe Finding 1.

**AK2-Pflichtlogik:** NAS-Button: `nas_name` **ist** `nas_match_folder` (queue_api.py:760) → `N(nas_name) == N(nas_match_folder)` gilt immer (identische Eingabe, deterministische Funktion). Metadaten-Button: erfordert `N(metadata_show_name) == metadata_show_name` — gilt für alle realistischen Eingaben, **nicht exakt** in zwei pathologischen Randklassen (Finding 2).

## Findings

### Blocker (vor Freigabe lösen)

1. **[wichtig]** Falsche Code-Behauptung in AK7 und Dissens-Auflösung: „❌ sichert Rot-Einfärbung via `app.js:2179`" (briefing.md:95-99) bzw. „appendConsoleLog (app.js:2179) nur bei ❌/„fehler"/„error" rot einfärbt — ⚠️-Zeile wäre neutral grau" (briefing.md:225-231). Tatsächlich ist `app.js:2177-2179` eine if/**else-if**-Kette: Zeilen mit `[System]`-Präfix erhalten die Klasse `system-line` (Farbe `var(--accent)`, `style.css:1387-1389`) und erreichen den ❌-Zweig **nie**. Beide AK7-Texte beginnen wörtlich mit `[System]:` → sie erscheinen in Akzentfarbe, nicht rot. Die ⚠️→❌-Entscheidung (Dissens grafiker vs. advocatus, begründet mit „Rot ist die etablierte Sichtbarkeitsfarbe") ruht damit auf einer falschen Prämisse — ⚠️ und ❌ wären visuell identisch. Auch advocatus Finding 6 selbst beruht auf demselben Misslesen; das Briefing hat die Selbstauskunft unverifiziert übernommen. Fix vor Freigabe: Begründung korrigieren (❌ nur als semantisches Icon, Farbe bleibt Akzent — konsistent zur bestehenden Konvention `app.js:6399`/`6726`) **oder** `[System]`-Präfix weglassen, damit der ❌-Zweig tatsächlich greift (Abweichung von der Konvention) — Alex-Entscheidung im finalen Planreview.

### Sollte behoben werden

2. **[kosmetisch]** N ist nicht exakt idempotent (ADR 3 / AK3-Implikatur „`nas_show_folder = metadata_name` → kein Hinweis"): zwei Randklassen, in denen `N(metadata_name) ≠ metadata_show_name` → der Metadaten-Button bricht die Schleife dort nicht (Verhalten = heute, keine Regression, aber der Fix greift nicht): (i) eine der fünf Suffixphrasen aus `helpers.py:101` mit Unterstrichen statt Leerzeichen (Regex verlangt `\s+`; die Unterstrich-Ersetzung `helpers.py:109` erzeugt den Treffer erst beim zweiten Durchlauf — die App selbst hängt die Suffixe nur mit Leerzeichen an, `search_api.py:376-435`, also nur bei manuell getippten Namen); (ii) `clean(show_name)` > 160 Zeichen und der Schnitt (`helpers.py:212`) landet exakt nach einem mitten im Namen stehenden `"]"` — der Schnitt erzeugt einen neuen trailing Bracket-Tag, den der zweite N-Durchlauf stript. Empfehlung: als dokumentierten Grenzfall in ADR 3 aufnehmen.

3. **[kosmetisch]** produktberater-Änderung 1 (expliziter Testfall „`nas_show_folder` mit trailing spaces trotzdem Match") ist nur teilweise in AK2 aufgegangen: die Bracket/Underscore-Fixture verifiziert das Cleaning auf beiden Seiten, aber der konkrete trailing-spaces-Fall ist kein AK-Punkt. Die Dissens-Darstellung „beide geforderten Änderungen … sind in AK2/AK6 aufgegangen" (briefing.md:236-238) ist damit leicht überhöht — entweder die Variante in AK2/AK3 aufnehmen oder als bewusst nicht übernommen dokumentieren.

### Optional

4. **[kosmetisch]** AK5-Gloss „Hinweis genau dann, wenn `nas_match_folder != metadata_show_name`" (briefing.md:78-79) unterschlägt die Truthiness-Bedingung (`if nas_match_folder and …`, queue_api.py:758): ohne gefundenen Ordner feuert kein Hinweis, obwohl `None != String`. Die operative Spec („wie heute") bleibt korrekt; nur die Klammer ist unpräzise.

## Potenziale (nicht Teil der Prüfung, keine Umsetzungsempfehlung ohne Alex-Go)

- Falls Rot tatsächlich gewünscht: statt des Präfix-Droppings wäre langfristig eine Trennung von Präfix-Styling und Fehler-Icon in `appendConsoleLog` denkbar (Zweig-Reihenfolge) — Out-of-Scope für #46, ggf. als Notiz in der #66-Session.
- Der Grenzfall aus Finding 2 gehört inhaltlich zur #66-Namensbereinigungs-Thematik und könnte dort als Hinweis mitreisen.
- Die trailing-spaces-Variante (Finding 3) wäre eine Zeile in AK2/AK3.

## Restrisiken / nicht ausgeführte Prüfungen

- **Git-Zustand nicht unabhängig verifizierbar** (keine Befehle erlaubt): Branch/HEAD/untracked nur anhand der wörtlichen Ausgabe im Briefing geprüft — diese ist intern konsistent (Upstream `origin/main` passt zur Status-Zeile; Worktree-Name passt zum Branch).
- **Tests nicht ausgeführt:** AK0/AK11-Grün-Behauptungen und die Ausnahme `test_conversion_estimation_test_encode` sind unplausibel-prüfbar nur durch einen echten Lauf.
- Idempotenz-Analyse (Finding 2) rein statisch gegen `helpers.py:97-111`/`208-213`; keine Ausführung von N gegen die Gegenbeispiele.

---

**VERDICT: REVISE**

1. [wichtig] AK7/Dissens: Falsche Code-Behauptung „❌ sichert Rot-Einfärbung via app.js:2179" — `[System]`-Präfix-Zweig (app.js:2177, style.css:1387-1389 `var(--accent)`) macht den ❌-Zweig für beide AK7-Texte unerreichbar; die ⚠️→❌-Dissens-Auflösung (briefing.md:95-99, 225-231) ruht auf dieser falschen Prämisse. Vor der Freigabe korrigieren (Rationale anpassen oder Präfix entfernen — Alex-Entscheidung).
2. [kosmetisch] N nicht exakt idempotent (ADR 3/AK3): zwei pathologische Randklassen (Unterstrich-Suffixphrasen; 160-Zeichen-Schnitt exakt nach mid-string `"]"`), in denen der Metadaten-Button die Schleife nicht bricht — als Grenzfall dokumentieren (helpers.py:101/:109/:212).
3. [kosmetisch] produktberater-Änderung 1 (trailing-spaces-Match-Testfall) nur teilweise in AK2 aufgegangen; „beide Änderungen aufgegangen" (briefing.md:236-238) leicht überhöht.
4. [kosmetisch] AK5-Gloss (briefing.md:78-79) omittiert die Truthiness-Bedingung `if nas_match_folder and …` (queue_api.py:758).
</task_result>

---

# Rohoutput plan-reviewer — Runde 2 (Korrekturstellen-Verifikation)

Ausgabe ungekürzt.

Hinweis Claude Code (2026-10-07): Der Text unterhalb der nächsten Linie ist die wörtliche Subagent-Antwort aus der OpenCode-Sitzung (ceo-planner ses_eede285a6ffeLjfbSwIYSoRN4T, Subagent-Sitzung ses_eedcec876ffeTQX5Vvg1Zxok85; Quelle: opencode export, nur die <task>-Hülle entfernt). Wiederhergestellt nach Alex-Go, weil die zuvor archivierte Fassung vom Moderator bearbeitet worden war.

---

<task_result>
# Plan-Review Runde 2: Korrekturstellen-Verifikation

## 1. Verifikation der vier Korrekturstellen (eigene Code-Prüfung)

**Korrektur 1 — AK7 + Dissensblock (Runde-1-Einwand 1, [wichtig]): ✅ ausgeräumt.**
- AK7 (briefing.md:98-105) behauptet jetzt: ❌ als semantisches Icon, `[System]`-Präfix-Zeilen durchlaufen den ersten Zweig der if/else-if-Kette `app.js:2177`, erscheinen in system-line-Akzentfarbe (`style.css:1387-1389`). **Verifiziert:** `app.js:2177` (`if (line.startsWith("[System]") || …)`) und `style.css:1387-1389` (`.console-line.system-line { color: var(--accent); }`) — korrekt.
- Die Zahl „**14 bestehende `[System]: ❌` Fehlerzeilen**" habe ich selbst nachgezählt: **exakt 14** appendConsoleLog-Zeilen (app.js:6399, 6403, 6726, 6730, 6757, 6761, 7865, 7867, 7881, 7883, 7895, 7897, 7933, 7961). Die genannten Beispiele 6399/6726 sind darunter. Zahl und Beispiele stimmen.
- Dissensblock (briefing.md:242-260): korrigierte Faktenlage ist code-exakt (else-if-Kette, ❌-Zweig für beide Textvarianten unerreichbar, ⚠️ und ❌ identisch eingefärbt); „Rot-Sichtbarkeits"-Begründung ausdrücklich verworfen; Lehren-Eintrag zur unverifizierten Übernahme von advocatus Finding 6 vorhanden; neue Frage 3 (Abschnitt 8) mit Empfehlung, Trade-off und Alex-Entscheidung — konsistent mit dem Dissensblock („Empfehlung: nein" ↔ „Empfehlung: Präfix behalten").
- Frage 3 (briefing.md:319-324): „Für echtes Rot müsste die Zeile ohne `[System]`-Präfix loggt werden (else-if-Kette, `app.js:2177-2179`)" — verifiziert korrekt (Zweig 2179-2180 setzt `var(--danger)` nur ohne Präfix).

**Korrektur 2 — ADR 3 Idempotenz-Grenzfälle (Einwand 2, [kosmetisch]): ✅ im Kern ausgeräumt, ein Präzisierungsrest (siehe Finding).**
- Beide Grenzfälle mit korrekten Zeilenangaben dokumentiert: `helpers.py:101` (fünf Suffix-Phrasen — verifiziert, es sind genau fünf Alternativen in der Regex), `helpers.py:109` (Unterstrich-Ersetzung), `helpers.py:212` (Kürzungsschnitt `name[:max_len].strip()`). Einordnung „Verhalten wie heute, keine Regression, Fix greift dort nicht, Grundursache #66" — korrekt.
- **Aber** der neue Halbsatz „beide Klassen entstehen nicht, wenn die Buttons die von der App selbst erzeugten Namen zurückspielen" (briefing.md:197-198) ist für Grenzfall (ii) unzutreffend — siehe Finding 1.

**Korrektur 3 — AK2 trailing-spaces-Zusatzvariante (Einwand 3, [kosmetisch]): ✅ ausgeräumt.**
- AK2 (briefing.md:69-70): `nas_show_folder = nas_name + "  "` muss den Hinweis ebenfalls unterdrücken — logisch korrekt: `N` strippt führend (`str(x).strip()`), also `N(nas_name + "  ") == N(nas_name) == N(nas_match_folder)` → Unterdrückung. Ausführbar/testbar.
- Dissensblock produktberater (briefing.md:265-269) jetzt ehrlich: „Erstdraft enthielt ihn nur implizit über die Bracket-Fixture — vom plan-reviewer in Runde 1 beanstandet und nachgezogen." Entspricht den Fakten.

**Korrektur 4 — AK5 Truthiness (Einwand 4, [kosmetisch]): ✅ ausgeräumt.**
- AK5 (briefing.md:78-82): „Hinweis genau dann, wenn `nas_match_folder` gefunden WURDE und von `metadata_show_name` abweicht (heutige Truthiness-Bedingung `if nas_match_folder and …`, `queue_api.py:758`)" — verifiziert: `queue_api.py:758` lautet exakt `if nas_match_folder and nas_match_folder != metadata_show_name:`. Exakt korrekt.

**Neuer Dissens-Eintrag [plan-reviewer] Runde 1 (briefing.md:270-275):** korrekte Wiedergabe aller vier Einwände mit korrekten Schweregraden ([wichtig], 3× [kosmetisch]) und korrekten Zuordnungen. Dissens-Pflicht weiterhin erfüllt — auch der Reviewer-Dissens ist jetzt dokumentiert.

## 2. Verschlechterungs-Stichproben

- **Frontmatter (Z. 1-8): unverändert** ✓ — `kind: plan`, `status: draft`, `approved_by: alex`, Platzhalter `approved_on`/`approval_quote` (kein erfundener Freigabetext), `source: roadmap#46`.
- **AK-Durchnummerierung:** AK0-AK12 lückenlos, in Reihenfolge, keine Duplikate ✓; konsistent mit Abschnitt 11 („AK0-AK11") und AK12 als PR-Ebene.
- **Abschnitt 6:** Offene Risiken 1-5 unverändert ✓; advocatus-Auflösung unverändert bis auf den Verweis-Schluss („formeller Abschluss durch die plan-reviewer-Runden, dokumentiert unten" — verweist jetzt korrekt auf den Eintrag im selben Abschnitt statt des früher ungenauen „Abschnitt 9"; Verbesserung).
- **Abschnitt 8:** Frage 1 unverändert; Frage 2 neu gefasst — **korrekt** („zwei pathologische Idempotenz-Grenzfälle … = Verhalten wie heute, Fix greift dort nicht" — ohne den problematischen Halbsatz aus ADR 3); Frage 3 neu mit Empfehlung/Trade-off/Alex-Entscheidung ✓; Schlussabsatz unverändert ✓.
- **ADRs 1, 2, 4, 5, 6: unverändert** ✓; ADR 3 nur in den Konsequenzen erweitert — Entscheidung/Alternativen/Begründung unangetastet → **Alex-Treue (a) nicht verschlechtert**; die Erweiterung dokumentiert nur, verhandelt nichts neu. (b) AK6/AK8 und (c) AK12 unverändert ✓. Frage 3 ist eine legitime neue Frage aus der korrigierten Faktenlage, keine Neuverhandlung von Alex' Entscheidung (b) — Farbe war nie Teil seiner Entscheidung.
- **Grenzen (Abschnitte 4/11), Git-Preflight (Abschnitt 10), Lizenzen (Abschnitt 7): unverändert** ✓.
- **Zusätzlich verifiziert:** Die Verworfens-Begründung „⚠️-Variante … ohne Konventionsvorbild" ist gedeckt — mein grep über `appendConsoleLog` mit ⚠️ liefert **null** Treffer; es existiert keinerlei ⚠️-Vorbild in der Konsole.

## Findings

### Blocker
Keine.

### Sollte behoben werden
Keine.

### Optional
1. **[kosmetisch]** ADR 3 (briefing.md:196-198): Der Halbsatz „beide Klassen entstehen nicht, wenn die Buttons die von der App selbst erzeugten Namen zurückspielen" ist für Grenzfall **(ii) unzutreffend**: Der Grenzfall entsteht gerade beim Zurückspielen des App-erzeugten `metadata_show_name` (queue_api.py:756/761), nämlich wenn `clean(show_name)` > 160 Zeichen ist und der Schnitt (`helpers.py:212`) exakt nach einem mitten im Namen stehenden `"]"` landet. Für Grenzfall (i) ist der Halbsatz korrekt (die App hängt die Suffixe ausschließlich mit Leerzeichen an, `search_api.py:376-435`). Kernaussagen (pathologisch, Verhalten wie heute, keine Regression, #66) und die entscheidungsrelevante Spiegelung in Abschnitt 8 Frage 2 bleiben korrekt. Präzisierungsvorschlag: „Klasse (i) entsteht nicht mit App-erzeugten Suchlabels; Klasse (ii) entsteht auch mit App-erzeugten Namen, aber nur bei >160-Zeichen-Namen mit unglücklichem Schnitt."

**Notiz (kein Einwand):** Frage 3 könnte Alex' Entscheidungsgrundlage vervollständigen: Für die Rot-Variante (❌ ohne `[System]`-Präfix) existieren bereits **8 bestehende Vorbilder** in der Konsole (app.js:6248, 7051, 7054, 7476, 7479, 10648, 15222, 15227 — alle tatsächlich rot via Zweig 2179). Die Empfehlung („Präfix behalten") wird dadurch nicht geschwächt — beide Muster sind in der Codebasis etabliert, das `[System]: ❌`-Muster ist das häufigere bei Systemfehlern.

## Restrisiken / nicht ausgeführte Prüfungen

- Git-Zustand weiterhin nur anhand der wörtlichen Ausgabe im Briefing prüfbar (keine Befehle erlaubt) — unverändert zu Runde 1.
- Tests nicht ausgeführt (AK0/AK11 bleiben Worker-Pflicht).
- Die 14er-Zählung umfasst ausschließlich `appendConsoleLog`-Zeilen mit `[System]: ❌`-Präfix; die weiteren ❌-Vorkommen (app.js:12099-12103, 16617) laufen über `textContent` außerhalb der Konsole und sind für die Konventionsaussage irrelevant.

---

**VERDICT: APPROVE**

1. [kosmetisch] ADR 3 (briefing.md:196-198): Halbsatz „beide Klassen entstehen nicht, wenn die Buttons die von der App selbst erzeugten Namen zurückspielen" ist für Grenzfall (ii) falsch — der Fall entsteht gerade mit dem App-erzeugten `metadata_show_name` bei >160-Zeichen-Namen mit unglücklichem Schnitt (`helpers.py:212`); für (i) korrekt. Präzisieren (Empfehlung, kein Blocker — Abschnitt 8 Frage 2 ist korrekt formuliert, keine Auswirkung auf AKs/Worker-Auftrag).

Alle vier Runde-1-Einwände sind ausgeräumt (Einwand 1 [wichtig] vollständig durch code-korrekte AK7/Dissens-Fassung inkl. verifizierter 14 Vorbilder; Einwände 2-4 durch Dokumentation/Zusatzvariante/exakte Truthiness-Formulierung). Keine Verschlechterung an Frontmatter, AK-Nummerierung, Abschnitten 6/8, ADRs, Alex-Treue, Grenzen, Git-Preflight oder Lizenzabschnitt. Der verbleibende kosmetische Punkt kann Alex beim finalen Planreview zur Kenntnis nehmen oder vor Freigabepunkt 2 präzisieren lassen.
</task_result>

---

**Nachtrag Moderator (nach Runde 2, vor Freigabepunkt 2):** Der kosmetische Einwand 1 wurde im Briefing präzisiert (ADR-3-Konsequenzen jetzt: Klasse (i) nur bei manuell getippten Namen, Klasse (ii) auch bei App-Namen >160 Zeichen mit unglücklicher Schnittstelle); die „Notiz" zu den 8 Rot-Vorbildern wurde in Abschnitt 8 Frage 3 ergänzt.
