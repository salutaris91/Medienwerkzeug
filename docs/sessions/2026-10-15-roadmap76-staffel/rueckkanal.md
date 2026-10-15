ABNAHME: JA

# Rückkanal-Prüfung: ROADMAP #76 — Folgenzuordnung berücksichtigt die Staffel

- Prüfer: this agent (Reviewer/Rückkanal, lesender Zugriff auf den Arbeitsbaum, 2026-10-15)
- Grundlage: `docs/sessions/2026-10-15-roadmap76-staffel/briefing.md` (status: approved, `approval_quote: "1–3 wie empfohlen, starte die Kette"`, Verfeinerung „ja, ADR 1 so verfeinern wie empfohlen", Nachtrag „Guthaben ist aufgeladen, 1 und 2 wie empfohlen" — jeweils Alex, 2026-10-15)
- Geprüfter Stand: uncommitteter Arbeitsbaum auf HEAD `dae45f5` — `gui/api/search_api.py` (Zeilen 42–322) und `tests/test_match_episodes_season.py` (9 Tests)

## 1. Regelumsetzung R1–R4a — vollständig und korrekt

- **R1 (Exakt zuerst):** `search_api.py:147–158` — Schlüssel werden gegen `^s(\d+)e(\d+)$` (case-insensitive) geprüft, Zahlenvergleich über `int()` ⇒ führende Nullen egal; exakter Treffer wird zuerst gesetzt (`exact_key is None`-Guard, Zeile 154) und beendet die Zuordnung (`continue`, Zeile 159). Korrekt.
- **R2 (Staffel vorhanden, Folge fehlt → None):** `search_api.py:160–163` — `season_keys` nicht leer, kein exakter Treffer ⇒ `matches[file] = None; continue`. Das `continue` blockiert nachweislich Direktprüfung, `absolute_number` (Zeile 176–186), Suffix-Suche (Zeile 189–198) **und** Fuzzy (Zeile 200–222). Korrekt.
- **R3 (Staffel nicht in Liste → bisheriges Verhalten):** `search_api.py:164` — bei leerem `season_keys` wird ohne `continue` in den unveränderten alten Pfad durchgereicht. Korrekt, entspricht Alex' Verfeinerung („Strenge nur, wenn die Folgenliste die Staffel der Datei enthält").
- **R4 (ohne SxxEyy/xxXyy → unverändert):** `parse_season_episode` (Zeile 118–126) liefert `None` ⇒ Block wird übersprungen, alter Pfad unverändert (`guess_ep_num` Zeile 83–112 textlich unangetastet). Korrekt.
- **R4a (Jahreszahlen in Klammern):** `search_api.py:134–141` — `finditer` über **alle** runden/eckigen Klammern; nur Zahlen **außerhalb** 1900–2100 setzen `has_bracket_abs_num` und deaktivieren die Staffel-Logik komplett (Vorrang der Klammer wie vorgeschrieben). Jahre allein lassen R1–R3 greifen. Bereich exakt 1900–2100 wie im Briefing. Korrekt.

Provider-Realität geprüft: „Alle Staffeln"-Listen erzeugen für TVDB (`mw_metadata.py:282–290`), TVmaze (`:534–537`) und TMDB (`:737–738`) zweistellig gepolsterte `SxxEyy`-Schlüssel — R1/R2 greifen also gegen echte Listen; Einzelstaffel- und ytdlp-Listen liefern einfache Nummern ⇒ R3-Pfad. Konsistent.

## 2. AK1–AK10 — Testinhalt geprüft, nicht nur Namen

Die 9 Tests in `tests/test_match_episodes_season.py` decken AK1–AK8 + AK10 ab; ich habe jeden Test gegen den Code durchgespielt:

- AK1 (Z. 36–49): Liste mit `absolute_number` (S01E01=1) — alter Code hätte `S01E01` geliefert, Test verlangt `S11E01` ⇒ **fängisch**.
- AK2 (Z. 51–64): S02E07 steht vor S11E07 in der Liste — alt: `S01E07` via absolute, Test verlangt `S11E07` ⇒ fängisch.
- AK3 (Z. 66–84): S11E14 fehlt, aber S11E04 hat `absolute_number` 14 — alt hätte falsch `S11E04` zugeordnet, Test verlangt `None` ⇒ fängisch, prüft exakt R2s absolute_number-Blockade.
- AK4 (Z. 86–99): `11x01`-Syntax ⇒ `S11E01`.
- AK5 (Z. 101–114): Einzelstaffel `"1"…"23"` ⇒ `"1"` (R3 unverändert).
- AK6 (Z. 116–132): Jahresliste `S2010E39`/`S2011E40`, Datei `S01E39` ⇒ `S2010E39` (R3).
- AK7 (Z. 134–154): rekonstruiert den bestehenden Test `tests/test_utils.py:2153` — ich habe zusätzlich den **Originaltest** gegen den neuen Code nachgefahren: `(381)` ⇒ Klammer-Gate aktiv ⇒ alter Pfad ⇒ `S2010E39`; `S01E05` ⇒ jetzt R1 statt Suffix, gleiches Ergebnis. Bleibt grün. Auch der zweite bestehende Aufrufer `tests/test_utils.py:2956` (Duplikat-Erkennung, `episode1.mp4` ohne SE-Muster) bleibt unberührt.
- AK8 (Z. 156–173): `S11E1` und `s11e01` ⇒ `S11E01` (Zahlenvergleich).
- AK10 (Z. 175–199): `(2010)` ignoriert ⇒ R1 auf `S11E01`; `(381)` hat Vorrang ⇒ Klammer-Pfad ⇒ `S2010E39`.

AK0/AK9 sind Suite-Ebene (nicht als Unit-Test abbildbar) — siehe Abschnitt 6 (Prüfgrenzen).

## 3. Hinweise (a)–(c) von Claude Code

**(a) `import re` in Zeile 44 — überflüssig, aber harmlos; die Begründung von Claude Code ist jedoch in der Quelle falsch.** `gui/core/helpers.py` hat **kein** modulweites `import re` (nur funktionslokale Importe, `helpers.py:373,433`), es stellt den Namen also nicht per Star-Import zur Verfügung. `re` kommt stattdessen über `from gui.workers.processor import *` (`search_api.py:7`), da `processor.py:623` ein Modul-Level-`import re` besitzt und kein `__all__` definiert. Der Vor-Code funktionierte bereits so (guess_ep_num nutzte `re`), das neue `import re` ist also redundant. Nicht zu beanstanden: Funktionslokale `import re` sind im Projekt Stil (`health_cache.py:362`, `transfers.py:660`). ⇒ [kosmetisch], kann bleiben.

**(b) `1920x1080` → Staffel 1920 — bestätigt unkritisch.** `parse_season_episode` (`search_api.py:123`) parst `1920x1080` als (1920, 1080), aber keine Provider-Liste kann Staffel 1920 enthalten (Jahres-Schlüssel realistisch ≤ ~2026, Serien-Staffeln ≪ 100) ⇒ immer R3 ⇒ exakt bisheriges Verhalten (der alte `guess_ep_num` `\d+x(\d+)`-Pfad, Zeile 95, tat das schon vorher). Theoretische Randklasse: eine Sendung mit Jahres-Schlüssel exakt 1920 + Datei mit `1920x…`-Token ⇒ R2→None statt Fuzzy — praktisch irrelevant. Anmerkung: die Implementierung ergänzt `(?<!\d)…(?!\d)` (Zeile 123) — eine leichte, unschädliche Verschärfung gegenüber dem Wortlaut `(\d+)x(\d+)` im Briefing; linksständig-gierige Matching liefert identische Ergebnisse.

**(c) Weitere Aufrufer — geprüft, keine abweichende Wirkung.** Einziger Konsument ist `gui/static/app.js:3645` (`/api/match-episodes`). Verhalten bei Server-`None`: `app.js:3816–3823` fällt im „Alle Staffeln"-Modus auf `guessSeasonAndEpisode` zurück (`js/parse.js:64–78`, liefert gepolstertes `SxxEyy`); die Dropdown-Auswahl vergleicht strikt gegen die Provider-Keys (`app.js:3854`). Trifft R2 genau zu (Folge fehlt in der Liste), existiert auch im Client-Layout kein passender Schlüssel ⇒ nichts wird selektiert, Default bleibt „-- Überspringen --" (`app.js:3844`) ⇒ **keine Fehlzordnung durch den Client-Backstop**, Nutzer:in wählt manuell — planmäßig. Manueller Modus ruft den Server gar nicht (`app.js:3614–3618`). Worker/`processor.py` rufen die Zuordnung nicht auf; `processor.py:1373/1405/3485/3496` und `extract_absolute_episode_number` (`processor.py:1425`, `queue_api.py:546`) konsumieren ausschließlich die bereits bestätigte Auswahl und erhalten damit die **korrigierten** Schlüssel — konsistent, kein Divergenzrisiko.

## 4. Regressionen

- **Einzelstaffel-Listen** (Nummern-Keys): Staffelerkennung findet keine `^s(\d+)e(\d+)$`-Keys ⇒ R3 ⇒ alter Pfad unverändert (AK5, AK7-Originaltest, Duplikat-Test `test_utils.py:2956`).
- **Absolute Nummern** `(381)`/`[381]` außerhalb 1900–2100: Klammer-Gate (Zeile 134–139) umgeht die Staffel-Logik vollständig ⇒ Vorrang wie im Briefing fixiert (AK10-Fall 2).
- **Jahres-Schlüssel** `S2010E39`: R3 bei Fremd-Staffel (AK6); Bonus ohne Risiko: Datei `S2010E41` bei Jahresliste trifft jetzt R2 (None) statt Fuzzy-Fehlzuordnung — planmäßig im Sinne von R2.
- Duplikat-Block (`search_api.py:303–320`): `None`-Matches sind falsy und werden übersprungen; `int(season)` mit `"all"` scheitert harmlos im `except` (Zeile 311–316) — Verhalten identisch zum Vor-Code.

## 5. Befunde (nach Schwere)

1. [kosmetisch] `gui/api/search_api.py:44` — `import re` redundant (verfügbar via `from gui.workers.processor import *`; **nicht** via helpers, anders als von Claude Code vermutet). Kann bleiben; Hausstil erlaubt funktionslokale Importe.
2. [kosmetisch] Vor-Code-Quirk, unverändert und nicht verschlimmert: `guess_ep_num` nimmt die **erste** Klammer (`search_api.py:86`), bei `Show (2010) (381) S11E01.mkv` also 2010 statt 381. Das neue Gate erkennt (381) korrekt, der alte Pfad danach erbt den Quirk — `guess_ep_num` war per Briefing tabu.
3. [wichtig → Roadmap, kein Blocker dieses Patches] Vertragslücke R4: Dateinamen nach Schema „Staffel 11 Folge 14" erkennt der Server nicht (nur `s(\d+)e(\d+)`/`(\d+)x(\d+)`), fallen in den absoluten Pfad und können weiterhin quer zu Staffeln zusammentreffen (isolierte Zahl 11 → `absolute_number` 11 → z. B. `S01E11`); der Client könnte es (`parse.js:74–77`), verliert aber gegen den Server-Wert. Regelt R4 ausdrücklich als „unverändert" — konform, aber als Follow-up-Eintrag in `ROADMAP.md` empfohlen.
4. [kosmetisch] Die neuen Tests setzen `utils._MOCK_SETTINGS` nicht; der Endpoint liert echte Settings (`search_api.py:230`). Harmlos, weil ohne `show_name`/`nas_show_folder` kein Directory-Walk stattfindet (`search_api.py:236–252`) — Muster entspricht dem Bestands-Test `test_utils.py:2153`. Mock-Rückgabe erfolgt über `tearDown` statt `finally` — funktional gleichwertig zur Briefing-Formulierung.

## 6. Prüfgrenzen (Selbstauskünfte, die ich nicht selbst verifizieren konnte)

Dieser Rückkanal war als reine Leseprüfung angelegt (kein Bash, kein Git, keine Subagenten). Daher **nicht selbst ausgeführt**, sondern als Worker-Beleg von Claude Code übernommen und wo möglich inhaltlich gegengeprüft:

- „Suite 522 passed / 1 deselected + Frontend 186/186" und `git diff --check` sauber (AK9) — unplausibel wäre das nicht: alle 9 Tests habe ich gegen den Code durchgespielt, der geteilte Bestandstest (AK7) bleibt nach meiner Trace-Analyse grün.
- „Nur 2 Dateien, 0 entfernte Zeilen" — meine Zeilennummer-Abgleiche (Briefing Z. 42/82 → jetzt Z. 43/83) sind konsistent mit reinen Additionen; ein formaler Deckungsnachweis obliegt dem nächsten Schritt (Reviewer-Freigabe/`approved-head.json` laut Briefing-Abschnitt „Freigabe- und Merge-Pfad").
- „Neue Tests gegen alten Stand 4 rot / 5 grün" — ich habe die Aufteilung selbst nachgerechnet: AK1–AK4 rot, AK5–AK8+AK10 grün. Stimmt exakt.

## 7. Empfehlung nächster Schritt

Keine Änderungen am Patch erforderlich. Weiter gemäß Briefing-Merge-Pfad: Handtest durch Alex im Anbieter-/Profilmodus mit „Alle Staffeln" (TWD-Fälle S11E01/S11E07/S11E14), danach Reviewer-Freigabe (`approved-head.json`) und `kit-push-approved-head`. Der Roadmap-Follow-up aus Befund 3 sollte als eigener Eintrag zurückgestellt werden.

VERDICT: APPROVE
1. [kosmetisch] Redundantes `import re` (`search_api.py:44`), Quellenangabe von Claude Code korrigiert (processor- statt helpers-Import).
2. [kosmetisch] Bestehender Erste-Klammer-Quirk in `guess_ep_num` (per Briefing tabu, unverändert).
3. [wichtig] „Staffel X Folge Y"-Namen bleiben außerhalb des Fix-Scopes (R4 konform) — als ROADMAP-Punkt nachziehen.
4. [kosmetisch] Tests lesen echte Settings ohne `_MOCK_SETTINGS` — harmlos, Bestandsmuster.
