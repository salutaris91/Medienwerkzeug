---
kind: plan
status: approved
approved_by: alex
approved_on: 2026-11-05
approval_quote: "folge pr; es passt ansopnsten ich habe noch keinen MIB Film bisher"
source: docs/sessions/2026-11-05-aehnliche-titel/rueckkanal.md
---

# Fix-Briefing — Rauschen im Aehnliche-Titel-Hinweis (Medienwerkzeug)

**Anlass:** Handtest von Alex auf dem NAS (Film "Men in Black 3"): Treffer wie "In the Grey" und "Doctor Strange in the Multiverse of Madness" (nur wegen des Wortes "in"), Ordnernamen mit kaputtem Sonderzeichen am Ende, derselbe Film doppelt (Filmordner und dessen Unterordner).
**Scope:** nur `gui/core/similar_titles.py` und sein Testfile. Kein Frontend, kein Endpoint-Umbau.

## 1. Anforderungen

1. **Stoppwoerter erweitern.** Zu `STOP_WORDS` kommen englische und deutsche Funktionswoerter, die sonst nur Rauschen erzeugen: `in`, `on`, `at`, `to`, `for`, `with`, `from`, `by`, `im`, `auf`, `mit`, `von`, `zu`, `fuer`, `of` bleibt. Bestehendes Verhalten (z.B. "X-Men" findet "X-Men"-Ordner) darf sich nicht aendern.
2. **Sonderzeichen bereinigen.** Namen, die aus dem Dateisystem kommen, koennen Zeichen der Unicode-Kategorien Co (private use), Cc, Cf, Cs enthalten (SMB/NAS-Zeichenabbildung). Diese Zeichen werden fuer Vergleich UND Anzeige entfernt: `folder` und `relative_path` in den Ergebnissen sind bereinigt. Dateisystemzugriffe (Pfad zum Lesen der NFO) benutzen weiter den echten, unbereinigten Pfad. Excludes (`exclude_folder(s)`) werden gegen bereinigte UND rohe Namen verglichen.
3. **Unterordner von Filmordnern nicht als eigener Treffer.** Ein Ordner der ersten Ebene gilt als Filmordner, wenn er direkt eine Videodatei (Endungen aus dem bestehenden `VIDEO_EXTENSIONS`-Satz, z.B. `gui/core/film_normalize.py`, nicht neu erfinden, ggf. importieren) oder eine `.nfo`-Datei enthaelt. Seine Unterordner werden nicht als Kandidaten geliefert. Ein Ordner ohne Video/NFO direkt darin gilt als Genre-/Sammelordner und wird wie bisher bis 2 Ebenen durchsucht (Genre-Unterordner-Treffer der Stufe 1 muessen weiter funktionieren). Gilt fuer Stufe 1 und Stufe 2 (gemeinsamer Scan `_iter_candidate_folders`).

## 2. Akzeptanzkriterien (ausfuehrbare Tests, "es prueft, dass ...")

- AK1: "Men in Black 3 (2012)" findet "In the Grey (2026)" und "Doctor.Strange.in.the.Multiverse.of.Madness.2022" NICHT, findet aber "Pitch.Black.2000" (gemeinsames Wort "black").
- AK2: Ein Ordnername mit angehaengtem Private-Use-Zeichen (z.B. U+F022) erscheint ohne dieses Zeichen in `folder` und `relative_path`; Treffer bleibt erhalten.
- AK3: Hat ein Filmordner (mit Videodatei) einen Unterordner mit aehnlichem Namen, liefert die Suche nur den Filmordner, nicht den Unterordner.
- AK4: Ein Genre-Ordner ohne Video/NFO mit Film-Unterordnern wird weiter durchsucht (Stufe 1 und 2 finden den Film darin).
- AK5: Alle bisherigen Tests in `tests/test_similar_titles_hint.py` und das Frontend-Test-Set bleiben gruen (Regression), ausser Tests, die nachweislich das alte Verhalten festschreiben ("in" als Treffer oder Unterordner-Treffer) und angepasst werden muessen: dann Test anpassen, nicht Produktivcode.
- AK6: Tests nur in `tmp_path`, kompakt (parametrisieren), `git diff --check` sauber.

## 3. Erlaubte Dateien

Nur aendern: `gui/core/similar_titles.py`, `tests/test_similar_titles_hint.py`. Nicht anfassen: alles andere, insbesondere `gui/static/**`, `gui/api/**`, `API.md`, `ROADMAP.md`, `STAND.md`, `VERLAUF.md`, `scripts/**`, `.env` nie lesen.

## 4. Abbruchkriterien

Wenn eine Anforderung eine Aenderung ausserhalb der erlaubten Dateien braucht oder AK1-AK4 sich nicht ohne Eingriff in Produktivcode-Weichen fuer Tests erfuellen lassen: stoppen und melden, keine kreative Loesung. Keine Test-Weichen im Produktivcode.

## 5. Nicht-Ziele

Keine Mehrzahl-/Stamm-Erkennung, kein Zusammenfassen mehrerer Scans, kein neues Frontend.
