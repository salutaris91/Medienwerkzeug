# AK0 — Ausgangsmessung (Claude Code, 2026-10-19)

Basis: Worktree `feat/roadmap-74-staffel-schnellauswahl` @ `d011499` (= `origin/main`; einzige Abweichung: untracked `docs/sessions/2026-10-18-roadmap74-staffel-kette/`, kein Code). Image `openhands-agy-worker:1.2.12` (ID `sha256:20809af7d57f…`); Kopie des Worktrees per `tar` (Ausschlüsse wie `run_agy_worker_a2.sh`) nach `/tmp/ws` im Container, dort `git init` + Baseline-Commit wie im Worker-Lauf (Präzedenz #75). Start/Ende: 2026-10-19T06:21:02Z – 2026-10-19T06:21:36Z.

Befehl (`test_cmd` aus Briefing Abschnitt 11):

```bash
python3 -m pip install -q --user --break-system-packages -r requirements.txt pytest && python3 -m pytest -q -p no:cacheprovider --deselect tests/test_utils.py::TestMediawerkzeugLogic::test_conversion_estimation_test_encode && npm run test:frontend
```

Ergebnis: pytest `529 passed, 1 deselected, 1 warning`; Frontend `# tests 211 / # pass 211 / # fail 0`; Exit 0.

Wörtliche Ausgabe (Trailing Whitespace entfernt; SHA-256 der Rohdatei `ak0-output.txt`: `2d0acdc85aefe400e421b4ede94cfeec1adc6353b457cb4de73c08cdfecc9401`; Rohdatei im Kit-Worktree unter `scripts/gate-a2/logs/2026-10-18-roadmap74-kette/ak0-output.txt`):

```text
  WARNING: The script yt-dlp is installed in '/home/openhands/.local/bin' which is not on PATH.
  Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.
  WARNING: The script waitress-serve is installed in '/home/openhands/.local/bin' which is not on PATH.
  Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.
  WARNING: The script send2trash is installed in '/home/openhands/.local/bin' which is not on PATH.
  Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.
  WARNING: The script pygmentize is installed in '/home/openhands/.local/bin' which is not on PATH.
  Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.
  WARNING: The scripts py.test and pytest are installed in '/home/openhands/.local/bin' which is not on PATH.
  Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.
  WARNING: The script flask is installed in '/home/openhands/.local/bin' which is not on PATH.
  Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.

[notice] A new release of pip is available: 26.1.2 -> 26.2.1
[notice] To update, run: pip install --upgrade pip
........................................................................ [ 13%]
........................................................................ [ 27%]
........................................................................ [ 40%]
........................................................................ [ 54%]
........................................................................ [ 68%]
........................................................................ [ 81%]
........................................................................ [ 95%]
.........................                                                [100%]
=============================== warnings summary ===============================
tests/test_onboarding.py::TestOnboarding::test_complete_and_skip_endpoints
  /tmp/ws/gui/core/telemetry.py:42: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    "timestamp": datetime.datetime.utcnow().isoformat() + "Z"

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
529 passed, 1 deselected, 1 warning in 28.23s

> medienwerkzeug@1.3.0 test:frontend
> node --test "tests/frontend/**/*.test.js"

TAP version 13
# Subtest: renderHealthStatus - warning state renders warning alert, not success
ok 1 - renderHealthStatus - warning state renders warning alert, not success
  ---
  duration_ms: 1.08475
  type: 'test'
  ...
# Subtest: renderDuplicateStatus - warning state renders warning alert, not success
ok 2 - renderDuplicateStatus - warning state renders warning alert, not success
  ---
  duration_ms: 0.279041
  type: 'test'
  ...
# Subtest: loadNormalizePreview - status 400 shows warning alert, not success
ok 3 - loadNormalizePreview - status 400 shows warning alert, not success
  ---
  duration_ms: 0.160583
  type: 'test'
  ...
# Subtest: renderNormalizePlan - 1 item renders Singular "Vorschlag"
ok 4 - renderNormalizePlan - 1 item renders Singular "Vorschlag"
  ---
  duration_ms: 0.123917
  type: 'test'
  ...
# Subtest: renderNormalizePlan - 2 items renders Plural "Vorschläge"
ok 5 - renderNormalizePlan - 2 items renders Plural "Vorschläge"
  ---
  duration_ms: 0.13175
  type: 'test'
  ...
# Subtest: renderNormalizePlan - empty plan renders neutral empty state without emoji
ok 6 - renderNormalizePlan - empty plan renders neutral empty state without emoji
  ---
  duration_ms: 0.068625
  type: 'test'
  ...
# Subtest: renderQueue - pipeline step message uses existing HTML escaping helper
ok 7 - renderQueue - pipeline step message uses existing HTML escaping helper
  ---
  duration_ms: 0.60525
  type: 'test'
  ...
# Subtest: renderHealthStatus - renders summary chips with total and group counts and no severity grouping
ok 8 - renderHealthStatus - renders summary chips with total and group counts and no severity grouping
  ---
  duration_ms: 29.569417
  type: 'test'
  ...
# Subtest: renderHealthStatus - type grouping renders type groups, checkboxes and tool-connectors
ok 9 - renderHealthStatus - type grouping renders type groups, checkboxes and tool-connectors
  ---
  duration_ms: 0.604542
  type: 'test'
  ...
# Subtest: renderHealthStatus - only nested_duplicate / structure issues displays tab specific empty state on media tab
ok 10 - renderHealthStatus - only nested_duplicate / structure issues displays tab specific empty state on media tab
  ---
  duration_ms: 0.326292
  type: 'test'
  ...
# Subtest: renderHealthStatus - structure-only result wires structure batch button
ok 11 - renderHealthStatus - structure-only result wires structure batch button
  ---
  duration_ms: 0.147083
  type: 'test'
  ...
# Subtest: renderHealthStatus - transition running -> warning clears loading spinner and hides structure container
ok 12 - renderHealthStatus - transition running -> warning clears loading spinner and hides structure container
  ---
  duration_ms: 0.102166
  type: 'test'
  ...
# Subtest: renderNfoAgentFiles - mediaType tvshow renders tvshow.nfo status matrix
ok 13 - renderNfoAgentFiles - mediaType tvshow renders tvshow.nfo status matrix
  ---
  duration_ms: 0.415834
  type: 'test'
  ...
# Subtest: NFO Agent combines the main NFO status with the metadata editor
ok 14 - NFO Agent combines the main NFO status with the metadata editor
  ---
  duration_ms: 0.876875
  type: 'test'
  ...
# Subtest: NFO Agent movie mode renders movie.nfo without series controls
ok 15 - NFO Agent movie mode renders movie.nfo without series controls
  ---
  duration_ms: 0.131417
  type: 'test'
  ...
# Subtest: submitNfoAgentJob - payload structures and write_show_nfo semantics
ok 16 - submitNfoAgentJob - payload structures and write_show_nfo semantics
  ---
  duration_ms: 0.61725
  type: 'test'
  ...
# Subtest: NFO Agent shows a calm non-blocking completeness hint
ok 17 - NFO Agent shows a calm non-blocking completeness hint
  ---
  duration_ms: 0.077
  type: 'test'
  ...
# Subtest: waitForServerRestart succeeds after a temporary connection failure
ok 18 - waitForServerRestart succeeds after a temporary connection failure
  ---
  duration_ms: 0.125667
  type: 'test'
  ...
# Subtest: waitForServerRestart stops after the configured attempt limit
ok 19 - waitForServerRestart stops after the configured attempt limit
  ---
  duration_ms: 0.076125
  type: 'test'
  ...
# Subtest: restoreServerRestartButton clears the loading state
ok 20 - restoreServerRestartButton clears the loading state
  ---
  duration_ms: 0.04075
  type: 'test'
  ...
# Subtest: Cache-Busting: index.html app.js version matches all ES-module import versions in app.js
ok 21 - Cache-Busting: index.html app.js version matches all ES-module import versions in app.js
  ---
  duration_ms: 3.040458
  type: 'test'
  ...
# Subtest: Cache-Busting: style.css in index.html has a non-empty ?v= version query
ok 22 - Cache-Busting: style.css in index.html has a non-empty ?v= version query
  ---
  duration_ms: 1.29875
  type: 'test'
  ...
# Subtest: Cache-Busting: utilities.css in index.html has a non-empty ?v= version query
ok 23 - Cache-Busting: utilities.css in index.html has a non-empty ?v= version query
  ---
  duration_ms: 0.522083
  type: 'test'
  ...
# Subtest: formatBytes - Nullwert
ok 24 - formatBytes - Nullwert
  ---
  duration_ms: 0.373125
  type: 'test'
  ...
# Subtest: formatBytes - Werte unter 1 KB
ok 25 - formatBytes - Werte unter 1 KB
  ---
  duration_ms: 0.067208
  type: 'test'
  ...
# Subtest: formatBytes - Einheiten und Schwellenwerte
ok 26 - formatBytes - Einheiten und Schwellenwerte
  ---
  duration_ms: 0.091875
  type: 'test'
  ...
# Subtest: formatBytes - Nachkommastellen und Rundung
ok 27 - formatBytes - Nachkommastellen und Rundung
  ---
  duration_ms: 0.056417
  type: 'test'
  ...
# Subtest: osBasename - extracts filename correctly
ok 28 - osBasename - extracts filename correctly
  ---
  duration_ms: 0.377334
  type: 'test'
  ...
# Subtest: formatFskLabel - formats FSK labels correctly
ok 29 - formatFskLabel - formats FSK labels correctly
  ---
  duration_ms: 0.074875
  type: 'test'
  ...
# Subtest: resolveSendPaths - resolves hierarchy properly
ok 30 - resolveSendPaths - resolves hierarchy properly
  ---
  duration_ms: 1.803375
  type: 'test'
  ...
# Subtest: openFskBatchModal - opens modal and sets up state
ok 31 - openFskBatchModal - opens modal and sets up state
  ---
  duration_ms: 0.426917
  type: 'test'
  ...
# Subtest: Scope-Change-Event - triggers new preview fetch
ok 32 - Scope-Change-Event - triggers new preview fetch
  ---
  duration_ms: 22.426291
  type: 'test'
  ...
# Subtest: Null-Ziel-Sperre im DOM
ok 33 - Null-Ziel-Sperre im DOM
  ---
  duration_ms: 21.172458
  type: 'test'
  ...
# Subtest: Apply-Fetch-Payload and preview rendering
ok 34 - Apply-Fetch-Payload and preview rendering
  ---
  duration_ms: 12.131208
  type: 'test'
  ...
# Subtest: Darstellung von partial und failed
ok 35 - Darstellung von partial und failed
  ---
  duration_ms: 20.67925
  type: 'test'
  ...
# Subtest: No native Dialogs and Inline Error Rendering
ok 36 - No native Dialogs and Inline Error Rendering
  ---
  duration_ms: 10.565959
  type: 'test'
  ...
# Subtest: Dynamic Button Text and Disabled State
ok 37 - Dynamic Button Text and Disabled State
  ---
  duration_ms: 22.789125
  type: 'test'
  ...
# Subtest: Apply payload includes status field
ok 38 - Apply payload includes status field
  ---
  duration_ms: 22.410167
  type: 'test'
  ...
# Subtest: show-group-fsk-btn click - triggers openFskBatchModal and fetches series scope
ok 39 - show-group-fsk-btn click - triggers openFskBatchModal and fetches series scope
  ---
  duration_ms: 1.0335
  type: 'test'
  ...
# Subtest: season-group-fsk-btn click - triggers openFskBatchModal and fetches season scope
ok 40 - season-group-fsk-btn click - triggers openFskBatchModal and fetches season scope
  ---
  duration_ms: 0.221083
  type: 'test'
  ...
# Subtest: Out-of-order preview requests are correctly discarded
ok 41 - Out-of-order preview requests are correctly discarded
  ---
  duration_ms: 0.1215
  type: 'test'
  ...
# Subtest: Modal direct scope and prevent dual requests
ok 42 - Modal direct scope and prevent dual requests
  ---
  duration_ms: 0.055541
  type: 'test'
  ...
# Subtest: 409 Conflict keeps error message visible after preview load
ok 43 - 409 Conflict keeps error message visible after preview load
  ---
  duration_ms: 43.814584
  type: 'test'
  ...
# Subtest: Apply-Lock blocks closeFskBatchModal
ok 44 - Apply-Lock blocks closeFskBatchModal
  ---
  duration_ms: 0.11575
  type: 'test'
  ...
# Subtest: Media view routes series, season and episode metadata actions through the NFO Agent
ok 45 - Media view routes series, season and episode metadata actions through the NFO Agent
  ---
  duration_ms: 0.505166
  type: 'test'
  ...
# Subtest: Media summary stays calm and exposes exact actions only in details
ok 46 - Media summary stays calm and exposes exact actions only in details
  ---
  duration_ms: 0.514667
  type: 'test'
  ...
# Subtest: Media view separates season findings from collapsible episode metadata findings
ok 47 - Media view separates season findings from collapsible episode metadata findings
  ---
  duration_ms: 0.2355
  type: 'test'
  ...
# Subtest: Scoped ignore modal lists present issue types grouped by catalog group and posts the exact scope
ok 48 - Scoped ignore modal lists present issue types grouped by catalog group and posts the exact scope
  ---
  duration_ms: 5.815333
  type: 'test'
  ...
# Subtest: Media view separates series and movies into tabs with counts
ok 49 - Media view separates series and movies into tabs with counts
  ---
  duration_ms: 0.183042
  type: 'test'
  ...
# Subtest: Scoped ignore modal is static, explicit, and reversible
ok 50 - Scoped ignore modal is static, explicit, and reversible
  ---
  duration_ms: 0.818708
  type: 'test'
  ...
# Subtest: Media-oriented movie view treats invalid FSK as a metadata problem
ok 51 - Media-oriented movie view treats invalid FSK as a metadata problem
  ---
  duration_ms: 0.156833
  type: 'test'
  ...
# Subtest: Media view does not resurrect an ignored missing series NFO from structural status
ok 52 - Media view does not resurrect an ignored missing series NFO from structural status
  ---
  duration_ms: 0.051541
  type: 'test'
  ...
# Subtest: nfo_missing visibility and action suppression
ok 53 - nfo_missing visibility and action suppression
  ---
  duration_ms: 0.631292
  type: 'test'
  ...
# Subtest: Film-Rendering in FSK Modal uses media_kind
ok 54 - Film-Rendering in FSK Modal uses media_kind
  ---
  duration_ms: 14.356875
  type: 'test'
  ...
# Subtest: Successful apply leaves one terminal action and refreshes health immediately
ok 55 - Successful apply leaves one terminal action and refreshes health immediately
  ---
  duration_ms: 11.561459
  type: 'test'
  ...
# Subtest: NFO-Agent rendered in skipped_missing
ok 56 - NFO-Agent rendered in skipped_missing
  ---
  duration_ms: 11.098958
  type: 'test'
  ...
# Subtest: Fertig-Klick bei ready=0 schliesst Modal
ok 57 - Fertig-Klick bei ready=0 schliesst Modal
  ---
  duration_ms: 24.155584
  type: 'test'
  ...
# Subtest: NFO Agent Lifecycle wertet done, error, cancelled und fehlende Queue-Jobs aus
ok 58 - NFO Agent Lifecycle wertet done, error, cancelled und fehlende Queue-Jobs aus
  ---
  duration_ms: 23.496458
  type: 'test'
  ...
# Error: TMDB-Filmmetadaten konnten nicht geladen werden: timed out
#     at eval (eval at <anonymous> (file:///tmp/ws/tests/frontend/fsk_batch_dom.test.js:236:1), <anonymous>:17353:35)
# Subtest: Escaping-Sicherheit bei NFO-Agent-Event-Delegation
ok 59 - Escaping-Sicherheit bei NFO-Agent-Event-Delegation
  ---
  duration_ms: 13.080375
  type: 'test'
  ...
# Subtest: NFO Agent switches between entry context and whole-series editing
ok 60 - NFO Agent switches between entry context and whole-series editing
  ---
  duration_ms: 0.347208
  type: 'test'
  ...
# Subtest: Submit label reflects the visible episode fields in season mode
ok 61 - Submit label reflects the visible episode fields in season mode
  ---
  duration_ms: 0.160958
  type: 'test'
  ...
# Subtest: Mediathek search result switches to manual entry instead of a TVDB fetch
ok 62 - Mediathek search result switches to manual entry instead of a TVDB fetch
  ---
  duration_ms: 0.076042
  type: 'test'
  ...
# Error: TMDB-Filmmetadaten konnten nicht geladen werden: timed out
#     at eval (eval at <anonymous> (file:///tmp/ws/tests/frontend/fsk_batch_dom.test.js:236:1), <anonymous>:17353:35)
# Subtest: Failed detail loads render an inline retry action instead of an alert
ok 63 - Failed detail loads render an inline retry action instead of an alert
  ---
  duration_ms: 2.5175
  type: 'test'
  ...
# Subtest: NFO Agent hides the back button when whole-series is the entry point
ok 64 - NFO Agent hides the back button when whole-series is the entry point
  ---
  duration_ms: 0.126166
  type: 'test'
  ...
# Subtest: NFO Agent submits manually when no provider ID is given
ok 65 - NFO Agent submits manually when no provider ID is given
  ---
  duration_ms: 0.31525
  type: 'test'
  ...
# Subtest: NFO Agent season mode edits the season without writing the series NFO
ok 66 - NFO Agent season mode edits the season without writing the series NFO
  ---
  duration_ms: 0.2085
  type: 'test'
  ...
# Subtest: NFO Agent episode mode submits only the selected episode
ok 67 - NFO Agent episode mode submits only the selected episode
  ---
  duration_ms: 0.280584
  type: 'test'
  ...
# Subtest: NFO Agent uses concise mode controls and clear missing-source copy
ok 68 - NFO Agent uses concise mode controls and clear missing-source copy
  ---
  duration_ms: 0.856541
  type: 'test'
  ...
# Subtest: Type-oriented episode findings preserve the focused episode context
ok 69 - Type-oriented episode findings preserve the focused episode context
  ---
  duration_ms: 0.247584
  type: 'test'
  ...
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8308:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8308:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8308:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8308:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8308:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8308:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8308:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8308:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8308:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8308:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8308:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8308:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8308:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8308:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8308:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8308:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8308:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error loading dashboard data: Error: Server antwortete mit Code 400
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8286:19)
# Error loading API keys: Error: API keys fetch failed
#     at eval (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8585:40)
# Error loading dashboard data: Error: Server antwortete mit Code 400
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8286:19)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error loading dashboard data: Error: Server antwortete mit Code 400
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8286:19)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8308:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8308:64)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8308:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8308:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8308:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8308:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8308:64)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8308:64)
# Subtest: AK1: Strict SxxExx pattern recognizes Show.S01E01.720p.mkv
ok 70 - AK1: Strict SxxExx pattern recognizes Show.S01E01.720p.mkv
  ---
  duration_ms: 17.508292
  type: 'test'
  ...
# Subtest: AK1: Strict SxxExx pattern does NOT recognize Movie.1920x1080.x264.mkv, The Rock (1996).mkv, Show.1x05.mkv, Staffel 2 Folge 3 – Show.mkv
ok 71 - AK1: Strict SxxExx pattern does NOT recognize Movie.1920x1080.x264.mkv, The Rock (1996).mkv, Show.1x05.mkv, Staffel 2 Folge 3 – Show.mkv
  ---
  duration_ms: 19.197166
  type: 'test'
  ...
# Subtest: AK2: Empty suggested_query and folder entries (is_dir: true) are never automatically grouped
ok 72 - AK2: Empty suggested_query and folder entries (is_dir: true) are never automatically grouped
  ---
  duration_ms: 12.552584
  type: 'test'
  ...
# Subtest: AK2: Groups require >= 2 matches and group pseudo-entry aggregates modified_at (max) and total_size (sum)
ok 73 - AK2: Groups require >= 2 matches and group pseudo-entry aggregates modified_at (max) and total_size (sum)
  ---
  duration_ms: 6.952333
  type: 'test'
  ...
# Subtest: AK2: Group pseudo-entry participates in sortInboxSuggestions
ok 74 - AK2: Group pseudo-entry participates in sortInboxSuggestions
  ---
  duration_ms: 10.727542
  type: 'test'
  ...
# Subtest: AK3: Group banner appears above sort bar and grouping is only applied after confirmation click
ok 75 - AK3: Group banner appears above sort bar and grouping is only applied after confirmation click
  ---
  duration_ms: 10.150417
  type: 'test'
  ...
# Subtest: AK3: Banner "Ignorieren" saves to localStorage and keeps banner visible with restore counter
ok 76 - AK3: Banner "Ignorieren" saves to localStorage and keeps banner visible with restore counter
  ---
  duration_ms: 6.641792
  type: 'test'
  ...
# Subtest: AK3 & AK13: Film entries show lock notice and "Als Serie / Folge behandeln" link
ok 77 - AK3 & AK13: Film entries show lock notice and "Als Serie / Folge behandeln" link
  ---
  duration_ms: 5.230459
  type: 'test'
  ...
# Subtest: AK13: Film exception works per entry, makes entry checkable, does not auto-group, and passes relative path
ok 78 - AK13: Film exception works per entry, makes entry checkable, does not auto-group, and passes relative path
  ---
  duration_ms: 8.900167
  type: 'test'
  ...
# Subtest: AK13: Unlocked movie that isProcessing has checkbox disabled
ok 79 - AK13: Unlocked movie that isProcessing has checkbox disabled
  ---
  duration_ms: 7.794916
  type: 'test'
  ...
# Subtest: AK12: Checkboxes only appear on valid candidates (tv single files), not on folders, dokus, or processing
ok 80 - AK12: Checkboxes only appear on valid candidates (tv single files), not on folders, dokus, or processing
  ---
  duration_ms: 7.405083
  type: 'test'
  ...
# Subtest: AK12: Selection state in Set persists across re-render and sort change, idempotent against duplicates
ok 81 - AK12: Selection state in Set persists across re-render and sort change, idempotent against duplicates
  ---
  duration_ms: 13.178
  type: 'test'
  ...
# Subtest: AK12: Bulk actions bar displays count, "Auswahl aufheben" resets, and group button transfers selection
ok 82 - AK12: Bulk actions bar displays count, "Auswahl aufheben" resets, and group button transfers selection
  ---
  duration_ms: 4.937791
  type: 'test'
  ...
# Subtest: AK11: Group row has own class, data-group-key, NO data-project, NO quarantine button
ok 83 - AK11: Group row has own class, data-group-key, NO data-project, NO quarantine button
  ---
  duration_ms: 4.93575
  type: 'test'
  ...
# Subtest: AK11: Sentinel values ("" and "__inbox_recursive__") are never automatically grouped
ok 84 - AK11: Sentinel values ("" and "__inbox_recursive__") are never automatically grouped
  ---
  duration_ms: 3.611083
  type: 'test'
  ...
# Subtest: H2 (B2/AK4): Productive series workflow handover via executeSeriesWorkflow creates request body with files + mappings + media_type "tv", mappings-Schlüssel ⊆ files, and correctly escaped quotes in data-file
ok 85 - H2 (B2/AK4): Productive series workflow handover via executeSeriesWorkflow creates request body with files + mappings + media_type "tv", mappings-Schlüssel ⊆ files, and correctly escaped quotes in data-file
  ---
  duration_ms: 6.509791
  type: 'test'
  ...
# Subtest: H1 (B1): Matching matrix includes all 10 video extensions (.ts, .m2ts, etc.) matching server GROUP_VIDEO_EXTENSIONS
ok 86 - H1 (B1): Matching matrix includes all 10 video extensions (.ts, .m2ts, etc.) matching server GROUP_VIDEO_EXTENSIONS
  ---
  duration_ms: 7.017458
  type: 'test'
  ...
# Subtest: H3 (B3): Group row expanded state persists across 6-second re-render (renderSmartInboxList)
ok 87 - H3 (B3): Group row expanded state persists across 6-second re-render (renderSmartInboxList)
  ---
  duration_ms: 5.626333
  type: 'test'
  ...
# Subtest: H4 (B4): /preview_process HTTP 400 response body (error/message) is visibly displayed
ok 88 - H4 (B4): /preview_process HTTP 400 response body (error/message) is visibly displayed
  ---
  duration_ms: 3.176709
  type: 'test'
  ...
# Subtest: H4 (B4): /process HTTP 400 response body (error/message) is visibly displayed in console and alert
ok 89 - H4 (B4): /process HTTP 400 response body (error/message) is visibly displayed in console and alert
  ---
  duration_ms: 3.819583
  type: 'test'
  ...
# Subtest: F1: nach Klick auf Gruppenzeilen-Knopf, Sammelknopf und Banner ist view-folder sichtbar (nicht hidden), die Startseiten-Ansicht ausgeblendet und mode-series aktiv
ok 90 - F1: nach Klick auf Gruppenzeilen-Knopf, Sammelknopf und Banner ist view-folder sichtbar (nicht hidden), die Startseiten-Ansicht ausgeblendet und mode-series aktiv
  ---
  duration_ms: 8.534958
  type: 'test'
  ...
# Subtest: F2: Beschriftungen - Gruppenzeile "Auswählen", Banner "Als Serie gruppieren", Sammelknopf "Ausgewählte als Serie verarbeiten", gesperrte Filme "Als Serie / Folge behandeln"
ok 91 - F2: Beschriftungen - Gruppenzeile "Auswählen", Banner "Als Serie gruppieren", Sammelknopf "Ausgewählte als Serie verarbeiten", gesperrte Filme "Als Serie / Folge behandeln"
  ---
  duration_ms: 3.563167
  type: 'test'
  ...
# Subtest: 1: Vorschau-Fenster: Dateiname mit " (und mit < >) bleibt vom Rendern bis in explicit_renames/explicit_subs des /process-Requests vollständig erhalten; kein HTML wird eingeschleust
ok 92 - 1: Vorschau-Fenster: Dateiname mit " (und mit < >) bleibt vom Rendern bis in explicit_renames/explicit_subs des /process-Requests vollständig erhalten; kein HTML wird eingeschleust
  ---
  duration_ms: 5.857167
  type: 'test'
  ...
# Subtest: 2: Doppelstart-Schutz: zwei schnelle Klicks auf Ausführen -> genau ein /process-Request
ok 93 - 2: Doppelstart-Schutz: zwei schnelle Klicks auf Ausführen -> genau ein /process-Request
  ---
  duration_ms: 4.864542
  type: 'test'
  ...
# Subtest: 2: Doppelstart-Schutz: bei Fehler im /process-Request wird der Ausführen-Knopf wieder aktiv
ok 94 - 2: Doppelstart-Schutz: bei Fehler im /process-Request wird der Ausführen-Knopf wieder aktiv
  ---
  duration_ms: 5.508708
  type: 'test'
  ...
# Subtest: 2: Doppelstart-Schutz: Banner-Knopf, Gruppenzeilen-Knopf und Sammelknopf werden beim ersten Klick deaktiviert und zeigen "wird gestartet…"
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8308:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8308:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8308:64)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8308:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8308:64)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8308:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:620:5), <anonymous>:8308:64)
ok 95 - 2: Doppelstart-Schutz: Banner-Knopf, Gruppenzeilen-Knopf und Sammelknopf werden beim ersten Klick deaktiviert und zeigen "wird gestartet…"
  ---
  duration_ms: 4.516792
  type: 'test'
  ...
# Subtest: 3(b): Gruppenname bei manueller Auswahl = gemeinsamer Namensanfang ohne Folgenkennung und ohne Trennzeichen am Ende; Fallback wie bisher
ok 96 - 3(b): Gruppenname bei manueller Auswahl = gemeinsamer Namensanfang ohne Folgenkennung und ohne Trennzeichen am Ende; Fallback wie bisher
  ---
  duration_ms: 3.741625
  type: 'test'
  ...
# Subtest: 4: Name in der Warteschlange: im manuellen Serien-Modus im Gruppen-Ablauf den Gruppennamen ohne Zusatz ("Testserie") verwenden, /process-Request enthält genau Gruppennamen
ok 97 - 4: Name in der Warteschlange: im manuellen Serien-Modus im Gruppen-Ablauf den Gruppennamen ohne Zusatz ("Testserie") verwenden, /process-Request enthält genau Gruppennamen
  ---
  duration_ms: 14.180875
  type: 'test'
  ...
# Subtest: 5: Warteschlangen-Prüfung: laufender Gruppen-Job mit anderen Dateien blockiert nicht, mit überschneidenden Dateien blockiert; normale Projekte unverändert
ok 98 - 5: Warteschlangen-Prüfung: laufender Gruppen-Job mit anderen Dateien blockiert nicht, mit überschneidenden Dateien blockiert; normale Projekte unverändert
  ---
  duration_ms: 5.126791
  type: 'test'
  ...
# Subtest: AK1: Pattern (a) in extractStrictSeasonEpisode handles all AK1a-f cases
ok 99 - AK1: Pattern (a) in extractStrictSeasonEpisode handles all AK1a-f cases
  ---
  duration_ms: 4.0865
  type: 'test'
  ...
# Subtest: AK4: Folder grouping, mixed groups, and fallback key extraction (AK4a-e)
ok 100 - AK4: Folder grouping, mixed groups, and fallback key extraction (AK4a-e)
  ---
  duration_ms: 3.255875
  type: 'test'
  ...
# Subtest: AK5: Checkbox, delegation via inboxFilesEntryForItem, and bulk group name (AK5a-e)
ok 101 - AK5: Checkbox, delegation via inboxFilesEntryForItem, and bulk group name (AK5a-e)
  ---
  duration_ms: 4.773125
  type: 'test'
  ...
# Subtest: Follow-up (a): Single-video folder row has title with relpath, loose files and multi-video folders do not
ok 102 - Follow-up (a): Single-video folder row has title with relpath, loose files and multi-video folders do not
  ---
  duration_ms: 2.9215
  type: 'test'
  ...
# Subtest: Follow-up (b): Manual matching row for "XyzS01E01/Xyz.Show.S01E01.Titel.mkv" has title prefill without "Xyz - " and data-file = full relpath
ok 103 - Follow-up (b): Manual matching row for "XyzS01E01/Xyz.Show.S01E01.Titel.mkv" has title prefill without "Xyz - " and data-file = full relpath
  ---
  duration_ms: 5.183833
  type: 'test'
  ...
# Subtest: Follow-up (c): Preselection for "Foo.S01E99/Real.Show.S02E05.mkv" results in S02E05
ok 104 - Follow-up (c): Preselection for "Foo.S01E99/Real.Show.S02E05.mkv" results in S02E05
  ---
  duration_ms: 3.170625
  type: 'test'
  ...
# Subtest: Follow-up (d): style.css contains position: sticky for \#smart-inbox-bulk-actions
ok 105 - Follow-up (d): style.css contains position: sticky for \#smart-inbox-bulk-actions
  ---
  duration_ms: 0.2555
  type: 'test'
  ...
# Subtest: AK1: Drei erkannte Gruppen A, B, C -> A prominent in Zone 1, B und C unter "Weitere Vorschläge (2)" erreichbar; bei nur einer Gruppe kein "Weitere Vorschläge"-Bereich
ok 106 - AK1: Drei erkannte Gruppen A, B, C -> A prominent in Zone 1, B und C unter "Weitere Vorschläge (2)" erreichbar; bei nur einer Gruppe kein "Weitere Vorschläge"-Bereich
  ---
  duration_ms: 33.577125
  type: 'test'
  ...
# Subtest: AK2: "Ignorieren" bei nicht-prominentem Vorschlag B schreibt JSON in localStorage, entfernt B aus offenen Vorschlägen und zeigt "Ausgeblendete Vorschläge (1)"
ok 107 - AK2: "Ignorieren" bei nicht-prominentem Vorschlag B schreibt JSON in localStorage, entfernt B aus offenen Vorschlägen und zeigt "Ausgeblendete Vorschläge (1)"
  ---
  duration_ms: 22.120125
  type: 'test'
  ...
# Subtest: AK3: Ignorierter Vorschlag bleibt nach zweitem eval mit frischem Modulzustand bei gleichem localStorage ausgeblendet
ok 108 - AK3: Ignorierter Vorschlag bleibt nach zweitem eval mit frischem Modulzustand bei gleichem localStorage ausgeblendet
  ---
  duration_ms: 14.321542
  type: 'test'
  ...
# Subtest: AK4: "Wieder anzeigen" entfernt einzelnen Schlüssel und stellt Vorschlag wieder her; "Alle wieder anzeigen" stellt alle aktuell erkannten Gruppen wieder her
ok 109 - AK4: "Wieder anzeigen" entfernt einzelnen Schlüssel und stellt Vorschlag wieder her; "Alle wieder anzeigen" stellt alle aktuell erkannten Gruppen wieder her
  ---
  duration_ms: 10.566834
  type: 'test'
  ...
# Subtest: AK5: Verwaister Schlüssel smart-inbox-ignore-group-GHOST zählt nicht, wird nicht gelistet und von "Alle wieder anzeigen" nicht entfernt
ok 110 - AK5: Verwaister Schlüssel smart-inbox-ignore-group-GHOST zählt nicht, wird nicht gelistet und von "Alle wieder anzeigen" nicht entfernt
  ---
  duration_ms: 12.223916
  type: 'test'
  ...
# Subtest: AK6: Nach Ignorieren aller Gruppen bleibt Banner sichtbar (nur Rückweg-Zone); bei null erkannten Gruppen ist Banner ausgeblendet und leer
ok 111 - AK6: Nach Ignorieren aller Gruppen bleibt Banner sichtbar (nur Rückweg-Zone); bei null erkannten Gruppen ist Banner ausgeblendet und leer
  ---
  duration_ms: 8.992875
  type: 'test'
  ...
# Subtest: AK7: Vorab gesetzter sessionStorage-Schlüssel blendet Vorschlag nicht aus; Ignorier-Pfad liest und schreibt kein sessionStorage
ok 112 - AK7: Vorab gesetzter sessionStorage-Schlüssel blendet Vorschlag nicht aus; Ignorier-Pfad liest und schreibt kein sessionStorage
  ---
  duration_ms: 8.432584
  type: 'test'
  ...
# Subtest: AK8: Gruppenname mit ", ', < und & funktioniert im strengen Selektor-Mock ohne SyntaxError (Anzeige escaped, Apply, Ignorieren, Zähler, Wiederanzeigen)
ok 113 - AK8: Gruppenname mit ", ', < und & funktioniert im strengen Selektor-Mock ohne SyntaxError (Anzeige escaped, Apply, Ignorieren, Zähler, Wiederanzeigen)
  ---
  duration_ms: 9.957792
  type: 'test'
  ...
# Subtest: AK9: Synchroner Wurf beim Start (via triggerQualityHintUpdates-Stub) nimmt appliedInboxGroups zurück, zeigt Inline-Meldung, ruft console.error und lässt Gruppe offen
ok 114 - AK9: Synchroner Wurf beim Start (via triggerQualityHintUpdates-Stub) nimmt appliedInboxGroups zurück, zeigt Inline-Meldung, ruft console.error und lässt Gruppe offen
  ---
  duration_ms: 7.712959
  type: 'test'
  ...
# Subtest: AK9 (F1-Zusatztest): Suchfehler nach Apply (fetch {ok:false} für /api/search) lässt Gruppe angewendet, zeigt keine Banner-Meldung und zeigt "Suchfehler" im Suchbereich
ok 115 - AK9 (F1-Zusatztest): Suchfehler nach Apply (fetch {ok:false} für /api/search) lässt Gruppe angewendet, zeigt keine Banner-Meldung und zeigt "Suchfehler" im Suchbereich
  ---
  duration_ms: 9.540375
  type: 'test'
  ...
# Subtest: AK9 (Apply-Sperre): Zweiter Apply-Klick während laufendem Start löst keinen zweiten Workflow aus (groupWorkflowRunning)
ok 116 - AK9 (Apply-Sperre): Zweiter Apply-Klick während laufendem Start löst keinen zweiten Workflow aus (groupWorkflowRunning)
  ---
  duration_ms: 7.01325
  type: 'test'
  ...
# Subtest: AK10: Werfendes localStorage crasht nicht, blendet Gruppe per In-Memory-Fallback für die Sitzung aus und protokolliert den Speicherfehler
ok 117 - AK10: Werfendes localStorage crasht nicht, blendet Gruppe per In-Memory-Fallback für die Sitzung aus und protokolliert den Speicherfehler
  ---
  duration_ms: 11.27875
  type: 'test'
  ...
# Subtest: AK15: Nach gescheitertem Start, "Ignorieren" und "Wieder anzeigen" (einzeln sowie "Alle wieder anzeigen") steht keine Fehlermeldung mehr im Banner
ok 118 - AK15: Nach gescheitertem Start, "Ignorieren" und "Wieder anzeigen" (einzeln sowie "Alle wieder anzeigen") steht keine Fehlermeldung mehr im Banner
  ---
  duration_ms: 16.682251
  type: 'test'
  ...
# Subtest: AK16: Bei localStorage === undefined blendet "Ignorieren" die Gruppe für die Sitzung aus und ruft console.warn auf
ok 119 - AK16: Bei localStorage === undefined blendet "Ignorieren" die Gruppe für die Sitzung aus und ruft console.warn auf
  ---
  duration_ms: 9.127
  type: 'test'
  ...
# Subtest: AK17: Aufklapp-Zustand von "Weitere Vorschläge" und "Ausgeblendete Vorschläge" bleibt bei erneutem renderSmartInboxList erhalten (Auf- und Zuklappen) und startet bei frischem Modulzustand (zweiter eval) eingeklappt
ok 120 - AK17: Aufklapp-Zustand von "Weitere Vorschläge" und "Ausgeblendete Vorschläge" bleibt bei erneutem renderSmartInboxList erhalten (Auf- und Zuklappen) und startet bei frischem Modulzustand (zweiter eval) eingeklappt
  ---
  duration_ms: 15.670208
  type: 'test'
  ...
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:644:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:644:5), <anonymous>:2292:9)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:644:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:644:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:644:5), <anonymous>:8308:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:644:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:644:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:644:5), <anonymous>:8308:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:644:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:644:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:644:5), <anonymous>:8308:64)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:644:5), <anonymous>:8308:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:644:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:644:5), <anonymous>:2292:9)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:644:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:644:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:644:5), <anonymous>:8308:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:644:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:644:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:644:5), <anonymous>:8308:64)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:644:5), <anonymous>:8308:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:644:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:644:5), <anonymous>:2292:9)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:644:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:644:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:644:5), <anonymous>:8308:64)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:644:5), <anonymous>:8308:64)
# Subtest: AK1: Neuzeichnen mit Liste ohne B entfernt B aus selectedInboxProjects und aktualisiert Zähler auf "1 ausgewählt"
ok 121 - AK1: Neuzeichnen mit Liste ohne B entfernt B aus selectedInboxProjects und aktualisiert Zähler auf "1 ausgewählt"
  ---
  duration_ms: 18.877125
  type: 'test'
  ...
# Subtest: AK2: Neuzeichnen mit B in processingSet entfernt B aus Auswahl und B's Kästchen ist nicht checked
ok 122 - AK2: Neuzeichnen mit B in processingSet entfernt B aus Auswahl und B's Kästchen ist nicht checked
  ---
  duration_ms: 28.465125
  type: 'test'
  ...
# Subtest: AK3: Wenn alle ausgewählten Einträge verschwunden sind, ist die Auswahl nach Neuzeichnen leer und die Bulk-Leiste ausgeblendet
ok 123 - AK3: Wenn alle ausgewählten Einträge verschwunden sind, ist die Auswahl nach Neuzeichnen leer und die Bulk-Leiste ausgeblendet
  ---
  duration_ms: 10.419125
  type: 'test'
  ...
# Subtest: AK4: Bulk-Klick mit {A, X} ohne Treffer für X: nur A wird an Workflow übergeben, 1 übersprungener Eintrag per Alert gemeldet, X nicht mehr ausgewählt
ok 124 - AK4: Bulk-Klick mit {A, X} ohne Treffer für X: nur A wird an Workflow übergeben, 1 übersprungener Eintrag per Alert gemeldet, X nicht mehr ausgewählt
  ---
  duration_ms: 13.122667
  type: 'test'
  ...
# Subtest: AK5: Bulk-Klick wenn alle Einträge ohne Treffer sind: startSeriesGroupWorkflow wird nicht aufgerufen, Meldung erscheint, Knopf wieder aktiv
ok 125 - AK5: Bulk-Klick wenn alle Einträge ohne Treffer sind: startSeriesGroupWorkflow wird nicht aufgerufen, Meldung erscheint, Knopf wieder aktiv
  ---
  duration_ms: 6.798042
  type: 'test'
  ...
# Subtest: AK5: Bulk-Klick wenn alle Einträge in Verarbeitung sind: startSeriesGroupWorkflow wird nicht aufgerufen, Meldung erscheint, Knopf wieder aktiv
ok 126 - AK5: Bulk-Klick wenn alle Einträge in Verarbeitung sind: startSeriesGroupWorkflow wird nicht aufgerufen, Meldung erscheint, Knopf wieder aktiv
  ---
  duration_ms: 7.168334
  type: 'test'
  ...
# Subtest: AK6: Gültige Auswahl aus TV-Einzeldatei und Einzelvideo-Ordner (single_video_relpath) ruft startSeriesGroupWorkflow mit korrekten files auf, keine Meldung
ok 127 - AK6: Gültige Auswahl aus TV-Einzeldatei und Einzelvideo-Ordner (single_video_relpath) ruft startSeriesGroupWorkflow mit korrekten files auf, keine Meldung
  ---
  duration_ms: 7.715667
  type: 'test'
  ...
# Subtest: R1(c): Auswählbarkeit - Nicht auswählbare Einträge (gesperrter Film, Multi-Video-Ordner) werden beim Neuzeichnen entfernt
ok 128 - R1(c): Auswählbarkeit - Nicht auswählbare Einträge (gesperrter Film, Multi-Video-Ordner) werden beim Neuzeichnen entfernt
  ---
  duration_ms: 6.024209
  type: 'test'
  ...
# Subtest: AK9: Bulk-Klick mit {A, Show "X".mkv} ohne Treffer für den zweiten: maskiert/sicher gegen SyntaxError, nur A geht an Workflow, Meldung "1 Eintrag ...", Show "X".mkv abgewählt und Kästchen unchecked
ok 129 - AK9: Bulk-Klick mit {A, Show "X".mkv} ohne Treffer für den zweiten: maskiert/sicher gegen SyntaxError, nur A geht an Workflow, Meldung "1 Eintrag ...", Show "X".mkv abgewählt und Kästchen unchecked
  ---
  duration_ms: 11.213083
  type: 'test'
  ...
# Subtest: AK10: gui/static/app.js enthält weder setCurrentSmartInboxRawSuggestions noch getCurrentSmartInboxRawSuggestions
ok 130 - AK10: gui/static/app.js enthält weder setCurrentSmartInboxRawSuggestions noch getCurrentSmartInboxRawSuggestions
  ---
  duration_ms: 1.928375
  type: 'test'
  ...
# Could not read inbox sort state from sessionStorage: SyntaxError: Expected property name or '}' in JSON at position 2 (line 1 column 3)
#     at JSON.parse (<anonymous>)
#     at getInboxSortState (eval at setupEnvironment (file:///tmp/ws/tests/frontend/inbox_sort.test.js:220:5), <anonymous>:12433:37)
#     at TestContext.<anonymous> (file:///tmp/ws/tests/frontend/inbox_sort.test.js:415:30)
#     at Test.runInAsyncScope (node:async_hooks:214:14)
#     at Test.run (node:internal/test_runner/test:1047:25)
#     at Test.processPendingSubtests (node:internal/test_runner/test:744:18)
#     at Test.postRun (node:internal/test_runner/test:1173:19)
#     at Test.run (node:internal/test_runner/test:1101:12)
#     at async Test.processPendingSubtests (node:internal/test_runner/test:744:7)
# Subtest: AK3: sortInboxSuggestions sorts by name using German numeric/base localeCompare
ok 131 - AK3: sortInboxSuggestions sorts by name using German numeric/base localeCompare
  ---
  duration_ms: 22.033042
  type: 'test'
  ...
# Subtest: AK3: sortInboxSuggestions sorts by date (modified_at) and places null at the end for BOTH asc and desc
ok 132 - AK3: sortInboxSuggestions sorts by date (modified_at) and places null at the end for BOTH asc and desc
  ---
  duration_ms: 7.437916
  type: 'test'
  ...
# Subtest: AK3: sortInboxSuggestions sorts by size (total_size) and places null at the end for BOTH directions
ok 133 - AK3: sortInboxSuggestions sorts by size (total_size) and places null at the end for BOTH directions
  ---
  duration_ms: 2.340375
  type: 'test'
  ...
# Subtest: AK3: sortInboxSuggestions resolves ties deterministically by project name
ok 134 - AK3: sortInboxSuggestions resolves ties deterministically by project name
  ---
  duration_ms: 2.247166
  type: 'test'
  ...
# Subtest: AK4 & AK7: Default sort state without sessionStorage is date desc
ok 135 - AK4 & AK7: Default sort state without sessionStorage is date desc
  ---
  duration_ms: 2.508833
  type: 'test'
  ...
# Subtest: AK4: index.html contains \#smart-inbox-sort-bar with Name, Datum, Größe buttons
ok 136 - AK4: index.html contains \#smart-inbox-sort-bar with Name, Datum, Größe buttons
  ---
  duration_ms: 0.69775
  type: 'test'
  ...
# Subtest: AK4: Clicking inactive sort button activates it (asc), clicking active toggles asc<->desc
ok 137 - AK4: Clicking inactive sort button activates it (asc), clicking active toggles asc<->desc
  ---
  duration_ms: 7.1865
  type: 'test'
  ...
# Subtest: AK4: Sort bar is hidden when suggestions list is empty
ok 138 - AK4: Sort bar is hidden when suggestions list is empty
  ---
  duration_ms: 2.079459
  type: 'test'
  ...
# Subtest: AK5: Sort choice is persisted in sessionStorage and applied across renders
ok 139 - AK5: Sort choice is persisted in sessionStorage and applied across renders
  ---
  duration_ms: 2.879167
  type: 'test'
  ...
# Subtest: AK5: getInboxSortState handles corrupted sessionStorage defensively
ok 140 - AK5: getInboxSortState handles corrupted sessionStorage defensively
  ---
  duration_ms: 4.469375
  type: 'test'
  ...
# Subtest: AK6: Meta line formats video_count, size, and German date with separator
ok 141 - AK6: Meta line formats video_count, size, and German date with separator
  ---
  duration_ms: 1.856333
  type: 'test'
  ...
# Subtest: AK6: Meta line cleanly omits null/missing size or date without empty delimiters
ok 142 - AK6: Meta line cleanly omits null/missing size or date without empty delimiters
  ---
  duration_ms: 1.799041
  type: 'test'
  ...
# Subtest: updateHintElement - recInfo is null
ok 143 - updateHintElement - recInfo is null
  ---
  duration_ms: 0.500291
  type: 'test'
  ...
# Subtest: updateHintElement - recInfo is undefined
ok 144 - updateHintElement - recInfo is undefined
  ---
  duration_ms: 0.486834
  type: 'test'
  ...
# Subtest: updateHintElement - currentVal equals optimal
ok 145 - updateHintElement - currentVal equals optimal
  ---
  duration_ms: 0.1135
  type: 'test'
  ...
# Subtest: updateHintElement - currentVal is greater than optimal
ok 146 - updateHintElement - currentVal is greater than optimal
  ---
  duration_ms: 0.0885
  type: 'test'
  ...
# Subtest: updateHintElement - currentVal is less than optimal
ok 147 - updateHintElement - currentVal is less than optimal
  ---
  duration_ms: 0.61725
  type: 'test'
  ...
# Subtest: isMaskedValue detects masked strings correctly
ok 148 - isMaskedValue detects masked strings correctly
  ---
  duration_ms: 0.549084
  type: 'test'
  ...
# Subtest: AC1: Clear-on-Edit clears masked field on first keypress, not on focus
ok 149 - AC1: Clear-on-Edit clears masked field on first keypress, not on focus
  ---
  duration_ms: 0.512458
  type: 'test'
  ...
# Subtest: AC1: Clear-on-Edit with Backspace / Delete clears entire mask cleanly
ok 150 - AC1: Clear-on-Edit with Backspace / Delete clears entire mask cleanly
  ---
  duration_ms: 0.1455
  type: 'test'
  ...
# Subtest: AC2: Blur-Restore restores masked value when focused and left without edit
ok 151 - AC2: Blur-Restore restores masked value when focused and left without edit
  ---
  duration_ms: 0.15975
  type: 'test'
  ...
# Subtest: AC2: Escape key restores original masked value
ok 152 - AC2: Escape key restores original masked value
  ---
  duration_ms: 0.109791
  type: 'test'
  ...
# Subtest: AC3: Validation Gate marks field with **** as invalid and blocks submit
ok 153 - AC3: Validation Gate marks field with **** as invalid and blocks submit
  ---
  duration_ms: 0.277
  type: 'test'
  ...
# Subtest: AC4: Dirty-Tracking includes only modified fields across all 6 fields
ok 154 - AC4: Dirty-Tracking includes only modified fields across all 6 fields
  ---
  duration_ms: 0.866625
  type: 'test'
  ...
# Subtest: AC5: Trimming removes leading and trailing whitespace from input values
ok 155 - AC5: Trimming removes leading and trailing whitespace from input values
  ---
  duration_ms: 0.063584
  type: 'test'
  ...
# Subtest: AC6: Decoupled Key Presence indicator works for short keys (****) and empty keys
ok 156 - AC6: Decoupled Key Presence indicator works for short keys (****) and empty keys
  ---
  duration_ms: 0.264625
  type: 'test'
  ...
# Subtest: AC12: Whitespace-only input is rejected and marked as invalid
ok 157 - AC12: Whitespace-only input is rejected and marked as invalid
  ---
  duration_ms: 0.288875
  type: 'test'
  ...
# Subtest: W1: Blur-Restore restores masked value when user triggers Clear-on-Edit but blurs with empty input
ok 158 - W1: Blur-Restore restores masked value when user triggers Clear-on-Edit but blurs with empty input
  ---
  duration_ms: 0.119083
  type: 'test'
  ...
# Subtest: W1: Blur-Restore restores masked value when user enters whitespace and blurs
ok 159 - W1: Blur-Restore restores masked value when user enters whitespace and blurs
  ---
  duration_ms: 0.061083
  type: 'test'
  ...
# Subtest: W1: Validation treats field cleared via Clear-on-Edit without new value as unchanged (changed=false)
ok 160 - W1: Validation treats field cleared via Clear-on-Edit without new value as unchanged (changed=false)
  ---
  duration_ms: 0.050709
  type: 'test'
  ...
# Subtest: W1: User clears field, types a new valid key, blurs -> new key is preserved and validation reports changed=true
ok 161 - W1: User clears field, types a new valid key, blurs -> new key is preserved and validation reports changed=true
  ---
  duration_ms: 0.100875
  type: 'test'
  ...
# Subtest: W1 / Decision A: Cleared input badge does not claim key removal (Roadmap Item \#59)
ok 162 - W1 / Decision A: Cleared input badge does not claim key removal (Roadmap Item \#59)
  ---
  duration_ms: 0.066417
  type: 'test'
  ...
# Subtest: Item 59 AK1: Configured key (dataset.hasKey='true') offers visible delete button
ok 163 - Item 59 AK1: Configured key (dataset.hasKey='true') offers visible delete button
  ---
  duration_ms: 0.051959
  type: 'test'
  ...
# Subtest: Item 59 AK2: Unconfigured key (dataset.hasKey='false') does not offer active delete button
ok 164 - Item 59 AK2: Unconfigured key (dataset.hasKey='false') does not offer active delete button
  ---
  duration_ms: 0.044375
  type: 'test'
  ...
# Subtest: Item 59 AK3: First click on delete button opens confirmation prompt without clearing input
ok 165 - Item 59 AK3: First click on delete button opens confirmation prompt without clearing input
  ---
  duration_ms: 0.112834
  type: 'test'
  ...
# Subtest: Item 59 AK4: Canceling confirmation prompt restores field to original state
ok 166 - Item 59 AK4: Canceling confirmation prompt restores field to original state
  ---
  duration_ms: 0.070875
  type: 'test'
  ...
# Subtest: Item 59 AK5: Confirming deletion clears input, marks delete flag, and validateMaskedInput reports changed=true with value=''
ok 167 - Item 59 AK5: Confirming deletion clears input, marks delete flag, and validateMaskedInput reports changed=true with value=''
  ---
  duration_ms: 0.150917
  type: 'test'
  ...
# Subtest: Item 59 AK6: Clear-on-Edit without delete confirmation preserves W1 protection (changed=false)
ok 168 - Item 59 AK6: Clear-on-Edit without delete confirmation preserves W1 protection (changed=false)
  ---
  duration_ms: 0.05975
  type: 'test'
  ...
# Subtest: Item 59 AK7: Masked value with **** is rejected and marked invalid regardless of delete flow
ok 169 - Item 59 AK7: Masked value with **** is rejected and marked invalid regardless of delete flow
  ---
  duration_ms: 0.052708
  type: 'test'
  ...
# Subtest: Item 59: Escape key resets delete confirmation and restores original value without bypassing focus path
ok 170 - Item 59: Escape key resets delete confirmation and restores original value without bypassing focus path
  ---
  duration_ms: 0.17
  type: 'test'
  ...
# Subtest: Item 59: Typing a new value after delete confirmation resets delete flag
ok 171 - Item 59: Typing a new value after delete confirmation resets delete flag
  ---
  duration_ms: 0.059833
  type: 'test'
  ...
# Subtest: Item 59 DOM Structure: All 6 masked-key-field blocks in index.html contain delete button and confirmation dialog
ok 172 - Item 59 DOM Structure: All 6 masked-key-field blocks in index.html contain delete button and confirmation dialog
  ---
  duration_ms: 1.363166
  type: 'test'
  ...
# Subtest: updateMwDataPanel - with mw_data containing url and sync
ok 173 - updateMwDataPanel - with mw_data containing url and sync
  ---
  duration_ms: 25.571667
  type: 'test'
  ...
# Subtest: updateMwDataPanel - without mw_data
ok 174 - updateMwDataPanel - without mw_data
  ---
  duration_ms: 0.0815
  type: 'test'
  ...
# Subtest: prepareSeriesPayload - with mw_data
ok 175 - prepareSeriesPayload - with mw_data
  ---
  duration_ms: 0.212834
  type: 'test'
  ...
# Subtest: prepareSeriesPayload - without mw_data
ok 176 - prepareSeriesPayload - without mw_data
  ---
  duration_ms: 0.053583
  type: 'test'
  ...
# Subtest: updateMwDataPanel - with unsafe scheme source_url
ok 177 - updateMwDataPanel - with unsafe scheme source_url
  ---
  duration_ms: 0.164917
  type: 'test'
  ...
# Subtest: guessSeasonAndEpisode - S01E02-Format
ok 178 - guessSeasonAndEpisode - S01E02-Format
  ---
  duration_ms: 0.506958
  type: 'test'
  ...
# Subtest: guessSeasonAndEpisode - 1x05-Format
ok 179 - guessSeasonAndEpisode - 1x05-Format
  ---
  duration_ms: 0.128417
  type: 'test'
  ...
# Subtest: guessSeasonAndEpisode - Deutsche Formate
ok 180 - guessSeasonAndEpisode - Deutsche Formate
  ---
  duration_ms: 0.189375
  type: 'test'
  ...
# Subtest: guessSeasonAndEpisode - Kein Treffer
ok 181 - guessSeasonAndEpisode - Kein Treffer
  ---
  duration_ms: 0.626166
  type: 'test'
  ...
# Subtest: guessEpisodeNumber - Erkennung aus verschiedenen Formaten
ok 182 - guessEpisodeNumber - Erkennung aus verschiedenen Formaten
  ---
  duration_ms: 0.156833
  type: 'test'
  ...
# Subtest: guessEpisodeNumber - Grenzwerte im Ziffern-Fallback-Pfad
ok 183 - guessEpisodeNumber - Grenzwerte im Ziffern-Fallback-Pfad
  ---
  duration_ms: 0.085583
  type: 'test'
  ...
# Subtest: cleanFilenameForManualTitle - Bereinigungen
ok 184 - cleanFilenameForManualTitle - Bereinigungen
  ---
  duration_ms: 0.243042
  type: 'test'
  ...
# Subtest: cleanFilenameForManualTitle - Leereingaben (Guard)
ok 185 - cleanFilenameForManualTitle - Leereingaben (Guard)
  ---
  duration_ms: 0.052084
  type: 'test'
  ...
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:2302:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:2271:9)
# Error loading settings: TypeError: undefined is not iterable (cannot read property Symbol(Symbol.iterator))
#     at Function.from (<anonymous>)
#     at eval (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8635:50)
#     at Array.forEach (<anonymous>)
#     at updateDestinationDropdowns (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8618:16)
#     at loadSettings (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8559:13)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8287:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:2302:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:2271:9)
# Error loading settings: TypeError: undefined is not iterable (cannot read property Symbol(Symbol.iterator))
#     at Function.from (<anonymous>)
#     at eval (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8635:50)
#     at Array.forEach (<anonymous>)
#     at updateDestinationDropdowns (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8618:16)
#     at loadSettings (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8559:13)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8287:64)
# Subtest: Profile Dropdown Refresh - Case (a): ok:true and data.success:true refreshes dropdown and logs no error
ok 186 - Profile Dropdown Refresh - Case (a): ok:true and data.success:true refreshes dropdown and logs no error
  ---
  duration_ms: 34.723417
  type: 'test'
  ...
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:2302:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:2271:9)
# Error loading settings: TypeError: undefined is not iterable (cannot read property Symbol(Symbol.iterator))
#     at Function.from (<anonymous>)
#     at eval (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8635:50)
#     at Array.forEach (<anonymous>)
#     at updateDestinationDropdowns (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8618:16)
#     at loadSettings (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8559:13)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8287:64)
# Subtest: Profile Dropdown Refresh - Case (b): ok:true and data.success:false logs warning and does not refresh dropdown
ok 187 - Profile Dropdown Refresh - Case (b): ok:true and data.success:false logs warning and does not refresh dropdown
  ---
  duration_ms: 32.851
  type: 'test'
  ...
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:2302:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:2271:9)
# Error loading settings: TypeError: undefined is not iterable (cannot read property Symbol(Symbol.iterator))
#     at Function.from (<anonymous>)
#     at eval (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8635:50)
#     at Array.forEach (<anonymous>)
#     at updateDestinationDropdowns (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8618:16)
#     at loadSettings (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8559:13)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8287:64)
# Error saving show profile on execution: Error: Failed to fetch network error
#     at mockFetch (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:155:23)
#     at Object.eval (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:10667:40)
#     at Object.dispatchEvent (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:37:31)
#     at TestContext.<anonymous> (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:339:22)
#     at async Test.run (node:internal/test_runner/test:1054:7)
#     at async Test.processPendingSubtests (node:internal/test_runner/test:744:7)
# Subtest: Profile Dropdown Refresh - Case (c): ok:false (HTTP 500) logs connection error and does not refresh dropdown
ok 188 - Profile Dropdown Refresh - Case (c): ok:false (HTTP 500) logs connection error and does not refresh dropdown
  ---
  duration_ms: 25.466
  type: 'test'
  ...
# Subtest: Profile Dropdown Refresh - Case (d): Network exception / invalid JSON logs connection error and processing continues
ok 189 - Profile Dropdown Refresh - Case (d): Network exception / invalid JSON logs connection error and processing continues
  ---
  duration_ms: 25.567583
  type: 'test'
  ...
# Subtest: DOM Structure & Styling: index.html contains settings-app-theme-error with theme class and no inline style
ok 190 - DOM Structure & Styling: index.html contains settings-app-theme-error with theme class and no inline style
  ---
  duration_ms: 1.795041
  type: 'test'
  ...
# Subtest: Theme Autosave AK1 & AK3 & AK5: non-ok response shows visible informative error and logs console.error
ok 191 - Theme Autosave AK1 & AK3 & AK5: non-ok response shows visible informative error and logs console.error
  ---
  duration_ms: 1.472333
  type: 'test'
  ...
# Subtest: Theme Autosave AK2 & AK3 & AK5: network exception in catch block shows visible informative error and logs console.error
ok 192 - Theme Autosave AK2 & AK3 & AK5: network exception in catch block shows visible informative error and logs console.error
  ---
  duration_ms: 2.078125
  type: 'test'
  ...
# Subtest: Theme Autosave AK4: successful save clears any previous error and keeps error hidden
ok 193 - Theme Autosave AK4: successful save clears any previous error and keeps error hidden
  ---
  duration_ms: 1.343167
  type: 'test'
  ...
# Subtest: Roadmap: Item 60 retains deferred context and reason in ROADMAP.md
ok 194 - Roadmap: Item 60 retains deferred context and reason in ROADMAP.md
  ---
  duration_ms: 0.534333
  type: 'test'
  ...
# Subtest: Theme Autosave Guard: second theme change aborts previous in-flight request and shows no error
ok 195 - Theme Autosave Guard: second theme change aborts previous in-flight request and shows no error
  ---
  duration_ms: 1.324583
  type: 'test'
  ...
# Subtest: Theme Autosave Guard: AbortError from fetch does not trigger error message or console.error
ok 196 - Theme Autosave Guard: AbortError from fetch does not trigger error message or console.error
  ---
  duration_ms: 1.35275
  type: 'test'
  ...
# Subtest: Roadmap: Item 62 retains deferred context and reason in ROADMAP.md
ok 197 - Roadmap: Item 62 retains deferred context and reason in ROADMAP.md
  ---
  duration_ms: 0.522125
  type: 'test'
  ...
# Subtest: cleanSeriesName - Leereingaben
ok 198 - cleanSeriesName - Leereingaben
  ---
  duration_ms: 0.368209
  type: 'test'
  ...
# Subtest: cleanSeriesName - Unterstriche ersetzen
ok 199 - cleanSeriesName - Unterstriche ersetzen
  ---
  duration_ms: 0.262666
  type: 'test'
  ...
# Subtest: cleanSeriesName - Mediathek- und URL-Sonderklammern entfernen
ok 200 - cleanSeriesName - Mediathek- und URL-Sonderklammern entfernen
  ---
  duration_ms: 0.111416
  type: 'test'
  ...
# Subtest: cleanSeriesName - Kanal-Tags / Bracket-Tags am Ende entfernen (wiederholt)
ok 201 - cleanSeriesName - Kanal-Tags / Bracket-Tags am Ende entfernen (wiederholt)
  ---
  duration_ms: 0.054875
  type: 'test'
  ...
# Subtest: cleanSeriesName - Kombination und Trimming
ok 202 - cleanSeriesName - Kombination und Trimming
  ---
  duration_ms: 0.84025
  type: 'test'
  ...
# Subtest: fetchStats - success
ok 203 - fetchStats - success
  ---
  duration_ms: 0.615041
  type: 'test'
  ...
# Subtest: fetchStats - non-ok status
ok 204 - fetchStats - non-ok status
  ---
  duration_ms: 0.131708
  type: 'test'
  ...
# Subtest: fetchStats - network error
ok 205 - fetchStats - network error
  ---
  duration_ms: 0.747333
  type: 'test'
  ...
# Subtest: fetchYoutubeSubscriptions - success
ok 206 - fetchYoutubeSubscriptions - success
  ---
  duration_ms: 0.11525
  type: 'test'
  ...
# Subtest: fetchYoutubeSubscriptions - non-ok status
ok 207 - fetchYoutubeSubscriptions - non-ok status
  ---
  duration_ms: 0.070334
  type: 'test'
  ...
# Subtest: fetchYoutubeSubscriptions - network error
ok 208 - fetchYoutubeSubscriptions - network error
  ---
  duration_ms: 0.087792
  type: 'test'
  ...
# Subtest: fetchSmartInboxSuggestions - success
ok 209 - fetchSmartInboxSuggestions - success
  ---
  duration_ms: 0.093333
  type: 'test'
  ...
# Subtest: fetchSmartInboxSuggestions - non-ok status
ok 210 - fetchSmartInboxSuggestions - non-ok status
  ---
  duration_ms: 0.053959
  type: 'test'
  ...
# Subtest: fetchSmartInboxSuggestions - network error
ok 211 - fetchSmartInboxSuggestions - network error
  ---
  duration_ms: 0.257125
  type: 'test'
  ...
1..211
# tests 211
# suites 0
# pass 211
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 459.246584
npm notice
npm notice New major version of npm available! 10.9.8 -> 12.2.0
npm notice Changelog: https://github.com/npm/cli/releases/tag/v12.2.0
npm notice To update run: npm install -g npm@12.2.0
npm notice
```
