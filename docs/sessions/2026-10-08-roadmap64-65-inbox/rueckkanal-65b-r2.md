# Rückkanal-Abnahme ROADMAP #65, Lauf B — Runde 2 (Härtung H1–H4)

**Datum:** 2026-10-11 · **Auftraggeber:** Claude Code (Rolle Reviewer/Vermittler), NICHT Alex.
**Alex-Bezug (wörtlich, 2026-10-11):** „1–2 wie empfohlen, starte den Härtungslauf“. Damit gilt wie bei Lauf A das **Abbruchkriterium**: Diese Runde prüft **nur**, ob H1–H4 aus `rueckkanal-65b.md` geschlossen sind, und meldet neue Befunde **nur, wenn sie [kritisch]** sind (Datenverlust, Aktion außerhalb der Gruppe, Fehler still statt sichtbar). Alles Übrige → ROADMAP-Kandidaten, Zuordnung #72.
**Geprüfter Stand:** Worktree `feat-roadmap-65-lauf-b-oberflaeche`, Head `129f18b` (`fix(inbox): harden series grouping UI before the hand test`). Diff `59c561d..HEAD` laut geliefertem `git diff --stat`: nur `gui/static/app.js` (+113/−… ) und `tests/frontend/inbox_group.test.js` (+389/−…). **Kein bash** → Head-Identität, Diff-Umfang und die Testresultate (508/170) sind Claude-Code-Berichte; [ich] hat sie nur plausibilisiert, **nicht selbst ausgeführt**. Alle Code-Aussagen unten sind von [ich] auf diesem Stand **gelesen** und mit Datei:Zeile belegt.
**Rollen im Text:** [ich] = Vermittlungsagent dieser Runde. **Keine Subagenten konsultiert** — der Auftrag war durch das Abbruchkriterium bewusst auf eine mechanische Abschluss-Prüfung von vier bekannten Punkten eingegrenzt; es war keine Design-Abwägung zu treffen, daher gibt es keinen Rollen-Widerspruch zu dokumentieren. Die Dissens-Pflicht ist hier mit [ichs] eigener Gegenprüfung (inkl. verworfener Hypothese, Abschnitt 4) erfüllt.

---

## ABNAHME: JA

**Begründung in einem Satz:** Alle vier Härtungspunkte H1–H4 sind im Produktionsverhalten geschlossen und jeweils von einem Test auf der **echten** Naht gedeckt (Tabelle unten, Datei:Zeile verifiziert); der von Claude Code aufgeworfene Prüfpunkt (Endungsliste jetzt an drei Stellen auf die Server-Liste angeglichen) ist eine **bewusste, korrekte Angleichung und kein Rückfall** — die Oberfläche zeigt nun genau die Dateitypen, die der Server ohnehin verarbeitet; **kein [kritisch]-Neubefund** (kein Datenverlust, keine Aktion außerhalb der Gruppe, kein stilles Scheitern). Damit ist Lauf B Härtung handtestbereit.

---

## 1. H1–H4: geschlossen? (Code gelesen, Test benannt)

| Punkt | Geschlossen | Beleg Code (Datei:Zeile) | Beleg Test |
|---|---|---|---|
| **H1** (B1: Endungs-Drift lässt `.ts`-Folgen still aus der Gruppe fallen) | **JA** | Client-Endungsliste an **allen drei** Matrix-/Match-Pfaden auf die 10 Server-Endungen gesetzt: `selectShow` `app.js:3558`, `fetchEpisodes` `app.js:3630`, `renderMatchingMatrix` `app.js:3681` — identisch mit `helpers.py:798` `GROUP_VIDEO_EXTENSIONS` und `processor.py:348/:488`. `.ts`/`.m2ts`/`.flv`/`.3gp`/`.wmv` bekommen damit eine Matching-Zeile → einen Mapping-Schlüssel → `mappings`-Schlüssel ⊆ `files`; keine stille Auslassung mehr. | `inbox_group.test.js:1099–1127`: 10 Dateien mit allen zehn Endungen → genau 10 `.matching-row`s, `data-file`-Liste == Eingabeliste. |
| **H2** (B2: AK4-Test prüfte toten Code, A→B-Naht ungetestet) | **JA** | `createSeriesGroupPayload` ist **vollständig entfernt** (Reposuche: keine Definition/Export mehr). Der Test treibt jetzt die **Produktionsfunktion** `executeSeriesWorkflow` (`app.js:4307`), die `payload.files=[...activeSeriesGroupFiles]` setzt (`:4424–4426`), `mappings` aus `data-file` der Zeilen sammelt (`:4319/:4343`) und über `prepareSeriesPayload` (spread, `nfo_ui.js:63` → `files` bleibt erhalten) an `openPreviewModal` → `/api/preview_process` übergibt (`:4466`). | `inbox_group.test.js:1043–1094`: fängt den Fetch ab, assert `capturedUrl==="/api/preview_process"`, `media_type==="tv"`, `files===files`, **jeder** `mappings`-Schlüssel ∈ `files`, und ein Dateiname mit `"` bleibt als Schlüssel intakt. |
| **H3** (B3: Gruppen-Aufklappzustand fiel alle 6 s zusammen) | **JA** | Aufklappzustand jetzt in ein **Modul-Level-Set** verlagert: `expandedInboxGroups` (`app.js:12397`), beim Rendern gelesen (`:12696` → `aria-expanded`/Mitglieder-`display`), im ToggleHandler befüllt/geleert (`:12743`/`:12750`). Da `renderSmartInboxList` (der 6-s-Rebuild) aus dem Set liest, überlebt Aufgeklappt-Sein den Poll — wie die Auswahl (AK12). | `inbox_group.test.js:1132–1180`: aufklappen → `expandedInboxGroups` enthält Schlüssel → **erneuter** `renderSmartInboxList` → `aria-expanded` bleibt `true`, Mitglieder bleiben sichtbar; zu- und wieder aufklappen geprüft. |
| **H4** (B4: spezifische 400-Meldungen verschluckt) | **JA** | **Preview:** `!response.ok` liest jetzt den Body und übernimmt `errData.error \|\| errData.message` in die Wurfmeldung (`app.js:10286–10294`); das `catch` zeigt sie sichtbar via `alert("Fehler: " + e.message)` (`:10380`). **Process:** Body-Parsing (`:10651–10657`), bei Meldung **sichtbar** als `appendConsoleLog(...) + alert(...)` (`:10659–10660`), Fallback generisch (`:10662`). | `inbox_group.test.js:1185–1209` (Preview-400 → `alert` enthält Server-Meldung) und `:1211–1244` (Process-400 → **sowohl** Console-Log **als auch** `alert` enthalten die Server-Meldung). |

**Nebenbefund, der mit H1/H2 mitgeschlossen hat (positiv, nicht gefordert):** Das in Runde 1 als 400-Quelle benannte **unescaped `data-file`** ist jetzt an beiden Renderpfaden escaped — `app.js:3715` (manuell) und `:3818` (normal) nutzen `escapeHTML(file)`, das `"` → `&quot;` wandelt (`app.js:251`). Der H2-Test (`:1061/:1093`) belegt, dass ein Dateiname mit `"` nicht mehr gestutzt wird. Damit ist der alte „`"` im Namen → Schlüssel ≠ files → Server-400“-Pfad **geschlossen**. [ich] hat das im Browser-Verhalten gegen `getAttribute` (liefert den dekodierten Originalnamen) durchdacht: Schlüssel == `files`-String, kein 400.

---

## 2. Bewertung des Prüfpunkts von Claude Code

**Frage:** H1 hat die Endungsliste an drei Stellen (`selectShow`, `fetchEpisodes`, `renderMatchingMatrix`) geändert — das betrifft auch den **normalen Serien-Ablauf ohne Gruppe** (`.ts` usw. erscheinen jetzt auch dort in der Matrix). Unkritisch (Angleich an den Server) oder unerwünschte Verhaltensänderung?

**[ich]: unkritisch — bewusste, korrekte Angleichung, kein Rückfall.** Begründung:
- Die drei betroffenen Stellen sind **identisch** die Pfade, in denen der **normale** (anbieter-basierte) Serienablauf die Videodateien für `/api/guess-season` (`:3558`), `/api/match-episodes` (`:3630`) und die Matrix-Zeilen (`:3681`) filtert. Sie wurden auf exakt die 10 Endungen gesetzt, die der **Server selbst** verarbeitet (`helpers.py:798`, `processor.py:348/:488`).
- **Vor** der Angleichung war der Client strenger als der Server: Eine `.ts`-Datei in einem Serien-Ordner wurde serverseitig ohnehin als Video gescannt/bewegt, erschien aber clientseitig **nicht** in der Matrix → ohne Zuordnung. Die Angleichung **beseitigt** diese Kluft, sie erzeugt keine neue. Es erscheint nichts, das der Server nicht längst verarbeitet hätte.
- Kein Datenverlust, keine Aktion außerhalb der Gruppe, kein stilles Scheitern — die Änderung macht **mehr** sichtbar und **explizit zuordenbar**, das Gegenteil von still. Ein nicht-Folgen-`.ts` im Ordner kann der Nutzer auf „Überspringen“ setzen.

**Einziger Vorbehalt (nicht kritisch, → ROADMAP):** Die 10-er-Liste steht jetzt als **drei Kopien** im Code, während **vier weitere** Stellen weiterhin die alte 5-er-Liste nutzen (2616, 2921, 7022, 16234). Diese vier liegen **außerhalb** der Gruppe→`files`→`mappings`→Server-Naht, erzeugen aber kleine Unwuchten:
- `app.js:2616` — **Sichtbarkeit des Qualitäts-Sliders**: ein Ordner **nur** mit `.ts`-Dateien zeigt jetzt Matrix-Zeilen, blendet aber ggf. das Qualitäts-Panel aus (Prüfliste-Punkt 7).
- `app.js:2921` — **Badge-Farbe** in der Dateiliste: `.ts`/`.wmv` etc. bekommen kein „video“-Badge (rein optisch).
Empfehlung: alle Endungslisten in **eine** gemeinsame Konstante überführen — ROADMAP #72, nicht blockierend.

---

## 3. Neubefunde

**Kein [kritisch]-Befund.** [ich] hat die durch die Härtung neu berührten Pfade gegen die drei Abbruch-Kriterien geprüft:
- **Datenverlust?** Nein. `files`/`mappings`-Vertrag hält (H2-Test), `prepareSeriesPayload` spreadet (NFO-Dateien gehen nicht verloren), keine Löschpfade an Gruppenzeilen angefasst (AK11 unverändert).
- **Aktion außerhalb der Gruppe?** Nein. Die Endungsangleichung betrifft nur die **Anzeige/Zuordnung**, nicht die Auswahl; `activeSeriesGroupFiles`-Rücksetzung (`:2870–2873`, `:12942`) unverändert.
- **Fehler still statt sichtbar?** Im Gegenteil: H4 macht 400er jetzt **sichtbarer** (alert mit Server-Text), H1/H2 schließen die letzte stille Auslassung.

**ROADMAP-Kandidaten (nicht blockierend, Zuordnung #72):**
- **R1** — Endungslisten bündeln: 3× 10-er-Kopie (`:3558/:3630/:3681`) + 4× 5-er-Rest (`:2616/:2921/:7022/:16234`) → eine geteilte Konstante (Drift-Risiko, s. Abschnitt 2).
- **R2** — Qualitäts-Slider-Sichtbarkeit (`:2616`) an die 10-er-Liste angleichen, damit `.ts`-Only-Ordner das Konvertierungs-Panel nicht ausblenden.
- **R3** — aus Runde 1 offen gebliebene H5/B-Punkte (unverändert, nur der Vollständigkeit halber getragen, **nicht** erneut verhandelt): `isProcessing`-Guard an Gruppen-Knopf/Banner-Apply (B5), Anime ohne Sperr-Hinweis (B6), `is_dir`-Asymmetrie Auto-`===true` vs. Checkbox-`===false` (B7), Client-Folgenregex `\d{1,3}` vs. Server `\d{1,2}` (kosmetischer Drift ohne Gruppenwirkung).

---

## 4. Dissens / verworfene Alternativen (Eigenprüfung [ich])

- **Verworfene Hypothese:** [ich] prüfte initial, ob die Endungsangleichung im **normalen** Ablauf ein Risiko ist, weil `/api/match-episodes`/`/api/guess-season` die zusätzlichen Endungen „nicht kennen“ könnten → **verworfen**: der Server scannt selbst mit denselben 10 Endungen (`system_api.py:338`, `processor.py:348/:488`), die Endpunkte nehmen nur Dateinamen entgegen; kein Choke-Punkt.
- **Verworfene strengere Lesart:** H4 nur als „Console-Log“ zu akzeptieren (Vor-Zustand Process) wäre am Abbruchkriterium „Fehler sichtbar“ gescheitert → [ich] hat den `alert`-Zweig (`:10660`) explizit nachgelesen und H4 dadurch als **geschlossen** (nicht nur „geloggt“) gewertet.
- **Nicht als geschlossen verkauft, was ich nicht ausführte:** Die 170/170- und 508-Befunde sind **Claude-Code-Berichte**; [ich] verifiziert hat Code-Pfade und Test-**Inhalte** (dass sie die echte Naht treffen), **nicht** deren Grün-Durchlauf. Restrisiko: ein Test könnte grün sein, aber eine Lücke haben — gemildert dadurch, dass jeder H-Test genau die in Runde 1 rot gemeldete Naht adressiert.

---

## 5. Aktualisierte Handtest-Prüfliste für Alex (echte 11-Staffel-Serie, ~264 Folgen)

> Klartext, abhakbar. **Was sich seit Runde 1 geändert hat:** Punkte, die damals auf einen bekannten Defekt (B1/B3/B4) abzielten, prüfen jetzt, ob der Fix **greift**. Wenn ein Punkt **fehlschlägt**, steht in „↓ wenn falsch“ das, was du sehen **solltest**, damit du es als Fehler erkennst.

**A. Gruppierung & Zähler (H1)**
1. [ ] Banner nennt Serienname + „N Folgen“ + Staffeln — N ist die **echte** Anzahl Mitglieder. ↓ wenn falsch: Zahl weicht von der Mitgliederliste ab (Hinweis auf Zähl-/Endungsfehler).
2. [ ] Gruppe auf „Als Serie gruppieren“ → Mitgliederliste zeigt **alle** Folgen, auch `.ts`/`.m2ts`/`.flv`/`.3gp`/`.wmv` (falls vorhanden). ↓ wenn falsch: eine Datei, die im Ordner liegt, taucht in der Mitglieder- oder Matrixliste nicht auf.
3. [ ] Im **Vorschau-/Modal** hat **jede** Gruppenfolge eine Zuordnungszeile; „N Folgen“ == Zahl der Zeilen == Zahl später verarbeiteter Dateien. ↓ wenn falsch: Zähler sagt 264, Matrix/Verarbeitung 263 → H1 greift nicht.
4. [ ] Normaler Serien-Ordner **ohne** Gruppe, der `.ts` enthält: die `.ts`-Datei erscheint jetzt in der Matrix. **Bestätige bewusst, dass dir das recht ist** (Prüfpunkt-Auswirkung). ↓ wenn du das **nicht** willst: kurz melden — dann wäre die Angleichung doch eine unerwünschte Verhaltensänderung.

**B. Aufklappen (H3)**
5. [ ] Gruppe aufklappen (Chevron) → Mitglieder sichtbar; **mindestens 10 Sekunden warten** (der 6-s-Poll läuft durch), ohne etwas zu klicken. Sie bleibt **offen**. ↓ wenn falsch: klappt nach ~6 s von selbst zu → H3 greift nicht.
6. [ ] Sortieren (Name/Datum/Größe) bei geöffneter Gruppe → Gruppe bleibt offen **und** Haken der Auswahl bleiben stehen. ↓ wenn falsch: Gruppe fällt zu oder Haken verschwinden.

**C. Übergabe & Sonderzeichen (H2 + data-file-Fix)**
7. [ ] Serie mit einer Datei, deren Name ein **Anführungszeichen `"`** enthält (oder eine künstlich so benannte Testdatei): Gruppe → Modal → **kein** Abbruch, die Datei behält ihre Zeile. ↓ wenn falsch: **früher** kam ein generischer 400; jetzt **sollte** es sauber durchlaufen. Kommt trotzdem ein Fehler, ist die Escaping-Kette nicht dicht.
8. [ ] Qualitäts-/Konvertierungs-Panel ist sichtbar, wenn du es brauchst (betrifft nur-`.ts`-Ordner, R2). ↓ wenn falsch: Panel ausgeblendet trotz Videodateien → R2 ist real.

**D. Fehler sichtbar (H4)**
9. [ ] Eine absichtlich ungültige Anfrage provozieren (z. B. Mapping auf eine Datei, die nicht in `files` ist — oder Server kurz anderweitig testen): die **spezifische** Server-Meldung erscheint im **Popup** (und im Konolenpanel beim Start), nicht nur ein generisches „Fehler beim Abrufen der Vorschau“. ↓ wenn falsch: nur generischer Text → H4 greift nicht.
10. [ ] Prozess-Start mit abgelehnter Payload: **Popup** mit Server-Text erscheint (Vorher: nur Log). ↓ wenn falsch: kein Popup → H4 Process-Zweig unvollständig.

**E. Unverändert zu prüfen (wie Runde 1, Kernzusagen)**
11. [ ] Quarantäne-Knopf **nur** am echten Ordner, **nie** an der Gruppenzeile (auch bei Namensgleich Gruppe „Show“ vs. Ordner „Show“). ↓ wenn falsch: Gruppenzeile hat Löschknopf → AK11 gebrochen.
12. [ ] Ein Job, Outbox-Struktur `Staffel N` korrekt, Inbox danach leer **außer** bewusst übersprungenem. ↓ wenn falsch: Folgen fehlen in der Outbox oder bleiben dubliziert.
13. [ ] Zweimal schnell „Als Serie gruppieren“: der **zweite** Lauf scheitert **laut** (Server-Härtung Lauf A), nicht still (B5 bleibt offen, kein Datenrisiko). ↓ wenn falsch: zwei Jobs laufen parallel → B5-Endschutz greift nicht.
14. [ ] „Ignorieren“ hält die Sitzung; Reload bringt den Banner zurück (bewusst so). ↓ wenn falsch: Ignore wirkt dauerhaft oder verschwindet sofort ohne Klick.
15. [ ] Queue-Eintrag des Gruppen-Jobs: Anzeige/Name plausibel (Restunsicherheit leerer Projektname, Lauf A). ↓ wenn falsch: Eintrag unbenannt/leer → Handtest-Hinweis an Lauf A zurück.

---

## 6. Empfehlung an Alex

1. **ABNAHME: JA → Handtest jetzt durchführen.** H1–H4 sind geschlossen und testseitig auf der echten Naht gedeckt; kein [kritisch]-Neubefund. Der Engpass ist ausschließlich dein Pflicht-Handtest (Abschnitt 5), nicht erneute Code-Runde.
2. **Prüfpunkt ist erledigt:** die Endungsangleichung ist die richtige Richtung (Angleich an den Server), **keine** Rückfrage nötig — außer Punkt A4 der Prüfliste zeigt, dass dir das geänderte Verhalten im normalen Ablauf nicht gefällt. Dann melden wir es als Design-Punkt an dich zurück.
3. **ROADMAP-Pflege (deine Entscheidung, dieser Lauf hat nichts in `ROADMAP.md` geschrieben):** R1–R3 (Abschnitt 3) an #72 anhängen; #65-Status erst **nach** Merge + bestandenem Handtest auf „erledigt“.
4. **Reihenfolge Merge/Handtest:** wie Lauf A — Handtest **vor** dem PR-Merge-Go (Klasse C bleibt bei dir). Kein Push/PR aus dieser Runde.

**Stichproben-pflichtige Themen (Geld/Aussenwirkung/Recht/Registrierung/Kauf):** keine berührt — reine Oberfläche des Einzelnutzer-Werkzeugs, keine neuen Assets/Fonts/Icons. **Rohoutputs:** Diese Runde hat bewusst **keine** Subagenten konsultiert (scope-eingegrenzt durch das Abbruchkriterium); die Analyse liegt vollständig in dieser Datei, [ich] als einzige Stimme.

---

*Ende Rückkanal Lauf B, Runde 2. Gemäß Auftrag: nur diese eine Datei geschrieben, danach STOPP — kein Git, kein Push, kein repo-operator, keine STAND.md/VERLAUF.md, keine Rohoutput-Abschreibung.*
