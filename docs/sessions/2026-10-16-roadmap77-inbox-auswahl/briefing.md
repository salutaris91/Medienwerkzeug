---
kind: plan
status: approved
approved_by: alex
approved_on: 2026-10-16
approval_quote: "A und ADR 2–4 wie empfohlen, starte die Kette"
source: roadmap#77
---

# Feature Briefing: #77 — Inbox-Auswahl auf aktuelle, auswählbare Einträge beschränken

**Bindende Alex-Entscheidungen (wörtlich, 2026-10-16):** „A und ADR 2–4 wie empfohlen, starte die Kette“ — (A) Auswahl bereinigt sich beim Neuzeichnen + Schutz im Bulk-Weg, **kein** zusätzliches Leeren im allgemeinen Verarbeiten-Pfad; (ADR 2) übersprungene Einträge sichtbar melden, nichts still; (ADR 3) Ablauf Gate-A2 → Plausibilität → Rückkanal → Handtest (OrbStack, zwei Bulk-Aufträge nacheinander) → `kit-push-approved-head`, Cache-Buster v102; (ADR 4) Schreibgrenzen wie unten.

## 1. Problem

`gui/static/app.js`: `selectedInboxProjects` (Z. 12472) wird nur über „Auswahl aufheben“ (Z. 12697) oder Abhaken geleert. `renderSmartInboxList` (Z. 12973) übernimmt die Auswahl unverändert — auch für Einträge, die nicht mehr in der Liste stehen oder gerade verarbeitet werden (Kästchen gesperrt, aber weiter `checked`, Z. 13153, und im Zähler „N ausgewählt“). Der Bulk-Weg in `updateBulkActionsBarUI` (Z. 12716) macht aus einem Eintrag ohne Treffer in `currentSmartInboxRawSuggestions` ein `{ project: proj }` und schickt damit den nackten Ordnernamen → Server lehnt ab („Ordner sind im files-Parameter nicht erlaubt: …“). Workaround bisher: Seite neu laden oder „Auswahl aufheben“.

## 2. Regeln (verbindlich)

- **R1 Bereinigen beim Neuzeichnen:** `renderSmartInboxList` entfernt vor dem Zeichnen aus `selectedInboxProjects` jeden Eintrag, der (a) nicht in den übergebenen `rawSuggestions` steht, (b) laut `processingSet` gerade verarbeitet wird oder (c) nicht auswählbar ist (gleiche Regel wie die Kästchen: TV-Einzeldatei/Einzelvideo-Ordner oder freigeschalteter Film). Danach wird die Bulk-Leiste (`updateBulkActionsBarUI`) mit dem bereinigten Zähler aktualisiert. Die Prüfung (c) nutzt dieselbe Logik wie die Kästchen (keine zweite, abweichende Kopie; ggf. kleine Hilfsfunktion, die an beiden Stellen verwendet wird).
- **R2 Schutz im Bulk-Weg:** Der Klick auf „Ausgewählte als Serie verarbeiten“ verwendet nur Einträge mit aktuellem Treffer in `currentSmartInboxRawSuggestions`, die nicht in Verarbeitung sind. Der Fallback `|| { project: proj }` entfällt; ein Eintrag ohne Treffer wird nie gesendet.
- **R3 Sichtbare Meldung:** Fallen in R2 Einträge weg, erscheint eine Meldung mit der Anzahl (z. B. „2 Einträge sind nicht mehr in der Inbox und wurden übersprungen.“) über `alert` wie im übrigen Code; die übersprungenen Einträge werden aus `selectedInboxProjects` entfernt und der Zähler aktualisiert. Bleibt **kein** Eintrag übrig, wird `startSeriesGroupWorkflow` **nicht** aufgerufen, die Meldung sagt das („Keine der ausgewählten Dateien ist noch in der Inbox – nichts gestartet.“), der Knopf wird wieder freigegeben.
- **R4 Unverändert:** gültige Auswahl (inkl. Einzelvideo-Ordner mit `single_video_relpath`, `inboxFilesEntryForItem`), Gruppen-Banner, Gruppenzeile, `startSeriesGroupWorkflow`, der allgemeine Verarbeiten-Pfad (`/api/process`), Server-Code.
- **R5 Cache-Buster:** `app.js?v=101` → `v=102` in `gui/static/index.html` **und** alle `?v=101`-Importe in `gui/static/app.js` (sonst wird `tests/frontend/cache_busting.test.js` rot).

## Akzeptanzkriterien

- AK0 Ausgangsmessung: bestehende Suite vor der Änderung grün (vom Reviewer belegt).
- AK1 Auswahl {A, B}, Neuzeichnen mit Liste ohne B → Auswahl {A}, Zähler „1 ausgewählt“.
- AK2 Auswahl {A, B}, Neuzeichnen mit B in `processingSet` → Auswahl {A}; B's Kästchen nicht `checked`.
- AK3 Auswahl enthält nur Einträge, die verschwunden sind → nach Neuzeichnen leer, Bulk-Leiste ausgeblendet.
- AK4 Bulk-Klick mit {A, X}, X ohne Treffer in `currentSmartInboxRawSuggestions` (ohne vorheriges Neuzeichnen): `startSeriesGroupWorkflow` erhält nur A's Eintrag; **kein** Eintrag mit nacktem Ordnernamen X; Meldung nennt 1 übersprungenen Eintrag; X ist danach nicht mehr ausgewählt.
- AK5 Bulk-Klick, alle Einträge ohne Treffer bzw. in Verarbeitung: `startSeriesGroupWorkflow` wird nicht aufgerufen, Meldung erscheint, Knopf wieder aktiv.
- AK6 Unverändert: gültige Auswahl aus TV-Einzeldatei und Einzelvideo-Ordner (`single_video_relpath`) → `startSeriesGroupWorkflow` mit denselben `files` wie vorher, keine Meldung.
- AK7 Cache-Buster überall `v=102`, `cache_busting.test.js` grün.
- AK8 Alle bestehenden Tests (insb. `tests/frontend/inbox_group.test.js`) unverändert grün; gesamte Suite (`pytest` ohne den bekannten Umgebungs-Test, Frontend) grün, `git diff --check` sauber.

## Worker-Auftrag

1. Ändern nur: `gui/static/app.js` (nur `renderSmartInboxList` bzw. eine kleine Hilfsfunktion für die Auswählbarkeit, `updateBulkActionsBarUI` und die `?v=`-Importe), `gui/static/index.html` (nur `app.js?v=`).
2. Neue Testdatei `tests/frontend/inbox_selection.test.js` für AK1–AK6 (Muster wie `tests/frontend/inbox_group.test.js`: DOM-Mock, `alert` und `startSeriesGroupWorkflow` als Spione, keine Netzwerkzugriffe, keine Dateien außerhalb temporärer Verzeichnisse). Bestehende Tests nicht ändern.
3. Nicht anfassen: `gui/api/**`, übrige `gui/**`, `tests/test_*.py`, bestehende `tests/frontend/*.test.js`, `ROADMAP.md`, `API.md`, `docs/**`, `scripts/**`, `data/**`; `.env` nie lesen.

## Freigabe- und Merge-Pfad

Gate-A2-Lauf → Plausibilitätsprüfung (Claude Code) → Rückkanal (`ceo-planner` über `scripts/opencode-guarded-run.py`, Ergebnis `docs/sessions/2026-10-16-roadmap77-inbox-auswahl/rueckkanal.md` mit `ABNAHME: JA|NEIN`) → Handtest Alex (OrbStack, mehrere Einzelvideo-Ordner, zwei Bulk-Aufträge nacheinander, Zähler, keine Server-Ablehnung) → Freigabe-Datei (Reviewer, nach dem Rückkanal-Commit) → `ceo-planner` (minimaler Prompt) → `pr-operator` → `kit-push-approved-head` → PR → Merge Alex → NAS-Update (Klasse C).
