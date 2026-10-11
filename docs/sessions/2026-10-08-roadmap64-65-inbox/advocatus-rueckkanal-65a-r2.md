# Rohoutput advocatus — Rückkanal-Abnahme #65 Lauf A, Runde 2, 2026-10-09

Hinweis Claude Code (2026-10-09): Mechanisch aus `opencode export ses_ee000108cffeVtCNa3GOEYXLqe` (ceo-planner, Rückkanal-Sitzung Runde 2) abgelegt, nicht vom Moderator abgeschrieben (Lehre 59). Einzige Änderung: Trailing Whitespace entfernt. Volle Daten: Kit `scripts/gate-a2/logs/2026-10-09-roadmap65-lauf-a-nachbesserung2/export-rueckkanal.json`.

---

## Advocatus: Scope-Sweep files[] Lauf A r2 (Subagent-Sitzung ses_edffa622bffeMP3R26P6k2uvTC, Status: completed)

<task id="ses_edffa622bffeMP3R26P6k2uvTC" state="completed">
<task_result>
# Rückkanal-Bericht — ROADMAP #65 Lauf A, ZWEITE Runde (Risikoprüfer/advocatus)

Prüfgegenstand: Nachbesserungslauf (Head laut Kontext `481d7f0`), der R1–R4, D1, D3 schließen soll. Arbeitsweise: ausschließlich statische Code-Lektüre im exklusiven Worktree, keine Git-Verifikation (kein bash), kein Schreiben. Referenz: `rueckkanal-65a.md` (gelesen zuerst).

---

## 1. ABNAHME-Einschätzung je Befund

| Befund | Urteil | Beleg (Datei:Zeile) |
|---|---|---|
| **R1** (files[] an `media_type=="tv"` binden) | **geschlossen** | `queue_api.py:75–78` (preview: `if files_param is not None: if media_type != "tv": return 400`), `queue_api.py:816–819` (process: identischer 400), `processor.py:870–872` (process_worker: `raise RuntimeError(f"files[] wird nur für media_type 'tv' unterstützt, erhalten: '{media_type}'.")`). Alle drei Konsumpunkte (preview, process, worker) sind abgesichert; die Worker-Prüfung ist die Sicherungsnetz-Ebene für direkte `process_worker`-Aufrufe. |
| **R2** (explicit_*-Scope-Check ohne Basename-Fallback) | **geschlossen** | `processor.py:953–969`: `explicit_junk` (`norm_j = os.path.normpath(j); if norm_j not in scope_files: raise`), `explicit_subs` (`:958–963`), `explicit_renames` (`:964–969`). Ausschließlich `normpath(entry) in scope_files`-Memberschaft; kein `os.path.basename`-Fallback mehr. Die Anwendung (Trash/Rename) liegt strikt danach (`:972` ff.), d. h. LAUTer Abbruch VOR jeder Bewegung bleibt erhalten. |
| **R3** (Fallback-Untertitel-Rename im files-Zweig) | **geschlossen** | `processor.py:1465–1497`: Wortgrenze `vprefix = vstem + "."` (`:1468`), Iteration nur über `companion_files` mit `comp_dir == filename_dir` (`:1470–1475`), Kollisions-`raise` für doppelte Zielnamen (`:1481–1485`) und für bereits existierendes Ziel (`:1488–1492`), erst dann `os.rename` (`:1495`). Der unbegrenzte `os.listdir(current_dir)`-Pfad existiert nur noch im `else`-Zweig (`:1498–1510`), also bei `files_param is None`. |
| **R4** (Unterordner-Gruppen verlieren Begleitdateien nicht) | **geschlossen** | `processor.py:1467` (`vstem = os.path.splitext(os.path.basename(filename))[0]` — Basename statt vollem Relativ-Schlüssel), `:1474` (`normpath(comp_dir) == normpath(filename_dir)`), und die allowed_files-Konstruktion `:1619–1641` (fügt `comp`, `comp_name` sowie `clean_title`-Varianten für Unterordner-Companions hinzu). Preview (`queue_api.py:571` `base_old = os.path.splitext(basename)[0]`) und Process sind jetzt kohärent. |
| **D1** (Cleanup-Gating nur an `files_param is None`) | **geschlossen** | `processor.py:1052` (`if files_param is None:`) und `:1657` (`cleanup_empty_dirs=(files_param is None)`). Der `current_dir != inbox_root`-Zusatz ist an beiden Stellen entfernt; die einzige verbliebene `current_dir != inbox_root`-Stelle ist `:346` in `_finalize_job` (vorbestehend, kein files-Bezug). Alt-Pfade ohne `files` (inkl. Wurzel-/Einzeldatei-Jobs) verhalten sich damit wieder wie vor #65. |
| **D3** (fehlender tv-Einzeldatei-Regressionstest) | **geschlossen** | `tests/test_inbox_group_files.py:621–649` (`test_d3_regression_tv_single_file_job_without_files_cleans_empty_dirs`) — echter `process_worker`-Lauf mit tv-Einzeldatei in Root + leerem Fremd-Unterordner, prüft Ausgabe UND Bereinigung des leeren Ordners. |

**Zwischenfazit:** Alle sechs nachzubessernden Befunde sind auf dem geprüften Stand korrekt und mit ausführbaren Tests geschlossen. Die Nachbesserung ist inhaltlich sauber umgesetzt.

---

## 2. Neue Findings (nur Neues gegenüber rueckkanal-65a.md)

### N1 [kritisch] — Zielnamens-Kollision beim Fallback-Video-Rename überschreibt Fremddatei stillschweigend

**Stelle:** `processor.py:1443–1459` (Fallback-Zweig `explicit_renames is None`), konkret `:1459 os.rename(filepath, target_filepath)` ohne `os.path.exists(target_filepath)`-Check.

**Mechanismus:** Bei einem `files`-Job ist `current_dir == inbox_root`. `target_filepath = os.path.join(current_dir, target_filename)` (`:1412`), `target_filename = f"{clean_title}{ext}"`. Existiert im Inbox-Root eine **Fremddatei** mit exakt dem Namen `clean_title.ext` (z. B. eine früher verarbeitete Folge oder eine manuell abgelegte Datei gleichen Namens), überschreibt `os.rename` sie auf POSIX stillschweigend — **Datenverlust ohne Warnung**.

**Repro-Pfad:** `POST /api/process` mit `{"media_type":"tv","show_name":"MyShow","season":1,"files":["Show.S01E01.mkv"],"mappings":{"Show.S01E01.mkv":{"season":1,"episode":1,"title":"Pilot"}}}` — **ohne** `explicit_renames`. Liegt im Inbox-Root zusätzlich eine Datei `MyShow - S01E01 - Pilot.mkv` (nicht in `files`, nicht Begleitdatei), wird sie bei `:1459` überschrieben. Der bestehende AK6-Haupttest (`:273–352`) fährt genau diesen Pfad, setzt seine Kollisionsdatei aber als `MyShow - S01E01 - Pilot.adversarial.txt` (andere Endung), sodass der exakte Zielnamens-Clash nicht ausgelöst wird.

**Bewertung:** Dies ist die AK6-Kernzusage-Verletzung derselben Klasse wie R1–R4 — ein `files[]`-Job berührt eine Datei außerhalb Gruppe ∪ Begleitdateien — und zwar **ohne** bösartige Parameter, allein durch Namensgleichheit. Der R3-Fix hat den Ziel-Existenzcheck nur für **Untertitelziele** (`:1489–1492 raise`) eingeführt, nicht für das Video-Ziel. Daher [kritisch].

### N2 [wichtig] — `explicit_renames`/`explicit_subs`: Ziel (`new`) weder Scope- noch Existenz-geprüft

**Stellen:** `processor.py:1030–1038` (`explicit_renames`: `os.rename(old_path, new_path)` bei `:1037`), `:1040–1049` (`explicit_subs`: `os.rename` bei `:1048`).

**Mechanismus:** Der R2-Scope-Check (`:964–969` bzw. `:958–963`) prüft ausschließlich die **Quelle** (`old`). Der Zielname `new` ist vollständig ungeprüft: kein `normpath`-Konfinement, keine Memberschaft in `scope_files`, kein `os.path.exists(new_path)` vor dem Rename. `new_path = os.path.join(current_dir, r["new"])` mit `current_dir == inbox_root` (`:1032`).

**Repro-Pfad:** `POST /api/process` mit `{"media_type":"tv","files":["Show.S01E01.mkv"],"mappings":{"Show.S01E01.mkv":1},"explicit_renames":[{"old":"Show.S01E01.mkv","new":"Fremdordner/Fremddatei.txt"}]}`. Der `old`-Eintrag liegt in `scope_files` → Check passiert. Existiert `Fremdordner/Fremddatei.txt`, wird sie bei `:1037` überschrieben. Ein legitimer Preview-Fluss setzt `new` zwar auf `clean_title.ext`, aber die offene API erlaubt beliebige `new`-Werte inkl. Unterordner-Ziele. Der Kollisions-Check `:985–1028` erkennt nur Mehrfach-`old`→gleiches-`new` **innerhalb der Liste**, nicht Kollisionen mit dem Dateisystem.

**Bewertung:** Scope-Durchgriff derselben Klasse (Ziel liegt außerhalb der Gruppe), erfordert allerdings manipulierte/irrtümliche `new`-Werte. Daher eine Stufe unter N1 → [wichtig].

### N3 [wichtig] — Konvertierungs-Pfad schreibt temp/final in den Inbox-Root ohne Existenzcheck (Hypothese H3)

**Stellen:** `processor.py:1554` (`temp_output = os.path.join(current_dir, f"{clean_title}_neu.mkv")`) und `:1581` (`final_filepath=os.path.join(current_dir, f"{clean_title}.mkv")`) — bei `files`-Job ist `current_dir == inbox_root`.

**Mechanismus:** Bei `convert=True` schreibt `execute_video_conversion` den Temp-/Final-Output in den Inbox-Root. Existiert dort eine Fremddatei mit exakt `{clean_title}_neu.mkv` oder `{clean_title}.mkv`, wird sie von ffmpeg (bzw. über `delete_original`/Post-Schritte) überschrieben. Zusätzlich: das Video wurde bereits bei `:1459` auf `clean_title.ext` umbenannt, und `final_filepath` `clean_title.mkv` kollidiert potenziell mit einer **anderen** Fremddatei als das `:1459`-Ziel, sofern die Quelldatei-Endung von `.mkv` abweicht.

**Bewertung:** Dieselbe Kollisionsklasse wie N1, zusätzlich erweitert um die Suffixe `_neu.mkv` und das konvertierte `.mkv`. `convert` ist ein Opt-in-Parameter; Schwere [wichtig].

---

## 3. Hypothesen-Bewertung

- **H1 (Zielnamens-Kollision ohne Existenzcheck) — bestätigt, [kritisch].** Drei ungeschützte `os.rename`-Ziele: `:1459` (Fallback-Video, **ohne** `explicit_renames`), `:1037` (explicit_renames, **mit**), `:1048` (explicit_subs, **mit**). Der R3-Fix schützt nur Untertitelziele im Fallback-Zweig (`:1489–1492`), nicht die drei oben genannten Stellen. Erreichbar über `/process` in beiden Varianten (mit und ohne `explicit_renames`).

- **H2 (`/queue/retry` umgeht Gates) — widerlegt.** `queue_api.py:927–996` re-queued nur bereits persistierte Job-Params. `job_queue_worker` (`processor.py:3690–3706`) ruft `process_worker(params)` auf, der bei `files_param is not None` **vollständig revalidiert**: `media_type`-Check (`:871`), `validate_group_files` (`:879`), TOCTOU-Existenzprüfung (`:948–951`). Ein `files`+Nicht-tv-Job kann gar nicht erst entstehen (`/process` lehnt mit 400 ab), und selbst ein Altbestands-Job würde beim Retry im Worker mit `RuntimeError` abgewiesen. Kein Umgehungsweg.

- **H3 (Konvertierungs-Pfad) — bestätigt, [wichtig].** Siehe N3. temp/final im Inbox-Root ohne Existenzcheck; zusätzliche Kollisionsfläche über `_neu.mkv`/konvertiertes `.mkv`.

- **H4 (Normalisierungsasymmetrie) — widerlegt als Sicherheitslücke.** `validate_group_files` liefert Rohstrings (`f_clean`, `helpers.py:862`), `companion_files` liefert `relpath`-normalisierte Pfade (`helpers.py:912`); der R2-Check vergleicht `normpath(entry)` gegen dieses gemischte Set. Die Asymmetrie erzeugt **nur konservative falsche Abweisungen** (unnormalisierte Client-Pfade wie `Sub//File.mkv` oder Case-Varianten auf case-insensitivem APFS werden nicht als Mitglied erkannt → `RuntimeError`). Eine **falsche Zulassung** ist nicht konstruierbar: `normpath(j) in scope_files` erzwingt case-sensitiv exakte Übereinstimmung, und `os.path.join(current_dir, j)` zeigt dann case-insensitiv garantiert auf dieselbe Datei. Kein Datenrisiko; lediglich ein Robustheits-/Konsistenz-Hinweis (Rohstrings konsequent `normpath`en).

- **H5 (weitere Lücken derselben Klasse):** Keine zusätzlichen über N1–N3 hinaus gefunden. Die geprüften übrigen Konsumenten (`safe_move_recursive`-Aufrufe `:1649–1658` mit `allowed_files`, `:1748–1755` nur bei `files_param is None`, `:2128–2135` movie — durch R1 nicht mehr files-erreichbar; `move_with_fallback` `:386–479` operiert nur im job-eigenen Outbox-Ziel mit Existenzprüfung `:469–474`; `tool_pull_files`/`tool_batch_convert` `:3200–3269` sind Nicht-tv-Zweige und durch R1 für `files` unerreichbar) zeigen keinen Durchgriff auf Inbox-Fremddaten.

---

## 4. Testabdeckung / Testlücken

**Jede Schließung hat einen echten End-to-End-Fall (process_worker-Ausführung):**
- R1: `test_r1_files_param_with_non_tv_media_type_rejected` (`:478–514`) — echte `test_client.post`-Aufrufe für beide Endpunkte + direkter `process_worker`-Lauf.
- R2: `test_r2_explicit_junk_same_basename_in_other_folder_aborts_loudly` (`:516–546`) und `test_explicit_subs_and_renames_outside_scope_aborts_loudly` (`:691–724`).
- R3: `test_r3_fallback_subtitle_rename_boundary_and_foreign_file_untouched` (`:548–586`) und `test_fallback_subtitle_rename_multiple_languages_preserved` (`:651–689`).
- R4: `test_r4_subfolder_group_with_companion_file_moved_to_outbox` (`:588–619`).
- D1/D3: `test_d3_regression_tv_single_file_job_without_files_cleans_empty_dirs` (`:621–649`) und `test_backwards_compatibility_paths_without_files_param` (`:432–473`).

Die AK5-Helper-Tests (`:73–168`) sind Unit-Tests, aber die **Schließungsfälle** R1–R4/D1/D3 sind echte Ausführungen, nicht nur Helper-Aufrufe.

**Nicht durch Tests gefangen:**
- **N1/H1:** kein Test legt eine Fremddatei mit **exakt** dem Video-Zielnamen (`clean_title.ext`) an. Der AK6-Haupttest (`:304`) verwendet `…adversarial.txt` und prüft damit nur den `safe_move_recursive`-`prefix_filter`-Durchgriff, nicht den `os.rename`-Ziel-Clash bei `:1459`.
- **N2:** kein Test für `explicit_renames`/`explicit_subs` mit `new` außerhalb Scope bzw. auf existierende Fremddatei.
- **N3/H3:** kein Test mit `convert=True` + `files`-Job + Kollisionsdatei (`_neu.mkv`/final `.mkv`).
- **H2:** kein `retry`-Test mit `files` — akzeptabel, da H2 widerlegt ist, aber die Revalidierung im Retry-Pfad ist ungetestet (Restrisiko-Notiz).

---

## 5. Entkräftete Punkte (geprüft, kein Finding)

- **H2** (retry-Umgehung): widerlegt, vollständige Revalidierung im Worker.
- **H4** (Normalisierungsasymmetrie als Sicherheitslücke): nur konservative falsche Abweisungen, keine falsche Zulassung.
- `safe_move_recursive`-allowed_files-Realpath-Set (`:502–510` + `:518–521`) schließt Fremdzugriff beim Verschieben in den Outbox weiterhin aus; die F2-Klasse bleibt gedeckt.
- `_finalize_job` `:346` (`current_dir != inbox_root`) greift bei `files`-Jobs nicht (dort `current_dir == inbox_root`) — vorbestehend, kein files-Bezug.
- `tvshow.nfo`/Artwork-Ziel (`:1101–1103`) bleibt bei `files`-Jobs im Outbox-Show-Ordner, nicht im Inbox-Root.
- `move_with_fallback` (`:386–479`): Ziel-Existenzprüfung vorhanden (`:469–474`), operiert nur im job-eigenen Outbox-Ziel; NAS-Companion-Copy (`:137–139`) nur im Outbox-Ordner (bereits in rueckkanal-65a entkräftet).
- `tool_pull_files`/`tool_batch_convert`: Nicht-tv-Zweige, durch R1 für `files`-Eingaben unerreichbar.

---

## Gesamteinschätzung

Die sechs beauftragten Schließungen (R1–R4, D1, D3) sind vollständig und korrekt umgesetzt und getestet. Die AK6-Kernzusage ist jedoch weiterhin **nicht lückenlos**: Es verbleibt eine neue Lücke derselben Klasse — die **Zielnamens-Kollision** beim Rename in den Inbox-Root (N1 [kritisch], N2/N3 [wichtig]). Diese ist klein behebbar (Existenzcheck am Ziel analog `:1489–1492` vor den `os.rename`-Stellen `:1037`/`:1048`/`:1459` sowie vor den Konvertierungs-Zielpfaden `:1554`/`:1581`), plus drei ergänzende Regressionstests. Empfehlung: weiterer kleiner Nachbesserungslauf vor dem Merge.

*Reine Lektüre — es wurde nichts geschrieben, kein Git, kein bash ausgeführt. Head-Identität `481d7f0` wurde nicht selbst verifiziert (kein Git-Zugriff).*
</task_result>
</task>
