# AK0 — Ausgangsmessung (Claude Code, 2026-10-12)

Basis: `git clone` des Worktrees @ `f674727` (Code identisch mit `origin/main` @ `17b96d1`; `git diff --stat 17b96d1 HEAD -- . ':!docs' ':!ROADMAP.md'` leer). Image `openhands-agy-worker:1.2.12`, Start/Ende: 2026-10-12T13:33:22Z – 2026-10-12T13:33:56Z.

Befehl (`test_cmd` aus Briefing Abschnitt 11):

```bash
python3 -m pip install -q --user --break-system-packages -r requirements.txt pytest && python3 -m pytest -q -p no:cacheprovider --deselect tests/test_utils.py::TestMediawerkzeugLogic::test_conversion_estimation_test_encode && npm run test:frontend
```

Ergebnis: pytest `509 passed, 1 deselected, 1 warning`; Frontend `# tests 179 / # pass 179 / # fail 0`; Exit 0.

Wörtliche Ausgabe (Trailing Whitespace entfernt):

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
........................................................................ [ 14%]
........................................................................ [ 28%]
........................................................................ [ 42%]
........................................................................ [ 56%]
........................................................................ [ 70%]
........................................................................ [ 84%]
........................................................................ [ 99%]
.....                                                                    [100%]
=============================== warnings summary ===============================
tests/test_onboarding.py::TestOnboarding::test_complete_and_skip_endpoints
  /workspace/project/gui/core/telemetry.py:42: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    "timestamp": datetime.datetime.utcnow().isoformat() + "Z"

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
509 passed, 1 deselected, 1 warning in 27.76s

> medienwerkzeug@1.3.0 test:frontend
> node --test "tests/frontend/**/*.test.js"

TAP version 13
# Subtest: renderHealthStatus - warning state renders warning alert, not success
ok 1 - renderHealthStatus - warning state renders warning alert, not success
  ---
  duration_ms: 1.118317
  type: 'test'
  ...
# Subtest: renderDuplicateStatus - warning state renders warning alert, not success
ok 2 - renderDuplicateStatus - warning state renders warning alert, not success
  ---
  duration_ms: 0.293454
  type: 'test'
  ...
# Subtest: loadNormalizePreview - status 400 shows warning alert, not success
ok 3 - loadNormalizePreview - status 400 shows warning alert, not success
  ---
  duration_ms: 0.206872
  type: 'test'
  ...
# Subtest: renderNormalizePlan - 1 item renders Singular "Vorschlag"
ok 4 - renderNormalizePlan - 1 item renders Singular "Vorschlag"
  ---
  duration_ms: 0.138957
  type: 'test'
  ...
# Subtest: renderNormalizePlan - 2 items renders Plural "Vorschläge"
ok 5 - renderNormalizePlan - 2 items renders Plural "Vorschläge"
  ---
  duration_ms: 0.111373
  type: 'test'
  ...
# Subtest: renderNormalizePlan - empty plan renders neutral empty state without emoji
ok 6 - renderNormalizePlan - empty plan renders neutral empty state without emoji
  ---
  duration_ms: 0.068333
  type: 'test'
  ...
# Subtest: renderQueue - pipeline step message uses existing HTML escaping helper
ok 7 - renderQueue - pipeline step message uses existing HTML escaping helper
  ---
  duration_ms: 0.669407
  type: 'test'
  ...
# Subtest: renderHealthStatus - renders summary chips with total and group counts and no severity grouping
ok 8 - renderHealthStatus - renders summary chips with total and group counts and no severity grouping
  ---
  duration_ms: 13.527682
  type: 'test'
  ...
# Subtest: renderHealthStatus - type grouping renders type groups, checkboxes and tool-connectors
ok 9 - renderHealthStatus - type grouping renders type groups, checkboxes and tool-connectors
  ---
  duration_ms: 0.40191
  type: 'test'
  ...
# Subtest: renderHealthStatus - only nested_duplicate / structure issues displays tab specific empty state on media tab
ok 10 - renderHealthStatus - only nested_duplicate / structure issues displays tab specific empty state on media tab
  ---
  duration_ms: 0.300454
  type: 'test'
  ...
# Subtest: renderHealthStatus - structure-only result wires structure batch button
ok 11 - renderHealthStatus - structure-only result wires structure batch button
  ---
  duration_ms: 0.130373
  type: 'test'
  ...
# Subtest: renderHealthStatus - transition running -> warning clears loading spinner and hides structure container
ok 12 - renderHealthStatus - transition running -> warning clears loading spinner and hides structure container
  ---
  duration_ms: 0.090666
  type: 'test'
  ...
# Subtest: renderNfoAgentFiles - mediaType tvshow renders tvshow.nfo status matrix
ok 13 - renderNfoAgentFiles - mediaType tvshow renders tvshow.nfo status matrix
  ---
  duration_ms: 0.438994
  type: 'test'
  ...
# Subtest: NFO Agent combines the main NFO status with the metadata editor
ok 14 - NFO Agent combines the main NFO status with the metadata editor
  ---
  duration_ms: 0.785989
  type: 'test'
  ...
# Subtest: NFO Agent movie mode renders movie.nfo without series controls
ok 15 - NFO Agent movie mode renders movie.nfo without series controls
  ---
  duration_ms: 0.136664
  type: 'test'
  ...
# Subtest: submitNfoAgentJob - payload structures and write_show_nfo semantics
ok 16 - submitNfoAgentJob - payload structures and write_show_nfo semantics
  ---
  duration_ms: 0.622325
  type: 'test'
  ...
# Subtest: NFO Agent shows a calm non-blocking completeness hint
ok 17 - NFO Agent shows a calm non-blocking completeness hint
  ---
  duration_ms: 0.063165
  type: 'test'
  ...
# Subtest: waitForServerRestart succeeds after a temporary connection failure
ok 18 - waitForServerRestart succeeds after a temporary connection failure
  ---
  duration_ms: 0.107457
  type: 'test'
  ...
# Subtest: waitForServerRestart stops after the configured attempt limit
ok 19 - waitForServerRestart stops after the configured attempt limit
  ---
  duration_ms: 0.085249
  type: 'test'
  ...
# Subtest: restoreServerRestartButton clears the loading state
ok 20 - restoreServerRestartButton clears the loading state
  ---
  duration_ms: 0.041125
  type: 'test'
  ...
# Subtest: Cache-Busting: index.html app.js version matches all ES-module import versions in app.js
ok 21 - Cache-Busting: index.html app.js version matches all ES-module import versions in app.js
  ---
  duration_ms: 6.377785
  type: 'test'
  ...
# Subtest: Cache-Busting: style.css in index.html has a non-empty ?v= version query
ok 22 - Cache-Busting: style.css in index.html has a non-empty ?v= version query
  ---
  duration_ms: 1.197399
  type: 'test'
  ...
# Subtest: Cache-Busting: utilities.css in index.html has a non-empty ?v= version query
ok 23 - Cache-Busting: utilities.css in index.html has a non-empty ?v= version query
  ---
  duration_ms: 0.544575
  type: 'test'
  ...
# Subtest: formatBytes - Nullwert
ok 24 - formatBytes - Nullwert
  ---
  duration_ms: 0.377328
  type: 'test'
  ...
# Subtest: formatBytes - Werte unter 1 KB
ok 25 - formatBytes - Werte unter 1 KB
  ---
  duration_ms: 0.07254
  type: 'test'
  ...
# Subtest: formatBytes - Einheiten und Schwellenwerte
ok 26 - formatBytes - Einheiten und Schwellenwerte
  ---
  duration_ms: 0.093041
  type: 'test'
  ...
# Subtest: formatBytes - Nachkommastellen und Rundung
ok 27 - formatBytes - Nachkommastellen und Rundung
  ---
  duration_ms: 0.062915
  type: 'test'
  ...
# Subtest: osBasename - extracts filename correctly
ok 28 - osBasename - extracts filename correctly
  ---
  duration_ms: 0.390078
  type: 'test'
  ...
# Subtest: formatFskLabel - formats FSK labels correctly
ok 29 - formatFskLabel - formats FSK labels correctly
  ---
  duration_ms: 0.096957
  type: 'test'
  ...
# Subtest: resolveSendPaths - resolves hierarchy properly
ok 30 - resolveSendPaths - resolves hierarchy properly
  ---
  duration_ms: 0.798196
  type: 'test'
  ...
# Subtest: openFskBatchModal - opens modal and sets up state
ok 31 - openFskBatchModal - opens modal and sets up state
  ---
  duration_ms: 0.427077
  type: 'test'
  ...
# Subtest: Scope-Change-Event - triggers new preview fetch
ok 32 - Scope-Change-Event - triggers new preview fetch
  ---
  duration_ms: 24.510734
  type: 'test'
  ...
# Subtest: Null-Ziel-Sperre im DOM
ok 33 - Null-Ziel-Sperre im DOM
  ---
  duration_ms: 22.178934
  type: 'test'
  ...
# Subtest: Apply-Fetch-Payload and preview rendering
ok 34 - Apply-Fetch-Payload and preview rendering
  ---
  duration_ms: 12.378824
  type: 'test'
  ...
# Subtest: Darstellung von partial und failed
ok 35 - Darstellung von partial und failed
  ---
  duration_ms: 21.298238
  type: 'test'
  ...
# Subtest: No native Dialogs and Inline Error Rendering
ok 36 - No native Dialogs and Inline Error Rendering
  ---
  duration_ms: 11.717666
  type: 'test'
  ...
# Subtest: Dynamic Button Text and Disabled State
ok 37 - Dynamic Button Text and Disabled State
  ---
  duration_ms: 22.739009
  type: 'test'
  ...
# Subtest: Apply payload includes status field
ok 38 - Apply payload includes status field
  ---
  duration_ms: 23.61008
  type: 'test'
  ...
# Subtest: show-group-fsk-btn click - triggers openFskBatchModal and fetches series scope
ok 39 - show-group-fsk-btn click - triggers openFskBatchModal and fetches series scope
  ---
  duration_ms: 1.013611
  type: 'test'
  ...
# Subtest: season-group-fsk-btn click - triggers openFskBatchModal and fetches season scope
ok 40 - season-group-fsk-btn click - triggers openFskBatchModal and fetches season scope
  ---
  duration_ms: 0.21708
  type: 'test'
  ...
# Subtest: Out-of-order preview requests are correctly discarded
ok 41 - Out-of-order preview requests are correctly discarded
  ---
  duration_ms: 0.123665
  type: 'test'
  ...
# Subtest: Modal direct scope and prevent dual requests
ok 42 - Modal direct scope and prevent dual requests
  ---
  duration_ms: 0.070541
  type: 'test'
  ...
# Subtest: 409 Conflict keeps error message visible after preview load
ok 43 - 409 Conflict keeps error message visible after preview load
  ---
  duration_ms: 43.390757
  type: 'test'
  ...
# Subtest: Apply-Lock blocks closeFskBatchModal
ok 44 - Apply-Lock blocks closeFskBatchModal
  ---
  duration_ms: 0.121123
  type: 'test'
  ...
# Subtest: Media view routes series, season and episode metadata actions through the NFO Agent
ok 45 - Media view routes series, season and episode metadata actions through the NFO Agent
  ---
  duration_ms: 0.508076
  type: 'test'
  ...
# Subtest: Media summary stays calm and exposes exact actions only in details
ok 46 - Media summary stays calm and exposes exact actions only in details
  ---
  duration_ms: 0.554658
  type: 'test'
  ...
# Subtest: Media view separates season findings from collapsible episode metadata findings
ok 47 - Media view separates season findings from collapsible episode metadata findings
  ---
  duration_ms: 0.207914
  type: 'test'
  ...
# Subtest: Scoped ignore modal lists present issue types grouped by catalog group and posts the exact scope
ok 48 - Scoped ignore modal lists present issue types grouped by catalog group and posts the exact scope
  ---
  duration_ms: 4.529894
  type: 'test'
  ...
# Subtest: Media view separates series and movies into tabs with counts
ok 49 - Media view separates series and movies into tabs with counts
  ---
  duration_ms: 0.167873
  type: 'test'
  ...
# Subtest: Scoped ignore modal is static, explicit, and reversible
ok 50 - Scoped ignore modal is static, explicit, and reversible
  ---
  duration_ms: 0.975319
  type: 'test'
  ...
# Subtest: Media-oriented movie view treats invalid FSK as a metadata problem
ok 51 - Media-oriented movie view treats invalid FSK as a metadata problem
  ---
  duration_ms: 0.157748
  type: 'test'
  ...
# Subtest: Media view does not resurrect an ignored missing series NFO from structural status
ok 52 - Media view does not resurrect an ignored missing series NFO from structural status
  ---
  duration_ms: 0.056082
  type: 'test'
  ...
# Subtest: nfo_missing visibility and action suppression
ok 53 - nfo_missing visibility and action suppression
  ---
  duration_ms: 0.662658
  type: 'test'
  ...
# Subtest: Film-Rendering in FSK Modal uses media_kind
ok 54 - Film-Rendering in FSK Modal uses media_kind
  ---
  duration_ms: 10.689805
  type: 'test'
  ...
# Subtest: Successful apply leaves one terminal action and refreshes health immediately
ok 55 - Successful apply leaves one terminal action and refreshes health immediately
  ---
  duration_ms: 11.636167
  type: 'test'
  ...
# Subtest: NFO-Agent rendered in skipped_missing
ok 56 - NFO-Agent rendered in skipped_missing
  ---
  duration_ms: 11.602335
  type: 'test'
  ...
# Subtest: Fertig-Klick bei ready=0 schliesst Modal
ok 57 - Fertig-Klick bei ready=0 schliesst Modal
  ---
  duration_ms: 23.850619
  type: 'test'
  ...
# Subtest: NFO Agent Lifecycle wertet done, error, cancelled und fehlende Queue-Jobs aus
ok 58 - NFO Agent Lifecycle wertet done, error, cancelled und fehlende Queue-Jobs aus
  ---
  duration_ms: 25.552802
  type: 'test'
  ...
# Error: TMDB-Filmmetadaten konnten nicht geladen werden: timed out
#     at eval (eval at <anonymous> (file:///workspace/project/tests/frontend/fsk_batch_dom.test.js:236:1), <anonymous>:17051:35)
# Subtest: Escaping-Sicherheit bei NFO-Agent-Event-Delegation
ok 59 - Escaping-Sicherheit bei NFO-Agent-Event-Delegation
  ---
  duration_ms: 12.003496
  type: 'test'
  ...
# Subtest: NFO Agent switches between entry context and whole-series editing
ok 60 - NFO Agent switches between entry context and whole-series editing
  ---
  duration_ms: 0.408494
  type: 'test'
  ...
# Subtest: Submit label reflects the visible episode fields in season mode
ok 61 - Submit label reflects the visible episode fields in season mode
  ---
  duration_ms: 0.182872
  type: 'test'
  ...
# Subtest: Mediathek search result switches to manual entry instead of a TVDB fetch
ok 62 - Mediathek search result switches to manual entry instead of a TVDB fetch
  ---
  duration_ms: 0.084958
  type: 'test'
  ...
# Error: TMDB-Filmmetadaten konnten nicht geladen werden: timed out
#     at eval (eval at <anonymous> (file:///workspace/project/tests/frontend/fsk_batch_dom.test.js:236:1), <anonymous>:17051:35)
# Subtest: Failed detail loads render an inline retry action instead of an alert
ok 63 - Failed detail loads render an inline retry action instead of an alert
  ---
  duration_ms: 2.236009
  type: 'test'
  ...
# Subtest: NFO Agent hides the back button when whole-series is the entry point
ok 64 - NFO Agent hides the back button when whole-series is the entry point
  ---
  duration_ms: 0.11779
  type: 'test'
  ...
# Subtest: NFO Agent submits manually when no provider ID is given
ok 65 - NFO Agent submits manually when no provider ID is given
  ---
  duration_ms: 0.34112
  type: 'test'
  ...
# Subtest: NFO Agent season mode edits the season without writing the series NFO
ok 66 - NFO Agent season mode edits the season without writing the series NFO
  ---
  duration_ms: 0.25708
  type: 'test'
  ...
# Subtest: NFO Agent episode mode submits only the selected episode
ok 67 - NFO Agent episode mode submits only the selected episode
  ---
  duration_ms: 0.32437
  type: 'test'
  ...
# Subtest: NFO Agent uses concise mode controls and clear missing-source copy
ok 68 - NFO Agent uses concise mode controls and clear missing-source copy
  ---
  duration_ms: 1.025069
  type: 'test'
  ...
# Subtest: Type-oriented episode findings preserve the focused episode context
ok 69 - Type-oriented episode findings preserve the focused episode context
  ---
  duration_ms: 0.81453
  type: 'test'
  ...
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2292:9)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:8306:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:8306:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:8306:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:8306:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:8306:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:8306:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:8306:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:8306:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:8306:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:8306:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:8306:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:8306:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:8306:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:8306:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:8306:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:8306:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:8306:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2292:9)
# Error loading dashboard data: Error: Server antwortete mit Code 400
#     at loadDashboard (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:8284:19)
# Error loading API keys: Error: API keys fetch failed
#     at eval (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:8583:40)
# Error loading dashboard data: Error: Server antwortete mit Code 400
#     at loadDashboard (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:8284:19)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2292:9)
# Error loading dashboard data: Error: Server antwortete mit Code 400
#     at loadDashboard (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:8284:19)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:8306:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2292:9)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:8306:64)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:8306:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:8306:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:8306:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:8306:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2292:9)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:8306:64)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:8306:64)
# Subtest: AK1: Strict SxxExx pattern recognizes Show.S01E01.720p.mkv
ok 70 - AK1: Strict SxxExx pattern recognizes Show.S01E01.720p.mkv
  ---
  duration_ms: 17.805538
  type: 'test'
  ...
# Subtest: AK1: Strict SxxExx pattern does NOT recognize Movie.1920x1080.x264.mkv, The Rock (1996).mkv, Show.1x05.mkv, Staffel 2 Folge 3 – Show.mkv
ok 71 - AK1: Strict SxxExx pattern does NOT recognize Movie.1920x1080.x264.mkv, The Rock (1996).mkv, Show.1x05.mkv, Staffel 2 Folge 3 – Show.mkv
  ---
  duration_ms: 18.344072
  type: 'test'
  ...
# Subtest: AK2: Empty suggested_query and folder entries (is_dir: true) are never automatically grouped
ok 72 - AK2: Empty suggested_query and folder entries (is_dir: true) are never automatically grouped
  ---
  duration_ms: 9.299825
  type: 'test'
  ...
# Subtest: AK2: Groups require >= 2 matches and group pseudo-entry aggregates modified_at (max) and total_size (sum)
ok 73 - AK2: Groups require >= 2 matches and group pseudo-entry aggregates modified_at (max) and total_size (sum)
  ---
  duration_ms: 5.823834
  type: 'test'
  ...
# Subtest: AK2: Group pseudo-entry participates in sortInboxSuggestions
ok 74 - AK2: Group pseudo-entry participates in sortInboxSuggestions
  ---
  duration_ms: 10.886428
  type: 'test'
  ...
# Subtest: AK3: Group banner appears above sort bar and grouping is only applied after confirmation click
ok 75 - AK3: Group banner appears above sort bar and grouping is only applied after confirmation click
  ---
  duration_ms: 9.153995
  type: 'test'
  ...
# Subtest: AK3: Banner "Ignorieren" saves to sessionStorage and hides banner for session
ok 76 - AK3: Banner "Ignorieren" saves to sessionStorage and hides banner for session
  ---
  duration_ms: 7.648266
  type: 'test'
  ...
# Subtest: AK3 & AK13: Film entries show lock notice and "Als Serie / Folge behandeln" link
ok 77 - AK3 & AK13: Film entries show lock notice and "Als Serie / Folge behandeln" link
  ---
  duration_ms: 3.407827
  type: 'test'
  ...
# Subtest: AK13: Film exception works per entry, makes entry checkable, does not auto-group, and passes relative path
ok 78 - AK13: Film exception works per entry, makes entry checkable, does not auto-group, and passes relative path
  ---
  duration_ms: 8.483837
  type: 'test'
  ...
# Subtest: AK13: Unlocked movie that isProcessing has checkbox disabled
ok 79 - AK13: Unlocked movie that isProcessing has checkbox disabled
  ---
  duration_ms: 5.182801
  type: 'test'
  ...
# Subtest: AK12: Checkboxes only appear on valid candidates (tv single files), not on folders, dokus, or processing
ok 80 - AK12: Checkboxes only appear on valid candidates (tv single files), not on folders, dokus, or processing
  ---
  duration_ms: 5.045137
  type: 'test'
  ...
# Subtest: AK12: Selection state in Set persists across re-render and sort change, idempotent against duplicates
ok 81 - AK12: Selection state in Set persists across re-render and sort change, idempotent against duplicates
  ---
  duration_ms: 12.268908
  type: 'test'
  ...
# Subtest: AK12: Bulk actions bar displays count, "Auswahl aufheben" resets, and group button transfers selection
ok 82 - AK12: Bulk actions bar displays count, "Auswahl aufheben" resets, and group button transfers selection
  ---
  duration_ms: 4.350646
  type: 'test'
  ...
# Subtest: AK11: Group row has own class, data-group-key, NO data-project, NO quarantine button
ok 83 - AK11: Group row has own class, data-group-key, NO data-project, NO quarantine button
  ---
  duration_ms: 3.986944
  type: 'test'
  ...
# Subtest: AK11: Sentinel values ("" and "__inbox_recursive__") are never automatically grouped
ok 84 - AK11: Sentinel values ("" and "__inbox_recursive__") are never automatically grouped
  ---
  duration_ms: 3.280787
  type: 'test'
  ...
# Subtest: H2 (B2/AK4): Productive series workflow handover via executeSeriesWorkflow creates request body with files + mappings + media_type "tv", mappings-Schlüssel ⊆ files, and correctly escaped quotes in data-file
ok 85 - H2 (B2/AK4): Productive series workflow handover via executeSeriesWorkflow creates request body with files + mappings + media_type "tv", mappings-Schlüssel ⊆ files, and correctly escaped quotes in data-file
  ---
  duration_ms: 6.439742
  type: 'test'
  ...
# Subtest: H1 (B1): Matching matrix includes all 10 video extensions (.ts, .m2ts, etc.) matching server GROUP_VIDEO_EXTENSIONS
ok 86 - H1 (B1): Matching matrix includes all 10 video extensions (.ts, .m2ts, etc.) matching server GROUP_VIDEO_EXTENSIONS
  ---
  duration_ms: 6.113538
  type: 'test'
  ...
# Subtest: H3 (B3): Group row expanded state persists across 6-second re-render (renderSmartInboxList)
ok 87 - H3 (B3): Group row expanded state persists across 6-second re-render (renderSmartInboxList)
  ---
  duration_ms: 4.757224
  type: 'test'
  ...
# Subtest: H4 (B4): /preview_process HTTP 400 response body (error/message) is visibly displayed
ok 88 - H4 (B4): /preview_process HTTP 400 response body (error/message) is visibly displayed
  ---
  duration_ms: 3.41541
  type: 'test'
  ...
# Subtest: H4 (B4): /process HTTP 400 response body (error/message) is visibly displayed in console and alert
ok 89 - H4 (B4): /process HTTP 400 response body (error/message) is visibly displayed in console and alert
  ---
  duration_ms: 3.267662
  type: 'test'
  ...
# Subtest: F1: nach Klick auf Gruppenzeilen-Knopf, Sammelknopf und Banner ist view-folder sichtbar (nicht hidden), die Startseiten-Ansicht ausgeblendet und mode-series aktiv
ok 90 - F1: nach Klick auf Gruppenzeilen-Knopf, Sammelknopf und Banner ist view-folder sichtbar (nicht hidden), die Startseiten-Ansicht ausgeblendet und mode-series aktiv
  ---
  duration_ms: 7.562059
  type: 'test'
  ...
# Subtest: F2: Beschriftungen - Gruppenzeile "Auswählen", Banner "Als Serie gruppieren", Sammelknopf "Ausgewählte als Serie verarbeiten", gesperrte Filme "Als Serie / Folge behandeln"
ok 91 - F2: Beschriftungen - Gruppenzeile "Auswählen", Banner "Als Serie gruppieren", Sammelknopf "Ausgewählte als Serie verarbeiten", gesperrte Filme "Als Serie / Folge behandeln"
  ---
  duration_ms: 3.212829
  type: 'test'
  ...
# Subtest: 1: Vorschau-Fenster: Dateiname mit " (und mit < >) bleibt vom Rendern bis in explicit_renames/explicit_subs des /process-Requests vollständig erhalten; kein HTML wird eingeschleust
ok 92 - 1: Vorschau-Fenster: Dateiname mit " (und mit < >) bleibt vom Rendern bis in explicit_renames/explicit_subs des /process-Requests vollständig erhalten; kein HTML wird eingeschleust
  ---
  duration_ms: 4.733224
  type: 'test'
  ...
# Subtest: 2: Doppelstart-Schutz: zwei schnelle Klicks auf Ausführen -> genau ein /process-Request
ok 93 - 2: Doppelstart-Schutz: zwei schnelle Klicks auf Ausführen -> genau ein /process-Request
  ---
  duration_ms: 4.428478
  type: 'test'
  ...
# Subtest: 2: Doppelstart-Schutz: bei Fehler im /process-Request wird der Ausführen-Knopf wieder aktiv
ok 94 - 2: Doppelstart-Schutz: bei Fehler im /process-Request wird der Ausführen-Knopf wieder aktiv
  ---
  duration_ms: 4.681266
  type: 'test'
  ...
# Subtest: 2: Doppelstart-Schutz: Banner-Knopf, Gruppenzeilen-Knopf und Sammelknopf werden beim ersten Klick deaktiviert und zeigen "wird gestartet…"
ok 95 - 2: Doppelstart-Schutz: Banner-Knopf, Gruppenzeilen-Knopf und Sammelknopf werden beim ersten Klick deaktiviert und zeigen "wird gestartet…"
  ---
  duration_ms: 4.65485
  type: 'test'
  ...
# Subtest: 3(b): Gruppenname bei manueller Auswahl = gemeinsamer Namensanfang ohne Folgenkennung und ohne Trennzeichen am Ende; Fallback wie bisher
ok 96 - 3(b): Gruppenname bei manueller Auswahl = gemeinsamer Namensanfang ohne Folgenkennung und ohne Trennzeichen am Ende; Fallback wie bisher
  ---
  duration_ms: 3.12683
  type: 'test'
  ...
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/inbox_group.test.js:615:5), <anonymous>:8306:64)
# Subtest: 4: Name in der Warteschlange: im manuellen Serien-Modus im Gruppen-Ablauf den Gruppennamen ohne Zusatz ("Testserie") verwenden, /process-Request enthält genau Gruppennamen
ok 97 - 4: Name in der Warteschlange: im manuellen Serien-Modus im Gruppen-Ablauf den Gruppennamen ohne Zusatz ("Testserie") verwenden, /process-Request enthält genau Gruppennamen
  ---
  duration_ms: 12.698778
  type: 'test'
  ...
# Subtest: 5: Warteschlangen-Prüfung: laufender Gruppen-Job mit anderen Dateien blockiert nicht, mit überschneidenden Dateien blockiert; normale Projekte unverändert
ok 98 - 5: Warteschlangen-Prüfung: laufender Gruppen-Job mit anderen Dateien blockiert nicht, mit überschneidenden Dateien blockiert; normale Projekte unverändert
  ---
  duration_ms: 6.137246
  type: 'test'
  ...
# Could not read inbox sort state from sessionStorage: SyntaxError: Expected property name or '}' in JSON at position 2 (line 1 column 3)
#     at JSON.parse (<anonymous>)
#     at getInboxSortState (eval at setupEnvironment (file:///workspace/project/tests/frontend/inbox_sort.test.js:220:5), <anonymous>:12431:37)
#     at TestContext.<anonymous> (file:///workspace/project/tests/frontend/inbox_sort.test.js:415:30)
#     at Test.runInAsyncScope (node:async_hooks:214:14)
#     at Test.run (node:internal/test_runner/test:1047:25)
#     at Test.processPendingSubtests (node:internal/test_runner/test:744:18)
#     at Test.postRun (node:internal/test_runner/test:1173:19)
#     at Test.run (node:internal/test_runner/test:1101:12)
#     at async Test.processPendingSubtests (node:internal/test_runner/test:744:7)
# Subtest: AK3: sortInboxSuggestions sorts by name using German numeric/base localeCompare
ok 99 - AK3: sortInboxSuggestions sorts by name using German numeric/base localeCompare
  ---
  duration_ms: 13.794304
  type: 'test'
  ...
# Subtest: AK3: sortInboxSuggestions sorts by date (modified_at) and places null at the end for BOTH asc and desc
ok 100 - AK3: sortInboxSuggestions sorts by date (modified_at) and places null at the end for BOTH asc and desc
  ---
  duration_ms: 7.193231
  type: 'test'
  ...
# Subtest: AK3: sortInboxSuggestions sorts by size (total_size) and places null at the end for BOTH directions
ok 101 - AK3: sortInboxSuggestions sorts by size (total_size) and places null at the end for BOTH directions
  ---
  duration_ms: 2.186594
  type: 'test'
  ...
# Subtest: AK3: sortInboxSuggestions resolves ties deterministically by project name
ok 102 - AK3: sortInboxSuggestions resolves ties deterministically by project name
  ---
  duration_ms: 1.999347
  type: 'test'
  ...
# Subtest: AK4 & AK7: Default sort state without sessionStorage is date desc
ok 103 - AK4 & AK7: Default sort state without sessionStorage is date desc
  ---
  duration_ms: 2.667128
  type: 'test'
  ...
# Subtest: AK4: index.html contains \#smart-inbox-sort-bar with Name, Datum, Größe buttons
ok 104 - AK4: index.html contains \#smart-inbox-sort-bar with Name, Datum, Größe buttons
  ---
  duration_ms: 0.646241
  type: 'test'
  ...
# Subtest: AK4: Clicking inactive sort button activates it (asc), clicking active toggles asc<->desc
ok 105 - AK4: Clicking inactive sort button activates it (asc), clicking active toggles asc<->desc
  ---
  duration_ms: 7.258646
  type: 'test'
  ...
# Subtest: AK4: Sort bar is hidden when suggestions list is empty
ok 106 - AK4: Sort bar is hidden when suggestions list is empty
  ---
  duration_ms: 2.232176
  type: 'test'
  ...
# Subtest: AK5: Sort choice is persisted in sessionStorage and applied across renders
ok 107 - AK5: Sort choice is persisted in sessionStorage and applied across renders
  ---
  duration_ms: 2.324509
  type: 'test'
  ...
# Subtest: AK5: getInboxSortState handles corrupted sessionStorage defensively
ok 108 - AK5: getInboxSortState handles corrupted sessionStorage defensively
  ---
  duration_ms: 4.217398
  type: 'test'
  ...
# Subtest: AK6: Meta line formats video_count, size, and German date with separator
ok 109 - AK6: Meta line formats video_count, size, and German date with separator
  ---
  duration_ms: 1.803558
  type: 'test'
  ...
# Subtest: AK6: Meta line cleanly omits null/missing size or date without empty delimiters
ok 110 - AK6: Meta line cleanly omits null/missing size or date without empty delimiters
  ---
  duration_ms: 1.642476
  type: 'test'
  ...
# Subtest: updateHintElement - recInfo is null
ok 111 - updateHintElement - recInfo is null
  ---
  duration_ms: 0.406536
  type: 'test'
  ...
# Subtest: updateHintElement - recInfo is undefined
ok 112 - updateHintElement - recInfo is undefined
  ---
  duration_ms: 0.058874
  type: 'test'
  ...
# Subtest: updateHintElement - currentVal equals optimal
ok 113 - updateHintElement - currentVal equals optimal
  ---
  duration_ms: 0.056957
  type: 'test'
  ...
# Subtest: updateHintElement - currentVal is greater than optimal
ok 114 - updateHintElement - currentVal is greater than optimal
  ---
  duration_ms: 0.051166
  type: 'test'
  ...
# Subtest: updateHintElement - currentVal is less than optimal
ok 115 - updateHintElement - currentVal is less than optimal
  ---
  duration_ms: 0.538784
  type: 'test'
  ...
# Subtest: isMaskedValue detects masked strings correctly
ok 116 - isMaskedValue detects masked strings correctly
  ---
  duration_ms: 0.534867
  type: 'test'
  ...
# Subtest: AC1: Clear-on-Edit clears masked field on first keypress, not on focus
ok 117 - AC1: Clear-on-Edit clears masked field on first keypress, not on focus
  ---
  duration_ms: 0.505576
  type: 'test'
  ...
# Subtest: AC1: Clear-on-Edit with Backspace / Delete clears entire mask cleanly
ok 118 - AC1: Clear-on-Edit with Backspace / Delete clears entire mask cleanly
  ---
  duration_ms: 0.110415
  type: 'test'
  ...
# Subtest: AC2: Blur-Restore restores masked value when focused and left without edit
ok 119 - AC2: Blur-Restore restores masked value when focused and left without edit
  ---
  duration_ms: 0.158539
  type: 'test'
  ...
# Subtest: AC2: Escape key restores original masked value
ok 120 - AC2: Escape key restores original masked value
  ---
  duration_ms: 0.107623
  type: 'test'
  ...
# Subtest: AC3: Validation Gate marks field with **** as invalid and blocks submit
ok 121 - AC3: Validation Gate marks field with **** as invalid and blocks submit
  ---
  duration_ms: 0.285329
  type: 'test'
  ...
# Subtest: AC4: Dirty-Tracking includes only modified fields across all 6 fields
ok 122 - AC4: Dirty-Tracking includes only modified fields across all 6 fields
  ---
  duration_ms: 0.889154
  type: 'test'
  ...
# Subtest: AC5: Trimming removes leading and trailing whitespace from input values
ok 123 - AC5: Trimming removes leading and trailing whitespace from input values
  ---
  duration_ms: 0.072791
  type: 'test'
  ...
# Subtest: AC6: Decoupled Key Presence indicator works for short keys (****) and empty keys
ok 124 - AC6: Decoupled Key Presence indicator works for short keys (****) and empty keys
  ---
  duration_ms: 0.270662
  type: 'test'
  ...
# Subtest: AC12: Whitespace-only input is rejected and marked as invalid
ok 125 - AC12: Whitespace-only input is rejected and marked as invalid
  ---
  duration_ms: 0.308079
  type: 'test'
  ...
# Subtest: W1: Blur-Restore restores masked value when user triggers Clear-on-Edit but blurs with empty input
ok 126 - W1: Blur-Restore restores masked value when user triggers Clear-on-Edit but blurs with empty input
  ---
  duration_ms: 0.12679
  type: 'test'
  ...
# Subtest: W1: Blur-Restore restores masked value when user enters whitespace and blurs
ok 127 - W1: Blur-Restore restores masked value when user enters whitespace and blurs
  ---
  duration_ms: 0.061999
  type: 'test'
  ...
# Subtest: W1: Validation treats field cleared via Clear-on-Edit without new value as unchanged (changed=false)
ok 128 - W1: Validation treats field cleared via Clear-on-Edit without new value as unchanged (changed=false)
  ---
  duration_ms: 0.06279
  type: 'test'
  ...
# Subtest: W1: User clears field, types a new valid key, blurs -> new key is preserved and validation reports changed=true
ok 129 - W1: User clears field, types a new valid key, blurs -> new key is preserved and validation reports changed=true
  ---
  duration_ms: 0.117415
  type: 'test'
  ...
# Subtest: W1 / Decision A: Cleared input badge does not claim key removal (Roadmap Item \#59)
ok 130 - W1 / Decision A: Cleared input badge does not claim key removal (Roadmap Item \#59)
  ---
  duration_ms: 0.084166
  type: 'test'
  ...
# Subtest: Item 59 AK1: Configured key (dataset.hasKey='true') offers visible delete button
ok 131 - Item 59 AK1: Configured key (dataset.hasKey='true') offers visible delete button
  ---
  duration_ms: 0.062166
  type: 'test'
  ...
# Subtest: Item 59 AK2: Unconfigured key (dataset.hasKey='false') does not offer active delete button
ok 132 - Item 59 AK2: Unconfigured key (dataset.hasKey='false') does not offer active delete button
  ---
  duration_ms: 0.061624
  type: 'test'
  ...
# Subtest: Item 59 AK3: First click on delete button opens confirmation prompt without clearing input
ok 133 - Item 59 AK3: First click on delete button opens confirmation prompt without clearing input
  ---
  duration_ms: 0.119123
  type: 'test'
  ...
# Subtest: Item 59 AK4: Canceling confirmation prompt restores field to original state
ok 134 - Item 59 AK4: Canceling confirmation prompt restores field to original state
  ---
  duration_ms: 0.077499
  type: 'test'
  ...
# Subtest: Item 59 AK5: Confirming deletion clears input, marks delete flag, and validateMaskedInput reports changed=true with value=''
ok 135 - Item 59 AK5: Confirming deletion clears input, marks delete flag, and validateMaskedInput reports changed=true with value=''
  ---
  duration_ms: 0.162498
  type: 'test'
  ...
# Subtest: Item 59 AK6: Clear-on-Edit without delete confirmation preserves W1 protection (changed=false)
ok 136 - Item 59 AK6: Clear-on-Edit without delete confirmation preserves W1 protection (changed=false)
  ---
  duration_ms: 0.064332
  type: 'test'
  ...
# Subtest: Item 59 AK7: Masked value with **** is rejected and marked invalid regardless of delete flow
ok 137 - Item 59 AK7: Masked value with **** is rejected and marked invalid regardless of delete flow
  ---
  duration_ms: 0.056583
  type: 'test'
  ...
# Subtest: Item 59: Escape key resets delete confirmation and restores original value without bypassing focus path
ok 138 - Item 59: Escape key resets delete confirmation and restores original value without bypassing focus path
  ---
  duration_ms: 0.076082
  type: 'test'
  ...
# Subtest: Item 59: Typing a new value after delete confirmation resets delete flag
ok 139 - Item 59: Typing a new value after delete confirmation resets delete flag
  ---
  duration_ms: 0.062665
  type: 'test'
  ...
# Subtest: Item 59 DOM Structure: All 6 masked-key-field blocks in index.html contain delete button and confirmation dialog
ok 140 - Item 59 DOM Structure: All 6 masked-key-field blocks in index.html contain delete button and confirmation dialog
  ---
  duration_ms: 1.27644
  type: 'test'
  ...
# Subtest: updateMwDataPanel - with mw_data containing url and sync
ok 141 - updateMwDataPanel - with mw_data containing url and sync
  ---
  duration_ms: 9.706445
  type: 'test'
  ...
# Subtest: updateMwDataPanel - without mw_data
ok 142 - updateMwDataPanel - without mw_data
  ---
  duration_ms: 0.087415
  type: 'test'
  ...
# Subtest: prepareSeriesPayload - with mw_data
ok 143 - prepareSeriesPayload - with mw_data
  ---
  duration_ms: 0.214206
  type: 'test'
  ...
# Subtest: prepareSeriesPayload - without mw_data
ok 144 - prepareSeriesPayload - without mw_data
  ---
  duration_ms: 0.057124
  type: 'test'
  ...
# Subtest: updateMwDataPanel - with unsafe scheme source_url
ok 145 - updateMwDataPanel - with unsafe scheme source_url
  ---
  duration_ms: 0.279413
  type: 'test'
  ...
# Subtest: guessSeasonAndEpisode - S01E02-Format
ok 146 - guessSeasonAndEpisode - S01E02-Format
  ---
  duration_ms: 0.507285
  type: 'test'
  ...
# Subtest: guessSeasonAndEpisode - 1x05-Format
ok 147 - guessSeasonAndEpisode - 1x05-Format
  ---
  duration_ms: 0.107249
  type: 'test'
  ...
# Subtest: guessSeasonAndEpisode - Deutsche Formate
ok 148 - guessSeasonAndEpisode - Deutsche Formate
  ---
  duration_ms: 0.17958
  type: 'test'
  ...
# Subtest: guessSeasonAndEpisode - Kein Treffer
ok 149 - guessSeasonAndEpisode - Kein Treffer
  ---
  duration_ms: 0.842405
  type: 'test'
  ...
# Subtest: guessEpisodeNumber - Erkennung aus verschiedenen Formaten
ok 150 - guessEpisodeNumber - Erkennung aus verschiedenen Formaten
  ---
  duration_ms: 0.183081
  type: 'test'
  ...
# Subtest: guessEpisodeNumber - Grenzwerte im Ziffern-Fallback-Pfad
ok 151 - guessEpisodeNumber - Grenzwerte im Ziffern-Fallback-Pfad
  ---
  duration_ms: 0.088291
  type: 'test'
  ...
# Subtest: cleanFilenameForManualTitle - Bereinigungen
ok 152 - cleanFilenameForManualTitle - Bereinigungen
  ---
  duration_ms: 0.248955
  type: 'test'
  ...
# Subtest: cleanFilenameForManualTitle - Leereingaben (Guard)
ok 153 - cleanFilenameForManualTitle - Leereingaben (Guard)
  ---
  duration_ms: 0.054082
  type: 'test'
  ...
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:2302:40)
#     at loadStatus (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:2271:9)
# Error loading settings: TypeError: undefined is not iterable (cannot read property Symbol(Symbol.iterator))
#     at Function.from (<anonymous>)
#     at eval (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8633:50)
#     at Array.forEach (<anonymous>)
#     at updateDestinationDropdowns (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8616:16)
#     at loadSettings (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8557:13)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8285:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:2302:40)
#     at loadStatus (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:2271:9)
# Error loading settings: TypeError: undefined is not iterable (cannot read property Symbol(Symbol.iterator))
#     at Function.from (<anonymous>)
#     at eval (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8633:50)
#     at Array.forEach (<anonymous>)
#     at updateDestinationDropdowns (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8616:16)
#     at loadSettings (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8557:13)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8285:64)
# Subtest: Profile Dropdown Refresh - Case (a): ok:true and data.success:true refreshes dropdown and logs no error
ok 154 - Profile Dropdown Refresh - Case (a): ok:true and data.success:true refreshes dropdown and logs no error
  ---
  duration_ms: 36.265858
  type: 'test'
  ...
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:2302:40)
#     at loadStatus (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:2271:9)
# Error loading settings: TypeError: undefined is not iterable (cannot read property Symbol(Symbol.iterator))
#     at Function.from (<anonymous>)
#     at eval (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8633:50)
#     at Array.forEach (<anonymous>)
#     at updateDestinationDropdowns (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8616:16)
#     at loadSettings (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8557:13)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8285:64)
# Subtest: Profile Dropdown Refresh - Case (b): ok:true and data.success:false logs warning and does not refresh dropdown
ok 155 - Profile Dropdown Refresh - Case (b): ok:true and data.success:false logs warning and does not refresh dropdown
  ---
  duration_ms: 35.844198
  type: 'test'
  ...
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:2302:40)
#     at loadStatus (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:2271:9)
# Error loading settings: TypeError: undefined is not iterable (cannot read property Symbol(Symbol.iterator))
#     at Function.from (<anonymous>)
#     at eval (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8633:50)
#     at Array.forEach (<anonymous>)
#     at updateDestinationDropdowns (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8616:16)
#     at loadSettings (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8557:13)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8285:64)
# Error saving show profile on execution: Error: Failed to fetch network error
#     at mockFetch (file:///workspace/project/tests/frontend/profile_dropdown_refresh.test.js:155:23)
#     at Object.eval (eval at setupTestEnvironment (file:///workspace/project/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:10665:40)
#     at Object.dispatchEvent (file:///workspace/project/tests/frontend/profile_dropdown_refresh.test.js:37:31)
#     at TestContext.<anonymous> (file:///workspace/project/tests/frontend/profile_dropdown_refresh.test.js:339:22)
#     at async Test.run (node:internal/test_runner/test:1054:7)
#     at async Test.processPendingSubtests (node:internal/test_runner/test:744:7)
# Subtest: Profile Dropdown Refresh - Case (c): ok:false (HTTP 500) logs connection error and does not refresh dropdown
ok 156 - Profile Dropdown Refresh - Case (c): ok:false (HTTP 500) logs connection error and does not refresh dropdown
  ---
  duration_ms: 25.905214
  type: 'test'
  ...
# Subtest: Profile Dropdown Refresh - Case (d): Network exception / invalid JSON logs connection error and processing continues
ok 157 - Profile Dropdown Refresh - Case (d): Network exception / invalid JSON logs connection error and processing continues
  ---
  duration_ms: 26.833284
  type: 'test'
  ...
# Subtest: DOM Structure & Styling: index.html contains settings-app-theme-error with theme class and no inline style
ok 158 - DOM Structure & Styling: index.html contains settings-app-theme-error with theme class and no inline style
  ---
  duration_ms: 1.66906
  type: 'test'
  ...
# Subtest: Theme Autosave AK1 & AK3 & AK5: non-ok response shows visible informative error and logs console.error
ok 159 - Theme Autosave AK1 & AK3 & AK5: non-ok response shows visible informative error and logs console.error
  ---
  duration_ms: 1.95993
  type: 'test'
  ...
# Subtest: Theme Autosave AK2 & AK3 & AK5: network exception in catch block shows visible informative error and logs console.error
ok 160 - Theme Autosave AK2 & AK3 & AK5: network exception in catch block shows visible informative error and logs console.error
  ---
  duration_ms: 2.526047
  type: 'test'
  ...
# Subtest: Theme Autosave AK4: successful save clears any previous error and keeps error hidden
ok 161 - Theme Autosave AK4: successful save clears any previous error and keeps error hidden
  ---
  duration_ms: 1.497062
  type: 'test'
  ...
# Subtest: Roadmap: Item 60 retains deferred context and reason in ROADMAP.md
ok 162 - Roadmap: Item 60 retains deferred context and reason in ROADMAP.md
  ---
  duration_ms: 0.780614
  type: 'test'
  ...
# Subtest: Theme Autosave Guard: second theme change aborts previous in-flight request and shows no error
ok 163 - Theme Autosave Guard: second theme change aborts previous in-flight request and shows no error
  ---
  duration_ms: 1.596894
  type: 'test'
  ...
# Subtest: Theme Autosave Guard: AbortError from fetch does not trigger error message or console.error
ok 164 - Theme Autosave Guard: AbortError from fetch does not trigger error message or console.error
  ---
  duration_ms: 1.456479
  type: 'test'
  ...
# Subtest: Roadmap: Item 62 retains deferred context and reason in ROADMAP.md
ok 165 - Roadmap: Item 62 retains deferred context and reason in ROADMAP.md
  ---
  duration_ms: 0.40666
  type: 'test'
  ...
# Subtest: cleanSeriesName - Leereingaben
ok 166 - cleanSeriesName - Leereingaben
  ---
  duration_ms: 0.383702
  type: 'test'
  ...
# Subtest: cleanSeriesName - Unterstriche ersetzen
ok 167 - cleanSeriesName - Unterstriche ersetzen
  ---
  duration_ms: 0.260246
  type: 'test'
  ...
# Subtest: cleanSeriesName - Mediathek- und URL-Sonderklammern entfernen
ok 168 - cleanSeriesName - Mediathek- und URL-Sonderklammern entfernen
  ---
  duration_ms: 0.129665
  type: 'test'
  ...
# Subtest: cleanSeriesName - Kanal-Tags / Bracket-Tags am Ende entfernen (wiederholt)
ok 169 - cleanSeriesName - Kanal-Tags / Bracket-Tags am Ende entfernen (wiederholt)
  ---
  duration_ms: 0.064958
  type: 'test'
  ...
# Subtest: cleanSeriesName - Kombination und Trimming
ok 170 - cleanSeriesName - Kombination und Trimming
  ---
  duration_ms: 0.871571
  type: 'test'
  ...
# Subtest: fetchStats - success
ok 171 - fetchStats - success
  ---
  duration_ms: 0.597283
  type: 'test'
  ...
# Subtest: fetchStats - non-ok status
ok 172 - fetchStats - non-ok status
  ---
  duration_ms: 0.11829
  type: 'test'
  ...
# Subtest: fetchStats - network error
ok 173 - fetchStats - network error
  ---
  duration_ms: 0.870862
  type: 'test'
  ...
# Subtest: fetchYoutubeSubscriptions - success
ok 174 - fetchYoutubeSubscriptions - success
  ---
  duration_ms: 0.092541
  type: 'test'
  ...
# Subtest: fetchYoutubeSubscriptions - non-ok status
ok 175 - fetchYoutubeSubscriptions - non-ok status
  ---
  duration_ms: 0.086166
  type: 'test'
  ...
# Subtest: fetchYoutubeSubscriptions - network error
ok 176 - fetchYoutubeSubscriptions - network error
  ---
  duration_ms: 0.089623
  type: 'test'
  ...
# Subtest: fetchSmartInboxSuggestions - success
ok 177 - fetchSmartInboxSuggestions - success
  ---
  duration_ms: 0.08179
  type: 'test'
  ...
# Subtest: fetchSmartInboxSuggestions - non-ok status
ok 178 - fetchSmartInboxSuggestions - non-ok status
  ---
  duration_ms: 0.054333
  type: 'test'
  ...
# Subtest: fetchSmartInboxSuggestions - network error
ok 179 - fetchSmartInboxSuggestions - network error
  ---
  duration_ms: 0.306079
  type: 'test'
  ...
1..179
# tests 179
# suites 0
# pass 179
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 455.496047
npm notice
npm notice New major version of npm available! 10.9.8 -> 12.2.0
npm notice Changelog: https://github.com/npm/cli/releases/tag/v12.2.0
npm notice To update run: npm install -g npm@12.2.0
npm notice
exit=0
```
