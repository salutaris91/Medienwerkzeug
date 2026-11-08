# Handtest-Parcours — Geführter Film-Assistent (ROADMAP #92)

Grundlage: `briefing.md` (FP2, status approved), FP1-Entscheidung 5.3 Variante b (kein Playwright). Zweck: Nachweis, dass die Etappen den Serien- und Doku-Pfad nicht verändern („verhaltensneutral“), solange `index.html`/`app.js` angefasst werden.

**Wann:** (1) **Referenzlauf vor E1** gegen den unveränderten Stand (`main`), (2) **Wiederholung nach jeder Etappe** (E1 bis E6) gegen den Branch/das Image der Etappe. Abweichung zum Referenzlauf ist ein **Blocker** (kein PR-Merge, Kette stoppt).

**Wer/Wo:** Alex, in der lokalen App (`python gui/main.py` oder `docker compose up`) mit **Wegwerf-Testdaten** (kleine Dummy-Videodateien in einer Test-Inbox, Ziel eine Test-Ausgabe statt der echten NAS-Bibliothek). Nichts gegen die produktive Bibliothek ausführen, solange nicht ausdrücklich gewollt. Konvertierung (H.265) und „Original löschen“ in allen Läufen **aus** lassen, außer in Lauf F-3.

Beschriftungen unten stammen aus `gui/static/index.html` (Stand `main` `86fdc26`). Weicht eine Beschriftung ab, im Protokoll vermerken, nicht stillschweigend anpassen.

## Protokollformat (je Lauf eine Zeile pro Prüfpunkt)

`Etappe | Lauf-ID | Prüfpunkt | Ergebnis (OK / Abweichung) | Beobachtung (1 Satz) | Datum`

Ablage: `docs/sessions/2026-11-06-film-assistent/handtest-protokoll.md` (Referenzlauf zuerst, dann je Etappe ein Block).

## Lauf F — Film (Inbox-Import)

| ID | Schritte | Erwartung (Referenz = heutiges Verhalten) |
|---|---|---|
| F-1 | Dummy-Film in der Inbox, Eintrag öffnen → Panel „Film verarbeiten“. TMDb-Suche nach einem bekannten Titel, Treffer wählen. Titel/Jahr/Plot ansehen. | Felder werden aus dem Treffer befüllt; nur Titel/Jahr/Plot editierbar (heute keine FSK/Genre-Felder). |
| F-2 | „Vorschau generieren“ → Vorschau-Modal ansehen (Zielpfad, Datei-Renames, ggf. Untertitel/Junk, #91-Hinweis „ähnlich/gleich“, falls ein ähnlicher Film auf dem Ziel liegt). „Jetzt final verarbeiten“. | Vorschau erscheint, Hinweis blockiert nie, Verarbeitung läuft durch; Ordner `<Titel (Jahr)>` mit Film, `.nfo`, `poster`, `fanart`/`backdrop` (und `logo`, falls TMDb eines liefert). |
| F-3 | Wie F-2 mit eingeschaltetem H.265 **oder** „Original löschen“ (nur mit Wegwerf-Datei). | Option wirkt wie bisher; kein Fehler im Job-Log. |
| F-4 | Provider OFDb statt TMDb wählen, Titel/Jahr/Plot ändern, verarbeiten. | Referenz-Beobachtung festhalten (heute werden die Änderungen bei OFDb nicht in die NFO übernommen); nach E1 gilt das neue Verhalten laut `briefing.md` (D6). |
| F-5 | Film verarbeiten, bei dem im **Inbox-Ordner** direkt neben der Videodatei (am besten gleichnamig) schon eine `.nfo` liegt. Nicht im NAS-Zielordner: Der Import erzeugt und prüft die NFO im Inbox-Projektordner, bevor die Datei transferiert wird (`processor.py`, `current_dir`). | Referenz-Beobachtung festhalten; nach E1 gewinnt der Wizard (D6b). |

## Lauf S — Serie (muss nach **jeder** Etappe identisch bleiben)

| ID | Schritte | Erwartung |
|---|---|---|
| S-1 | Dummy-Dateien `Serie.S01E01`, `S01E02` in der Inbox, als Serie gruppieren/öffnen, TMDb/TVDB-Treffer wählen. | Serien-Panel mit Staffel-/Episoden-Zuordnung wie bisher. |
| S-2 | Episoden-Mapping und Titel-/Plot-Overrides ändern, „Vorschau generieren“. | Vorschau-Modal inkl. Staffel-Warnung und ggf. Namenskonflikt-Hinweis (`preview-show-name-mismatch`) unverändert. |
| S-3 | „Jetzt final verarbeiten“. | Ordner `<Serie>/Season 01/…`, `tvshow.nfo`, Episoden-NFOs wie bisher. |

## Lauf D — Doku (nutzt dasselbe Panel `#context-movie`)

| ID | Schritte | Erwartung |
|---|---|---|
| D-1 | Eintrag als Doku öffnen („Doku verarbeiten“), Quelle wählen, „Vorschau generieren“, „Jetzt final verarbeiten“. | Kopf zeigt „Doku verarbeiten“, Ablauf wie heute, Ergebnis im Doku-Zielordner. |

## Lauf N — NFO-Agent und Health (unverändert bis E3)

| ID | Schritte | Erwartung |
|---|---|---|
| N-1 | Health-Ansicht → NFO-Agent für einen **Film**-Ordner öffnen, Quelle suchen, FSK/Genre setzen, speichern. | FSK/Genre in der NFO; leere Felder werden weiterhin **nicht** entfernt (Ist-Verhalten des NFO-Agenten). |
| N-2 | NFO-Agent für einen **Serien**-Ordner, Episoden-Modusleiste (`nfo-agent-edit-mode-bar`) benutzen, speichern. | Wie bisher. |

## Abnahme je Etappe

- Referenzlauf vollständig protokolliert, **bevor** die Kette für E1 startet (Voraussetzung für den Gate-A2-Start).
- Nach jeder Etappe: Läufe S, D, N komplett; Lauf F in dem Umfang, den die Etappe berührt (E1: F-1 bis F-5; E2: F-1 bis F-3; E3: F-1, N-1; E4–E6 nach Briefing).
- Jede Abweichung (OK → Abweichung) mit Beobachtung festhalten; Etappe wird nicht gemergt, bis sie behoben oder von Alex ausdrücklich als gewollt bestätigt ist.
