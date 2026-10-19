<!-- Mechanisch aus `opencode export ses_eace2c837ffeE6ahS5Qd3i7Q1V` extrahiert (Claude Code, 2026-10-19): alle Assistant-Textteile in Reihenfolge, ungekürzt, unverändert (nur Trailing Whitespace entfernt). Rohdatei: Kit-Worktree clever-mclaren-94c19f scripts/gate-a2/logs/2026-10-18-roadmap74-kette/rueckkanal/export-produktberater-eace2c837ffe.json -->

Jetzt prüfe ich noch die spezifischen Hinweise (a)–(f):



[produktberater] Rückkanal-Review — Feature-Kette #74 + #80-Rest + #83

---

## (1) Je-Etappe-Nutzenurteil

**E1 (#74 Staffel-Schnellauswahl): Nutzen voll umgesetzt.**
- Staffel-Knöpfe bei ≥2 Staffeln (aufsteigend, `Staffel N (k)`) → `app.js:13355-13400`. Einzelstaffel-Gruppen haben keine Staffel-Leiste → `app.js:13357`. Alle-Knopf umbenannt → `app.js:13350`. Banner-Split bei ≥2 Staffeln (nur gruppieren, kein Start) → `app.js:12873-12877`. Hinweiszeile → `app.js:12701-12703`.
- Tests decken ab: E1-AK1 (Knöpfe/Label), AK2 (Klick übergibt genau die Staffel inkl. Ordner-Folge via `single_video_relpath`), AK3 (Alle-Knopf), AK4 (6-s-Neuaufbau), AK5 (Sonderzeichen), AK6 (Banner-Split + Hinweis), AK7 (Sperre 4 Stellen), AK8 (Freigabe), AK9 (F2-Labeltest angepasst).
- **Urteil: Der Nutzer kann 11 Staffeln / 173 Folgen staffelweise verarbeiten, ohne 23 Einzelkästchen zu klicken. Tests prüfen die Assertions in den Rümpfen, nicht nur Namen.**

**E2 (#80-Rest sichtbare Fehler): Nutzen voll umgesetzt.**
- Inline-Fehlermeldungen in Gruppenzeile (`app.js:13489-13496`) und Bulk-Leiste (`app.js:12937-12939`). `console.error` an allen drei Startstellen. Modul-Map `groupRowStartErrors` + Variable `bulkStartError` überleben 6-s-Neuaufbau. Leeren beim nächsten Erfolg.
- Tests decken ab: E2-AK1 (Alle-Knopf Fehler), AK2 (Staffel-Knopf Fehler), AK3 (Bulk Fehler), AK4 (Überleben Neuaufbau), AK5 (Leeren bei Erfolg/Deselect/Verschwinden), AK6 (Bulk-Auswahl bleibt), AK7 (Bestand alert()-Pfade + `appliedInboxGroups` invariant).
- **Urteil: Fehler sind sichtbar statt stilles Scheitern. Tests prüfen Rolle, aria-live, Text, Platzierung, Sperre-Frei.**

**E3 (#83 Frist 30 s): Nutzen voll umgesetzt.**
- `SERIES_SEARCH_TIMEOUT_MS = 30000` (`app.js:3076`), lokaler Controller (`app.js:3090-3098`), `didTimeout`-Flag, Seq-Guard (`app.js:3220`), `clearTimeout` in `finally` (`app.js:3228`).
- Tests decken ab: E3-AK1 (Frist + Abort + Meldung + Sperre frei), AK2 (Ablösung still + Seq-Guard bei spätem Timer), AK3 (normale Suche unberührt + Timer-Cleanup), AK4 (Pfadabdeckung manuell + Workflow), AK5 (Timer-Harness: ≥30000 queue, <30000 sofort, scrollIntoView 200ms kompatibel, 4 Dateien umgestellt).
- **Urteil: Hängende Suche blockiert nicht mehr. Tests prüfen browser-treuen AbortError-Spy, Seq-Guard-Lücke, alle Pfade.**

---

## (2) Hinweise (a)–(f)

**(a) Knopf-Restore nur im catch, Sperre im finally**
- `app.js:13390-13393` (Staffel catch), `app.js:13395-13397` (Staffel finally); `app.js:13475-13478` (Alle catch), `app.js:13480-13482` (Alle finally); `app.js:13036-13039` (Bulk catch), `app.js:13041-13043` (Bulk finally).
- Nach erfolgreichem Start ohne vorherigen Fehler: kein Re-Render → Knopf bleibt ≤6 s auf "wird gestartet…".
- **Empfehlung: ROADMAP-Folgepunkt.** Aus Nutzersicht leicht verwirrend (≤6 s), aber funktional nicht blockierend (Sperre ist frei, man kann sofort neu klicken). ADR-K-4/R-C dokumentiert es als bekanntes Restrisiko. Kein Nachbesserungslauf.

**(b) Hardcoded "30 Sekunden" in Fristmeldung**
- `app.js:3221`: `'Suchfehler: Zeitüberschreitung nach 30 Sekunden. Bitte erneut versuchen.'`
- **Empfehlung: Nachbesserungslauf (trivial, 1 Zeile).** `${Math.round(SERIES_SEARCH_TIMEOUT_MS / 1000)} Sekunden` statt hardcoded 30. Wenn Alex es nicht im Review will: ROADMAP.

**(c) Banner-Sofortstart unsortiert**
- `app.js:12875`: `const files = members.map(m => inboxFilesEntryForItem(m));` — `members` ist unsortiert (Inbox-Reihenfolge).
- `app.js:12585-12588`: `sortedMembers` in `buildGroupedInboxSuggestions` sortiert nach season/episode → Gruppenzeile nutzt `item.items` (= `sortedMembers`).
- **Auswirkung:** Bei Einzelstaffel-Banner-Start zeigt die Zuordnungstabelle die Folgen in Inbox-Reihenfolge (z.B. E02, E03, E01), nicht sortiert.
- **Empfehlung: ROADMAP-Folgepunkt (vorbestehend).** Kein Regression dieser Kette, aber ein echter Bug aus Nutzersicht. Fix: eine Zeile `members.sort(...)` vor dem map in `app.js:12875`.

**(d) Gruppenerkennung entfernt Sonderzeichen**
- `app.js:12538-12539`: `detectInboxGroups` nutzt `suggested_query` direkt als `group_key`. Die Sonderzeichen-Entfernung passiert in `cleanSeriesName` (importiert aus `utils.js`), die auf `suggested_query` angewendet wird, bevor es in die Inbox-Daten kommt.
- **Empfehlung: ROADMAP-Folgepunkt (vorbestehend).** Wenn `Law & Order` zu `Law  Order` wird, ist der Gruppenname nicht mehr erkennbar.

**(f) searchSeries mehrere Aufrufer — Fristmeldung sinnvoll?**
- Alle Aufrufer (`detectExistingSeries` :2989/:3017, Auto-Suche :3069, manuell :7582, Workflow :13232) nutzen denselben Suchbereich `series-search-results`.
- **Empfehlung: akzeptieren.** Die Fristmeldung ist an allen Stellen sinnvoll, weil sie immer im Suchbereich erscheint und der Nutzer dort eine Rückmeldung bekommt. Kein Unterschied zwischen manuellem und Workflow-Pfad aus Nutzersicht.

---

## (3) ROADMAP-Kandidaten (max. 5, priorisiert)

1. **K2 "Rest der Gruppe auswählen" (#74 verwandt, `ROADMAP.md:2061`):** Nach dem Verarbeiten einer Staffel direkt die nächste auswählen, ohne zurück zur Liste. **Echter Nutzen** (Workflow-Beschleunigung bei 11 Staffeln). Schwächt MVP nicht — der MVP erlaubt bereits staffelweises Verarbeiten, K2 wäre Komfort.

2. **#82 "Ignorierte Vorschläge bei neuen Folgen automatisch zurückholen" (`ROADMAP.md:2200-2213`):** Ein ignorierter Gruppenvorschlag erscheint wieder, wenn seit dem Ignorieren neue Folgen dazukommen. **Echter Nutzen** (Serie "erstmal raushaben" und später zurückholen, Alex' Wunsch aus #75). Schwächt MVP nicht.

3. **Banner-Sofortstart sortieren (Hinweis c):** `members` vor dem map sortieren (`app.js:12875`). **Echter Nutzen** (Zuordnungstabelle in richtiger Reihenfolge). Vorbestehend, klein (1 Zeile).

4. **Knopf-Restore nach Erfolg (Hinweis a):** Nach erfolgreichem Start Knopf-Text wieder herstellen. **Leichter Nutzen** (weniger verwirrend). Kosmetisch, ≤6 s.

5. **Fristmeldung dynamisch (Hinweis b):** `SERIES_SEARCH_TIMEOUT_MS / 1000` statt hardcoded 30. **Wartbarkeits-Nutzen**. Trivial (1 Zeile).

---

## (4) Stichproben-pflichtig

**NEIN.** Reine lokale Frontend-Änderung. Keine neuen Abhängigkeiten, keine Außenwirkung über die eigene Instanz hinaus, keine Lizenzänderungen, keine Kaufentscheidungen, keine Rechtsfragen. Bestätigt.

---

## (5) Gesamturteil

**JA aus Nutzersicht.** Die drei Etappen liefern den versprochenen Nutzen: staffelweise Verarbeitung großer Serien ohne 23 Einzelkästchen (E1), sichtbare Fehler statt stilles Scheitern (E2), Weiterarbeiten nach hängender Suche ohne Neuladen (E3). Die Tests decken die AKs in den Rümpfen ab, nicht nur Namen. Die Hinweise (a)–(f) sind entweder vorbestehend (c, d), kosmetisch (a), trivial (b), oder akzeptabel (f). Der wichtigste offene Punkt ist K2 (#74 verwandt), aber der schwächt den MVP nicht — er ist Komfort für den nächsten Lauf.
