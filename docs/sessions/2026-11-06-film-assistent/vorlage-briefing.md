---
kind: plan
status: draft
approved_by: alex
approved_on: YYYY-MM-DD
approval_quote: "<Alex' Freigabe wörtlich nach Freigabepunkt 2>"
---

# Feature Briefing: [Name des Features]

## 1. Problemstellung
*Was ist das Problem? Warum ist dieses Feature notwendig? Welcher Schmerzpunkt wird gelöst?*

## 2. Zielnutzer
*Für wen ist dieses Feature gedacht? Wie passt es in deren Workflow?*

## 3. Akzeptanzkriterien
*Konkrete, überprüfbare Kriterien, wann das Feature als fertig gilt. Jedes Kriterium sollte möglichst als Testfall formuliert werden. Bei Etappen AKs mit Präfix nummerieren (`E1-AK1`, `E2-AK1` …).*
- [ ] Kriterium 1: ...
- [ ] Kriterium 2: ...

## Etappen (nur bei Feature-Ketten)
Weglassen, wenn der Plan nur ein Item umfasst. Höchstens 3 Etappen. Regeln: `docs/betriebsanleitung.md` §9.
**Diff-Budget:** Richtwert höchstens ~80 KB Gesamt-Diff je Etappe (der Diff allein kostet je Reviewer-Aufruf etwa 25k Tokens, grob 0,35 $; jede Review-Runde bezahlt ihn erneut). Etappen nach Diff-Größe schneiden, nicht nur nach Thema. Eine neue Testdatei über ~40 KB ist ein Signal, die Etappe zu teilen; größere Vorhaben als mehrere Ketten planen.

### E1 — <Titel> (roadmap#<nr>)
- Ziel: <1–2 Sätze>
- Akzeptanzkriterien: E1-AK1, E1-AK2 (stehen oben unter „Akzeptanzkriterien“)
- Erlaubte Dateien: <Pfade>
- Diff-Schätzung: <KB bzw. neue/geänderte Dateien; Richtwert ≤ 80 KB>
- Abbruchkriterium: <wann die Kette hier stoppt, zusätzlich zur Ampel in §9>

### E2 — …

## 4. Bewusst verworfen (Scope-Eingrenzung)
*Welche Ideen oder Erweiterungen wurden bewusst nicht in dieses Feature aufgenommen, um den Scope klein zu halten?*
- Verworfen 1: ...
- Verworfen 2: ...
