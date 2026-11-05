# Plan-Review Runde 2 — briefing.md (plan-reviewer, 2026-11-05)

> Ungekürzter Rohoutput des plan-reviewers, Runde 2 (Fortsetzung der Session
> `ses_e54c18a12ffeGaje1XGf3LErfs`). Eingabe: überarbeitetes briefing.md nach
> Einarbeitung aller 8 Einwände aus Runde 1; Auftrag: Behebungen verifizieren,
> AK12/AK13/AK19-Erfüllbarkeit durchrechnen, Formalkriterien erneut prüfen.

---

# Formelle Prüfung Runde 2 — Briefing „Ähnliche-Titel-Hinweis" (plan-reviewer, Inner-Loop)

**Artefakt:** `docs/sessions/2026-11-05-aehnliche-titel/briefing.md` (210 Zeilen, überarbeitet) + `ALEX_ZUSAMMENFASSUNG.md` (erweitert)
**Methode:** Vollneulektüre beider Dateien; Stichproben-Re-Verifikation der Worktree-Bezüge der Behebungen (`nfo_helper.py:130-147`, `queue_api.py:360-367`, `app.js:2884-2889`); übrige Code-Fakten aus der Runde-1-Verifikation fortgeführt (keine Codeänderungen im Rahmen der Überarbeitung, alle neu zitierten Zeilen waren bereits verifiziert).

---

## 1. Verifikation der Einwandbehebungen (8/8)

**B1 — Leer-Guard verbindlich für beide Zweige: BEHOBEN.** briefing.md:59 erklärt den Guard jetzt explizit als für Wort- **und** Präfixregel geltend, mit Total-Matcher-Begründung und dem Night/Nightcrawler-Beispiel. AK13 (:117) referenziert den Guard konsistent („Leer-Guard gilt auch für die Präfixregel"). Durchrechnung: „Night" → {night}, night ∈ GENERAL_WORDS (Liste :60 bestätigt) → Seite leer → Guard blockt Präfix „night" ⊂ „nightcrawler" ✓. „Teil 2" → „teil" ∈ GENERAL_WORDS ✓, „2" ∈ Fortsetzungszahlen ✓ → bereinigt leer → matcht keinen Titel ✓. Kein Total-Matcher mehr möglich.

**B2 — „300"-Fehlbehauptung: BEHOBEN.** Der Hinweis ist entfernt; :59 stellt fest: Zahlen-Tokens bleiben bedeutungstragend und sind untereinander matchbar, als bewusste Wahl mit Alex-Review-Verweis. AK12 (:116) enthält das neue Beispiel „300" vs. „300 (2006)" — durchrechnet: „300 (2006)" → Klammer weg → {300}; „300" → {300}; „300" ∉ Fortsetzungszahlen (nur 2..9) und ∉ GENERAL_WORDS → gemeinsames bedeutungstragendes Wort ✓, Leer-Guard nicht verletzt (beide Seiten {300}) → Treffer über Wortregel ✓ erfüllbar. Der Trade-off ist als Alex-Entscheidungspunkt in `ALEX_ZUSAMMENFASSUNG.md:25` erfasst („reine Zahlentitel wie ‚300' oder ‚1917' gelten als bedeutungsvoll … — OK so?") ✓.

**B3 — v/x und AK12-Begründung: BEHOBEN.** :58 entfernt `v`/`x` aus der Fortsetzungszahl-Liste (verbleibend: Ziffern 2..9, `ii, iii, iv, vi, vii, viii, ix`) mit Begründung (Kollision mit „X-Men"). AK12 (:116) begründet jetzt über die Wortregel mit dem gemeinsamen bedeutungstragenden Wort „x" („men" Allgemeinwort; „x" bleibt erhalten; Präfixregel nur noch als Backup). Durchrechnung: „X-Men (2000)" → {x, men}; „X-Men 2" → {x, men} („2" entfernt, „x" bleibt); gemeinsames bedeutungstragendes Wort „x" ✓ → Wortregel trägt; Leer-Guard nicht verletzt (beide Seiten {x}); Präfix „x men" == „x men" als Backup ✓; overlap 2 (Präfix zählt wie 2) konsistent mit dem JSON-Beispiel in 3.2 ✓. Die Begründungskette ist jetzt mit der eigenen Spezifikation konsistent — kein Test-Autor wird mehr auf einen roten Test geführt.

**B4 — NFO-seitige Label-Whitelist + AK19: BEHOBEN.** :38 spezifiziert die Label-Whitelist `{tmdb, tmdb_movie, tmdb_tv}` (case-insensitive — sinnvoll, da `read_nfo_metadata` `<mw_provider>`-Werte unnormalisiert übernimmt, `nfo_helper.py:133`), tvdb/sonstige Labels ⇒ Skip + Log, mit korrekter Begründung des `<tvdbid>`-Vorrangs. :54 spiegelt dies in der Funktions-Spezifikation. **AK19 (:123) gegen `nfo_helper.py:136-145` verifiziert:** Das Testbeispiel `<tvdbid>3409</tvdbid>` + `<tmdbid>3409</tmdbid>` konstruiert exakt den realen Codepfad — `tvdb_el` wird zuerst geprüft (137-140), `tmdb_el` nur im else (141-145), also liefert `read_nfo_metadata` Label `tvdb`/ID 3409; die Whitelist schließt `tvdb` aus ⇒ kein Stufe-1-Treffer trotz identischer Zahl 3409 gegen Payload `tmdb`/3409 — genau der Namespace-Kollisionsfall. Konsistenz-Check mit AK1: reines `<tmdbid>3409</tmdbid>` → Fallback-Label `tmdb_tv` → Whitelist lässt durch → Treffer ✓. Beide Whitelist-Seiten sind durch AKs abgedeckt, der Fallback-Label-Fehler (Fakten-Korrektur 4) ist vollständig und widerspruchsfrei gelöst.

**C1 — ytdlp_movie: BEHOBEN.** :36 nennt `ytdlp_movie` in der Skip-Aufzählung mit Verweis `app.js:2887` (stichprobenartig re-verifiziert ✓ — real lesbarer Wert, kein Erzeuger im Codebase, Skip defensiv korrekt), plus Begründung der geschlossenen Whitelist und `tmdb_movie`-Verifikation (`project_api.py:507`, `app.js:17376` — Runde 1 ✓).

**C2 — Platzierung: BEHOBEN.** :66 formuliert jetzt „am Ende des movie-Zweigs, unmittelbar vor `elif media_type == "tv"` (`:365`)" und erklärt korrekt, dass der Film-Zweig kein eigenes Return hat (gemeinsames `:787` hinter dem TV-Zweig). Gegen `queue_api.py:360-367` re-verifiziert: Film-Zweig endet :363, `elif` bei :365 ✓. Konsistent mit „tabu :365-787" (:77).

**C3 — AK16-Backend-Anteil in E1: BEHOBEN.** E1-Done (:132) prüft AK16 im Backend-Anteil direkt in `tests/test_similar_titles_hint.py` (`exclude_folders`); E2-Done (:137) prüft nur noch die UI-Sicht. Saubere Aufteilung, kein ungetesteter Zeitraum mehr.

**C4 — scout-Ideen 5/6: BEHOBEN.** :185 übernimmt Sammelreport (Idee 5) und Suchschritt-Frühwarnung (Idee 6) mit Herkunfts-Verweis (`synthese.md` Abschnitt 4 — verifiziert, die Tabelle bei Zeile 86 enthält genau diese Zuordnung) und expliziter Anweisung, sie bei der ROADMAP.md-Pflege nach Merge mit zu übernehmen.

---

## 2. AK12/AK13/AK19 — Erfüllbarkeits- und Konsistenzprüfung (wie gefordert)

- **AK12 erfüllbar:** ✓ — alle drei Fälle (X-Men 2 über Wortregel „x" + Präfix-Backup; Hobbit/Hobbits über Präfix mit beidseits bedeutungstragenden Tokens, Guard nicht verletzt; 300/„300 (2006)" über Wortregel) sind mit der Spezifikation :58-61 konsistent konstruierbar.
- **AK13 mit Leer-Guard konsistent:** ✓ — Fall 1 („Die X-Men Origins"/„Iron Man": Tokenmengen {x, men, origins} vs. {iron, man}, kein gemeinsames Token, kein Präfix, Guard irrelevant → kein Treffer); Fall 2 (Night/Nightcrawler: Guard blockt Präfix); Fall 3 („Teil 2": bereinigt leer → kein Total-Matcher). Alle drei in der natürlichen — jetzt einzigen — Lesart erfüllbar.
- **AK19 korrekt formuliert:** ✓ — siehe B4; Testfall, Codepfad und erwartetes Verhalten stimmen mit `nfo_helper.py:136-145` überein.
- **Neue innere Widersprüche durch die Edits:** Keine blockierenden oder wichtigen. Drei kosmetische Restpunkte, siehe Einwandliste.

---

## 3. Formalkriterien (Erneutprüfung)

- **Frontmatter (Kriterium 1):** ✓ — `status: draft` unverändert; `approved_by`/`approved_on`/`approval_quote` weiterhin Platzhalter (keine Vorfreigabe durch die Überarbeitung — explizit geprüft); `kind`/`source` korrekt.
- **Abschnitte (Kriterium 2):** ✓ — alle geforderten Abschnitte vorhanden; Abschnitt 9 um die scout-Übernahme erweitert, Struktur unangetastet.
- **AKs (Kriterium 3):** ✓ — jetzt 19 AKs, alle „Es prüft, dass …", tmp_path zugesichert, Test-Hintertür weiterhin Abbruchkriterium 3; alle 19 AKs sind einem Etappen-Done-Kriterium zugeordnet (E1: AK1-7, 10, 11-14, 16-Backend, 19; E2: AK8, 9, 15, 16-UI, 17, 18 — vollständig, keine Lücke, AK16 bewusst geteilt und gekennzeichnet).
- **Etappenvertrag (Kriterium 4):** ✓ — Erlaubte-Dateien-Listen unverändert, 5 Abbruchkriterien, Diff-Schätzungen unter 80 KB, `API.md` in E1, `cache_busting.test.js` nur lesend.
- **Dissens (Kriterium 5):** ✓ — Abschnitt 10 unverändert korrekt (produktberater-Veto mit Alex-Überstimmung, advocatus-Timeout mit Präzedenzbegründung + R1, scout-Franchise als V2); R1/R3/R4 in Abschnitt 9 erhalten; keine Verfälschung.
- **Lizenzen (Kriterium 6):** ✓ — Abschnitt 11 unverändert vollständig; ungeprüfte Dritt-Bibliotheken als Blocker markiert; keine stillschweigende Abhängigkeit.
- **FP1-Konsistenz (Kriterium 8):** ✓ — alle Strukturpunkte unverändert; die vier Edits bewegen sich innerhalb von FP1 (Leer-Guard verhindert unsinnige Treffer, keine verpassten echten; v/x und Zahlen-bedeutungstragend machen die Heuristik großzügiger bzw. fangen echte Duplikate — „lieber mehr Fehlalarme"; Label-Whitelist härtet die „deterministisch, sicher"-Stufe). Der Zahlen-Trade-off ist korrekt als Alex-Entscheidungspunkt ausgewiesen statt stillschweigend entschieden.
- **Kommunikation (Kriterium 9):** ✓ — Deutsch; keine Git-Schreib-/Umsetzungsanweisung; FP2/PR-Merge bleiben Alex-Punkte (:210).

---

## 4. Restrisiken / nicht ausgeführte Prüfungen

- Die Runde-1-Code-Verifikationen (30+ Fakten) wurden fortgeführt, nicht vollständig wiederholt; die drei stichprobenartig re-verifizierten Stellen bestätigen einen unveränderten Worktree. Ein zwischen den Runden unerkannt geänderter Code wäre nur über einen vollen Diff-Ausschluss auszuschließen — nach Aufgabenstellung wurden nur die beiden Markdown-Dateien bearbeitet.
- Die kosmetischen Punkte unten betreffen Formulierungsschärfe, nicht Verhaltenswidersprüche; keines davon blockiert FP2.

---

VERDICT: APPROVE
1. [kosmetisch] „Zahlen-Tokens ab 3 Stellen (`300`, `1917`) bleiben bedeutungstragend" (briefing.md:59) — die normativen Regeln (:58 Fortsetzungszahlen nur 2..9; :60 bedeutungstragend = nicht in GENERAL_WORDS) machen **alle** mehrstelligen Zahlen bedeutungstragend, auch zweistellige (Grenzfall: Film „21"); die Formulierung suggeriert eine Grenze bei 3 Stellen. „Mehrstellige Zahlen" wäre präziser.
2. [kosmetisch] Verweis „Alex-Review-Punkt (Abschnitte 9/12; plan-review B2)" (briefing.md:59) — Abschnitt 9 enthält den Zahlen-Trade-off nicht (er steht in `ALEX_ZUSAMMENFASSUNG.md:25` und implizit in Abschnitt 12s Heuristik-Review); halbtoter Verweis, bei der nächsten Revision angleichen.
3. [kosmetisch] Sortiergewichtung „Präfix-Treffer zählt wie 2" (briefing.md:61) — für Mischfälle (z. B. 3 gemeinsame bedeutungstragende Wörter **und** Präfix-Beziehung) ist unbestimmt, ob max(3, 2)=3 oder 3+2=5 gilt; das JSON-Beispiel (overlap: 2 bei 1 Wort + Präfix) disambiguiert nur den Hauptfall. Betrifft ausschließlich die Reihenfolge in Randfällen, nicht die Trefferentscheidung.

---

## Nachbereitung (Hauptassistent, nach APPROVE)

Die drei kosmetischen Punkte des Reviewers wurden wortgemäß eingearbeitet (keine Verhaltensänderung, nur Formulierungsschärfe):
1. „ab 3 Stellen" → „mehrstellige Zahlen-Tokens".
2. Verweis auf Abschnitte 9/12 → korrekter Verweis (Abschnitt 12 + `ALEX_ZUSAMMENFASSUNG.md` Entscheidungspunkt 2).
3. Sortierregel determiniert: `overlap = max(Anzahl geteilter bedeutungstragender Wörter, 2 bei Präfixtreffer, sonst 0)`.
