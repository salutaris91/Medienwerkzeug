# Rohoutput produktberater — Rückkanal-Abnahme #65 Lauf B, 2026-10-11

Hinweis Claude Code (2026-10-11): Mechanisch aus `opencode export ses_ed5ab38dbffeCFt68B8VTGCsW7` (ceo-planner, Rückkanal-Sitzung) abgelegt, nicht vom Moderator abgeschrieben (Lehre 59). Einzige Änderung: Trailing Whitespace entfernt. Volle Daten: Kit `scripts/gate-a2/logs/2026-10-11-roadmap65-lauf-b/export-rueckkanal.json`.

---

## produktberater: Chancen Lauf B (Subagent-Sitzung ses_ed59ebfbbffen95unkbPNFkDml, Status: completed)

<task id="ses_ed59ebfbbffen95unkbPNFkDml" state="completed">
<task_result>
Ich habe alle Kontextdateien, den ROADMAP-Abschnitt und den Lauf-B-Code vollständig gelesen. Hier ist meine Analyse.

---

## Bewertung: Lauf B Oberfläche — MVP-Fluss und neue Kandidaten

### Vorbemerkung: Verifizierter Lauf-B-Code-Stand

Gelesen und bestätigt: `app.js:12371–12930`. Alle Bausteine sind vorhanden und korrekt verdrahtet:
- `extractStrictSeasonEpisode` (:12377) — eigenes strenges Muster, kein `parse.js`-Aufruf
- `detectInboxGroups` (:12392) — `media_type==="tv"` && `is_dir===false` && nicht-leerer Schlüssel && ≥2 Treffer
- `buildGroupedInboxSuggestions` (:12417) — Pseudo-Eintrag mit `is_group: true`, `data-group-key`, KEIN `data-project`
- `updateGroupBannerUI` (:12469) — Banner mit Bestätigung/Ignorieren, sessionStorage-Ignorierung
- `updateBulkActionsBarUI` (:12526) — Bulk-Leiste ab ≥1 Auswahl, Zähler, „Auswahl aufheben", „Ausgewählte als Serie gruppieren"
- `startSeriesGroupWorkflow` (:12564) — setzt `activeSeriesGroupFiles`, klickt Serien-Modus, vorfüllt Suche
- `createSeriesGroupPayload` (:12588) — **produktiv toter Code** (dazu unten mehr)
- `renderSmartInboxList` (:12664) — Gruppenzeile mit Chevron, Members-Liste, Checkboxen, Film-Sperre, Bulk-Leiste

---

### 1. Nutzen: Erfüllt die Oberfläche den echten Nutzungskontext?

**Ja — der MVP-Fluss für die 264-Folgen-Serie ist DICHT.**

Vollständiger Flow im Code nachvollzogen:

1. **Erkennung:** `detectInboxGroups` gruppiert 264 Dateien mit gleichem `suggested_query` zu EINER Gruppe (vorausgesetzt, das Muster trifft und der Schlüssel ist nicht leer — das ist die bekannte Einschränkung für `1x05`/`Staffel 2 Folge 3`, die über Checkboxen abgedeckt ist).
2. **Banner:** `updateGroupBannerUI` zeigt „Als Serie gruppieren: ShowName (264 Folgen, Staffel 1–11)".
3. **Bestätigung:** Klick auf „Als Serie gruppieren" → `appliedInboxGroups.add(groupKey)` → Gruppenzeile erscheint in der Liste.
4. **Workflow-Start:** `startSeriesGroupWorkflow(groupKey, files)` mit allen 264 Dateien als `files[]`.
5. **Modal:** Bestehendes Vorschau-Modal, Suche vorbefüllt, 264 Zeilen Matching-Matrix.
6. **Übergabe:** `executeSeriesWorkflow` (:4307) baut das Payload mit `files: [...264]` und `mappings: {...}` (Nahtstelle :4424–4426).
7. **Server:** Ein Job, ein Scope, bewährter Serien-Flow.

**Wo der Flow sperrig bleibt (und ob das MVP-relevant ist):**

| Sperrstelle | Schwere | MVP-blockierend? |
|---|---|---|
| 264 Checkboxen einzeln anhaken (manueller Weg) | Hoch — aber der Auto-Banner löst das | Nein, Banner + Gruppen-Button decken den Hauptfall |
| `suggested_query` leer (z.B. `Staffel 2 Folge 3 – Show.mkv`) → keine Auto-Gruppe | Mittel — manuelle Checkboxen sind der Ausweg | Nein, AK12/AK13 decken das |
| 264 Zeilen im Vorschau-Modal (Dissens 4) | Mittel — DOM-Performance, Handtest nötig | Nein, ist als Restrisiko dokumentiert |
| Gruppe aus 2 Dateien (Fehlgruppierung) | Niedrig — Alex sieht die 2 Zeilen und erkennt den Fehler | Nein, Gegenmittel ist Abwählen im Modal |

**Fazit:** Kein zwingend fehlendes Element für den MVP-Fluss. Der Handtest (Briefing Abschnitt 8) ist der Pflichtschritt, nicht ein weiteres Feature.

---

### 2. Neue Chancen NUR aus Lauf-B-Fähigkeiten — Dupletten-Check

Ich habe jede Idee gegen #45, #68, #69, #70, #71, #72, K1–K4, P1–P4 und die verworfenen Positionen geprüft.

#### Geprüfte und ausgeschlossene Ideen (bereits dokumentiert):

| Idee | Status | Beleg |
|---|---|---|
| „Alle auswählen" auf Listenebene | **Verworfen** | Briefing Abschnitt 4, K2 (rueckkanal-64.md) |
| Gruppen-Editier-UI (Folgen verschieben, Schlüssel umbenennen) | **Zurückgestellt** | Briefing Abschnitt 4, Zeile 70 |
| Modal-Virtualisierung | **Verworfen MVP** | Briefing Abschnitt 4, Zeile 68; Dissens 4 |
| Auswahl-Persistenz (sessionStorage für Haken) | **Abgelehnt** | Briefing Abschnitt 6, Zeile 149 |
| Doku-Gruppierung | **Bewusst raus** | Briefing Abschnitt 4, Zeile 69 |
| Staffel-Zwischenüberschriften | **Raus** | Briefing Abschnitt 4, Zeile 71; Alex' Akt-3-Punkt 4 |
| Inbox-Ordner aufklappen | **Bereits #71** | ROADMAP.md:1962 |
| Filmreihe am Stück | **Bereits #69** | ROADMAP.md:1918 |
| Filter nach Medientyp | **Bereits #70** | ROADMAP.md:1940 |
| Speicher-Summenzeile | **#45 Vorstufe** | ROADMAP.md:1398 |

#### Prüfe ich jetzt auf genuinely-neuen Status:

---

**Idee: „Alle Folgen dieser Gruppe auswählen" (gruppenweiter Auswahl-Button)**

- **Was es wäre:** Auf der Gruppenzeile ein Button „Alle 264 auswählen" → alle Mitglieder als Checkbox-Haken → Bulk-Leiste → „Ausgewählte als Serie gruppieren".
- **Unterschied zum verworfenen „Alle auswählen":** Das verworfene war listenweit (264+ Einträge über alle Serien/Filme/Dokus). Dies hier ist gruppenweit (nur die 264 Mitglieder EINER bestätigten Gruppe).
- **Aber:** Die Gruppenzeile hat bereits einen Button „Als Serie gruppieren" (:12719–12721), der **direkt** `startSeriesGroupWorkflow(item.group_key, files)` mit ALLEN Mitgliedern aufruft. Der Umweg über Checkboxen wäre nur nützlich, wenn Alex einzelne Mitglieder VOR dem Workflow-Start ausschließen will.
- **Gegenmittel bereits vorhanden:** ADR-65-4 dokumentiert „vollständige Quell-Dateinamen im Modal + Abwählen einzelner Folgen" als Lösungsstrategie. Das Modal hat die Matching-Matrix, in der einzelne Zeilen auf „skip" gesetzt werden können.
- **Nutzen vs. Aufwand:** Komfortgewinn marginal (spart 3 Klicks im Modal bei Fehlgruppierung), aber neue UI-Komplexität (gruppenweiter Selektionszustand, Interaktion mit Bulk-Leiste, Testfläche). Für den Einzelnutzer, der die Gruppe im Modal sieht, ist das Abwählen dort zumutbar.
- **Empfehlung: Verwerfen.** Der Gruppen-Button „Als Serie gruppieren" deckt den Hauptfall ab; das Modal deckt den Korrekturfall. Ein dritter Weg („gruppenweise vorwählen") schafft eine zusätzliche Zustandsachse ohne echten Mehrwert.

---

**Idee: „Serie ignorieren für immer" (persistente Ignorierung)**

- **Was es wäre:** Der „Ignorieren"-Button im Banner (:12509–12516) persistiert aktuell in `sessionStorage` (Sitzung). „Für immer" bräuchte `localStorage` oder ein Server-Feld.
- **Nutzen:** Wenn Alex die Banner-Wiederkehr bei jedem Reload als störend empfindet.
- **Aber:** (a) Der Banner ist nicht-blockierend — er nervt, aber er hindert nicht. (b) Wenn Alex die Dateien wirklich nicht will, kann er sie einzeln in Quarantäne schieben. (c) „Für immer" ist ein starkes Versprechen — was, wenn die Dateien doch verarbeitet werden sollen? (d) Persistente Ignorierung erfordert neue Speicher-Logik (Server-Endpoint oder localStorage mit Cleanup-Regel).
- **Dupletten-Check:** ≠ verworfene sessionStorage-Auswahl-Persistenz (anderer Zustand, andere Semantik). Aber das Prinzip „bewusst nicht persistiert" (Briefing Abschnitt 6, Zeile 149) gilt analog.
- **Empfehlung: Verwerfen für jetzt.** Der Handtest wird zeigen, ob die Banner-Wiederkehr ein echtes Problem ist. Falls ja, ist `localStorage` mit einem „Ignorierte Serien"-Dialog (zum Reaktivieren) der minimale Weg — aber das ist dann immer noch ein eigenes Feature mit eigener Testfläche.

---

**Idee: Banner-Multi-Gruppe (mehrere Banner gleichzeitig)**

- **Was es wäre:** `updateGroupBannerUI` (:12469) zeigt nur EINE Gruppe (die erste nicht-ignorierte, nicht-angewendete). Bei 3 verschiedenen Serien in der Inbox sieht Alex nur einen Banner.
- **Aber:** Die anderen Gruppen sind als Gruppenzeilen in der Liste sichtbar (:12688–12773), jeweils mit eigenem „Als Serie gruppieren"-Button. Der Banner ist eine Benachrichtigung, die Gruppenzeile ist der dauerhafte Interaktionspunkt.
- **Empfehlung: Verwerfen.** Kein echtes Problem — die Gruppenzeilen lösen es bereits.

---

**Idee: Gruppen-Vorschau vor Bestätigung (erweiterte Banner-Anzeige)**

- **Was es wäre:** Der Banner zeigt „264 Folgen, Staffel 1–11". Die Gruppenzeile zeigt beim Aufklappen alle 264 Mitglieder mit SxxExx-Badges (:12729–12742).
- **Frage:** Reicht das? Für 264 Einträge ist die aufgeklappte Gruppenzeile eine lange Liste — aber sie ist da, mit Scroll, und zeigt jeden Dateinamen.
- **Empfehlung: Verwerfen als neues Feature.** Die Kombination Banner (Zusammenfassung) + Gruppenzeile (aufklappbar, alle Mitglieder) ist ausreichend. Dissens 4 (Modal-Performance) ist das dokumentierte Restrisiko, nicht die Gruppen-Vorschau.

---

**Idee: Merge zweier Gruppen mit gleichem Schlüssel (Kollisions-UX)**

- **Was es wäre:** Wenn zwei Serien denselben `suggested_query` haben, landen sie in einer Gruppe. ADR-65-4 dokumentiert das als Restrisiko.
- **Gegenmittel:** „Vollständige Quell-Dateinamen im Modal + Abwählen einzelner Folgen" (ADR-65-4, Zeile 97).
- **Empfehlung: Verwerfen als neues Feature.** Das Restrisiko ist bekannt und dokumentiert. Ein „Gruppe teilen"-UI wäre ein eigenes Editier-Feature (→ zurückgestelltes Gruppen-Editier-UI, Briefing Abschnitt 4).

---

### 3. Code-Befunde des Vermittlers — Feature oder Bug-Folge?

#### (a) Client-Endungsliste ohne `.ts` (`app.js:3681`) vs. Server 10 Endungen

**Verifiziert.** `app.js:3681`:
```js
return ['mp4', 'mkv', 'avi', 'webm', 'mov'].includes(ext);
```
Server `queue_api.py:113`:
```python
video_exts = ('.mp4', '.mkv', '.avi', '.webm', '.mov', '.ts', '.m2ts', '.flv', '.3gp', '.wmv')
```

**Analyse:** Dies ist in `renderMatchingMatrix` — der Vorschau-Modal, der die Dateien für die Episoden-Zuordnung anzeigt. Eine `.ts`-Datei würde:
1. Vom Server als `media_type: "tv"` klassifiziert werden (`project_api.py:1321` hat `.ts`).
2. Von `detectInboxGroups` als Gruppenmitglied erkannt werden (keine Endungsprüfung).
3. Im `files[]`-Payload an den Server geschickt werden (Server akzeptiert es).
4. **Aber:** Im Vorschau-Modal nicht in der Matching-Matrix erscheinen → der Nutzer sieht die Datei nicht, kann sie keiner Episode zuordnen.

**Bewertung:** Dies ist ein **vorbestehender Bug** (nicht von Lauf B eingeführt). Lauf B's Gruppierungserkennung ist endungsagnostic und funktioniert korrekt. Das Problem liegt in der bestehenden `renderMatchingMatrix`, die auch ohne `files[]`-Pfad gilt (Ordner-Projekte mit `.ts`-Dateien zeigen dieselbe Lücke).

**Empfehlung: Kein neues Feature. Härtungs-Kandidat für #72-Nachbarschaft** (oder eigener kleiner Bugfix). Die Fix ist trivial: die 5 fehlenden Endungen ergänzen. Aber das ist eine einzelne Zeile, kein Feature.

#### (b) `createSeriesGroupPayload` (~:12588) = toter Code; `executeSeriesWorkflow` (~:4424) ungetestet

**Verifiziert.** Der Test `inbox_group.test.js:896` prüft `createSeriesGroupPayload`. Aber im produktiven Code wird diese Funktion **nie aufgerufen**:

- `startSeriesGroupWorkflow` (:12564) setzt `activeSeriesGroupFiles` und `projectFiles`, klickt das Serien-Modus, füllt die Suche vor.
- Der Nutzer wählt im Modal eine Show, prüft die Zuordnungen, klickt „Verarbeiten".
- `executeSeriesWorkflow` (:4307) baut das Payload. Bei `:4424–4426`:
  ```js
  if (activeSeriesGroupFiles && activeSeriesGroupFiles.length > 0) {
      payload.files = [...activeSeriesGroupFiles];
  }
  ```
  Das ist die **echte Nahtstelle** — und sie ist ungetestet.

**Bewertung:** Dies ist ein **Test-Härtungsproblem**, kein Feature. Der Test prüft eine Hilfsfunktion, die für die Entwicklung geschrieben wurde, aber im produktiven Fluss keine Rolle spielt. Die echte Nahtstelle (`executeSeriesWorkflow` → `activeSeriesGroupFiles` → `payload.files`) ist durch keinen automatisierten Test gesichert.

**Empfehlung: Kein neues Feature. Härtungs-Kandidat für #72-Nachbarschaft.** Konkreter Vorschlag: (a) `createSeriesGroupPayload` entfernen oder als `// test-only` markieren, (b) einen Test schreiben, der `executeSeriesWorkflow` mit gesetztem `activeSeriesGroupFiles` prüft (Mock-DOM, `fetch`-Spy, Assert auf `payload.files`). Das ist eine halbe Gate-A2-Runde, kein eigenes ROADMAP-Item.

---

### 4. MVP-Disziplin: Gesamtbewertung

| Kriterium | Urteil |
|---|---|
| Echter Nutzer-Nutzen vs. Spielerei | Alle geprüften Ideen sind entweder Spielerei (Multi-Banner) oder durch bestehenden Code abgedeckt (Gruppen-Button, Gruppenzeile als Vorschau) |
| Aufwand KI vs. Alex-Engpass | Jede Idee wäre KI-seitig schnell umsetzbar, aber jeder neue PR bedeutet Alex-Review-Zeit — der Engpass. Kein Kandidat rechtfertigt diesen Engpass. |
| Abgrenzung zu bestehenden Einträgen | Alle Ideen sind entweder Dupletten oder gehören in #72 (Härtung) |
| Schließt Lauf B den MVP-Fluss dicht ab? | **Ja.** Der Flow Erkennung → Banner → Gruppe → Modal → Verarbeitung ist im Code vollständig und korrekt verdrahtet. |

---

### Kandidatenliste

**Keine neuen ROADMAP-Kandidaten.**

Nach strenger Dupletten-Prüfung gegen #45/#68/#69/#70/#71/#72, K1–K4, P1–P4 und die verworfenen Positionen bleibt kein genuinely neuer Kandidat übrig. Alle Ideen, die aus dem Lauf-B-Oberflächenstand entstehen könnten, sind entweder:

1. **Bereits abgedeckt** durch den bestehenden Lauf-B-Code (Gruppen-Button, Chevron-Vorschau, Bulk-Leiste),
2. **Bereits dokumentiert** als Restrisiko (ADR-65-4 Kollision, Dissens 4 Modal-Performance),
3. **Härtungs-Themen** für #72 (`.ts`-Endung, toter Code/Testlücke), oder
4. **Komfort-Ideen ohne MVP-Relevanz** (persistentes Ignorieren, Multi-Banner, gruppenweite Checkbox-Vorauswahl).

### Was in #72 gehört (aus Lauf B, keine Dupletten):

1. **`.ts`-Endung in `renderMatchingMatrix` ergänzen** (`app.js:3681`): 5 → 10 Endungen, synchron zur Server-Liste `queue_api.py:113`. Einzeiler, aber wichtig für `.ts`-Folgen in der Matching-Matrix.
2. **`createSeriesGroupPayload`-Test ersetzen**: Test auf `executeSeriesWorkflow` mit `activeSeriesGroupFiles` umschreiben (echte Nahtstelle :4424). `createSeriesGroupPayload` entfernen oder als Test-Hilfsfunktion kennzeichnen.

Beides sind kleine Härtungs-Punkte, keine eigenen ROADMAP-Einträge — sie gehören als Unterpunkte in #72 oder als eigenständige kleine PRs.

---

### Abschließende Aussage

**Lauf B schließt den MVP-Fluss für die 264-Folgen-Serie DICHT ab.** Es fehlt nichts Zwingendes. Der einzige offene Punkt ist der **Handtest** (Briefing Abschnitt 8) mit der echten Serie — er wird zeigen, ob die 264-Zeilen-Matrix im Modal performt und ob die `files[]`-End-to-End-Kette wie erwartet funktioniert. Bis dahin ist kein weiteres Feature nötig.

Die beiden Code-Befunde (`.ts`-Endung, toter Test-Code) sind reale, aber kleine Härtungsthemen für #72-Nachbarschaft — keine Features, keine eigenen ROADMAP-Einträge.
</task_result>
</task>
