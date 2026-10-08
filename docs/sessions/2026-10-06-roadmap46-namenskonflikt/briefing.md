---
kind: plan
status: approved
approved_by: alex
approved_on: 2026-10-07
approval_quote: "Ja, ich folge deinen Empfehlungen vollständig."
source: roadmap#46
---

# Feature Briefing: ROADMAP #46 Profil-Dropdown live aktualisieren + Bugfix Endlosschleife beim Namenskonflikt-Hinweis

## 1. Problemstellung

**Teil A — ROADMAP #46 (Profil-Dropdown):** Speichert die Serien-Vorschau beim
Ausführen ein Profil (`gui/static/app.js:10569`, `POST /api/profile`), wird das
clientseitige Dropdown `series-local-profile-select` nicht aktualisiert — der
Nutzer muss F5 drücken, um das neue Profil zu sehen. Zudem wird `response.ok`
nicht geprüft: HTTP-Fehler und Abweisungen bleiben still. Wichtig: Das Backend
(`gui/api/system_api.py:230-240`, `_post_profile_logic`) liefert auch bei
fehlgeschlagener Speicherung **HTTP 200** mit `{"success": false}` — "Erfolg"
bedeutet `response.ok` **UND** `data.success === true`.

**Teil B — Bug Endlosschleife Namenskonflikt:** `gui/api/queue_api.py:749-762`
(im `/preview_process`-Handler) meldet `show_name_mismatch`, wenn der per
Show-ID gefundene NAS-Ordner (`nas_match_folder`, roh aus dem Dateisystem)
vom bereinigten Metadatenamen (`metadata_show_name`) abweicht — ohne das
Request-Feld `nas_show_folder` zu beachten (Zeile 407 gelesen, nur an
`resolve_series_folder_name` übergeben). Die beiden Buttons des Hinweises
(`app.js:10286-10313`) setzen `basePayload.nas_show_folder` auf genau einen
dieser Namen und öffnen die Vorschau neu (`app.js:10260` POSTet die
basePayload) → der Server meldet denselben Hinweis erneut → Endlosschleife.

**Teil C — Herkunft der Namensverschmutzung „… 2010 US TMDB TV" (nur
dokumentieren, Behebung = ROADMAP #66):** Suchlabel
`gui/mw_metadata.py:233` (`f"{title} ({year}) [{country}]"`) und `:398`
(`f"{r['name']} [{provider.upper()}]"`) → `clean_show_name`
(`gui/core/utils.py:23`) entfernt nur die Klammern, lässt den Inhalt als
Klartext im Dateinamen → `clean_series_name_for_fs`
(`gui/core/helpers.py:97`) stript beim Laden nur *trailing* `[...]`-Tags.

**Teil D — ROADMAP-Texte #64–#66 (nur Backlog-Einträge, keine
Implementierung; Inhalt von Alex entschieden, Kickoff 06.10.2026):**
Wortentwurf in `docs/sessions/2026-10-06-roadmap46-namenskonflikt/roadmap-neue-eintraege.md`.
Optional mit Alex-Freigabe: #67 (XSS-Härtung, advocatus-Befund dieser Session).

## 2. Zielnutzer

Alex als Einzelnutzer beim Serienimport über die Sendezentrale: neues Profil
sofort im Dropdown ohne Seiten-Neuladen; Namenskonflikt-Hinweis blockiert den
Import nicht mehr in einer Schleife, wenn er „Namen übernehmen" klickt.

## 3. Akzeptanzkriterien

Alle Backend-Tests in `tests/test_utils.py::TestMediawerkzeugLogic`
(gleiche Vorrichtung `self.test_dir`, DummyHandler +
`GUIRequestHandler.handle_api_preview_process`-Fassade, `utils._MOCK_SETTINGS`,
gemocktes `fetch_tmdb_tv` — Vorbilder: Zeilen 3047 und 3123).

- [ ] **AK0 Ausgangsmessung:** `pytest` und `npm run test:frontend` VOR jeder
      Änderung ausführen; wörtliche Ausgabe im Worker-Protokoll.
- [ ] **AK1 Bestandsschutz:** `test_find_folder_by_id_and_name_mismatch` und
      `test_false_positive_show_name_mismatch_with_different_years` bleiben
      unverändert grün (beide senden kein `nas_show_folder` → müssen das
      heutige Verhalten behalten).
- [ ] **AK2 Override == NAS-Ordner:** Fixture mit NAS-Ordner, der per Show-ID
      gefunden wird und dessen roher Name `[...]`-Tags/Underscores enthalten
      DARF; `params["nas_show_folder"] = nas_name` (der aus dem Hinweis
      gelieferte Wert) → `assertNotIn("show_name_mismatch", result)`.
      Zusatzvariante (produktberater-Änderung 1): `nas_show_folder = nas_name
      + "  "` (trailing spaces) muss denselben Hinweis ebenfalls unterdrücken.
      Kontroll-Assert zwingend: dieselbe Fixture OHNE `nas_show_folder` →
      `assertIsNotNone(result.get("show_name_mismatch"))`.
- [ ] **AK3 Override == Metadatenname:** `nas_show_folder = metadata_name` →
      kein Hinweis; Kontroll-Assert wie AK2.
- [ ] **AK4 Dritter Name:** `nas_show_folder = "Komplettnamens-Ausweichwert"`
      (nach keiner Bereinigung gleich den beiden Kandidaten) → Hinweis bleibt
      erhalten, Felder `nas_name`/`metadata_name` unverändert.
- [ ] **AK5 Leeren-/Typ-Guard:** `nas_show_folder` fehlend, `""`,
      Whitespace-only und Nicht-String-Typen (`123`, `None`, `[]`) verhalten
      sich exakt wie heute: Hinweis genau dann, wenn `nas_match_folder`
      gefunden WURDE und von `metadata_show_name` abweicht (heutige
      Truthiness-Bedingung `if nas_match_folder and …`, `queue_api.py:758`).
- [ ] **AK6 Frontend-Profil-Save (neu `tests/frontend/profile_dropdown_refresh.test.js`),
      vier Fälle:** (a) `ok:true` + `{"success":true}` →
      `populateLocalProfilesDropdown`-Aufruf (Zähler), KEIN Fehler-Log;
      (b) `ok:true` + `{"success":false}` → `appendConsoleLog`-Fehlerhinweis,
      KEIN Dropdown-Aufruf; (c) `ok:false` (4xx/5xx) → Fehlerhinweis, kein
      Dropdown-Aufruf; (d) Exception (Netzwerk/ungültiges JSON) →
      Fehlerhinweis, Verarbeitung läuft weiter (Prozessstart wird erreicht).
      Harness-Voraussetzungen (von advocatus verifiziert, zwingend):
      Mock-`addEventListener` speichert Klick-Callbacks (Vorbild
      `app_warning.test.js:31-33` zählt nur — mustertauglich erweitern),
      Setter für module-scoped `currentPreviewPayload` (Muster
      `setNfoAgentScanData`, `app_warning.test.js:113`), fetch-Mock routet
      URL-diskriminierend `/api/profile` (POST), `/api/profiles` (GET),
      `/api/process` (POST) mit Call-Zählern, `allLocalProfiles`/DOM-State
      wird pro Test zurückgesetzt.
- [ ] **AK7 Fehlertexte (wörtlich; das ❌ ist ein semantisches Icon — Zeilen mit
      `[System]`-Präfix durchlaufen den Ersten Zweig der if/else-if-Kette
      `app.js:2177` und erscheinen in system-line-Akzentfarbe
      (`style.css:1387-1389`), exakt wie die 14 bestehenden `[System]: ❌`
      Fehlerzeilen, z. B. `app.js:6399`, `6726`):** HTTP-Fehler/Exception:
      `[System]: ❌ Profil konnte nicht gespeichert werden (Verbindungsfehler). Einstellungen gelten nur für diesen Lauf.`
      success:false:
      `[System]: ❌ Profil wurde nicht gespeichert. Einstellungen gelten nur für diesen Lauf. Nach Neuladen erneut versuchen.`
- [ ] **AK8 Implementierungsform Teil A:** `const response = await fetch(...)`;
  `response.json()`-Parse und Auswertung INNERHALB des bestehenden `try`
  (ab `app.js:10560`); `catch` führt zusätzlich `appendConsoleLog` aus
  (bestehendes `console.error` bleibt); bei Erfolg
  `populateLocalProfilesDropdown()` **ohne await** (fire-and-forget);
  `closePreviewModal()`/Verarbeitungsstart laufen in jedem Fall weiter.
- [ ] **AK9 Implementierungsform Teil B:** Unterdrückung nur bei
  `isinstance(nas_show_folder, str) and nas_show_folder.strip()`;
  Normalisierung `N(x) = limit_filename_length(clean_series_name_for_fs(str(x).strip()))`;
  kein Hinweis genau dann, wenn `N(nas_show_folder)` gleich
  `N(nas_match_folder)` ODER gleich `metadata_show_name`; sonst bestehende
  Logik unverändert. Keine Änderungen an `resolve_series_folder_name`,
  `clean_series_name_for_fs`, `clean_show_name`, Suchlabels.
- [ ] **AK10 Cache-Busting:** alle **10** Vorkommen `?v=93` → `?v=94`
  (`gui/static/index.html:2752` + `gui/static/app.js:1-9`);
  `cache_busting.test.js` bleibt grün; `style.css?v=47`/`utilities.css?v=1`
  bleiben unverändert (advocatus verifiziert: keine weiteren v93-Referenzen,
  kein Service Worker).
- [ ] **AK11 Abschlussmessung:** `pytest` + `npm run test:frontend` grün;
  Abweichungen gegen AK0 wörtlich erklärt; bekannte Ausnahme im
  Worker-Container: `test_conversion_estimation_test_encode`.
- [ ] **AK12 (PR-Ebene, NICHT Worker-Auftrag):** `ROADMAP.md` erhält die
  Einträge #64–#67 (Text ab „## 64." bis Ende #67 aus
  `roadmap-neue-eintraege.md`, wortgleich; #67 von Alex freigegeben am
  07.10.2026). Ausführung: `repo-operator` nach Alex-Go; der Gate-A2-Worker
  fasst ROADMAP.md nicht an.

## 4. Bewusst verworfen (Scope-Eingrenzung)

- **Server-Seitige Live-Push-Infrastruktur für #46** (SSE/WebSocket): F5 reichte
  bisher als Workaround; Client-Refresh nach Speichern ist der MVP-Weg (Alex
  entschieden).
- **Implementierung von #64/#65/#66:** nur Backlog-Texte in diesem PR (Alex
  entschieden; „keine Migration"-Grenze würde #66-Implementierung widersprechen).
- **Änderung an `clean_show_name`, `clean_series_name_for_fs`, Suchlabels,
  Profil-Dateinamen, `resolve_series_folder_name`:** Grundursache gehört zu #66
  (Profil-Entkopplung); hier nur Dokumentation der Kette.
- **XSS-Fix `app.js:10283` als Codeänderung in diesem PR:** vorbestehender
  advocatus-Befund, bewusst ausgelagert als Vorschlag für ROADMAP-#67 (keine
  Codeänderung ohne eigenen Test-Auftrag).
- **Case-insensitive Namensvergleiche:** verworfen — würde echte Abweichungen
  verschleiern (advocatus Finding 6); manuell anders getippte Namen gelten als
  dritter Name → Hinweis bleibt (gewollt).
- **Getrennte PRs je Teil:** verworfen nach produktberater — alle Teile klein,
  nicht konfliktär; Trennung vervielfacht Alex' Review-Overhead.
- **Modal/Toast bei Profil-Speicherfehler:** verworfen — Alex entschieden
  `appendConsoleLog`, Ausführung läuft weiter.

## 5. ADR-Blöcke

**ADR 1 — Erfolgskriterium Profil-Save: `response.ok && data.success`**
- Entscheidung: Dropdown-Refresh nur, wenn HTTP ok UND JSON `success === true`.
- Alternativen: nur `response.ok` prüfen (verworfen: `_post_profile_logic`
  liefert bei `save_show_profile()==False` HTTP 200 `{"success": false}` —
  Fehler blieben sonst weiter unsichtbar, genau der #46-Schmerz).
- Begründung: Code-verifiziert (`system_api.py:230-240`); produktberater und
  advocatus unabhängig identisch.
- Konsequenzen: Frontend-Test muss beide Ebenen mocken (AK6 a/b).

**ADR 2 — Fire-and-forget für `populateLocalProfilesDropdown()`**
- Entscheidung: Aufruf ohne `await` nach dem Save-Erfolg.
- Alternativen: `await` vor `closePreviewModal` (verworfen: blockiert
  Verarbeitungsstart, wenn `/api/profiles` hängt — advocatus Finding 3);
  paralleles `Promise.all` (verworfen: unnötige Komplexität).
- Begründung: Alex' Vorgabe „Ausführung läuft weiter" + eigene Fehlerabstattung
  der Funktion (`app.js:12389-12413`).
- Konsequenzen: Restrisiko bleibt, dass ein interner Fehler des Dropdown-Lades
  still in `console.error` endet (dokumentiert, Abschnitt 6).

**ADR 3 — Doppel-Normalisierung `N()` auf BEIDEN Vergleichsseiten**
- Entscheidung: `N(nas_show_folder) in {N(nas_match_folder), metadata_show_name}`
  mit `N(x) = limit_filename_length(clean_series_name_for_fs(str(x).strip()))`
  (identisch `series_helper.py:44-46`).
- Alternativen: Alex' Regel wörtlich mit rohem `nas_match_folder` vergleichen
  (verworfen: [kritisch] advocatus Finding 1 — „NAS-Namen übernehmen" würde
  bei Ordnernamen mit `[...]`-Tags/Underscores die Schleife weiterführen, weil
  der Client den rohen Namen zurückschickt, der Server ihn aber normalisiert).
- Begründung: Präzisierung der von Alex entschiedenen Regel, Absicht
  („kein Hinweis bei Übereinstimmung mit NAS-Ordner oder Metadatenname")
  bleibt exakt erhalten; nur der Vergleichsweg wird korrekt.
- Konsequenzen: Ein „dritter" Name, der nach Normalisierung mit dem
  NAS-Ordner kollidiert, wird stillschweigend als gleich akzeptiert —
  inhaltlich korrekt (derselbe Zielordner), dokumentiert.
  Dokumentierte Grenzfälle (plan-reviewer, Runde 1): `N` ist nicht in jedem
  pathologischen Fall idempotent — (i) Metadatenname enthält eine der fünf
  Suffix-Phrasen aus `helpers.py:101` mit Unterstrichen statt Leerzeichen
  (die Unterstrich-Ersetzung in Zeile 109 erzeugt den Regex-Treffer erst im
  zweiten Durchlauf), (ii) `clean(show_name)` überschreitet 160 Zeichen und
  der Kürzungsschnitt (`helpers.py:212`) landet exakt nach einem mitten im
  Namen stehenden `"]"`, wodurch ein neuer trailing Bracket-Tag entsteht.
  In beiden Fällen bleibt der Hinweis bestehen (Verhalten wie heute, keine
  Regression, nur greift der Fix dort nicht). Klasse (i) entsteht nur bei
  manuell getippten Namen (die App hängt ihre Suffixe stets mit Leerzeichen
  an, `search_api.py:376-435`); Klasse (ii) kann auch mit App-erzeugten
  Namen entstehen, aber nur bei >160-Zeichen-Namen mit unglücklicher
  Schnittstelle. Bewusst nicht behoben (Grundursache gehört zu #66).

**ADR 4 — Guard für fehlenden/leeren/Nicht-String-Override**
- Entscheidung: Override-Vergleich nur bei `isinstance(str)` und nicht leer
  nach `strip()`; sonst exakt heutige Logik (Fallthrough).
- Alternativen: blinde `str()`-Coercion (verworfen: `None`/`123`/`{}` würden zu
  Unsinn-Namen „None"/"123" und das Nicht-Setzen-Verhalten verändern).
- Begründung: Erstaufruf der Vorschau sendet kein `nas_show_folder`;
  Regression wäre ein neuer Bug (advocatus Finding 2).
- Konsequenzen: AK5 sichert das per Test ab.

**ADR 5 — Test-Design gegen triviales Grün**
- Entscheidung: Jeder Override-Test (AK2/AK3) enthält zwingend das
  Kontroll-Assert „ohne `nas_show_folder` liefert dieselbe Fixture den
  Hinweis"; Bracket-Tag-Ordnername als Pflicht-Fixture in AK2.
- Alternativen: nur `assertNotIn` (verworfen: grün, auch wenn der
  ID-Zweig nie erreicht wird — advocatus Finding 5).
- Begründung: Der Test muss beweisen, dass die Unterdrückung wirkt, nicht dass
  der Testaufbau scheitert.
- Konsequenzen: Worker schreibt 5 neue Backend-Tests (AK2-AK5), keiner ohne
  Kontroll-Assert.

**ADR 6 — Ein PR für alles + ROADMAP-Texte über repo-operator**
- Entscheidung: Beide Fixes + Bump + Tests in einem PR; ROADMAP-Einträge als
  wortgleiche Übernahme aus dem Session-Entwurf durch `repo-operator`
  (Verfahren von Alex in Freigabepunkt 1, Q1, bestätigt).
- Alternativen: drei PRs (verworfen: Review-Overhead, produktberater);
  Worker schreibt ROADMAP.md selbst (verworfen: Gate-A2-Grenze).
- Begründung: Teile sind unabhängig, klein und konfliktfrei.
- Konsequenzen: Merge/Rollback betreffen alle Teile gemeinsam (akzeptabel,
  da alle reversibel).

## 6. Dissens & offene Risiken (Pflichtabschnitt)

**Dissense (alle dokumentiert, keiner unterdrückt):**
- **[advocatus] VERDICT: REVISE** gegen den Plan-Entwurf mit 7 Einwänden.
 Auflösung: Einwand 1 [kritisch] → ADR 3 + AK2-Pflichtfixture; Einwand 2 → ADR 4 +
  AK5; Einwand 3 → ADR 2 + AK8; Einwand 4 → AK6-Harness-Voraussetzungen
  festgeschrieben; Einwand 5 → ADR 5; Einwand 6 [kosmetisch] → AK7 mit ❌;
  Einwand 7 [kosmetisch] → Akteursnamen stehen nur im NICHT übernommenen
  Kopf des Entwurfs, nicht in den Entry-Texten. Damit sind alle Einwände
  eingearbeitet; das REVISE gilt als aufgelöst (formeller Abschluss durch
  die plan-reviewer-Runden, dokumentiert unten).
- **[grafiker] vs [advocatus] bei success:false-Meldung:** grafiker empfahl
  ⚠️ (Warning-Ton), advocatus' Finding 6 behauptete, `appendConsoleLog`
  färbe nur bei `❌`/„fehler"/„error" rot, eine ⚠️-Zeile bleibe neutral.
  **Korrigierte Faktenlage (plan-reviewer Runde 1, von mir selbst verifiziert):**
  beide Prämissen waren falsch — `app.js:2177-2179` ist eine if/else-if-Kette,
  und jede Zeile mit `[System]`-Präfix läuft in den ersten Zweig
  (system-line, Akzentfarbe `style.css:1387-1389`); der ❌-Zweig wird für
  beide Textvarianten nie erreicht. ⚠️ wie ❌ erscheinen also identisch
  eingefärbt. **Entscheidung im Plan:** `[System]`-Präfix + ❌ beibehalten
  (AK7) — rein wegen der Konventionskonsistenz zu 14 bestehenden
  `[System]: ❌`-Fehlerzeilen; die ursprüngliche „Rot-Sichtbarkeits"-Begründung
  ist damit verworfen. Verworfen: ⚠️-Variante (semantisch vertretbar, aber
  ohne Konventionsvorbild bei Speichern-Fehlern). Offene Frage an Alex
  (Abschnitt 8, Frage 3): ob er für echte Rot-Einfärbung das
  `[System]`-Präfix opfern will — Empfehlung: nein.
  **Entschieden (Alex, 07.10.2026): Präfix bleibt; die AK7-Texte gelten
  wörtlich.**
  Lehren-Eintrag (Selbstauskunfts-Regel): ich hatte advocatus' Finding 6
  unverifiziert übernommen; der plan-reviewer hat die Falschbehauptung
  gefunden. Alle übrigen advocatus-Punkte wurden vor Aufnahme gegen Code
  geprüft.
- **[grafiker] Restrisiko „Meldung wird übersehen":** Auto-Scroll-Bedenken
  durch Verifikation aufgelöst — `appendConsoleLog` scrollt bereits
  (`app.js:2189-2190`). Bleibendes Restrisiko: minimierte Konsole wird nicht
  aufgeklappt (bewusst akzeptiert, Alex' Non-Blocking-Entscheidung).
- **[produktberater] „FREIGEBEN MIT ÄNDERUNGEN":** beide geforderten
  Änderungen sind eingegangen: die vier Frontend-Fälle in AK6; der
  trailing-spaces-Match-Testfall als explizite Zusatzvariante in AK2
  (Erstdraft enthielt ihn nur implizit über die Bracket-Fixture — vom
  plan-reviewer in Runde 1 beanstandet und nachgezogen).
- **[plan-reviewer] Runde 1 VERDICT: REVISE, 4 Einwände:** Einwand 1
  [wichtig] falsche Rot-Behauptung → AK7/Dissensblock korrigiert (oben);
  Einwand 2 [kosmetisch] N-Idempotenz-Grenzfälle → in ADR 3 dokumentiert;
  Einwand 3 [kosmetisch] trailing-spaces nur implizit → AK2-Variante;
  Einwand 4 [kosmetisch] AK5-Truthiness-Gloss → AK5 umformuliert. Damit
  alle vier behoben. **Runde 2: VERDICT: APPROVE**, 1 kosmetischer Rest
  (Halbsatz zu Idempotenz-Grenzfall (ii) in ADR 3 war unzutreffend) wurde
  vor Legung des finalen Planreviews präzisiert; Rot-Vorbilder-Hinweis in
  Abschnitt 8 Frage 3 ergänzt.

**Offene Risiken (nicht behoben, bewusst):**
1. `populateLocalProfilesDropdown()` schluckt eigene Fehler still
   (`console.error` nur) — Refresh kann ohne Nutzerhinweis ausbleiben
   (advocatus Finding 3.4; kosmetisch, Kandidat für #66-Session).
2. Vorbestehende stored-XSS-Stelle `app.js:10283` — nicht in diesem PR;
   als ROADMAP-#67-Text übernommen (von Alex freigegeben am 07.10.2026).
3. Vorbestehender Befund Pfad-Traversierung: `clean_series_name_for_fs`
   strippt keine `/`/`..`-Sequenzen; Absicherung erfolgt downstream via
   `is_path_allowed` (`processor.py`, adv.-Notiz) — außerhalb Scope, hier
   unverändert, nur dokumentiert.
4. Frontend-Eval-Harness bleibt fragil (Regex-Importentfernung, globale
   Zustände); AK6-Harness-Anforderungen mindern das, Restrisiko: Test könnte
   bei künftigen app.js-Umbauten brechen.
5. Worker-Container-Ausnahme `test_conversion_estimation_test_encode`
   (vorbekannt, in AK11 als Ausnahme dokumentiert).

## 7. Quellen, Referenzen & Lizenzen

- **Kein Third-Party-Code, keine Assets, Icons, Fonts oder Screenshots
  verwendet oder übernommen.** Alle Änderungen sind eigenständig im Projekt.
- Interne Referenzen (nur lesend): `app.js`, `queue_api.py`, `system_api.py`,
  `series_helper.py`, `helpers.py`, `utils.py`, `mw_metadata.py`,
  `test_utils.py`, `app_warning.test.js`, `cache_busting.test.js`,
  `ROADMAP.md`, `index.html`.
- [grafiker] nannte VS Code Output-Channel, GitHub Actions Job-Logs und Slack
  Toasts als **qualitative UX-Referenzen** — kein Code/Asset übernommen,
  daher keine Lizenzberührung. Toaster/Toast-Muster bewusst verworfen.
- Unklare Lizenzen: keine.

## 8. Offene Fragen an Alex (in Akt 2 gesammelt, NICHT einzeln gestellt)

**Beim finalen Planreview beantwortet (Alex, 2026-10-07, wörtlich:**
**„Ja, ich folge deinen Empfehlungen vollständig."** — Frage 1 mit „ja",
Frage 3 mit „Präfix behalten", gemäß den Empfehlungen dieses Abschnitts).

1. **ROADMAP-#67 (XSS-Härtung `app.js:10283`):** Als vierter Text-Eintrag in
   dasselbe PR übernehmen? **Empfehlung: ja** — reiner Backlog-Text, kostet
   nichts, und der Befund würde sonst nur in den Session-Rohoutputs
   (advocatus.md) untergehen. Trade-off: PR-Textumfang +1 Eintrag.
   Rohoutput: `docs/sessions/2026-10-06-roadmap46-namenskonflikt/advocatus.md`
   (Notiz „Weitere Notizen") und Entwurf in `roadmap-neue-eintraege.md`.
   **ENTSCHIEDEN: ja, übernommen (AK12).**
2. **Zur Kenntnis (keine Entscheidung nötig):** ein „dritter Name", der nach
   Normalisierung de facto derselbe Ordner ist, wird stillschweigend als
   gleich akzeptiert (ADR 3 Konsequenz); zwei pathologische
   Idempotenz-Grenzfälle von `N` bleiben bestehen = Verhalten wie heute,
   Fix greift dort nicht (ADR 3, Grundursache #66).
3. **Farbe der Profil-Fehlermeldung:** `[System]: ❌ …` erscheint in
   Akzentfarbe (Konvention, 14 Vorbilder), NICHT rot. Für echtes Rot müsste
   die Zeile ohne `[System]`-Präfix loggt werden (else-if-Kette,
   `app.js:2177-2179`). **Empfehlung: Präfix behalten** — Konsistenz
   gegenüber punktueller Rot-Hervorhebung; Trade-off: weniger auffällig als
   rot. Hinweis (plan-reviewer Runde 2): Auch für rot ohne Präfix existieren
   8 Vorbilder in der Konsole (u. a. `app.js:6248`, `7051`, `10648`) — beide
   Muster sind etabliert, `[System]: ❌` ist das häufigere bei Systemfehlern.
   Nur bei Alex-Wunsch abweichend umsetzen (dann AK7-Text anpassen).
   **ENTSCHIEDEN: Präfix behalten; AK7-Texte gelten wörtlich.**

Keine stichproben-pflichtigen Themen (Geld, Außenwirkung, Recht/Registrierung,
Kaufentscheidungen) berührt — Ausnahme: die XSS-Frage 1 ist
Sicherheits-Härtung der eigenen lokalen App, kein externer Effekt.

## 9. Aufwand (KI-Implementierung vs. Engpass Alex)

- **Worker (KI, schnell):** Backend-Gate + 5 Backend-Tests, Frontend-Block +
  Test-Harness mit 4 Fällen, Bump an 10 Stellen — Maschinenzeit ca. 1-2 h inkl.
  AK0/AK11-Messungen.
- **Engpass Alex (menschlich):** finaler Planreview dieser Session; danach
  PR-Review (~15-30 min), manueller Stichtest an der Vorschau
  (Namenskonflikt-Buttons + Profilspeicherung, ~10 min), Merge (Klasse C) und
  NAS-Update (`docker compose pull && up -d` nach grüner CI, siehe
  Deployment-Notizen).
- ROADMAP-Texte #64-#66/#67: keine Implementierungszeit, nur Lesebestätigung.

## 10. Git-Zustand (Preflight)

Von Claude Code im Worktree ausgeführt und wörtlich überliefert (2026-10-06):

```
$ git status --short --branch
## feat/roadmap-46-namenskonflikt...origin/main
?? docs/sessions/2026-10-06-roadmap46-namenskonflikt/
$ git log --oneline -3
3522ef2 chore: rebuild AGENTS.md from updated global rules (B1) (#146)
b174c76 feat(metadata): retry logic for JSON metadata fetches (ROADMAP #54 Teil 1) (#145)
66fcd38 chore: rebuild AGENTS.md from updated global rules (K1) (#144)
```

- Branch `feat/roadmap-46-namenskonflikt` (nicht main — kein main-Stop),
  HEAD = origin/main 3522ef2, Working Tree sauber außer diesem Session-Ordner.
- **Untracked Beifang:** `docs/sessions/2026-10-06-roadmap46-namenskonflikt/`
  (Session-Artefakte) — gehört zum PR-Umfang, wird explizit mit gestagt;
  kein anderes untracked Material vorhanden.
- PR-Umfang (nur diese Dateien, kein `git add -A`): `gui/static/app.js`,
  `gui/static/index.html`, `gui/api/queue_api.py`, `tests/test_utils.py`,
  `tests/frontend/profile_dropdown_refresh.test.js`,
  `ROADMAP.md` (nur repo-operator, AK12),
  `docs/sessions/2026-10-06-roadmap46-namenskonflikt/*`,
  STAND.md-Anhang/VERLAUF-Eintrag nach Huckepack-Regel im selben PR.
- Push mit `-u` auf eigenen Remote-Branch (Upstream zeigt aktuell auf
  origin/main — Hinweis von Claude Code übernommen).
- **Kein Commit ohne Alex-Go; Ausführung ausschließlich über `repo-operator`.**

## 11. Worker-Auftrag (Input für gate_run_task --task)

Umsetzung exakt nach Abschnitten 3 (AK0-AK11), 5 (ADRs) und den Grenzen:
Ändern darf der Gate-A2-Worker NUR `gui/static/app.js` (Speicherblock
10559-10592 + Import-Versionen Zeilen 1-9), `gui/static/index.html`
(Zeile 2752), `gui/api/queue_api.py` (Mismatch-Block 749-762),
`tests/test_utils.py` (nur NEUE Tests in `TestMediawerkzeugLogic`, bestehende
unverändert), `tests/frontend/profile_dropdown_refresh.test.js` (neu).
Nicht anfassen: ROADMAP.md, briefing.md, STAND.md, VERLAUF.md, alle anderen
Quelldateien (insbesondere `clean_show_name`, `clean_series_name_for_fs`,
`resolve_series_folder_name`, Suchlabels, `system_api.py`), `.env` nie lesen.
AK0/AK11-Ausgaben wörtlich mitliefern.
