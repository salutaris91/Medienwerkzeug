# Aufgabe Etappe E1 — Wizard-Rahmen + Film-Editor + Backend-Nachzug (ROADMAP #92)

Grundlage: `docs/sessions/2026-11-06-film-assistent/briefing.md` (status approved, FP2 von Alex 2026-11-06: "Damit gebe ich FP2 frei."). Gebaut wird **nur Etappe E1** mit den Akzeptanzkriterien E1-AK1 bis E1-AK8 und den Entscheidungen D1 (Schnitt A), D3 (Design-Empfehlungen) und D6 (a/b/c) aus dem Abschnitt "Entscheidungen FP2". Die Umsetzungshinweise zu D6 im Briefing sind verbindlich.

## Bauen
- `gui/static/js/film_wizard.js` und `gui/static/js/nfo_editor.js` (neu, ES-Module, keine window-Hacks): Vier-Schritte-Wizard im `mw-modal`-Muster, Einstieg "Film verarbeiten" in der Inbox; Schritt 2 editiert Titel/Jahr/Plot/FSK/Genre; Schritt 3 überspringbarer Platzhalter; nach Schritt 2/3 "Weiter" öffnet den bisherigen Optionen-/Vorschau-Flow (Übergangslösung bis E2).
- Backend-Nachzug in `gui/workers/processor.py` (Inbox-Film-Import, beide Provider-Zweige): Wizard-Overrides inkl. `fsk`/`genres` per `patch_nfo_fields()` in `<clean_movie_name>.nfo` schreiben. D6a: Patch-Fehler bricht den Job sichtbar ab. D6b: bei nicht-leeren Wizard-Overrides gewinnt der Wizard (Overwrite erzwungen), andere Aufrufer von `should_overwrite_nfo` bleiben unverändert. D6c: bewusst leer gesendete Felder entfernen den Provider-Wert (opt-in-Parameter in `patch_nfo_fields`, NFO-Agent-Verhalten unverändert).
- Tests je Akzeptanzkriterium (Test-Kompaktheit beachten). **Das Worker-Image hat weder pytest noch jsdom** (geprüft im Image `openhands-agy-worker:1.4.7-py2`: Python 3.13, Node 22, flask und yaml vorhanden):
  - **Backend-Tests** zwingend mit `unittest.TestCase`, kein `import pytest`. Die neue Datei heißt exakt `tests/test_inbox_movie_overrides.py` (das Testkommando referenziert sie; bei anderem Namen schlägt der Lauf fehl). Ergänzungen zu bestehenden Tests in `tests/test_nfo_write.py` ebenfalls als `unittest.TestCase`.
  - **Frontend-Tests** mit `node:test` und `node:assert` plus handgeschriebenen DOM-Mocks nach dem Muster von `tests/frontend/masked_input.test.js`. Kein jsdom-Import, auch wenn das Briefing umgangssprachlich "jsdom-Test" sagt. Neue Dateien: `tests/frontend/film_wizard.test.js`, `tests/frontend/nfo_editor.test.js`.
  - Testkommando des Laufs: `python3 -m unittest tests/test_nfo_write.py tests/test_inbox_movie_overrides.py && node --test tests/frontend/*.test.js`. Die 238 bestehenden Frontend-Tests müssen weiter grün bleiben.

## Nicht bauen
- Kein NFO-Agent-Umbau, kein Serien-/Doku-Pfad, kein Preview-Modal-Umzug (das ist E2/E3), keine Artwork-Auswahl (E5), kein Provider-Vergleich (E4), keine Reihen-Queue (E6), kein `#91`-Umzug.
- `#context-movie` darf nicht entfernt werden (wird auch für Doku genutzt).
- Cache-Buster (`app.js?v=`, 9 Modul-Importe) konsistent hochziehen.
