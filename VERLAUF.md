# Projektverlauf – Historie

Hier befindet sich die kumulative Historie des projektfortschritts, ausgelagert aus `STAND.md`.

## Stand am 14.07.2026 (Phase 2.5c – FSK-Workflow-Abschlusskorrektur)

- **Worker-Zwischenstand bereinigt:** Die durch Leerzeilen auf 1.405 Zeilen aufgeblähte Backend-Testdatei wurde auf einen lesbaren Stand zurückgeführt; fachliche Regressionen wurden gezielt statt per globalem Whitespace-Skript ergänzt.
- **Backend-Sicherheitsverträge:** Tests sichern `agent_path` für flache und verschachtelte Episoden, Kategorie- und Serienroot-Grenzen, Symlink-Ausbrüche, vorhandene `season.nfo` sowie den Same-Count-Zielaustausch mit HTTP 409 und Schreibabbruch ab.
- **Produktionsnaher NFO-Agent-Lifecycle:** Die Frontend-Tests verwenden die echten Event-Bindings und den produktiven `/api/queue`-Pollingweg für erfolgreiche, fehlgeschlagene, abgebrochene und nicht mehr vorhandene Jobs.
- **Idempotente Event-Bindings:** Wiederholtes Binden erzeugt keine doppelten NFO-Agent- oder Health-Aktionslistener; Sonderzeichenpfade werden über die echte Event-Delegation korrekt an den NFO-Agenten übergeben.
- **Automatisierte Verifikation:** `python3 -m pytest tests/` mit 430 bestandenen Tests und `npm run test:frontend` mit 74 bestandenen Tests.
- **Projektwissen:** Der lokale Graphify-Wissensgraph und seine Wiki-/HTML-Exporte wurden nach Code und Dokumentation neu erzeugt.
- **OrbStack-Sicherheitscheck:** Der bestehende Testcontainer meldet `health=ok` und `runtime=docker`; seine Bind-Mounts zeigen ausschließlich auf `.runtime-test/media-run` und `.runtime-test/config` des bisherigen Fix-Worktrees. Ein aktueller Branch-Build und die visuelle Abnahme bleiben deshalb getrennte nächste Schritte.

## Stand am 14.07.2026 (Phase 2.5c-3 - FSK-Workflow-Integration Fix)

# Aktueller Stand

> Status: **FSK-Workflow-Integration (Phase 2.5c-1) fertig implementiert. Bereit für Code-Review & Tests.**

---

## Aktuelle Aufgabe

### Phase 2.5c-1 – FSK-Batch-Modal State-Machine & Sync
Alle 5 besprochenen Findings aus der Planungsphase wurden im Code erfolgreich behoben:
- [x] **Medientyp-Bootstrap:** Modal erhält `media_kind` aus strukturierter Übergabe. Fehlende Hierarchie bei gemischter Selektion wird berücksichtigt.
- [x] **Zustandsmodell (4-Phasen):** Modal verweilt im Zustand `Applying` und wechselt auf `Completed`, `Partial` oder `Failed`.
- [x] **Problem-Badges:** Issue-Keys werden in `renderHealthStatus` ausgelesen und als Badges angezeigt.
- [x] **NFO-Agent-Rückkehr:** FSK-Modal wird versteckt, wenn der NFO-Agent öffnet, und springt nach Erfolg des Agenten wieder auf inkl. Neu-Scan.
- [x] **Exakte Zielmengenprüfung:** Beim Apply wird ein strikter Realpath-Vergleich zwischen Preview- und Apply-Targets (inklusive Lückenüberprüfung) durchgeführt (HTTP 409).

## Erledigte Aufgaben

- [x] Code-Revision gemäß Review (Phase 2.5c-2).
- [x] Commit der Änderungen im Branch `fix/fsk-workflow-review`.
- [x] Graphify Knowledge-Graph aktualisiert.

## Nächster Schritt / Übergabe

- [ ] Alex: Branch `fix/fsk-workflow-review` lokal testen.
- [ ] Alex: Merge nach `main` (sofern alle Tests und UI-Flows passen).


## Stand am 14.07.2026 (Phase 2.5c-2 – Schritt 2: Serienorientierte Health-Ansicht & Gruppenaktionen abgeschlossen)

- **Phase 2.5c-2 (Schritt 2) – Serienorientierte Health-Ansicht & Gruppenaktionen (Branch `fix/fsk-workflow-review`):**
  * **Medienstruktur-Aggregation:** Health-Scan sammelt Filme, Serien, Staffeln und Episoden mitsamt Pfaden, FSK-Status und zugehörigen Issue-Keys.
  * **Cache-Upgrade:** `SCAN_VERSION` auf 3 angehoben, um alte v2-Zählerzustände im Cache zu entwerten und durch die neue medienorientierte `media_metadata` Struktur zu ersetzen.
  * **API-Erweiterung:** `/nas/health-status` liefert die aggregierte `media_structure` für Serien und Filme.
  * **UI-Integration:** Neue Ansicht `"Medienorientiert"` im Health-Anzeigemodus ermöglicht das Ausklappen von Serien -> Staffeln -> betroffenen Episoden.
  * **Serien- & Staffel-Gruppenaktionen:** Direktes Aufrufen des FSK-Batch-Modals für komplette Serien oder Staffeln mit Dropdown-Vorauswahl im Dashboard.
  * **Präzise Zähler- & Aktions-Trennung (Revision 2.2):** Die Prädikate `isEpAffectedGeneral` und `isEpFskActionable` trennen allgemeine Medienanzeige (`nfo_missing`, `unreadable`) von tatsächlichen FSK-Schreibaktionen.
  * **Konditionales Ausblenden:** FSK-Schreib-Buttons werden für unbeschreibbare Medien konsequent unterdrückt. Fehlt die `tvshow.nfo`, zählt die Serie selbst nicht als FSK-aktionsfähig. Sind jedoch mindestens zwei Episoden FSK-aktionsfähig, wird weiterhin eine Serien-Gruppenaktion angeboten, während an der Serie zusätzlich der `NFO Agent` verfügbar bleibt.
  * **Tests:** Python-Tests in `test_fsk_health.py` und erweiterte Node.js Frontend-DOM-Tests (69/69), welche insbesondere pfadbezogene DOM-Assertions für Mischfälle und FSK-Ausblendungen abdecken, erfolgreich umgesetzt.

## Stand am 13.07.2026 (Phase 2.5c-2 – Schritt 1: FSK Altersfreigaben Stapelverarbeitung & Integrität abgeschlossen)

- **Phase 2.5c-2 (Schritt 1) – FSK Altersfreigaben Stapelverarbeitung & Integrität (Branch `feature/fsk-workflow-overhaul`):**
  * **Binäres NFO-Schreiben:** Bytegenaue, binäre Ersetzung des Werts im `<mpaa>` Tag unter Erhalt von Dateirechten, Umlauten (BOMs), Attributen und Kommentaren.
  * **Race-Condition & mtime-Absicherung:** Präzise String-Repräsentation von `mtime_ns` im JSON-Plan zur Vermeidung von JavaScript-Rundungsfehlern. Toleranz gegenüber reinen mtime-Änderungen auf dem Server (keine Fehlalarme).
  * **Fehlende NFOs:** Korrekte Repräsentation als `status: "skipped_missing"` und `"fingerprint": null` im Clientplan. HTTP 409 bei Widersprüchen.
  * **Zentraler Media-Kind-Resolver:** Bestimmung von `media_kind` ausschließlich über den Resolver-Kategoriekontext (`walk_nas_categories`).
  * **UI & Barrierefreiheit:** Umstellung des FSK-Batch-Modals auf ein `<select>` Dropdown für den FSK-Zielwert. Inline-Fehlerpanel statt nativer `alert`/`confirm` Dialoge. Dynamische Beschriftung des Apply-Buttons ("X NFOs auf FSK Y ändern"). Monospace-Schrift für Pfadangaben.
  * **Testabdeckung:** Erstellung dedizierter Binärtests in `test_nfo_write.py` und API-Integrations- sowie UI-Tests in `test_fsk_batch.py` und `fsk_batch_dom.test.js`.

## Stand am 13.07.2026 (Phase 2.5c-1 – Hierarchische FSK-Zuweisung abgeschlossen)

- **Phase 2.5c-1 – Hierarchische FSK-Zuweisung (Plan v8):**
  * Der Review-Plan v8 wurde vollständig implementiert. Alle Backend- und Frontend-Tests laufen zu 100% grün, einschließlich der neuen Sidecar-Video-Validierungen und Partial-Status-Logik.
  * Backend-Zulässigkeitsprüfung `is_valid_media_nfo` mit strenger Video-Sidecar-Kopplung (für `/nas/health-fix` und `/nas/fsk-batch/apply`).
  * Unterstützung von `partial`/`failed` Statuswerten im `apply`-Endpunkt, inklusive Mapping von Exceptions auf feingranulare Status-Ergebnisse.
  * Update der Frontend-App-Logik (`app.js`) für das FSK-Batch-Modal, um dynamisch Hierarchie-Pfade (`series_path`, `season_path`) je nach Nutzer-Scope zu nutzen.
  * Frontend HTML-Render in `app.js` mit `data-scope-kind`, `data-series-path` und `data-season-path` Attributen ausgestattet.
  * Test-Suite für Plan v8 Lücken ergänzt (`test_fsk_batch.py`, `test_fsk_health.py`, `test_health_scan_cache.py`) und Dummy-Video-Dateien für Sidecar-Checks hinzugefügt.

## Stand am 12.07.2026 (FSK Batch: Hierarchische Zuweisung)

- **Hierarchische FSK-Batch-Zuweisung (Branch `feature/fsk-hierarchical-assignment`):**
  * **Scope-Auswahl:** Möglichkeit zur Zuweisung auf Datei- (`single`), Staffel- (`season`) oder Serien-Ebene (`series`).
  * **Preview & Payload:** Bei Änderung des Scopes wird die Preview mit den passenden Pfaden asynchron aktualisiert.
  * **Validierung:** `nas_api.py` führt strenge Security-Checks durch, sodass Ausbrüche aus dem NAS-Root per Symlink (inklusive temporären Dirs) konsequent geblockt werden.
  * **Unit Tests:** Vollständige DOM-Tests isolieren den FSK-Controller erfolgreich von globalem App-Status. Backend-Tests decken die hierarchische Pfadauflösung inklusive Scope-Prüfung ab.
  * **Test Isolation & Whitespace:** Der gesamte Branch ist whitespace-bereinigt. Der VM-Harness für Frontend-Tests läuft nun ohne irrelevante Timers und Fehler-Logs durch.

## Stand am 11.07.2026 (NFO-Agent: Kanonische Pfadauflösung & Health-Scan Ladeanzeige)

- **UX-Refinements & Ladeanzeige (Branch `feature/nfo-agent-refinements`):**
  * **Kanonischer tvshow.nfo Pfad:** Sowohl `/scan-project` als auch der NFO-Agent-Worker nutzen nun `resolve_series_root` für eine einheitliche Pfadauflösung (Elternordner bei Staffeln/Specials).
  * **Sicherheits-Härtung:** NFO-Agent validiert nun sowohl `current_dir` als auch den kanonischen Serienhauptordner `show_dir` per `is_path_allowed`.
  * **Optionales tvshow.nfo Schreiben:** Das Modal bietet für Serien eine optionale Kopfzeile (`⚙️ Verarbeiten` vs. `⏭️ Überspringen`) mit Statusbadges (`[Keine NFO]`, `[NFO fehlerhaft]`, `[NFO unvollständig]`, `[NFO vorhanden]`). Bei "skip" wird `write_show_nfo: false` übermittelt.
  * **Health-Scan Ladeanzeige:** Die Health-Tabelle fängt den Ladezustand nach Klick auf "Fertig" durch einen Lade-Spinner und einen Begleittext ("Health-Scan wird aktualisiert ...") ab. Suchparameter und KPIs werden ausgeblendet, bis der Scan abgeschlossen ist.
  * **Integrationstests & Review-Fixes:** Integrationstests decken die Cache-Invalidierung, das Patchen des DATA_DIR, den echten Workerpfad mit `write_show_nfo: false` sowie die API-Zustandsmatrix über den `/scan-project`-Response ab. Frontend-Tests verifizieren den sequenziellen `running -> warning` Übergang (Ausblenden des Spinners und Aktualisierung der Dashboard-Metadaten) und alle vier Statusbadges samt Payload-Semantik im NFO-Agenten. Alle 390 Backend- und 50 Frontend-Tests sind vollständig grün und Whitespace-bereinigt (`git diff --check` bestanden).

## Stand am 11.07.2026 (NFO-Agent: UX-Polish, Staffel-Ermittlung & Cache-Invalidierung)

- **UX-Polish & Polish (Branches `fix/nfo-agent-modal-ux` & `fix/nfo-agent-polish`):**
  * **Modal-Verhalten & done-Button:** Modal-Höhe ist nun auf `90vh` begrenzt; das Metadaten-Formular scrollt flexibel, damit die Buttons im Footer sichtbar bleiben. Ein neuer done-Button (kein Auto-Close) schließt das Modal erst auf Benutzer-Klick und triggert den Health-Scan neu.
  * **Polling über `/api/queue`:** Pollt nun den Fortschritt und Status direkt über die Queue-API `/api/queue` (Pipeline-Schritt `metadata`), was den nicht-existierenden `/api/jobs/logs`-Endpunkt vollständig ersetzt.
  * **NFO-Agent pro Einzelbefund:** Der obere Batch-Button wurde entfernt. Der NFO-Agent wird nun exklusiv per-Befund über einen `NFO Agent`-Button aufgerufen, da jedes Verzeichnis ein individuelles Mapping benötigt.
  * **Staffel-Ermittlung:** Erkennt die Staffelnummer automatisch aus dem Ordnernamen (z.B. `Staffel 2` oder `S03`) und befüllt das Staffel-Feld zur passenden Filterung der Episodenauswahl.
  * **Cache-Invalidierung:** Löscht bei erfolgreichem NFO-Agent-Lauf den Cache-Eintrag des Verzeichnisses und dessen Elternverzeichnisses (`HealthCacheManager.invalidate_entry`), damit korrigierte Befunde sofort nach dem Scan aus der Health-Liste verschwinden.
  * **Vergrößertes Log-Fenster:** Log-Fenster auf `200px` vergrößert.
  * **Unit-Tests:** Zusätzlicher Unit-Test `test_health_cache_invalidate_entry` hinzugefügt.

## Stand am 11.07.2026 (NFO-Agent: Auto-Suche & Metadaten-Vorbefüllung)

- **Auto-Suche & Metadaten-Vorbefüllung (Branch `feature/nfo-agent-autosearch`):**
  * **Backend-Namensbereinigung:** `get_clean_search_name` entfernt Provider-Tags (z.B. `[TVDB]`) und Staffel-Suffixe aus dem Pfadnamen, behält aber Jahreszahlen zur präzisen Suche.
  * **Parent-NFO-Lookup:** Sucht bei Staffelordnern im übergeordneten Elternverzeichnis nach `tvshow.nfo` und parst diese. Setzt `metadata_source = "nfo"`.
  * **Profil-Fallback:** Liefert Provider & ID aus dem Serienprofil, falls keine NFO existiert. Setzt `metadata_source = "profile"`.
  * **Frontend-Erweiterungen:**
    * Führt beim Öffnen des Modals automatisch die Metadaten-Suche mit dem bereinigten Namen aus.
    * Zeigt die Suchergebnisse in einer klickbaren Trefferliste an.
    * Kennzeichnet Treffer mit Badges (`aus tvshow.nfo`, `aus Serienprofil`, `Profil abweichend`) basierend auf normalisiertem Provider-Vergleich.
    * ID-Eingabe und Provider-Auswahl sind standardmäßig in eine einklappbare `<details>`-Box ausgelagert.
    * Blendet Fehlermeldungs-Alerts aus und öffnet stattdessen das Detail-Panel bei leeren oder fehlgeschlagenen Suchen.
  * **Videofilter-Bugfix:** Filtert in der Dateiliste Nicht-Video-Dateien (z.B. JPGs) zuverlässig heraus.
  * **Unit-Tests:** Zwei neue Backend-Tests in `test_utils.py` decken Parent-NFO-Lookup und Profil-Fallback ab.

## Stand am 11.07.2026 (NFO-Agent: Modal-Suche repariert & vorbefüllt)

- **Modal-Suche reparieren & vorbefüllen (Branch `fix/nfo-agent-modal-search`):**
  * **Endpunkte korrigiert:** Die Suche nutzt nun den existierenden Endpunkt `/api/search?type=tv|movie&q=...`. Details werden korrekt über `/api/metadata/fetch?media_type=tv|movie` abgerufen.
  * **Film-Provider-Mapping:** Mappt den Such-Provider `tmdb` bei Filmen automatisch auf `tmdb_movie`, damit die Dropdowns und das Backend die API-Anfragen korrekt zuordnen können.
  * **Profil-Vorbefüllung:** Nach dem Scan wird bei Serien optional ein Abruf über `/api/profile?show_name=...` gestartet. Fehlen Werte (ID, Name, Provider) in der NFO, befüllt das Profil diese Lücken automatisch (NFO hat Vorrang).
  * **Dynamic Episode Fetching:** Wählt der Benutzer ein Episoden-Mapping aus (oder ist eines vorgeladen), werden dessen Episoden-Metadaten (Titel, Plot) on-demand via `/api/metadata/fetch?media_type=episode...` geladen, um Daten-Redundanz zu vermeiden.
  * **UI-Klarstellungen:**
    * ID-Eingabefeld-Label zu „Show / Movie ID (wird autom. gefüllt)“ geändert.
    * Master-Überschreibschutz-Balken präzisiert zu: „Fertige NFOs werden übersprungen. Zum Reparieren leerer/kaputter NFOs ‚überschreiben‘ anhaken.“
  * **Verifikation:** Sämtliche backend-seitigen und frontend-seitigen Tests (`npm run test:frontend`) laufen fehlerfrei durch.

## Stand am 11.07.2026 (NFO-Agent: Dedizierter Metadaten-Job & Modal-Umbau - Ansatz A)


- **NFO Agent: Dedizierter Metadaten-Job & Modal-Umbau (Ansatz A - Revidiert):**
  - **Exklusiver Metadaten-Job:** Der NFO-Agent läuft jetzt über einen eigenen Job-Typ `tool_nfo_agent` mit einer minimalen, einstufigen Pipeline (`metadata`), wodurch Konvertierungen, Dateiverschiebungen oder Löschungen strukturell ausgeschlossen sind.
  - **Sicherheits-Pfad-Gate:** Der NFO-Agent prüft den Zielpfad aktiv über `is_path_allowed`, bevor Metadaten geschrieben werden, und bricht bei unerlaubten Pfaden sofort ab.
  - **Eigenes Modal-Interface:** `#modal-nfo-agent` in `index.html` bietet eine vollständige, gethemte Such- und Review-Maske inklusive Episoden-Mappings, Titel-/Plot-Overrides für Shows/Movies/Episoden und einem integrierten Live-Logstream.
  - **Datenschutz & Härtung:**
    - Show- und Movie-Overrides werden nur übermittelt, wenn der Benutzer sie in der UI wirklich geändert hat, was das ungewollte Überschreiben intakter Serien-/Film-NFOs verhindert.
    - Die Episodennummern und Staffeln werden im Backend zu Integern gecastet, was Formatierungs-Crashes bei unvorhergesehenen Zeichenketten im Mapping-Zweig strukturell ausschließt.
  - **Auto-Close & Scan-Refresh:** Nach erfolgreichem Abschluss schließt sich das Modal nach 1,5 Sekunden selbst und stößt im Hintergrund einen neuen Bibliotheks-Scan (`startHealthScan`) an.
  - **Tests & Verifikation:** 3 neue Tests in `tests/test_utils.py` decken Serien- und Filmverarbeitung sowie den unzulässigen Pfad-Abbruch ab. Die gesamte Testsuite läuft fehlerfrei durch.

## Stand am 11.07.2026 (UI-Integration des NFO-Agenten & NFO-Vollständigkeitsscan)

- **UI-Integration des NFO-Agenten (Branch: `feature/nfo-backfill-review`):**
  - **Review-UI Integration:** Klicks auf „NFO Agent“ (Dashboard oder Health-Befunde) öffnen nun direkt das interaktive Review- und Editier-Interface (Inbox-Workflow) für den jeweiligen NAS-Ordner, anstatt die stumme Terminal-Konsole zu öffnen.
  - **Sichere Überschreib-Politik:** Für jede Videodatei wird der NFO-Zustand (`exists` und `complete`) ermittelt. Im Review-Interface werden bereits vollständige NFOs standardmäßig im Mappings-Dropdown auf **„skip“** gesetzt, um handgepflegte Daten vor ungewolltem Überschreiben zu schützen. Nur unvollständige oder fehlende NFOs werden standardmäßig zur Generierung vorausgewählt.
  - **Option A (Konsistenter Haupt-NFO-Schutz):** Im Backend (`processor.py`) werden `tvshow.nfo` und Film-NFOs nur dann überschrieben, wenn sie unvollständig/beschädigt sind, fehlen oder der Benutzer explizit manuelle Metadaten-Änderungen in der UI vorgenommen hat (was das Vorhandensein von Overrides bewirkt).
  - **Auto-Load & Provider-Fallbacks:** Das `/api/scan-project` parst bei absoluten Pfaden (NAS-Ordnern) die vorhandene `tvshow.nfo` oder Film-NFO, liest Provider und IDs aus (inklusive Fallbacks auf `<tmdbid>` für Filme) und lädt diese Metadaten und die Episoden-Mappings vollautomatisch im Review-UI.
  - **Health-Scan Erweiterung:** Der Health-Scan prüft existierende NFOs auf Vollständigkeit (Severity `critical` bei fehlendem Titel/Plot, Severity `warning` bei fehlendem Produktionsjahr/Ausstrahlungsdatum) und meldet `incomplete_nfo` mit passenden Labels und Zähler-Einhängung im Dashboard.
  - **Unit-Tests:** 4 neue Testmethoden in `tests/test_utils.py` decken die absolute Pfad-Prüfung, die Sicherheits-Validierung, den Vollständigkeitsscan, das Überschreib-Schutzmodell und das Overwrite-Bypass-Verhalten im NFO-Generator ab. Cache-Tests wurden an die neue Vollständigkeitsprüfung angepasst.
  - **Testsuite:** Alle 379 Tests laufen erfolgreich durch.

## Stand am 10.07.2026 (NFO Overwrite Bug behoben)

- **Behebung des NFO-Overwrite-Bugs bei leeren Overrides (Branch: `fix/nfo-overwrite-empty`):**
  - **Backend-Härtung:** In `gui/mw_metadata.py` an allen 16 Stellen (Filme, Serien und Episoden) die Prüfung von `"field" in nfo_overrides` auf `nfo_overrides.get("field")` umgestellt. Dadurch werden leere Overrides ignoriert.
  - **Frontend-Payload-Hygiene:** In `gui/static/app.js` leere Override-Felder vor dem Absenden aus dem Payload entfernt, um unnötige Datenübertragungen zu vermeiden.
  - **Unit-Test:** Neuen Regressionstest `test_tvdb_episode_nfo_empty_overrides` hinzugefügt. Dieser prüft, dass leere Overrides die online abgerufenen Metadaten nicht überschreiben, und verwendet ein temporäres Verzeichnis (via `tempfile.gettempdir` Patch) zur Vermeidung von Cache-Seiteneffekten.
  - **Testsuite:** Die gesamte Testsuite mit 375 Tests läuft erfolgreich durch.

## Stand am 09.07.2026 (Nachkorrektur – TVDB-Suchlimit erhöht)

- **TVDB-Suchlimit erhöht (Branch: `fix/tvdb-search-limit`):**
  - **Anhebung des Limits:** In `gui/mw_metadata.py` (`search_tvdb`) das API-Schnittlimit von `[:8]` auf `[:25]` erhöht. Damit kommen auch tiefer platzierte offizielle Suchtreffer wie "Dragon Ball (1986)" an Position 11 durch und werden nicht vor dem Relevanz-Ranking verworfen.
  - **Spezifischer Relevanz-Test:** Ein neuer Test `test_tvdb_search_relevance` in `tests/test_utils.py` mockt eine TVDB-Suche mit 20 Ergebnissen, bei der der beste Treffer erst auf Platz 11 (hinter 10 Fan-Projekten) liegt. Der Test stellt sicher, dass das Limit die Serie durchlässt und das Relevanz-Ranking (`calculate_match_score`) sie korrekt an Index 0 platziert.
  - **Deduplizierung & API-Sauberkeit:** Der Test mockt die anderen Provider (TMDb, TVmaze) als leer, um eventuelle Nebeneffekte auszuschließen.
  - **Testsuite:** Alle 48 Tests in `test_utils.py` sowie die 21 Endpunkt-Tests laufen erfolgreich durch.

## Stand am 09.07.2026 (Nachkorrektur – NAS-Quarantäne geleert & Cleaner-Fix)

- **NAS-Quarantäne und Trash-Cleaner-Verbesserungen:**
  - **NAS-Quarantäne geleert:** 115 Einträge / 19 GB entfernt. SMB-Verzeichnis-Cache-Fehler behoben; restliche Lock-Dateien per POSIX-`unlink` direkt auf dem NAS gelöscht.
  - **Cleaner-Fix (PR #109, `fbe1507`):** `_empty_trash_core` fasst nun flach/fremd abgelegte Einträge nach `retention_days` an, gesichert durch denselben `_secure_delete_entry`-Guard. 4 neue Tests hinzugefügt.
  - **Doku-Fix (PR #110, `352ed9a`):** NAS-Bereitstellungspfad in CLAUDE.md/AGENTS.md auf `docker compose pull && up -d` korrigiert.

## Stand am 09.07.2026 (Nachkorrektur – Konvertierungsfortschritt sichtbar machen)

- **Queue-UX während H.265-Konvertierungen (Branch: fix/conversion-progress-visibility):**
  - **Sofort sichtbarer Konvertierungsstart:** `process_worker` setzt vor dem eigentlichen FFMPEG-Aufruf nun den Job-Hauptstatus und den Pipeline-Step `convert` auf `Konvertierung gestartet: ...`. Dadurch bleibt die Queue-Karte nicht mehr bei „Verarbeitung gestartet...“ stehen, wenn FFMPEG noch keine Prozentwerte ausgegeben hat.
  - **Fortlaufende Step-Meldungen:** FFMPEG-Progress-Callbacks spiegeln ihre Meldungen zusätzlich in `pipeline.convert.message` und `job.message`, damit die UI den aktuellen Konvertierungszustand ohne Entwicklerkonsole anzeigen kann.
  - **NAS-Transferabschluss korrigiert:** Erfolgreiche NAS-Transfers setzen ihren Pipeline-Step nun explizit auf `done` und `100`, damit die Kachel nach abgeschlossenem Kopieren nicht weiter blau als laufend angezeigt wird.
  - **pCloud-/Cloud-Start sichtbar:** Cloud-Uploads setzen ihren Pipeline-Step bereits vor dem ersten Progress-Callback auf `running` mit Startmeldung. Dadurch sieht der Nutzer nach dem NAS-Transfer sofort, dass Speicherziel 2 begonnen hat.
  - **Frontend-Anzeige:** `renderQueue` rendert Step-spezifische Pipeline-Messages direkt in den Prozesskacheln. Lange Meldungen werden umbrochen und als Tooltip vollständig verfügbar gemacht.
  - **Review-Nacharbeit:** Der Queue-Renderer nutzt nun den vorhandenen Helper `escapeHTML` statt des nicht existierenden `escapeHtml`. Der Convert-Start setzt bei Mehrdatei-Jobs den bestehenden Durchschnittsfortschritt statt eines harten `0%`-Resets.
  - **Regressionstests:** `test_movie_processing_with_convert` prüft den kritischen Zwischenzustand vor dem ersten FFMPEG-Progress. Zusätzlich prüfen `test_movie_nas_transfer_marks_pipeline_step_done` und `test_movie_cloud_transfer_is_visible_before_progress_callback` den NAS-Abschluss und den sichtbaren pCloud-Start. `renderQueue - pipeline step message uses existing HTML escaping helper` sichert den Frontend-Renderpfad für Step-Messages ab. `test_average_progress_preserves_multi_file_convert_progress` prüft den Mehrdatei-Fortschritt. `test_show_nas_transfer_marks_pipeline_step_done` deckt zusätzlich den serien-spezifischen NAS-Branch (Einzeldatei- plus Begleitdatei-Kopie) ab.
  - **Qualitätssicherung:** `python3 -m pytest` (369 passed), `npm run test:frontend` (47 passed), `git diff --check` (sauber) und `./scripts/refresh_graphify.sh` erfolgreich ausgeführt.

## Stand am 09.07.2026 (Phase 2.6b – Konvertierungsqualität / Archivqualität)

- **Qualitätsverbesserung & Archivmodus (Branch: feature/conversion-quality-polish):**
  - **VAAPI QP 18 für Archivqualität:** Die maximale VAAPI-Encodingqualität (`quality=100`) wurde von QP 22 auf QP 18 angehoben, um einen echten visuell verlustfreien Archivierungs-Modus bereitzustellen.
  - **Single Source of Truth:** Extraktion der kompletten Encoder- und Qualitätsmapping-Entscheidungslogik in eine gemeinsame Funktion `resolve_encoder_and_quality(quality, force_software=False) -> dict` in `gui/core/media.py`. Sowohl `build_hevc_ffmpeg_cmd` als auch die API nutzen diese gemeinsame Funktion, wodurch jeglicher Drift zwischen UI und FFMPEG-Befehlsausführung verhindert wird.
  - **Backend API:** Neuer GET-Endpunkt `/api/system/quality-info` liefert die encoder-spezifische Parametrisierung (`{encoder, param_name, param_value}`) für einen Qualitätswert zurück.
  - **Frontend-UX & Dynamischer Nomenklatur-Hinweis:** Vorkommen von "CRF" im UI-Code (auch in den Conversion Intelligence Texten) wurden durch den verständlichen Begriff "Qualität" oder "Qualitätswert" ersetzt. Im Frontend zeigt die Funktion `updateQualityIndicator` nun asynchron und Slider-spezifisch den tatsächlichen Encoder-Parameter an (z. B. `60 (libx265 CRF 26)` bzw. `100 (hevc_vaapi QP 18)`).
  - **Asynchroner Race-Guard & Cache:** Schutz vor Race-Conditions bei schnellen Bewegungen der Slider über `lastQualityRequestIds[valElId]`. Ein clientseitiger Cache (`qualityInfoCache`) schont die API.
  - **Testsuite:** Alle 10 Tests in `test_docker_conversion.py` (inkl. neuem `test_resolve_encoder_and_quality`) und der plattformunabhängig gemockte API-Test in `test_endpoints.py` laufen erfolgreich durch (365/365 Backend-Tests bestanden, 46/46 Frontend-Tests bestanden).
  - **Roadmap-Updates:** Die Tickets #44 (VAAPI QP 18) und #49 (Bibliotheks-Scan ohne Medienserver) in `AFTER_RELEASE_ROADMAP.md` wurden als `erledigt` markiert.

## Stand am 09.07.2026 (Phase 2.6a – Bibliotheksscan-Konfiguration und verständliche Preflight-Hinweise glätten)

- **Scan-Robustheit bei fehlendem Medienserver (Branch: feature/library-scan-config-polish):**
  - **Optionaler Medienserver:** Der Bibliotheksscan bricht bei fehlendem Medienserver nicht mehr ab. Medienserver-spezifische Artwork-Prüfungen (Poster, Fanart, Logo, Banner, Staffelposter) werden übersprungen, während die datei- und ordnerbasierten Strukturchecks weiterhin laufen.
  - **Cache-Härtung:** `calculate_hybrid_state` in `health_cache.py` fängt `validator=None` sauber ab. Bei Serien ohne Validator wird über einen rekursiven `os.walk` eine Erfassung aller Videodateien (`mtime` und `size`, als Listen serialisiert für JSON-Stabilität bei Roundtrips) und NFO-Dateien (`mtime`) durchgeführt.
  - **Backend API:** `/api/nas/health-scan` bricht nicht mehr mit HTTP 400 ab, wenn kein Medienserver konfiguriert ist, sondern startet den Scan regulär.
  - **Warnbanner im Frontend:** Wenn die Medienserver-Prüfung übersprungen wurde, zeigt das Dashboard über den Befunden ein gelbes Info-Warnbanner an mit direktem Navigationslink zu den Einstellungen (`Einstellungen > Speicher & Sync` bzw. `#nav-settings-dashboard`), um den Benutzer anzuleiten.
  - **Symmetrische Scanstart-Sperre:** Das Frontend filtert in `loadHealthCategories` unvollständige Sync-Kategorien (ohne NAS-Pfad `nas_sub`) aus. Gibt es 0 gültige Kategorien, wird ein Empty State mit Link zu den Einstellungen gerendert, der Button „Bibliothek prüfen“ wird deaktiviert und mit einem erklärenden Tooltip versehen. `resetHealthScanButton` prüft ebenfalls das Vorhandensein, damit Polling-Events den gesperrten Button nicht fälschlicherweise wieder aktivieren.
  - **Frontend-Sicherheitscheck:** In `startHealthScan` bricht das Frontend sofort ab, wenn keine Kategorien selektiert oder vorhanden sind, um Fehlstarts zu verhindern.
  - **Testsuite:** Aktualisierung des API-Tests in `test_health_scan_cache.py` und Ergänzung zweier neuer Unittests in `test_artwork_validation.py` für Filme und Serien ohne Validator. Im Serientest wird `os.path.isdir` gemockt, um den echten Pfad zu `_check_season` und deren validatorfreie Ausführung zu verifizieren.
  - **Code-Qualität:** Whitespace-Fehler auf Commit-Ebene vollständig bereinigt.

## Stand am 02.07.2026 (Phase 2.5d – UI/Preview-Fixes für Ordnerstrukturen)

- **UI/Preview-Fixes (Branch: feature/nas-structure-fix):**
  - **Vorschau-Modal im Vordergrund:** Das Vorschau-Modal (`#modal-structure-preview`) hat einen höheren z-index (`1000005`) erhalten, wodurch es sich nun zuverlässig vor dem Batch-Modal öffnet und bedienbar bleibt.
  - **Vorher/Nachher-Baum bei nested_duplicate korrigiert:** Der linke Baum ("Aktuelle Ordnerstruktur") zeigt nun die doppelte Ordnerebene (`Dracula.../Dracula.../...`) an, und der rechte Baum ("Geplanter Zielzustand") visualisiert die flache, bereinigte Struktur direkt unter dem Filmordner. Beide Bäume sind nun konsistent mit dem äußeren Ordner (`outer_name`) als Root präfixiert.
  - **Mehrfach verschachtelte identische Ordner:** Ketten wie `Film/Film/Film/datei.mkv` werden nun bis zum tiefsten Inhaltsordner erkannt. Dadurch entstehen keine falschen Zielkonflikte mehr, wenn der nächste gleichnamige Unterordner nur Teil der redundanten Verschachtelung ist. Nach dem Hochziehen werden leere Rest-Unterordner sicher in die Quarantäne verschoben.
  - **NAS-Pfad-UX-Fix:** Die geführte NAS-Eingabe löscht vorhandene IP-Adressen nicht mehr, wenn ein lokaler Mac-Pfad wie `/Volumes/Kino` gewählt wird. Dadurch bleibt automatisches Verbinden möglich, auch wenn zusätzlich ein lokaler Mount-Pfad gepflegt wird.
  - **Race-Condition im Vorschau-Dialog behoben:** Der aktive Vorschau-Pfad wird nun direkt am Modal gespeichert. Dadurch bleibt der Button „Struktur auflösen“ auch dann funktionsfähig, wenn währenddessen der Health-Status neu gerendert wird. Während der Batch-Prüfung bleiben Vorschauaktionen gesperrt, bis die Prüfung abgeschlossen ist.
  - **Einzelaktion getrennt:** In den Struktur-Befunden öffnet „Vorschau“ weiterhin die Vorher/Nachher-Ansicht. „Auflösen“ startet nun direkt nach einer Sicherheitsbestätigung; diese Bestätigung kann über „zukünftig nicht mehr anzeigen“ lokal deaktiviert werden.
  - **Batch-Abschluss repariert:** Nach erfolgreicher Sammelauflösung wird der Abschlussbutton zu einem echten „Fertig“-Button, der das Batch-Modal zuverlässig schließt.
  - **Filmstruktur-Widget geglättet:** Der separate Vorschau-Button im Widget „Filmstruktur aufräumen“ wurde entfernt, weil die Analyse über den zentralen Bibliotheksscan läuft. Der leere Zustand lautet nun neutral „Keine Auffälligkeiten gefunden.“ statt „Noch keine Vorschau erstellt.“ oder „Alles sauber – nichts zu normalisieren.“.
  - **Cache-Bust für Frontend-Fix:** `app.js` wurde auf `v=80` angehoben, damit Browser und Desktop-Runtime nach den Struktur-Fix-Nacharbeiten nicht versehentlich alte Event-Handler oder alte Vorschau-Logik weiterverwenden.
  - **Qualitätssicherung:** Unit-Tests in `test_nas_structure_fix.py` angepasst, und alle Backend- und Frontend-Tests erfolgreich verifiziert.

---

## Stand am 01.07.2026 (Phase 2.5d – Verschachtelte/doppelte Ordnerstrukturen & Sammelordner auflösen)

- **Ordnerstruktur auflösen (Branch: feature/nas-structure-fix):**
  - **Sicherheits- & Validierungslogik im Backend:** Die API prüft streng und unterscheidet präzise zwischen `nested_duplicate` und `genre_container`. Wenn ein Ordner kein Jahr im Namen hat, keine Videodateien direkt enthält und mindestens einen Unterordner mit Videos besitzt, wird er als `genre_container` eingestuft. Er wird in Serienkategorien blockiert. Vorhandene Dateien/Ordner am Zielort werden als Konflikte markiert.
  - **Plausibilitätsprüfung für Unterordner:** Verhindert das Mitverschieben von nicht-medialen Nebenordnern (wie `Extras/`) durch eine strenge Prüfung: Jeder Unterordner muss entweder ein Video enthalten oder wie ein Filmordner aufgebaut sein (eine Jahreszahl im Namen tragen). Andernfalls wird ein Konflikt ausgegeben.
  - **Umfassendes Items-to-move-Konzept:** Unterstützt sowohl das Flachklopfen einzelner Dateien/Unterordner (für `nested_duplicate`) als auch das Verschieben ganzer Filmordner eine Ebene nach oben (für `genre_container`).
  - **UX- & Begrifflichkeiten-Glättung:** Vermeidung von „sicheren Strukturproblemen“ in der UI. Nutzung von klareren Bezeichnungen:
    - „Alle sicheren Strukturprobleme prüfen“ &rarr; „Ordnerstrukturen vorbereiten“
    - „Sichere auflösen“ &rarr; „Geprüfte Ordnerstrukturen auflösen“
    - Status „Sicher“ &rarr; „Kann automatisch aufgelöst werden“
    - Status „Konflikt“ &rarr; „Manuelle Prüfung nötig“
  - **Vorschau-Modal (`modal-structure-preview`):** Zeigt detaillierte, typspezifische Vorher/Nachher-Ansichten mit angepassten Titeln und neutralem Wording („Filmordner verschieben“ vs. „Datei verschieben“).
  - **Batch-Prüfer & Abarbeitung (`modal-structure-batch`):** Prüft alle Befunde im Hintergrund. Wenn keine Befunde automatisch auflösbar sind, wird eine rote, klare Fehlermeldung gerendert, anstatt stillschweigend nichts zu tun.
  - **Stabile Klickverkabelung für Strukturaktionen:** Die neuen Buttons „Vorschau“, „Auflösen“ und „Ordnerstrukturen vorbereiten“ nutzen nun Event-Delegation auf dem Bibliotheksbereich, damit sie nach Polling/Re-Render weiterhin reagieren. Die Struktur-Modals werden nun korrekt mit `active` geöffnet und mit `hidden` geschlossen; vorher kamen die Preview-Requests zwar im Backend an, aber das Modal blieb unsichtbar. `app.js` wurde auf `v=76` gebumpt, damit der Browser den Fix sicher neu lädt.
  - **Quarantäne statt Löschen:** Leere Sammelordner und verschachtelte Unterordner werden sicher über `trash.send_to_trash(..., force=True)` in Quarantäne verschoben. Falls nach dem Verschieben noch nicht-mediale Dateien im Sammelordner verbleiben (z. B. `.txt` oder `.nfo`), bleibt der Ordner erhalten, und die API liefert eine präzise Warnmeldung an das Frontend zurück.
  - **Hundertprozentige Testabdeckung:** 12 Python-Tests in `tests/test_nas_structure_fix.py`, 45 Frontend-Tests und die komplette Python-Suite verifizieren alle Funktionalitäten, Fehlertypen, Warnungen und Konflikte fehlerfrei.

---

## Stand am 01.07.2026 (Phase 2.5b – Bibliothekspflege: Wartungs-Cockpit & UI-Polish)

- **Wartungs-Cockpit & Premium-Umbenennungs-Flow (Branch: feature/maintenance-cockpit):**
  - **Drei Haupttabs in „Bibliothek pflegen“:** Die Bibliothekspflege wurde in die drei Top-Level-Tabs *Übersicht*, *Aufräumen* und *Werkzeuge* aufgeteilt. Umschalten erfolgt ohne Seitenreload.
  - **Größere Tab-Navigation (UI-Polish):** Größere Schrift (`1.05rem`), erweitertes Padding (`12px 10px`) und 3px dicke aktive Akzent-Unterstreichung. Besserer Abstand zwischen den Tabs (`gap: 32px`).
  - **Zähler-Badges an Untertabs:** Die Subtabs in *Aufräumen* (*Struktur*, *Filme & Serien*, *Duplikate*) haben nun dynamische Zähler-Badges (z. B. `Struktur (45)`), die sich nach jedem Scan befüllen und filterbar sind.
  - **Fachlich präzise Bezeichnungen:** Umbenennung der Kartentitel im Aufräumen-Tab zu *Strukturprobleme*, *Auffälligkeiten in Filme & Serien* und *Doppelte Episoden*.
  - **Scan-Steuerung auf Übersicht zentriert:** Alle Scan-Startbuttons, die Tiefenscan-Checkbox, Kategorienauswahl und Scan-Statusanzeigen wurden komplett aus dem Aufräumen-Tab entfernt und auf dem Übersicht-Tab gebündelt. Der Klick auf „Bibliothek prüfen“ startet den Scan und leitet den Benutzer nach 500ms automatisch auf das Aufräumen-Ergebnis weiter.
  - **Premium-Umbenennungsdialog (`modal-health-rename`):** Dialog für sichere, direkte Einzelaktionen wie *Ordner an Dateiname anpassen*, *Dateiname an Ordner anpassen* und *Freien Namen vergeben*. Emojis wurden durch konsistente inline SVGs (`folder`, `file`, `search`) ersetzt.
  - **Pfadausnutzung bei Videobefunden:** Klick auf „Öffnen“ bei einer Datei löst den Pfad im Backend automatisch auf den parent Ordner auf, um reibungslose Container-Navigation zu gewährleisten.
  - **Zeilenumbrüche in Befundlisten:** Lange Pfade und Dateinamen nutzen nun `overflow-wrap: anywhere; word-break: break-word;`, um unschöne Ellipsen-Abschneidungen zu verhindern, während die Aktionsbuttons rechts stabil platziert bleiben.
  - **Zustandssynchronisierung im Medien-Tab:** Spezifischer Empty State („Keine Auffälligkeiten für einzelne Medien...“) wird gerendert, falls in der Gesamtliste noch ungelöste Strukturfehler vorliegen.

---

## Stand am 01.07.2026 (Phase 2.5a – Health Dashboard Fehlertyp-Gruppierung & Medienpflege-Konnektoren)

- **Umschaltbare Gruppierung im NAS Bibliotheks-Check (Branch: feature/maintenance-cockpit):**
  - **Kategorien & Fehlertyp-Labels:** `HEALTH_TYPE_LABELS` und `HEALTH_RECOMMENDED_ACTIONS` in `gui/static/app.js` hinterlegt, um maschinenlesbare Fehlertypen in sprechende deutsche Beschreibungen und Handlungsempfehlungen zu übersetzen.
  - **Umschaltbare Gruppierungs-Logik:** Im Dashboard kann nun nahtlos zwischen "Nach Schweregrad gruppieren" (Standard) und "Nach Fehlertyp gruppieren" gewechselt werden. Der ausgewählte Modus (`healthGroupMode`) bleibt bei Aktualisierungen des Scans erhalten.
  - **Checkboxen-Logik für Sammel-Aktionen:** Im Fehlertyp-Modus wurden Sammel-Auswahl-Checkboxen ("Select All") pro Gruppe sowie Einzel-Checkboxen mit automatischer Berechnung des Indeterminate-Zustands implementiert.
  - **Empfehlungen & Gruppen-Zähler:** Jede Fehlertyp-Gruppe zeigt nun direkt eine passende Empfehlung an, sowie die summierten Schweregrade (kritisch, Warnung, Hinweis) der enthaltenen Befunde.
  - **Batch-Fixes (Phase 2.5b/c):** Visuelle Buttons für FSK-Zuweisung, Ordner-Flachklopfen, NFO Agent, H.265-Batch-Konvertierung und Ordner-Bereinigung integriert und mit Alerts für die nächste Phase verdrahtet.
  - **Medienpflege-Konnektoren:** Direkte Verknüpfung der Gruppen mit den Medienwerkzeugen (`tool_nfo_agent`, `tool_batch_convert`, `tool_clean`) per `runContextTool` unter Übergabe des ersten ausgewählten Pfades (`presetPath` in `openToolRunnerModal`).

---

## Stand am 01.07.2026 (Phase 2.4a & Phase 2.4b – Startseite & Docker-NAS-Härtung)

- **Startseite / Medienwerkzeug-Übersicht zusammengeführt & nachbearbeitet (Branch: feature/phase2-home-overview):**
  - **Sendezentrale zu Medienwerkzeug:** Die Startseite (`view-empty`) heißt jetzt vollständig „Medienwerkzeug“. Der Hero-Text lautet einladend: „Willkommen in deinem Medienwerkzeug“.
  - **Dashboard-Konsolidierung:** Das bisherige separate Dashboard in der Sidebar wurde entfernt.
  - **Startseite gliedern:** Die Startseite ist nun in 5 logische Bereiche gegliedert:
    1. **Arbeitsbereich & Inbox:** Inbox/Outbox-Größen, Direktlinks zu Pfaden, Smart-Inbox Vorschläge, globaler `BEREINIGEN`-Button.
    2. **Speicher & Importquellen:** NAS-Speicherbelegung (kreisförmige Anzeige) und Import-Quellen-Status (mit optionalem manuellen Import-Trigger).
    3. **Konvertierungs-Verlauf & Statistiken:** Letzte Konvertierungen & Speicherplatzreduktion (Bar Chart) und die empfohlenen H.265-Zielqualitäten der Conversion Intelligence.
    4. **Detailliertes Konvertierungsprotokoll:** Chronologische Liste aller Videokomprimierungen.
    5. **Bibliothekszustand:** Der allgemeine Zustand der Bibliothek (z. B. "Sehr gut" oder "Noch keine Diagnose durchgeführt") sowie die Anzahl der Filme, Serien und Episoden werden übersichtlich dargestellt.
  - **Bibliothek pflegen:** Die Bibliotheksseite (`view-library`) wurde in „Bibliothek pflegen“ umbenannt und enthält nun die 4 Haupt-Wartungskacheln (*NAS Bibliotheks-Check*, *Duplikat-Erkennung*, *Filme normalisieren* und *NAS-Renaming-Tool*) im Standard-Layout. Diese sind fest integriert und nicht mehr ausblendbar.
  - **JS & Event-Handling bereinigt:** Alle ungenutzten Sidebar-Klick-Handler für das Dashboard sowie die Widgets-Ausblend-Logiken wurden im JS sauber entfernt oder zu No-Ops migriert, um Fehlerfreiheit zu garantieren.
  - **Mobile Optimierung:** Flexible Grid-Systeme (`dashboard-grid`) und responsives Layout stellen sicher, dass alle Controls auch auf kleinen Displays und Smartphones überlauf- und fehlerfrei dargestellt werden.
  - **UX- & Test-Nacharbeiten (Merge-Prüfung):**
    - Die Fehlermeldungen im NAS-Verbindungstest wurden präzisiert (Vermeidung von leeren `fehlt:` Klammern, klarer Scroll-Link zu den Sync-Kategorien).
    - Generator-Abbruch im NAS-Verbindungstest implementiert (`next(shows_gen)`), um extrem lange Ladezeiten bei großen Netzlaufwerken zu verhindern.
    - Fehlerbehandlung bei der Duplikat-Erkennungs-Startphase optimiert (direkte Auswertung von `data.error` statt pauschalem „Ein Scan läuft bereits“).
    - Korrekte Singular- und Plural-Unterteilung für Film-Normalisierungs-Vorschläge ("Vorschlag" / "Vorschläge").
    - Umfassende Frontend-Testabdeckungen in `tests/frontend/app_warning.test.js` integriert und DOM-Mocks für querySelector(All) erweitert.

- **Docker-NAS-Verbindungshärtung & Runtime-Awareness (Branch: feature/phase2-docker-nas-fixes, feature/phase2-docker-nas-header-fixes, feature/phase2-docker-nas-read-access & feature/phase2-docker-nas-read-access-details):**
  - **Docker-NAS-Härtung:** Im Docker-Betrieb reicht das bloße Vorhandensein des gemounteten Einhängepfades nicht mehr aus, um direkt "Verbunden" zu melden. Es werden nun wie im Desktop-Betrieb auch die Sync-Kategorien und Lesezugriffe auf die Unterordner geprüft und andernfalls der Warnstatus `connected_but_no_library_paths` zurückgegeben.
  - **SMB-Freigabe-Pflicht gelockert:** Im NAS-Verbindungstest wird die Angabe einer SMB-Freigabe für Docker-Setups oder rein lokal gemountete Pfade nicht mehr als zwingend erachtet (`share_required: false`), so dass der Verbindungstest ohne rot zu werden grün anzeigt.
  - **Settings-Bereich & Tooltips angepasst:** Platzhalter und Label-Beschreibungen wurden dynamisch an die Docker-Laufzeit angepasst (z. B. "Container-Pfad im Docker-Setup (z.B. /media)" statt macOS-spezifischem Text).
  - **Web-Folder-Picker Fallback:** Der Folder-Browse-Button für die NAS-Tools wurde im Docker-Modus mit dem HTML5-Web-Folder-Picker (`window.openFolderPicker`) als Fallback ausgestattet, um unklare Ausfälle im Container-Betrieb zu verhindern.
  - **Koppelung beim App-Start:** Das Laden der Capabilities (`loadCapabilities()`) steuert nun die gesamte Initialisierungskette der App, so dass die Settings und Storage-Targets niemals vorliegenden Capabilities-Daten rendern.
  - **Follow-up-Fixes & Trennung von Existenz und Lesbarkeit:**
    - Globalen NAS-Header-Badge-Warnstatus korrigiert (behandelt nun `connected_but_no_library_paths` als *Unvollständig* mit gelber Farbe, um eine einheitliche Anzeige zur Startseiten-Kachel zu gewährleisten).
    - Erreichbarkeits-Meldung für Container-Setups in `"Container-Pfad erreichbar"` umbenannt.
    - Container-Pfad-Priorisierung implementiert: Ein existierender und lesbarer Pfad im Container gilt nun immer als primärer Anker für die Erreichbarkeit, unabhängig davon, ob alte SMB-IP-Werte in der Konfiguration vorhanden sind.
    - Geführtes NAS-Eingabefeld im Docker-Modus von der SMB-Vorbelegung befreit (zeigt nun standardmäßig den Container-Pfad an).
    - Lesbarkeitsprüfung getrennt: Im Verbindungstest (`/api/nas/test`) wird nun getrennt `local_path_exists` (Pfad-Existenz) und `local_path_readable` (Leseberechtigungen) ermittelt und im JSON-Response zurückgeliefert. Das Frontend visualisiert beide Stati getrennt und liefert gezielte Handlungsempfehlungen bei fehlenden Rechten (Docker-Volume-Berechtigungen vs. Mac-Rechte) statt falschem „Pfad existiert nicht“-Feedback.
    - Regressionstests für den Fall, dass der Pfad zwar existiert, aber nicht lesbar ist, in der Testsuite verankert.

---

## Stand am 30.06.2026 (Phase 2.2e – Hauptflächen Emoji/UI-Polish)

- **Emoji-Polish der primären Ansichten, YouTube-Module, FAQ und Einstellungen (Branch: feature/phase2-main-surface-emoji-polish):**
  - **Login- & Einstellungsbereich:** Emojis bei Aktionen wie `🔒` (Passwort ändern), `🔓` (Abmelden), `💾` (Einstellungen speichern) und `🔓` (Anmelden) durch professionelle inline Lucide-SVGs (`lock`, `log-out`, `save`, `log-in`) ersetzt.
  - **YouTube-Abonnements & Details:**
    - Emojis in den Transferziel-Badges (`📁 NAS`, `☁️ pCloud`, `💻 Lokal`) sowie im Modus (`⚙️`), der Aktualisierung (`🔄`), Ausschlusskriterien (`🚫`), dem deutschen Sprachfilter (`🇩🇪`) und dem letzten Check (`⏱️`) durch passende inline Lucide-SVGs (`server`, `cloud`, `monitor`, `settings`, `refresh-cw`, `ban`, `clock`) bzw. neutralen Text ersetzt.
    - Die Buttons `Abo hinzufügen` (`➕`), `Jetzt alle prüfen` (`🔄`) und `Ignorieren` (`⌛`) auf SVGs umgerüstet.
  - **Smart-Inbox-Vorschläge:** Emojis in Medien-Typen-Badges (`🎬 Film`, `📺 Serie`, `🌿 Doku`, `🌸 Anime`) durch inline Lucide-SVGs (`film`, `tv`, `leaf`, `sparkles`) ersetzt.
  - **Ordnerauswahl, Statusmeldungen & Logs:**
    - Bereinigung verbleibender Emojis in der Normalisierungsvorschau (Ersetzen von `📂` und `📄` durch reinen Text) und im Dubletten-Vergleich (`💾 Auf NAS vorhanden` durch `server`-SVG ersetzt).
    - Entfernung von Emojis aus System-Erfolgsprotokollen in der Entwicklerkonsole (z. B. bei der Bereinigung, dem Import und dem Ordner-Merge).
  - **Software-Updates & Abhängigkeiten:** Update-Prüfbutton (`🔄 Auf Aktualisierung prüfen`) und Ladeindikatoren mit einheitlichen Lucide-SVGs (`refresh-cw`, `loader-2`) ausgestattet.

---

## Stand am 30.06.2026 (Phase 2.2c)

- **Inbox-Projekt-Cleanup & Sidebar-Entschlackung (Branch: feature/phase2-inbox-project-cleanup):**
  - **Startseite entschlackt:** Entfernung der kleinteiligen `Bereinigen`-Buttons neben Inbox und Outbox. Es verbleibt ein einziger, globaler `BEREINIGEN`-Button, der standardmäßig beides scannt.
  - **Quarantäne-Shortcut für Projekte:** Hinzufügen einer direkten Quarantäne-Aktion (`Quarantäne`-Button mit Papierkorb-SVG) an jedem erkannten Projekt in der Smart-Inbox-Vorschlagsliste der Startseite.
  - **Sichere Quarantäne:** Klick auf den Quarantäne-Button löst nach Bestätigung den Aufruf des bestehenden Endpunkts `/api/delete-project` aus, wodurch das Projektverzeichnis sicher in die Quarantäne verschoben wird.
  - **Sidebar-Entschlackung:** Die redundante Sidebar-Sektion `Projektordner` (`section-project-folders`) wurde komplett ausgeblendet, um Doppelungen zu vermeiden und Platz zu schaffen.
  - **Nullguards:** Robustheits-Guards im JavaScript sichern ab, dass keine Fehler auftreten, wenn die Sidebar-Elemente nicht gerendert oder ausgeblendet sind.

---

## Stand am 30.06.2026 (Phase 2.2b)

- **Phase 2.2b – Sicherer Output-Cleanup:**
  - Status: Erfolgreich implementiert und in `main` gemergt.
  - Anpassungen:
    - **Größenanzeige im Arbeitsbereich:** Hinzufügen von Echtzeit-Größenanzeigen (`inbox-size-display` und `outbox-size-display`) in der Startseiten-Kachel.
    - **Robuste Belegungserkennung:** Übergabe der exakten Bytes (`inbox_bytes`, `outbox_bytes`) über die Status-API, um auch KB-große Dateien zuverlässig zu erfassen und farblich als "nicht leer" zu markieren.
    - **Fokus im Modal:** Optische Hervorhebung der Output-Option (Medien Output) im Bereinigungs-Auswahl-Modal (Phase 1) mittels Akzentrahmen und eines `Empfohlen`-Badges zur Lenkung der Aufmerksamkeit.
    - **Strukturierte Vorschau:** Die Dateiliste im Bereinigungs-Modal gruppiert die Dateien nun strukturiert nach ihren übergeordneten Projektordnern, was die Auswertung stark vereinfacht.
    - **Dynamische Quarantäne-Semantik:** Kennzeichnung jeder Datei mit einem optischen `Quarantäne`-Badge (rot). Bei Abwahl ändert sich das Badge interaktiv zu `Behalten` (grün), um das Sicherheitsmodell visuell transparent zu machen.
    - **Sicherer Quarantäne-Flow:** Der Flow verschiebt Dateien ausschließlich in Quarantäne (`send_to_trash`), ohne endgültige Löschungen oder Emojis in der Haupt-UI einzuführen.

---

## Älterer Projektverlauf (v1.3.0 und davor)

- **Phase 2.2a – Informationsarchitektur Startseite, Output & Bibliotheks-Wartung:**
  - Die Startseiten-Kachel `card-smart-inbox` wurde in **„Arbeitsbereich & Inbox“** umbenannt und ist nun standardmäßig permanent sichtbar.
  - Integration von Inbox (Input) und Outbox (Output) Pfaden oben in der Kachel mit Direktaktionen (`Input öffnen` und `Output öffnen`), die über `window.openFolder` geladen werden.
  - Dynamische Anpassung der Button-Texte (`Input ansehen` / `Output ansehen`) im Docker-Modus, da `window.openFolder` dort die Web-Ordneransicht anzeigt.
  - Der Startseiten-Button wurde in **`BEREINIGEN`** umbenannt und mit dem Danger-Stil (`btn-danger`) als visuelle Risikoaktion ausgewiesen.
  - Bei 0 Projekten in der Inbox wird ein informativer Platzhalter-Hinweis angezeigt, anstatt die Karte auszublenden.
  - Die `Bibliotheks-Wartung` wurde mit einer neuen Sektion **„Medienpflege-Werkzeuge“** ausgestattet, in die die Kacheln für *NFO Agent*, *H.265 Batch-Konvertierung*, *Ordner bereinigen* und *Speicherziel-Syncing* gespiegelt wurden.
  - Präzisierung der Kachel-Untertitel für *Ordner bereinigen* zu **„Junk-Dateien & leere Ordner“** (sowohl in der Bibliotheks-Wartung als auch im Werkzeuge-Dashboard).
  - Die Original-Einstiege im *Werkzeuge*-Tab bleiben stabil und funktionsfähig erhalten.

- **Phase 2.1 Navigation & Konsole:**
  - Der Sidebar-Eintrag "Warteschlange" wurde gelöscht. Der Einstieg erfolgt nun ausschließlich über die Topbar.
  - Sidebar-Labels: "Online-Medien" wurde in "Video-Downloader" und "Bibliothek" in "Bibliotheks-Wartung" umbenannt. UI-Ansichten blieben unverändert.
  - Konsolen-Steuerung (Dev-Mode): Die Konsole wird nur noch angezeigt und ist nur noch ansteuerbar, wenn die Umgebungsvariable `MW_DEV_MODE=true` (bzw. 1, yes, on) aktiv ist UND `show_console=true` in den Einstellungen gesetzt ist.
  - Console-Checkbox: Die Checkbox "Entwickler-Konsole dauerhaft einblenden" wird in den Einstellungen bei inaktivem Entwicklermodus ausgeblendet.
  - Sicherheit & Handler: Alle Toggle-/Klick- und Weiterleitungspfade wurden abgesichert, so dass die Konsole im Nicht-Entwicklermodus niemals eingeblendet wird.

- **Frontend Trust Reskin Phase 1:**
  - Default-Theme (`body.theme-deep-space` & `:root`) auf mattes Zink/Graphit-Farbschema umgestellt.
  - Eckenradien verringert, Hover-Glows/Cone-Effekte deaktiviert.
  - Emojis aus der Navigations-Sidebar durch inline-SVGs im Lucide-Stil ersetzt.
  - Emojis und Texte von Primär- und Risikoaktionen bereinigt.
  - Emojis von Warnbannern und Card-Headern durch Lucide-SVGs ersetzt.
  - Warteschlangen-Rendering komplett emoji-frei überarbeitet: nutzt nun Lucide-Stil SVGs.

- **Ältere Bugfixes & Features:**
  - Behebung von TVDB-Episoden-NFO-Problemen und fuzzy matching.
  - Implementierung von pro-Job-Logging.
  - Härtung der pCloud-FUSE-Integration und Normalisierung von Episodentiteln.
  - Implementierung des unique session cookie names.
  - Härtung des asynchronen Queue-Waitings.
