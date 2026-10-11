# Rückkanal-Abnahme ROADMAP #65, Lauf A (Server) — DRITTE und LETZTE Runde (Abbruchkriterium)

**Datum:** 2026-10-09 · **Auftraggeber:** Claude Code (Rolle Reviewer/Vermittler), NICHT Alex.
**Alex-Bezug (wörtlich, 2026-10-09):** „1–2 wie empfohlen, starte den dritten Lauf“ — damit gilt das von Claude Code vorgeschlagene **Abbruchkriterium**: geprüft wird nur, ob N1, N2, N3 (und N5) aus `rueckkanal-65a-r2.md` geschlossen sind; neue Befunde werden nur gemeldet, wenn sie **[kritisch]** sind (stiller Datenverlust / Überschreiben fremder Dateien oder Aktion außerhalb der Gruppe durch einen **legitimen** Aufruf). Alles Übrige → ROADMAP-Kandidaten, nicht blockierend.
**Geprüfter Stand:** Worktree `feat-roadmap-65-als-serie-gruppieren`, Head `f264b1f` (laut geliefertem `git log`; kein bash — Head-Identität nicht selbst verifiziert). Code gelesen auf diesem Stand.
**Referenzen:** `rueckkanal-65a-r2.md` (zweite Runde, ABNAHME: NEIN, N1–N6), `rueckkanal-65a.md` (erste Runde), `briefing-65.md` (approved).
**Rollen im Text:** [ich] = Vermittlungsagent; [advocatus] = Risikoprüfer, mit derselben kritisch-Nur-Grenze konsultiert; seine Aussagen sind ungekürzt dem [advocatus]-Transkript zu entnehmen (Claude-Code-`opencode export`; gemäß Auftragsregel „Rohoutputs nicht abschreiben“ diese Runde **nicht** als Anhang eingebettet — hier nur sinngemäße, zugerechnete Wiedergabe).
**Vor-Review-Kontext (Berichte von Claude Code, nicht selbst verifiziert):** Gate-A2 APPROVED nach 2 Runden; Diff `cb152f0..f264b1f` nur `API.md` (+4), `gui/workers/processor.py` (+68), `tests/test_inbox_group_files.py` (+279); 508 passed/1 deselected + Frontend 150/150; 6 neue Tests (N1 ×2, N2 ×2, N3 ×2) gegen `cb152f0` rot. **Plausibilität [ich]:** 502 (Runde 2) + 6 neue Tests = 508 ✓; die 6 Testnamen existieren genau (`:729, :768, :805, :872, :937, :971`) ✓; `queue_api.py` im Diff unberührt, damit gelten die R1/R2-Schließungen auf API-Seite unverändert fort ✓.

---

## ABNAHME: JA

**Begründung in einem Satz:** Alle vier verbliebenen Befunde (N1, N2, N3, N5) sind nachweislich geschlossen — an jedem Zielpunkt steht jetzt ein `files_param`-gegateter Existenz-/Konfinement-Check **vor** der schreibenden Aktion, jeweils mit echtem `process_worker`-End-to-End-Test inklusive byte-genauer Fremddatei-Assertion — und weder [ich] noch [advocatus] haben unabhängig voneinander einen neuen [kritischen] Befund im Sinne des Abbruchkriteriums gefunden; der Zielpfad der AK6-Kernzusage („ein `files[]`-Job berührt AUSSCHLIESSLICH Gruppe ∪ Begleitdateien“) ist damit auf der Ziel-Seite ebenso hart abgesichert wie in Runde 2 auf der Quell-Seite.

Zusätzlich über den Auftrag hinaus gehärtet (von [ich] und [advocatus] bestätigt, mit Test): die **Episoden-NFO-Zielkollision** in der Inbox-Root (`processor.py:1560–1565`, Check vor `generate_episode_nfo`-Aufruf `:1570`) — dieselbe Klasse wie N1, in Runde 2 nicht als Befund geführt, jetzt ebenfalls laut abgesichert (`test_n1_nfo_target_collision_with_foreign_file_aborts_loudly`).

---

## 1. Befund-Tabelle: Schließungsprüfung (Code-Prüfung [ich], unabhängig bestätigt durch [advocatus])

| Befund | Geschlossen? | Beleg Code | Beleg Test |
|---|---|---|---|
| **N1** [kritisch] Fallback-Video-Rename überschreibt Fremddatei mit exaktem Zielnamen in der Inbox-Root | **ja** | `processor.py:1489–1492`: vor `os.rename(filepath, target_filepath)` (`:1495`) prüft `files_param is not None and os.path.exists(target_filepath) and os.path.abspath(filepath) != os.path.abspath(target_filepath)` → `RuntimeError „Kollision beim Umbenennen von Video“`. Die `abspath`-Gleichheits-Ausnahme erhält den legitimen No-Op-Fall (Datei heißt bereits korrekt → kein Fehlabbruch). Flankierend: fehlende Quelle wirft jetzt laut (`:1482–1483`) statt still zu `continue`-en, und Rename-Fehler werden bei `files`-Jobs nicht mehr geschluckt (`:1496–1498 raise`) | `test_n1_fallback_video_target_collision_with_foreign_file_aborts_loudly` (`tests/test_inbox_group_files.py:729–766`): exakt der R2-Repro (Zielname **mit gleicher Endung** `.mkv`, kein `explicit_renames`), assertiert RuntimeError **und** byte-treue Fremddatei (`:763–764`) plus Erhalt der Quelle (`:766`); ergänzt durch den NFO-Test `:768–803` |
| **N2** [wichtig] `explicit_renames`/`explicit_subs`: Ziel `new` ungeprüft (a) Überschreibung, (b) Pfadteil, (c) absolut | **ja** (im vereinbarten Fix-Umfang; Rest (b) siehe ROADMAP-Kandidaten) | Validierung: subs `processor.py:969–978`, renames `:988–997` — je (c) Absolut-Pfad-Ablehnung (`:970–971`/`:989–990`), (b) Traversal-/Konfinement-Check unter `current_dir` (`:972–974`/`:991–993`), (a) Ziel-Existenz-Check (`:977–978`/`:995–997`); **und** unmittelbar vor jedem `os.rename` eine zweite, gegen TOCTOU zwischen Validierung und Anwendung gerichtete Existenzprüfung (`:1065–1066` renames, `:1078–1079` subs) mit derselben `abspath`-Ausnahme; fehlende Quelle → lauter TOCTOU-Raise (`:1062–1063`/`:1075–1076`) | `test_n2_explicit_renames_destination_validation_and_collisions` (`:805–870`) prüft alle drei Wirkungen (absolut `/tmp/evil/…`, `../outside.mkv`, existierendes `Fremdordner/Target.mkv`) und die byte-treue Fremddatei (`:867–870`); `test_n2_explicit_subs_destination_validation_and_collisions` (`:872–935`) analog für `explicit_subs` (`:932–935`) |
| **N3** [wichtig] Konvertierung schreibt temp/final in den Root ohne Check | **ja** | `processor.py:1604–1614`: vor `execute_video_conversion` (`:1638`) prüfen bei `files`-Jobs beide Ziele — `temp_output` `{clean_title}_neu.mkv` (`:1607–1610`) und `final_conv_output` `{clean_title}.mkv` (`:1611–1614`) — auf Existenz, jeweils mit `abspath`-Ausnahme gegenüber `target_filepath`. Diese Ausnahme ist **notwendig und hinreichend richtig**: bei Quell-Endung `.mkv` ist das eigene, soeben umbenannte Video identisch mit dem Final-Ziel — ohne Ausnahme würde jede legitime mkv→mkv-Konvertierung fehlabbrechen; mit Ausnahme bleibt die Fremddatei-Kollision (anderer Name ⇒ anderes abspath) erfasbar | `test_n3_convert_temp_target_collision_aborts_loudly` (`:937–969`) und `test_n3_convert_final_target_collision_aborts_loudly` (`:971–1003`) — beide mit `.mp4`-Quelle (Zielname ≠ Final-`.mkv`), assertieren exakte Fehlermeldungen (`:966`, `:1000`) und byte-treue Fremddateien (`:967–969`, `:1001–1003`) |
| **N5** [wichtig, Doku] API.md dokumentiert den neuen 400er nicht | **ja** | `API.md:263` (`/api/preview-process`): „Nur für `media_type` `'tv'` erlaubt (andere Medientypen werden mit HTTP 400 abgewiesen)“; `API.md:268` (`/api/process`): dieselbe Einschränkung plus Strikter-Scope-Hinweis — beide Endpunkte der R1-Änderung abgedeckt | — (reine Doku; Verhaltensebene bereits durch R1-Test `:478–514` gedeckt) |

**D1-Prinzip (Alt-Pfade unverändert) — von [ich] und [advocatus] unabhängig bestätigt:** sämtliche neuen Raises liegen hinter `files_param is not None` (Validierung komplett im Block `:947–997`; Einzel-Gates `:1062/:1065/:1074/:1078`, `:1482/:1489/:1497`, `:1560/:1577`, `:1606`); der unbegrenzte `os.listdir`-Untertitel-Fallback (`:1540–1552`) und die Show-Meta-Datei-Bewegung (`:1778`) bleiben ausschließlich im `files_param is None`-Zweig. Alt-Jobs verhalten sich weiterhin wie vor #65.

**Nicht erneut geprüft (unberührt, da nicht im Diff):** `queue_api.py` (R1-Gates), die in Runde 2 entkräfteten Stellen (`safe_move_recursive`-Aufrufe, `move_with_fallback`, `_finalize_job:346`, NAS-Companion-Copy, movie-/tool-Zweige, Retry-Pfad).

---

## 2. Neue [kritische] Befunde

**Keine.** [ich] (eigener Rundgang über alle schreibenden Aktionen im `files`-Zweig: Renames, NFO, Convert, `shutil.move` in die Outbox `:1669`, `safe_move_recursive` `:1709–1718`) und [advocatus] (explizit gegen die Frage „gibt es eine **legitime** Aufruffolge, die eine Fremddatei im Inbox-Root noch still berührt?“) kamen unabhängig zum selben Ergebnis: keine. Der Outbox-`shutil.move` `:1669` adressiert nur den job-eigenen Episodenordner und ist durch `file_already_in_outbox`-Skip (`:1661–1662`) sowie die vorbestehende Manifest-Logik gedeckt — kein Inbox-Fremdzugriff, kein neuer Befund.

Damit ist das Abbruchkriterium erfüllt: **die Rückkanal-Schleife zu #65 Lauf A endet hier.**

---

## 3. ROADMAP-Kandidaten (nicht blockierend)

Gemäß Abbruchkriterium ausdrücklich **nicht** Teil des Abnahme-Urteils; Vorschlag zur Aufnahme in `ROADMAP.md` (Formulierungsvorschlag, Entscheidung liegt bei Alex/Claude Code):

1. **N2-Rest (b):** `new` mit **relativem Pfadteil in einen existierenden Inbox-Unterordner** (kein `..`, nicht absolut, Ziel existiert noch nicht) passiert die Checks — die Gruppe würde in einen fremden Ordner **hineinlegt** (kein Überschreiben, nur mit manipuliertem Parameter erreichbar, kein legitimer Client sendet Pfadteile). Erwägen: `new` bei `files`-Jobs auf flache Namen unter `current_dir` konfieren. [advocatus] und [ich] unabhängig.
2. **N4 (aus Runde 2, bewusst nicht jetzt gelöst):** Halb-umbenannter/halb-kopierter Zustand bei lautem Abbruch (Video schon umbenannt, spätere Episode kollidiert; Retry läuft dann in die neuen Kollisions-Raises, inkl. **stale `{clean_title}_neu.mkv`** aus abgebrochenem Convert — [advocatus]-Notiz: konservativ, laut, kein Datenverlust). Gehört in die Retry-/Wiederaufnahme-Story **#68** als Anwendungsfall.
3. **TOCTOU Ziel-Fenster:** Zwischen `os.path.exists(Ziel)` und `os.rename`/ffmpeg-Start kann lokal eine neue Datei entstehen ([advocatus]-Restunsicherheit; über legitimen Client nicht steuerbar, Einzelplatz-Server — Restrisiko, kein Blocker).
4. **N6 (aus Runde 2, [kosmetisch]):** Normalisierungsasymmetrie `scope_files` (Roh- + normpath-Einträge) — nur konservative Fehl-Abschreibungen; Notiz: Rohstrings konsequent `normpath`en. Neue Randnotiz [ich]: der `relpath(...).startswith("..")`-Konfinement-Check lehnt auch Dateinamen wie `..foo.mkv` konservativ ab — Fehl-Abschreibung, kein Risiko.
5. **D2/D4 (aus Runde 1/2, [kosmetisch], unverändert offen):** Endungsliste doppelt (`helpers.py:798` ≡ `queue_api.py:113`); toter Code `get_group_scope_files` (`helpers.py:921–929`).
6. **Test-Hygiene ([advocatus]-Notiz):** `test_n1_nfo_…` patcht den TVDb-Fetch nicht; der Netzwerkpfad wird im Erfolgsfall zwar vor dem Fetch abgebrochen, die Konstruktion ist aber potenziell flaky — bei Gelegenheit härten.
7. **Retry-Revalidierung ungetestet** (Restnotiz aus Runde 2): Pfad statisch entkräftet, aber ohne Test.

**Bezug zu #71 (Lauf B):** #71 setzt auf genau diesem jetzt abgesicherten Zielpfad auf; die Kandidaten 1–3 sind „vor/bei Lauf B mitdenken“-Material, keine Voraussetzungen.

---

## 4. Empfehlung an Alex

1. **ABNAHME: JA → mergebereit.** Die drei Zielpunkt-Fixes sind symmetrisch zum bewährten R3-Muster, durchgehend `files_param`-gegated (D1-Prinzip gewahrt) und mit sechs echten End-to-End-Tests inkl. Byte-Identitäts-Behauptungen gesichert. **Kein weiterer Nachbesserungsschlag nötig** — das Abbruchkriterium ist erfüllt, die Schleife endet. Trade-off der Annahme: die ROADMAP-Kandidaten 1–3 bleiben als bekannte, unkritische Resten offen; das ist der vereinbarte Preis des Abbruchkriteriums.
2. **Reihenfolge wie beschlossen:** PR/Merge von Lauf A (Merge = Klasse C, dein Einzel-Go), dann Lauf B (#71); N4 als Anwendungsfall bei #68 notieren.
3. **Zeiten:** KI-seitig ist alles erledigt; dein Engpass ist nur diese Leseproben-Entscheidung (Merge-Go) plus ggf. die ROADMAP-Punkte 1–7 zum Abnicken.

**Stichproben-pflichtige Themen (Geld/Aussenwirkung/Recht/Registrierung/Kauf):** keine — reine Server-Integritätsrunde, keine Assets/Lizenzen/Registrierungen berührt.

---

## 5. Dissens-Pflicht

- **Diese Runde: kein Rollenwiderspruch.** [ich] und [advocatus] kamen unabhängig auf dieselben vier Schließungen, denselben „keine [kritisch]“-Befund und dieselben ROADMAP-Reste (N2(b), stale temp, Halbzustand). Der Vollständigkeit halber dokumentiert: die in Runde 2 dokumentierten Dissense (N1-Schwere [wichtig] vs. [kritisch]; H2/H4-Entkräftungen) sind gegenstandslos, seit N1 geschlossen ist; die mildere N1-Lesart bleibt dort als verworfene Alternative archiviert.
- **Differenz nur im Detail:** [advocatus] führt den stale-`_neu.mkv`-Retry-Fall als eigenen Kandidaten, [ich] würde ihn unter N4 (#68) einordnen — rein kategorisierend, keine Bewertungsdifferenz.

## 6. Restunsicherheiten (nicht selbst ausführbar)

Kein bash/git: Head-Identität (`f264b1f`), der Diff-Umfang `cb152f0..f264b1f` (3 Dateien), die Testresultate (508 grün/1 deselected, Frontend 150/150, 6 Tests gegen `cb152f0` rot) und `git diff --check` sind Claude-Code-Berichte — von [ich] nur plausibilisiert (Testanzahl-Arithmetik, Testnamen-Vorhandensein, Konsistenz des Gelesenen mit dem gemeldeten Umfang), nicht ausgeführt. Die Byte-Identität der Alt-Pfade gegen `6152839` (D1) bleibt wie in Runde 2 aus dem Code abgeleitet, nicht diff-verifiziert. `scripts/refresh_graphify.sh` wurde von uns nicht ausgeführt (Schreib-/Git-Aktionen sind uns untersagt).

---

*Ende des Rückkanal-Laufs r3 — gemäß Abbruchkriterium der letzte Lauf zu #65 Lauf A. Danach STOPP: kein Git, kein Push, kein repo-operator, keine weiteren Dateien. Diese Datei war die einzige Schreibaktion; der ungekürzte [advocatus]-Beitrag liegt im Subagent-Transkript (Claude-Code-Export), gemäß Auftrag „Rohoutputs nicht abschreiben“ diesmal nicht eingebettet.*
