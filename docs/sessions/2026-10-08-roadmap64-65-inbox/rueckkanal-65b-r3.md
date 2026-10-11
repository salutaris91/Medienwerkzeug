# Rückkanal-Abnahme ROADMAP #65, Lauf B — Runde 3 (Handtest-Nachbesserung F1–F3)

**Datum:** 2026-10-11 · **Auftraggeber:** Claude Code (Rolle Reviewer/Vermittler), NICHT Alex.
**Alex-Bezug (wörtlich, 2026-10-11):** „a ja, b wie empfohlen, starte den Nachbesserungslauf“ — Anlass war sein Handtest-Befund, dass „Ausgewählte als Serie gruppieren“ und der Gruppenzeilen-Knopf nichts sichtbar taten (`startSeriesGroupWorkflow()` schaltete nie auf `view-folder` um). Beauftragte Beschriftungen: Link „Als Serie / Folge behandeln“, Gruppenzeilen-Knopf „Auswählen“.
**Abbruchkriterium (wie Runden 1–2):** geprüft wird **nur**, ob F1–F3 umgesetzt sind; neue Befunde werden **nur [kritisch]** gemeldet (Datenverlust, Aktion außerhalb der Gruppe, Fehler still statt sichtbar). Übriges → ROADMAP-Kandidaten, Zuordnung #72.
**Geprüfter Stand:** Worktree `feat-roadmap-65-lauf-b-oberflaeche`, Head `fe121f6` (`fix(inbox): open the series workspace from group actions, wording from hand test`). Diff `bd4dd8e..fe121f6` laut geliefertem `git diff --stat`: nur `gui/static/app.js` (+180/−15), `gui/static/index.html` (1 Zeile), `tests/frontend/inbox_group.test.js` (+175/−…). **Kein bash** → Head-Identität, Diff-Umfang, `git diff --check` und die Testresultate (508 Backend / 172 Frontend, die 3 neuen/geänderten Tests gegen `bd4dd8e` rot) sind **Claude-Code-Berichte**, von [ich] nur plausibilisiert (172 = 170 aus Runde 2 + genau die 2 neuen Tests F1/F2; keine Backend-Datei im Diff → 508 unverändert plausibel), **nicht selbst ausgeführt**. Alle Code-Aussagen unten sind auf diesem Stand **gelesen** und mit Datei:Zeile belegt.
**Rollen im Text:** [ich] = Vermittlungsagent dieser Runde. **Keine Subagenten konsultiert** — so beauftragt; es war keine Design-Abwägung zu treffen. Die Dissens-Pflicht ist durch [ichs] eigene Gegenprüfung (Abschnitt 4, inkl. verworfener Hypothesen) erfüllt.

---

## ABNAHME: JA

**Begründung in einem Satz:** F1 ist umgesetzt — alle drei Gruppen-Wege (Banner, Sammelknopf, Gruppenzeilen-Knopf) laufen durch die eine Funktion `startSeriesGroupWorkflow`, die jetzt sichtbar auf die Arbeitsansicht umschaltet (Dateiliste, Titel, Serien-Modus, Suche), und ein echter Test treibt alle drei Wege über die Produktionsfunktionen; F2/F3 (Beschriftungen) sind umgesetzt und gegentestet; der Vergleich mit `selectProject`/`scanProject` findet vier Zustände, die der Gruppenweg nicht setzt — keiner erreicht Datenverlust, Gruppenüberschreitung oder stilles Scheitern, also **kein [kritisch]-Neubefund**; der relevanteste (Doku-Flag) geht als [wichtig] an #72.

---

## 1. F1: Arbeitsansicht aus allen drei Gruppen-Wegen — umgesetzt

Alle drei Wege rufen **dieselbe** Funktion auf, der Fix sitzt also zentral:

| Weg | Aufrufstelle |
|---|---|
| Banner „Als Serie gruppieren“ | `app.js:12541–12546` → `startSeriesGroupWorkflow(groupKey, files)` |
| Sammelknopf „Ausgewählte als Serie gruppieren“ | `app.js:12574–12579` → dito (Gruppenname aus `suggested_query`/`cleanSeriesName`) |
| Gruppenzeilen-Knopf „Auswählen“ | `app.js:12926–12928` → dito (`item.items.map(m => m.project)`) |

Was `startSeriesGroupWorkflow` (`:12587–12767`) jetzt zusätzlich tut (der eigentliche Nachbesserungs-Kern, zuvor fehlte alles davon außer Zustand + Modus-Klick):

- **View-Wechsel** (`:12686–12695`): alle `.view-panel` → `hidden`/inaktiv, dann `view-folder` → sichtbar + `active`; `scrollToDetailTop()` (`:12696–12698`). Muster identisch zu `scanProject:2815–2821`.
- **Titel/Pfad** (`:12700–12707`): „Gruppe: {Name}“ bzw. „Serie (Gruppe)“, Pfad-Zeile „N Datei(en) ausgewählt“.
- **Statistik-Bereich ausgeblendet** (`:12708–12711`) — bewusst, es gibt keinen Scan; `scanProject` blendet ihn initial ebenfalls aus (`:2827`).
- **Modus-Auswahl sichtbar**, Rekursiver-Hinweis aus (`:12713–12717`).
- **Dateiliste gefüllt** (`:12719–12744`): eine Zeile pro Gruppenmitglied, Name via `escapeHTML` (`:12737`), Typ-Badge.
- **Serien-Modus aktiviert** (`:12746–12752`), `context-series` sichtbar (`:12754–12757`), Suchfeld mit Gruppennamen vorfüllen + `searchSeries()` (`:12759–12766`).

**Test:** `inbox_group.test.js:1278–1354` fährt alle drei Wege über die **echten** Produktionsfunktionen (`renderSmartInboxList` → echter Knopf-Klick auf `.btn-select-group` / `.btn-banner-apply-group`; `updateBulkActionsBarUI` → echter Klick auf `#btn-bulk-group-series`) und assert pro Weg: `view-folder` nicht hidden **und** active, `view-empty` hidden **und** nicht active, `mode-series` active. Die Mock-DOM sammelt `.view-panel`-Elemente real (`test:449–468` iteriert alle registrierten Elemente), die Asserts sind also keine No-Ops. Kein toter Code wie seinerzeit in AK4/B2.

## 2. F1-Vergleich mit dem normalen Weg (`selectProject`/`scanProject`): welche Zustände fehlen?

Der Serien-Ablauf **nach** dem Umschalten braucht nachweislich: `projectFiles` (Matrix-Zeilen, `:3677–3682`), `activeSeriesGroupFiles` (`payload.files`, `:4424–4426`), `currentProject` (`payload.project_name`, `:4405`), Matching-Panel (aus `projectFiles` neu aufgebaut), Dateiliste (neu gefüllt). **Das alles setzt der Gruppenweg** (`:12589–12594`, `:12719–12744`). Die `executeSeriesWorkflow`-Payload-Berechnung (`:4307–4467`) liest zusätzlich nur DOM-Optionen (Ziel, Konvertieren, Qualität) — alles vorhanden.

Vier Zustände setzt `scanProject`, der Gruppenweg aber **nicht**:

| Zustand | Normalweg | Gruppenweg | Auswirkung im Serien-Ablauf | Bewertung |
|---|---|---|---|---|
| `currentProjectIsDoku` | gesetzt bei jedem Scan (`:2875`) | **nicht zurückgesetzt** | `searchSeries` leitet daraus den Suchtyp ab (`:3093` → `type=doku` statt `tv`) und `selectShow` die Ziel-Vorbelegung (`:3517–3524` → `/Dokus/Doku-Serien`, fließt in `payload.destination_id` `:4396/:4417`). **Nur wenn in derselben Sitzung zuvor ein Doku-Ordner geöffnet wurde** (Initialwert `false`, `:223`), sucht die Gruppe im falschen Katalog und das Ziel ist falsch vorbelegt — beides **sichtbar** (Ergebnisliste, Ziel-Dropdown), kein Datenverlust, keine Gruppenüberschreitung. | **[wichtig] → #72** (Einzeiler: `currentProjectIsDoku = false;` in `startSeriesGroupWorkflow`) |
| `currentProjectSuggestedQuery` | gesetzt (`:2876`) | nicht gesetzt | Der Modus-Klick (`:12751`) triggert den Karten-Handler, der das Suchfeld mit dem **veralteten** Wert füllt (`:1820/:1848`) und `detectExistingSeries("")` → `searchSeries()` auslöst (`:1849`, `:2982–2984`). Der Gruppenweg überschreibt das Feld sofort mit dem Gruppennamen (`:12761`) und ruft `searchSeries()` erneut (`:12764`); die zweite Anfrage bricht die erste ab (`:3080–3082`). Ergebnis korrekt, nur ein verworfener Request. | [klein] → #72-Notiz |
| `window.currentProjectFileNfoStatuses` | gesetzt (`:2874`) | nicht gesetzt | Nur Lesestelle: NFO-Badges in der Matching-Matrix (`:3834/:3840`), null-sicher. Frische Sitzung → keine Badges; nach vorherem Ordner-Scan potenziell falscher Badge **nur bei exaktem Namenszusammentreffen**. Reine Anzeige. | [kosmetisch] → #72 |
| `updateProjectProcessingStatus(...)` | sofort (`:2807`) | nicht aufgerufen | Verarbeitungs-Warnung + Modus-Selector-Opacity (`:2421–2444`) bleiben bis zum nächsten 6-s-Poll (`:2418`) ggf. in alter Optik; `currentProject=""` ⇒ der Poll löst den Zustand selbst. | [kosmetisch], selbstheilend |

**Fazit F1-Vergleich:** Kein Zustand fehlt, den der Serien-Ablauf zwingend **braucht**, um korrekt zu enden — die Dateiliste, Matrix und Payload-Naht sind gedeckt. Der Doku-Flag ist der einzige mit funktionalem Effekt, er ist sitzungsabhängig, sichtbar und mit einem Einzeiler hebbar → nicht [kritisch] nach Abbruchkriterium, als [wichtig] an #72.

## 3. F2/F3: Beschriftungen — umgesetzt

- **F3 Gruppenzeilen-Knopf „Auswählen“** (`app.js:12870–12872`, Zap-Icon + Text): passt zum Knopf normaler Inbox-Einträge (`configureSmartInboxButton`, `:2517` — „Auswählen“/„In Bearbeitung…“). Test `:1389–1397` assert „Auswählen“ **und** dass „Als Serie gruppieren“ dort nicht mehr steht.
- **F2 Link „Als Serie / Folge behandeln“** (`app.js:12989`): alter Text „Trotzdem als Serie freigeben“ ist in `gui/static` nirgends mehr vorhanden (Reposuche). Tests `:1407–1413` (neu) und `:826–845` (AK3/AK13 angepasst) asserten neuen Text + Abwesenheit des alten.
- **Unangetastete Beschriftungen** (Alex-Zitate, bewusst gleich): Banner-Knopf „Als Serie gruppieren“ (`:12527`), Sammelknopf „Ausgewählte als Serie gruppieren“ (`:12561`) — Test `:1382–1388/:1399–1405`.
- **Cache-Buster (AK9):** `app.js?v=97` in allen neun Imports (`:1–9`) + `index.html:2760`; `style.css?v=49` unverändert (`index.html:9`) — konsistent, da kein Style-Datei-Diff.

## 4. Neubefunde

**Kein [kritisch]-Befund** gegen die drei Kriterien (Datenverlust / Aktion außerhalb der Gruppe / Fehler still statt sichtbar):

- Der Doku-Flag-Fall (Abschnitt 2, Zeile 1) endet in sichtbarer Fehlauswahl, nicht in stiller Datenbewegung außerhalb der Gruppe — die verarbeiteten Dateien bleiben die Gruppenmitglieder.
- Der doppelte `searchSeries`-Aufruf (Abschnitt 2, Zeile 2) ist flüchtig und wird durch Abort überdeckt; kein Render-Flackern möglich, weil der Aufruf synchron auf den Klick folgt.
- Dateiliste: `escapeHTML` an der Namenszelle (`:12737`); die Badge-Endungsliste ist erneut die 5er-Liste (`:12727`) — **bekannt** aus Runde 2 (R1/R2, .ts zeigt kein „video“-Badge), keine neue Klasse, kein Funktionsverlust (die Matrix nutzt die 10er-Liste seit H1).

**ROADMAP-Kandidaten (Zuordnung #72, nicht blockierend):**
- **N1** — `currentProjectIsDoku` (und ergänzend `currentProjectSuggestedQuery`) im Gruppenweg zurücksetzen bzw. auf den Gruppennamen setzen; sonst Doku-Folge-Szenario mit Fehlsuche/Falsch-Ziel.
- **N2** — doppelten `searchSeries`-Aufruf vermeiden (Modus-Klick vor Suchfeld-Setzen löst Suche mit Alt-Query aus; Ergebnis korrekt, Request überflüssig).
- **N3** — `window.currentProjectFileNfoStatuses` im Gruppenweg explizit leeren (Badge-Hygiene).
- **N4** — `updateProjectProcessingStatus` im Gruppenweg direkt aufrufen statt bis zum 6-s-Poll zu warten.
- R1–R3 aus Runde 2 bleiben unverändert bestehen; N1–N4 reihen sich dort ein.

## 5. Dissens / verworfene Alternativen (Eigenprüfung [ich])

- **Verworfene strengere Lesart:** [ich] prüfte initial, ob der veraltete Doku-Flag als **[kritisch]** zu melden wäre („falscher Suchtyp = immer noch stille Fehlbedienung“). **Verworfen**, weil das Abbruchkriterium kritisch an Datenverlust/Gruppenüberschreitung/stillen **Fehler** bindet: hier gibt es keine Fehlermeldung überhaupt, sondern ein sichtbares, im UI korrigierbares Ergebnis in einem randständigen Sitzungsablauf (erst Doku-Ordner öffnen, dann Gruppe). Downgrade [wichtig] → #72.
- **Verworfene Hypothese „F1-Test ist No-Op“:** geprüft, ob die Mock-DOM `document.querySelectorAll(".view-panel")` überhaupt auf `view-empty`/`view-folder` trifft (dann wäre das view-empty-Assert echt). Treffer-Bestätigung über die Mock-Implementierung `test:449–468` (iteriert alle registrierten Elemente, Klassensuche) → Asserts sind real, Hypothese verworfen.
- **Nicht als verifiziert verkauft, was ich nicht ausführte:** Head-Identität, Diff-Umfang, `git diff --check`, 508/172 grün und „3 Tests gegen `bd4dd8e` rot“ sind Claude-Code-Berichte; [ich] hat Code-Pfade, Test-**Inhalte** und Arithmetik (170+2=172) plausibilisiert, **nicht** die Läufe. Restrisiko wie in Runde 2: ein Test könnte grün sein und trotzdem eine Lücke haben — gemildert dadurch, dass der F1-Test über echte Buttons die echte Funktion fährt.

## 6. Hinweise für Alex: Handtest fortsetzen ab Punkt 4

Ausgangslage: Punkte 1–3 der Runde-2-Prüfliste (Banner/Zähler/Modal) konntest du nicht sauber durchprüfen, weil der Klick ins Nichts führte. **Neue Vorab-Punkte 0a–0c** (der eigentliche Nachbesserungsnachweis), dann weiter mit 4–15 wie geliefert:

- **0a.** [ ] Gruppe aufklappen → Knopf **„Auswählen“** klicken → die **Arbeitsansicht erscheint** (Dateiliste mit allen Gruppenmitgliedern, Titel „Gruppe: …“, Modus „Serie“ aktiv, Suchfeld mit Serienname gefüllt, Suchergebnisse laden). ↓ wenn falsch: nichts sichtbar → Fix greift nicht, sofort melden.
- **0b.** [ ] Zwei Häkchen setzen → „**Ausgewählte als Serie gruppieren**“ → derselbe Anblick wie 0a.
- **0c.** [ ] Banner „Als Serie gruppieren“ → ebenfalls Anblick wie 0a. **Wichtig für alle weiteren Punkte:** erst jetzt ist der Weg ins Vorschau-Modal bedienbar (Suchergebnis wählen → Matrix → Vorschau).
- **0d. (Sonderszenario N1)** [ ] Wenn du **in derselben Sitzung vorher einen Doku-Ordner geöffnet** hast: Gruppe → „Auswählen“ → die Serien-Suche sollte **TV-Serien** liefern (keine Doku-Treffer) und das NAS-Ziel auf „/Serien“ stehen. ↓ wenn falsch: Doku-Restflag-Szenario ist real → N1 wäre hochzustufen. Sauberer ist: Seite neu laden, dann erst Gruppe testen.
- **4.** [ ] Normaler Serien-Ordner **ohne** Gruppe mit `.ts`-Datei: erscheint in der Matrix (Runde-2-Punkt A4, unverändert).
- **5–6.** [ ] Aufklappen bleibt offen durch Poll/Sortieren (H3, unverändert).
- **7–8.** [ ] `"` im Dateinamen durchklicken (H2/Escaping); Qualitäts-Panel sichtbar (R2) — beides spielt jetzt **in der Arbeitsansicht**, die du erst seit 0a überhaupt erreichst.
- **9–10.** [ ] Fehlermeldungen sichtbar (H4, unverändert).
- **11–15.** [ ] Unverändert: Quarantäne nie an Gruppenzeile, ein Job mit `Staffel N`-Outbox, Doppelstart laut, „Ignorieren“ pro Sitzung, Queue-Anzeige des Gruppen-Jobs (leerer Projektname — jetzt zusätzlich prüfen: **Queue-Eintrag heißt „Gruppe: …“?** Der Titel in der Arbeitsansicht ist neu, der Queue-Name bleibt `""` aus Lauf-A-Design).

**Empfehlung:** 0a–0d zuerst (drei Klicks, ~2 Minuten), dann die restlichen Punkte in einem Durchgang. Wenn 0a–0c und 4–15 durch sind, ist Lauf B handtest-abgenommen; N1–N4 gehören in die #72-Pflege, nicht in eine vierte Code-Runde.

## 7. Empfehlung an Alex

1. **ABNAHME: JA → Handtest ab Punkt 0a fortsetzen.** F1–F3 sind umgesetzt, zentral in der gemeinsamen Funktion, und der F1-Test deckt alle drei Wege über echte Klicks ab. Kein [kritisch]-Neubefund; der Engpass bleibt ausschließlich dein Handtest.
2. **ROADMAP-Pflege (deine Entscheidung, dieser Lauf hat nichts in `ROADMAP.md` geschrieben):** N1–N4 an #72 anhängen (N1 ist der einzige mit funktionalem Kern); #65-Status erst nach Merge + bestandenem Handtest auf „erledigt“.
3. **Reihenfolge wie gehabt:** Handtest **vor** PR-Merge-Go (Klasse C bleibt bei dir). Aus dieser Runde: kein Push, kein PR, kein Git.

**Stichproben-pflichtige Themen (Geld/Aussenwirkung/Recht/Registrierung/Kauf):** keine berührt — reine Oberfläche des Einzelnutzer-Werkzeugs, keine neuen Assets/Fonts/Icons. **Rohoutputs:** keine Subagenten konsultiert (Auftrag); die gesamte Analyse liegt in dieser Datei, [ich] als einzige Stimme.

---

*Ende Rückkanal Lauf B, Runde 3. Gemäß Auftrag: nur diese eine Datei geschrieben, danach STOPP — kein Git, kein Push, kein repo-operator, keine STAND.md/VERLAUF.md.*
