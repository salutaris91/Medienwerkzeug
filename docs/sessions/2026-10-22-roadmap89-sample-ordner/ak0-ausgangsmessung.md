# AK0 — Ausgangsmessung (Claude Code, 2026-10-22)

Basis: Worktree `fix/roadmap-89-sample-ordner` @ `0105ad0` (Code = `f0a29a4`, nur docs-Commits darüber). Image `openhands-agy-worker:1.2.12`; Kopie per `tar` (Ausschlüsse wie `run_agy_worker_a2.sh`) nach `/tmp/ws`, dort `git init` + Baseline-Commit wie im Worker-Lauf. Start/Ende: 2026-10-22T16:30:01Z – 2026-10-22T16:30:34Z.

Befehl (`test_cmd` aus Briefing Abschnitt 11):

```bash
python3 -m pip install -q --user --break-system-packages -r requirements.txt pytest && python3 -m pytest -q -p no:cacheprovider --deselect tests/test_utils.py::TestMediawerkzeugLogic::test_conversion_estimation_test_encode && npm run test:frontend
```

Ergebnis: pytest `529 passed, 1 deselected, 1 warning`; Frontend `# tests 231 / # pass 231 / # fail 0`; Exit 0.

Wörtliche Ausgabe (Trailing Whitespace entfernt; SHA-256 der Rohdatei im Kit `scripts/gate-a2/logs/2026-10-22-roadmap89-sample-ordner/ak0-output.txt`: `b401a4c72b0976428c46d1307f1d813efcc0835f5868f5f71c09d980b198a83f`):

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

[notice] A new release of pip is available: 26.1.2 -> 26.2.2
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
529 passed, 1 deselected, 1 warning in 27.31s

> medienwerkzeug@1.3.0 test:frontend
> node --test "tests/frontend/**/*.test.js"

TAP version 13
# Subtest: renderHealthStatus - warning state renders warning alert, not success
ok 1 - renderHealthStatus - warning state renders warning alert, not success
  ---
  duration_ms: 1.096246
  type: 'test'
  ...
# Subtest: renderDuplicateStatus - warning state renders warning alert, not success
ok 2 - renderDuplicateStatus - warning state renders warning alert, not success
  ---
  duration_ms: 0.233041
  type: 'test'
  ...
# Subtest: loadNormalizePreview - status 400 shows warning alert, not success
ok 3 - loadNormalizePreview - status 400 shows warning alert, not success
  ---
  duration_ms: 0.148666
  type: 'test'
  ...
# Subtest: renderNormalizePlan - 1 item renders Singular "Vorschlag"
ok 4 - renderNormalizePlan - 1 item renders Singular "Vorschlag"
  ---
  duration_ms: 0.116208
  type: 'test'
  ...
# Subtest: renderNormalizePlan - 2 items renders Plural "Vorschläge"
ok 5 - renderNormalizePlan - 2 items renders Plural "Vorschläge"
  ---
  duration_ms: 0.113458
  type: 'test'
  ...
# Subtest: renderNormalizePlan - empty plan renders neutral empty state without emoji
ok 6 - renderNormalizePlan - empty plan renders neutral empty state without emoji
  ---
  duration_ms: 0.068791
  type: 'test'
  ...
# Subtest: renderQueue - pipeline step message uses existing HTML escaping helper
ok 7 - renderQueue - pipeline step message uses existing HTML escaping helper
  ---
  duration_ms: 0.601122
  type: 'test'
  ...
# Subtest: renderHealthStatus - renders summary chips with total and group counts and no severity grouping
ok 8 - renderHealthStatus - renders summary chips with total and group counts and no severity grouping
  ---
  duration_ms: 11.384289
  type: 'test'
  ...
# Subtest: renderHealthStatus - type grouping renders type groups, checkboxes and tool-connectors
ok 9 - renderHealthStatus - type grouping renders type groups, checkboxes and tool-connectors
  ---
  duration_ms: 0.40154
  type: 'test'
  ...
# Subtest: renderHealthStatus - only nested_duplicate / structure issues displays tab specific empty state on media tab
ok 10 - renderHealthStatus - only nested_duplicate / structure issues displays tab specific empty state on media tab
  ---
  duration_ms: 0.308333
  type: 'test'
  ...
# Subtest: renderHealthStatus - structure-only result wires structure batch button
ok 11 - renderHealthStatus - structure-only result wires structure batch button
  ---
  duration_ms: 0.137958
  type: 'test'
  ...
# Subtest: renderHealthStatus - transition running -> warning clears loading spinner and hides structure container
ok 12 - renderHealthStatus - transition running -> warning clears loading spinner and hides structure container
  ---
  duration_ms: 0.103458
  type: 'test'
  ...
# Subtest: renderNfoAgentFiles - mediaType tvshow renders tvshow.nfo status matrix
ok 13 - renderNfoAgentFiles - mediaType tvshow renders tvshow.nfo status matrix
  ---
  duration_ms: 0.440082
  type: 'test'
  ...
# Subtest: NFO Agent combines the main NFO status with the metadata editor
ok 14 - NFO Agent combines the main NFO status with the metadata editor
  ---
  duration_ms: 0.852664
  type: 'test'
  ...
# Subtest: NFO Agent movie mode renders movie.nfo without series controls
ok 15 - NFO Agent movie mode renders movie.nfo without series controls
  ---
  duration_ms: 0.123708
  type: 'test'
  ...
# Subtest: submitNfoAgentJob - payload structures and write_show_nfo semantics
ok 16 - submitNfoAgentJob - payload structures and write_show_nfo semantics
  ---
  duration_ms: 0.599372
  type: 'test'
  ...
# Subtest: NFO Agent shows a calm non-blocking completeness hint
ok 17 - NFO Agent shows a calm non-blocking completeness hint
  ---
  duration_ms: 0.065833
  type: 'test'
  ...
# Subtest: waitForServerRestart succeeds after a temporary connection failure
ok 18 - waitForServerRestart succeeds after a temporary connection failure
  ---
  duration_ms: 0.114916
  type: 'test'
  ...
# Subtest: waitForServerRestart stops after the configured attempt limit
ok 19 - waitForServerRestart stops after the configured attempt limit
  ---
  duration_ms: 0.078541
  type: 'test'
  ...
# Subtest: restoreServerRestartButton clears the loading state
ok 20 - restoreServerRestartButton clears the loading state
  ---
  duration_ms: 0.038791
  type: 'test'
  ...
# Subtest: Cache-Busting: index.html app.js version matches all ES-module import versions in app.js
ok 21 - Cache-Busting: index.html app.js version matches all ES-module import versions in app.js
  ---
  duration_ms: 7.034223
  type: 'test'
  ...
# Subtest: Cache-Busting: style.css in index.html has a non-empty ?v= version query
ok 22 - Cache-Busting: style.css in index.html has a non-empty ?v= version query
  ---
  duration_ms: 1.147079
  type: 'test'
  ...
# Subtest: Cache-Busting: utilities.css in index.html has a non-empty ?v= version query
ok 23 - Cache-Busting: utilities.css in index.html has a non-empty ?v= version query
  ---
  duration_ms: 0.540164
  type: 'test'
  ...
# Subtest: formatBytes - Nullwert
ok 24 - formatBytes - Nullwert
  ---
  duration_ms: 0.494748
  type: 'test'
  ...
# Subtest: formatBytes - Werte unter 1 KB
ok 25 - formatBytes - Werte unter 1 KB
  ---
  duration_ms: 0.07175
  type: 'test'
  ...
# Subtest: formatBytes - Einheiten und Schwellenwerte
ok 26 - formatBytes - Einheiten und Schwellenwerte
  ---
  duration_ms: 0.094875
  type: 'test'
  ...
# Subtest: formatBytes - Nachkommastellen und Rundung
ok 27 - formatBytes - Nachkommastellen und Rundung
  ---
  duration_ms: 0.059458
  type: 'test'
  ...
# Subtest: osBasename - extracts filename correctly
ok 28 - osBasename - extracts filename correctly
  ---
  duration_ms: 0.436624
  type: 'test'
  ...
# Subtest: formatFskLabel - formats FSK labels correctly
ok 29 - formatFskLabel - formats FSK labels correctly
  ---
  duration_ms: 0.085167
  type: 'test'
  ...
# Subtest: resolveSendPaths - resolves hierarchy properly
ok 30 - resolveSendPaths - resolves hierarchy properly
  ---
  duration_ms: 0.802955
  type: 'test'
  ...
# Subtest: openFskBatchModal - opens modal and sets up state
ok 31 - openFskBatchModal - opens modal and sets up state
  ---
  duration_ms: 0.424165
  type: 'test'
  ...
# Subtest: Scope-Change-Event - triggers new preview fetch
ok 32 - Scope-Change-Event - triggers new preview fetch
  ---
  duration_ms: 23.50541
  type: 'test'
  ...
# Subtest: Null-Ziel-Sperre im DOM
ok 33 - Null-Ziel-Sperre im DOM
  ---
  duration_ms: 22.166998
  type: 'test'
  ...
# Subtest: Apply-Fetch-Payload and preview rendering
ok 34 - Apply-Fetch-Payload and preview rendering
  ---
  duration_ms: 12.654993
  type: 'test'
  ...
# Subtest: Darstellung von partial und failed
ok 35 - Darstellung von partial und failed
  ---
  duration_ms: 20.475339
  type: 'test'
  ...
# Subtest: No native Dialogs and Inline Error Rendering
ok 36 - No native Dialogs and Inline Error Rendering
  ---
  duration_ms: 10.648834
  type: 'test'
  ...
# Subtest: Dynamic Button Text and Disabled State
ok 37 - Dynamic Button Text and Disabled State
  ---
  duration_ms: 22.14479
  type: 'test'
  ...
# Subtest: Apply payload includes status field
ok 38 - Apply payload includes status field
  ---
  duration_ms: 22.998453
  type: 'test'
  ...
# Subtest: show-group-fsk-btn click - triggers openFskBatchModal and fetches series scope
ok 39 - show-group-fsk-btn click - triggers openFskBatchModal and fetches series scope
  ---
  duration_ms: 1.033705
  type: 'test'
  ...
# Subtest: season-group-fsk-btn click - triggers openFskBatchModal and fetches season scope
ok 40 - season-group-fsk-btn click - triggers openFskBatchModal and fetches season scope
  ---
  duration_ms: 0.234041
  type: 'test'
  ...
# Subtest: Out-of-order preview requests are correctly discarded
ok 41 - Out-of-order preview requests are correctly discarded
  ---
  duration_ms: 0.136166
  type: 'test'
  ...
# Subtest: Modal direct scope and prevent dual requests
ok 42 - Modal direct scope and prevent dual requests
  ---
  duration_ms: 0.065375
  type: 'test'
  ...
# Subtest: 409 Conflict keeps error message visible after preview load
ok 43 - 409 Conflict keeps error message visible after preview load
  ---
  duration_ms: 41.190384
  type: 'test'
  ...
# Subtest: Apply-Lock blocks closeFskBatchModal
ok 44 - Apply-Lock blocks closeFskBatchModal
  ---
  duration_ms: 0.131916
  type: 'test'
  ...
# Subtest: Media view routes series, season and episode metadata actions through the NFO Agent
ok 45 - Media view routes series, season and episode metadata actions through the NFO Agent
  ---
  duration_ms: 0.449582
  type: 'test'
  ...
# Subtest: Media summary stays calm and exposes exact actions only in details
ok 46 - Media summary stays calm and exposes exact actions only in details
  ---
  duration_ms: 0.44679
  type: 'test'
  ...
# Subtest: Media view separates season findings from collapsible episode metadata findings
ok 47 - Media view separates season findings from collapsible episode metadata findings
  ---
  duration_ms: 0.191541
  type: 'test'
  ...
# Subtest: Scoped ignore modal lists present issue types grouped by catalog group and posts the exact scope
ok 48 - Scoped ignore modal lists present issue types grouped by catalog group and posts the exact scope
  ---
  duration_ms: 4.054026
  type: 'test'
  ...
# Subtest: Media view separates series and movies into tabs with counts
ok 49 - Media view separates series and movies into tabs with counts
  ---
  duration_ms: 0.135541
  type: 'test'
  ...
# Subtest: Scoped ignore modal is static, explicit, and reversible
ok 50 - Scoped ignore modal is static, explicit, and reversible
  ---
  duration_ms: 0.798955
  type: 'test'
  ...
# Subtest: Media-oriented movie view treats invalid FSK as a metadata problem
ok 51 - Media-oriented movie view treats invalid FSK as a metadata problem
  ---
  duration_ms: 0.130458
  type: 'test'
  ...
# Subtest: Media view does not resurrect an ignored missing series NFO from structural status
ok 52 - Media view does not resurrect an ignored missing series NFO from structural status
  ---
  duration_ms: 0.043541
  type: 'test'
  ...
# Subtest: nfo_missing visibility and action suppression
ok 53 - nfo_missing visibility and action suppression
  ---
  duration_ms: 0.654664
  type: 'test'
  ...
# Subtest: Film-Rendering in FSK Modal uses media_kind
ok 54 - Film-Rendering in FSK Modal uses media_kind
  ---
  duration_ms: 11.26229
  type: 'test'
  ...
# Subtest: Successful apply leaves one terminal action and refreshes health immediately
ok 55 - Successful apply leaves one terminal action and refreshes health immediately
  ---
  duration_ms: 11.558289
  type: 'test'
  ...
# Subtest: NFO-Agent rendered in skipped_missing
ok 56 - NFO-Agent rendered in skipped_missing
  ---
  duration_ms: 13.056617
  type: 'test'
  ...
# Subtest: Fertig-Klick bei ready=0 schliesst Modal
ok 57 - Fertig-Klick bei ready=0 schliesst Modal
  ---
  duration_ms: 24.418489
  type: 'test'
  ...
# Subtest: NFO Agent Lifecycle wertet done, error, cancelled und fehlende Queue-Jobs aus
ok 58 - NFO Agent Lifecycle wertet done, error, cancelled und fehlende Queue-Jobs aus
  ---
  duration_ms: 25.962984
  type: 'test'
  ...
# Error: TMDB-Filmmetadaten konnten nicht geladen werden: timed out
#     at eval (eval at <anonymous> (file:///tmp/ws/tests/frontend/fsk_batch_dom.test.js:236:1), <anonymous>:17472:35)
# Subtest: Escaping-Sicherheit bei NFO-Agent-Event-Delegation
ok 59 - Escaping-Sicherheit bei NFO-Agent-Event-Delegation
  ---
  duration_ms: 12.216536
  type: 'test'
  ...
# Subtest: NFO Agent switches between entry context and whole-series editing
ok 60 - NFO Agent switches between entry context and whole-series editing
  ---
  duration_ms: 0.304874
  type: 'test'
  ...
# Subtest: Submit label reflects the visible episode fields in season mode
ok 61 - Submit label reflects the visible episode fields in season mode
  ---
  duration_ms: 0.159541
  type: 'test'
  ...
# Subtest: Mediathek search result switches to manual entry instead of a TVDB fetch
ok 62 - Mediathek search result switches to manual entry instead of a TVDB fetch
  ---
  duration_ms: 0.065834
  type: 'test'
  ...
# Error: TMDB-Filmmetadaten konnten nicht geladen werden: timed out
#     at eval (eval at <anonymous> (file:///tmp/ws/tests/frontend/fsk_batch_dom.test.js:236:1), <anonymous>:17472:35)
# Subtest: Failed detail loads render an inline retry action instead of an alert
ok 63 - Failed detail loads render an inline retry action instead of an alert
  ---
  duration_ms: 1.686743
  type: 'test'
  ...
# Subtest: NFO Agent hides the back button when whole-series is the entry point
ok 64 - NFO Agent hides the back button when whole-series is the entry point
  ---
  duration_ms: 0.110416
  type: 'test'
  ...
# Subtest: NFO Agent submits manually when no provider ID is given
ok 65 - NFO Agent submits manually when no provider ID is given
  ---
  duration_ms: 0.305207
  type: 'test'
  ...
# Subtest: NFO Agent season mode edits the season without writing the series NFO
ok 66 - NFO Agent season mode edits the season without writing the series NFO
  ---
  duration_ms: 0.223499
  type: 'test'
  ...
# Subtest: NFO Agent episode mode submits only the selected episode
ok 67 - NFO Agent episode mode submits only the selected episode
  ---
  duration_ms: 0.289083
  type: 'test'
  ...
# Subtest: NFO Agent uses concise mode controls and clear missing-source copy
ok 68 - NFO Agent uses concise mode controls and clear missing-source copy
  ---
  duration_ms: 0.871496
  type: 'test'
  ...
# Subtest: Type-oriented episode findings preserve the focused episode context
ok 69 - Type-oriented episode findings preserve the focused episode context
  ---
  duration_ms: 0.218665
  type: 'test'
  ...
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8324:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8324:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8324:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8324:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8324:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8324:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8324:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8324:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8324:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8324:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8324:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8324:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8324:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8324:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8324:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8324:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8324:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error loading dashboard data: Error: Server antwortete mit Code 400
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8302:19)
# Error loading API keys: Error: API keys fetch failed
#     at eval (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8601:40)
# Error loading dashboard data: Error: Server antwortete mit Code 400
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8302:19)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error loading dashboard data: Error: Server antwortete mit Code 400
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8302:19)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8324:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8324:64)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8324:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8324:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8324:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8324:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8324:64)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8324:64)
# Subtest: AK1: Strict SxxExx pattern recognizes Show.S01E01.720p.mkv
ok 70 - AK1: Strict SxxExx pattern recognizes Show.S01E01.720p.mkv
  ---
  duration_ms: 28.234309
  type: 'test'
  ...
# Subtest: AK1: Strict SxxExx pattern does NOT recognize Movie.1920x1080.x264.mkv, The Rock (1996).mkv, Show.1x05.mkv, Staffel 2 Folge 3 – Show.mkv
ok 71 - AK1: Strict SxxExx pattern does NOT recognize Movie.1920x1080.x264.mkv, The Rock (1996).mkv, Show.1x05.mkv, Staffel 2 Folge 3 – Show.mkv
  ---
  duration_ms: 18.752136
  type: 'test'
  ...
# Subtest: AK2: Empty suggested_query and folder entries (is_dir: true) are never automatically grouped
ok 72 - AK2: Empty suggested_query and folder entries (is_dir: true) are never automatically grouped
  ---
  duration_ms: 8.977924
  type: 'test'
  ...
# Subtest: AK2: Groups require >= 2 matches and group pseudo-entry aggregates modified_at (max) and total_size (sum)
ok 73 - AK2: Groups require >= 2 matches and group pseudo-entry aggregates modified_at (max) and total_size (sum)
  ---
  duration_ms: 5.204772
  type: 'test'
  ...
# Subtest: AK2: Group pseudo-entry participates in sortInboxSuggestions
ok 74 - AK2: Group pseudo-entry participates in sortInboxSuggestions
  ---
  duration_ms: 11.33179
  type: 'test'
  ...
# Subtest: AK3: Group banner appears above sort bar and grouping is only applied after confirmation click
ok 75 - AK3: Group banner appears above sort bar and grouping is only applied after confirmation click
  ---
  duration_ms: 12.875784
  type: 'test'
  ...
# Subtest: AK3: Banner "Ignorieren" saves to localStorage and keeps banner visible with restore counter
ok 76 - AK3: Banner "Ignorieren" saves to localStorage and keeps banner visible with restore counter
  ---
  duration_ms: 9.270673
  type: 'test'
  ...
# Subtest: AK3 & AK13: Film entries show lock notice and "Als Serie / Folge behandeln" link
ok 77 - AK3 & AK13: Film entries show lock notice and "Als Serie / Folge behandeln" link
  ---
  duration_ms: 4.941731
  type: 'test'
  ...
# Subtest: AK13: Film exception works per entry, makes entry checkable, does not auto-group, and passes relative path
ok 78 - AK13: Film exception works per entry, makes entry checkable, does not auto-group, and passes relative path
  ---
  duration_ms: 12.57441
  type: 'test'
  ...
# Subtest: AK13: Unlocked movie that isProcessing has checkbox disabled
ok 79 - AK13: Unlocked movie that isProcessing has checkbox disabled
  ---
  duration_ms: 6.162601
  type: 'test'
  ...
# Subtest: AK12: Checkboxes only appear on valid candidates (tv single files), not on folders, dokus, or processing
ok 80 - AK12: Checkboxes only appear on valid candidates (tv single files), not on folders, dokus, or processing
  ---
  duration_ms: 7.135347
  type: 'test'
  ...
# Subtest: AK12: Selection state in Set persists across re-render and sort change, idempotent against duplicates
ok 81 - AK12: Selection state in Set persists across re-render and sort change, idempotent against duplicates
  ---
  duration_ms: 15.851106
  type: 'test'
  ...
# Subtest: AK12: Bulk actions bar displays count, "Auswahl aufheben" resets, and group button transfers selection
ok 82 - AK12: Bulk actions bar displays count, "Auswahl aufheben" resets, and group button transfers selection
  ---
  duration_ms: 4.705565
  type: 'test'
  ...
# Subtest: AK11: Group row has own class, data-group-key, NO data-project, NO quarantine button
ok 83 - AK11: Group row has own class, data-group-key, NO data-project, NO quarantine button
  ---
  duration_ms: 3.632236
  type: 'test'
  ...
# Subtest: AK11: Sentinel values ("" and "__inbox_recursive__") are never automatically grouped
ok 84 - AK11: Sentinel values ("" and "__inbox_recursive__") are never automatically grouped
  ---
  duration_ms: 5.786812
  type: 'test'
  ...
# Subtest: H2 (B2/AK4): Productive series workflow handover via executeSeriesWorkflow creates request body with files + mappings + media_type "tv", mappings-Schlüssel ⊆ files, and correctly escaped quotes in data-file
ok 85 - H2 (B2/AK4): Productive series workflow handover via executeSeriesWorkflow creates request body with files + mappings + media_type "tv", mappings-Schlüssel ⊆ files, and correctly escaped quotes in data-file
  ---
  duration_ms: 6.558642
  type: 'test'
  ...
# Subtest: H1 (B1): Matching matrix includes all 10 video extensions (.ts, .m2ts, etc.) matching server GROUP_VIDEO_EXTENSIONS
ok 86 - H1 (B1): Matching matrix includes all 10 video extensions (.ts, .m2ts, etc.) matching server GROUP_VIDEO_EXTENSIONS
  ---
  duration_ms: 7.737512
  type: 'test'
  ...
# Subtest: H3 (B3): Group row expanded state persists across 6-second re-render (renderSmartInboxList)
ok 87 - H3 (B3): Group row expanded state persists across 6-second re-render (renderSmartInboxList)
  ---
  duration_ms: 6.073351
  type: 'test'
  ...
# Subtest: H4 (B4): /preview_process HTTP 400 response body (error/message) is visibly displayed
ok 88 - H4 (B4): /preview_process HTTP 400 response body (error/message) is visibly displayed
  ---
  duration_ms: 4.224109
  type: 'test'
  ...
# Subtest: H4 (B4): /process HTTP 400 response body (error/message) is visibly displayed in console and alert
ok 89 - H4 (B4): /process HTTP 400 response body (error/message) is visibly displayed in console and alert
  ---
  duration_ms: 4.998273
  type: 'test'
  ...
# Subtest: F1: nach Klick auf Gruppenzeilen-Knopf, Sammelknopf und Banner ist view-folder sichtbar (nicht hidden), die Startseiten-Ansicht ausgeblendet und mode-series aktiv
ok 90 - F1: nach Klick auf Gruppenzeilen-Knopf, Sammelknopf und Banner ist view-folder sichtbar (nicht hidden), die Startseiten-Ansicht ausgeblendet und mode-series aktiv
  ---
  duration_ms: 6.972181
  type: 'test'
  ...
# Subtest: F2: Beschriftungen - Gruppenzeile "Alle verarbeiten", Banner "Als Serie gruppieren", Sammelknopf "Ausgewählte als Serie verarbeiten", gesperrte Filme "Als Serie / Folge behandeln"
ok 91 - F2: Beschriftungen - Gruppenzeile "Alle verarbeiten", Banner "Als Serie gruppieren", Sammelknopf "Ausgewählte als Serie verarbeiten", gesperrte Filme "Als Serie / Folge behandeln"
  ---
  duration_ms: 5.857144
  type: 'test'
  ...
# Subtest: 1: Vorschau-Fenster: Dateiname mit " (und mit < >) bleibt vom Rendern bis in explicit_renames/explicit_subs des /process-Requests vollständig erhalten; kein HTML wird eingeschleust
ok 92 - 1: Vorschau-Fenster: Dateiname mit " (und mit < >) bleibt vom Rendern bis in explicit_renames/explicit_subs des /process-Requests vollständig erhalten; kein HTML wird eingeschleust
  ---
  duration_ms: 5.154564
  type: 'test'
  ...
# Subtest: 2: Doppelstart-Schutz: zwei schnelle Klicks auf Ausführen -> genau ein /process-Request
ok 93 - 2: Doppelstart-Schutz: zwei schnelle Klicks auf Ausführen -> genau ein /process-Request
  ---
  duration_ms: 5.127814
  type: 'test'
  ...
# Subtest: 2: Doppelstart-Schutz: bei Fehler im /process-Request wird der Ausführen-Knopf wieder aktiv
ok 94 - 2: Doppelstart-Schutz: bei Fehler im /process-Request wird der Ausführen-Knopf wieder aktiv
  ---
  duration_ms: 5.030856
  type: 'test'
  ...
# Subtest: 2: Doppelstart-Schutz: Banner-Knopf, Gruppenzeilen-Knopf und Sammelknopf werden beim ersten Klick deaktiviert und zeigen "wird gestartet…"
ok 95 - 2: Doppelstart-Schutz: Banner-Knopf, Gruppenzeilen-Knopf und Sammelknopf werden beim ersten Klick deaktiviert und zeigen "wird gestartet…"
  ---
  duration_ms: 4.067193
  type: 'test'
  ...
# Subtest: 3(b): Gruppenname bei manueller Auswahl = gemeinsamer Namensanfang ohne Folgenkennung und ohne Trennzeichen am Ende; Fallback wie bisher
ok 96 - 3(b): Gruppenname bei manueller Auswahl = gemeinsamer Namensanfang ohne Folgenkennung und ohne Trennzeichen am Ende; Fallback wie bisher
  ---
  duration_ms: 3.151363
  type: 'test'
  ...
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8324:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8324:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8324:64)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8324:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8324:64)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8324:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_group.test.js:632:5), <anonymous>:8324:64)
# Subtest: 4: Name in der Warteschlange: im manuellen Serien-Modus im Gruppen-Ablauf den Gruppennamen ohne Zusatz ("Testserie") verwenden, /process-Request enthält genau Gruppennamen
ok 97 - 4: Name in der Warteschlange: im manuellen Serien-Modus im Gruppen-Ablauf den Gruppennamen ohne Zusatz ("Testserie") verwenden, /process-Request enthält genau Gruppennamen
  ---
  duration_ms: 14.456153
  type: 'test'
  ...
# Subtest: 5: Warteschlangen-Prüfung: laufender Gruppen-Job mit anderen Dateien blockiert nicht, mit überschneidenden Dateien blockiert; normale Projekte unverändert
ok 98 - 5: Warteschlangen-Prüfung: laufender Gruppen-Job mit anderen Dateien blockiert nicht, mit überschneidenden Dateien blockiert; normale Projekte unverändert
  ---
  duration_ms: 5.152147
  type: 'test'
  ...
# Subtest: AK1: Pattern (a) in extractStrictSeasonEpisode handles all AK1a-f cases
ok 99 - AK1: Pattern (a) in extractStrictSeasonEpisode handles all AK1a-f cases
  ---
  duration_ms: 4.088776
  type: 'test'
  ...
# Subtest: AK4: Folder grouping, mixed groups, and fallback key extraction (AK4a-e)
ok 100 - AK4: Folder grouping, mixed groups, and fallback key extraction (AK4a-e)
  ---
  duration_ms: 3.165738
  type: 'test'
  ...
# Subtest: AK5: Checkbox, delegation via inboxFilesEntryForItem, and bulk group name (AK5a-e)
ok 101 - AK5: Checkbox, delegation via inboxFilesEntryForItem, and bulk group name (AK5a-e)
  ---
  duration_ms: 4.77194
  type: 'test'
  ...
# Subtest: Follow-up (a): Single-video folder row has title with relpath, loose files and multi-video folders do not
ok 102 - Follow-up (a): Single-video folder row has title with relpath, loose files and multi-video folders do not
  ---
  duration_ms: 2.954489
  type: 'test'
  ...
# Subtest: Follow-up (b): Manual matching row for "XyzS01E01/Xyz.Show.S01E01.Titel.mkv" has title prefill without "Xyz - " and data-file = full relpath
ok 103 - Follow-up (b): Manual matching row for "XyzS01E01/Xyz.Show.S01E01.Titel.mkv" has title prefill without "Xyz - " and data-file = full relpath
  ---
  duration_ms: 5.632395
  type: 'test'
  ...
# Subtest: Follow-up (c): Preselection for "Foo.S01E99/Real.Show.S02E05.mkv" results in S02E05
ok 104 - Follow-up (c): Preselection for "Foo.S01E99/Real.Show.S02E05.mkv" results in S02E05
  ---
  duration_ms: 3.337904
  type: 'test'
  ...
# Subtest: Follow-up (d): style.css contains position: sticky for \#smart-inbox-bulk-actions
ok 105 - Follow-up (d): style.css contains position: sticky for \#smart-inbox-bulk-actions
  ---
  duration_ms: 0.259457
  type: 'test'
  ...
# Subtest: AK1: Drei erkannte Gruppen A, B, C -> A prominent in Zone 1, B und C unter "Weitere Vorschläge (2)" erreichbar; bei nur einer Gruppe kein "Weitere Vorschläge"-Bereich
ok 106 - AK1: Drei erkannte Gruppen A, B, C -> A prominent in Zone 1, B und C unter "Weitere Vorschläge (2)" erreichbar; bei nur einer Gruppe kein "Weitere Vorschläge"-Bereich
  ---
  duration_ms: 33.484497
  type: 'test'
  ...
# Subtest: AK2: "Ignorieren" bei nicht-prominentem Vorschlag B schreibt JSON in localStorage, entfernt B aus offenen Vorschlägen und zeigt "Ausgeblendete Vorschläge (1)"
ok 107 - AK2: "Ignorieren" bei nicht-prominentem Vorschlag B schreibt JSON in localStorage, entfernt B aus offenen Vorschlägen und zeigt "Ausgeblendete Vorschläge (1)"
  ---
  duration_ms: 25.527402
  type: 'test'
  ...
# Subtest: AK3: Ignorierter Vorschlag bleibt nach zweitem eval mit frischem Modulzustand bei gleichem localStorage ausgeblendet
ok 108 - AK3: Ignorierter Vorschlag bleibt nach zweitem eval mit frischem Modulzustand bei gleichem localStorage ausgeblendet
  ---
  duration_ms: 20.785129
  type: 'test'
  ...
# Subtest: AK4: "Wieder anzeigen" entfernt einzelnen Schlüssel und stellt Vorschlag wieder her; "Alle wieder anzeigen" stellt alle aktuell erkannten Gruppen wieder her
ok 109 - AK4: "Wieder anzeigen" entfernt einzelnen Schlüssel und stellt Vorschlag wieder her; "Alle wieder anzeigen" stellt alle aktuell erkannten Gruppen wieder her
  ---
  duration_ms: 15.037401
  type: 'test'
  ...
# Subtest: AK5: Verwaister Schlüssel smart-inbox-ignore-group-GHOST zählt nicht, wird nicht gelistet und von "Alle wieder anzeigen" nicht entfernt
ok 110 - AK5: Verwaister Schlüssel smart-inbox-ignore-group-GHOST zählt nicht, wird nicht gelistet und von "Alle wieder anzeigen" nicht entfernt
  ---
  duration_ms: 11.795788
  type: 'test'
  ...
# Subtest: AK6: Nach Ignorieren aller Gruppen bleibt Banner sichtbar (nur Rückweg-Zone); bei null erkannten Gruppen ist Banner ausgeblendet und leer
ok 111 - AK6: Nach Ignorieren aller Gruppen bleibt Banner sichtbar (nur Rückweg-Zone); bei null erkannten Gruppen ist Banner ausgeblendet und leer
  ---
  duration_ms: 7.323305
  type: 'test'
  ...
# Subtest: AK7: Vorab gesetzter sessionStorage-Schlüssel blendet Vorschlag nicht aus; Ignorier-Pfad liest und schreibt kein sessionStorage
ok 112 - AK7: Vorab gesetzter sessionStorage-Schlüssel blendet Vorschlag nicht aus; Ignorier-Pfad liest und schreibt kein sessionStorage
  ---
  duration_ms: 7.595179
  type: 'test'
  ...
# Subtest: AK8: Gruppenname mit ", ', < und & funktioniert im strengen Selektor-Mock ohne SyntaxError (Anzeige escaped, Apply, Ignorieren, Zähler, Wiederanzeigen)
ok 113 - AK8: Gruppenname mit ", ', < und & funktioniert im strengen Selektor-Mock ohne SyntaxError (Anzeige escaped, Apply, Ignorieren, Zähler, Wiederanzeigen)
  ---
  duration_ms: 10.184127
  type: 'test'
  ...
# Subtest: AK9: Synchroner Wurf beim Start (via triggerQualityHintUpdates-Stub) nimmt appliedInboxGroups zurück, zeigt Inline-Meldung, ruft console.error und lässt Gruppe offen
ok 114 - AK9: Synchroner Wurf beim Start (via triggerQualityHintUpdates-Stub) nimmt appliedInboxGroups zurück, zeigt Inline-Meldung, ruft console.error und lässt Gruppe offen
  ---
  duration_ms: 8.401509
  type: 'test'
  ...
# Subtest: AK9 (F1-Zusatztest): Suchfehler nach Apply (fetch {ok:false} für /api/search) lässt Gruppe angewendet, zeigt keine Banner-Meldung und zeigt "Suchfehler" im Suchbereich
ok 115 - AK9 (F1-Zusatztest): Suchfehler nach Apply (fetch {ok:false} für /api/search) lässt Gruppe angewendet, zeigt keine Banner-Meldung und zeigt "Suchfehler" im Suchbereich
  ---
  duration_ms: 7.797178
  type: 'test'
  ...
# Subtest: AK9 (Apply-Sperre): Zweiter Apply-Klick während laufendem Start löst keinen zweiten Workflow aus (groupWorkflowRunning)
ok 116 - AK9 (Apply-Sperre): Zweiter Apply-Klick während laufendem Start löst keinen zweiten Workflow aus (groupWorkflowRunning)
  ---
  duration_ms: 7.832762
  type: 'test'
  ...
# Subtest: AK10: Werfendes localStorage crasht nicht, blendet Gruppe per In-Memory-Fallback für die Sitzung aus und protokolliert den Speicherfehler
ok 117 - AK10: Werfendes localStorage crasht nicht, blendet Gruppe per In-Memory-Fallback für die Sitzung aus und protokolliert den Speicherfehler
  ---
  duration_ms: 12.563743
  type: 'test'
  ...
# Subtest: AK15: Nach gescheitertem Start, "Ignorieren" und "Wieder anzeigen" (einzeln sowie "Alle wieder anzeigen") steht keine Fehlermeldung mehr im Banner
ok 118 - AK15: Nach gescheitertem Start, "Ignorieren" und "Wieder anzeigen" (einzeln sowie "Alle wieder anzeigen") steht keine Fehlermeldung mehr im Banner
  ---
  duration_ms: 15.037443
  type: 'test'
  ...
# Subtest: AK16: Bei localStorage === undefined blendet "Ignorieren" die Gruppe für die Sitzung aus und ruft console.warn auf
ok 119 - AK16: Bei localStorage === undefined blendet "Ignorieren" die Gruppe für die Sitzung aus und ruft console.warn auf
  ---
  duration_ms: 7.057681
  type: 'test'
  ...
# Subtest: AK17: Aufklapp-Zustand von "Weitere Vorschläge" und "Ausgeblendete Vorschläge" bleibt bei erneutem renderSmartInboxList erhalten (Auf- und Zuklappen) und startet bei frischem Modulzustand (zweiter eval) eingeklappt
ok 120 - AK17: Aufklapp-Zustand von "Weitere Vorschläge" und "Ausgeblendete Vorschläge" bleibt bei erneutem renderSmartInboxList erhalten (Auf- und Zuklappen) und startet bei frischem Modulzustand (zweiter eval) eingeklappt
  ---
  duration_ms: 17.121934
  type: 'test'
  ...
# Subtest: E1-AK1: Gruppenzeile mit >= 2 Staffeln trägt genau einen Knopf pro Staffel ("Staffel N (k)", aufsteigend); Einzelstaffel-Gruppe hat KEINE Staffel-Knopf-Reihe; Alle-Knopf heißt "Alle verarbeiten"
ok 121 - E1-AK1: Gruppenzeile mit >= 2 Staffeln trägt genau einen Knopf pro Staffel ("Staffel N (k)", aufsteigend); Einzelstaffel-Gruppe hat KEINE Staffel-Knopf-Reihe; Alle-Knopf heißt "Alle verarbeiten"
  ---
  duration_ms: 27.64002
  type: 'test'
  ...
# Subtest: E1-AK2: Klick auf "Staffel 11 (3)" übergibt startSeriesGroupWorkflow genau die Folgen dieser Staffel in Folgenreihenfolge (Ordner-Folge über single_video_relpath) und wechselt die Ansicht
ok 122 - E1-AK2: Klick auf "Staffel 11 (3)" übergibt startSeriesGroupWorkflow genau die Folgen dieser Staffel in Folgenreihenfolge (Ordner-Folge über single_video_relpath) und wechselt die Ansicht
  ---
  duration_ms: 24.681281
  type: 'test'
  ...
# Subtest: E1-AK3: Klick auf "Alle verarbeiten" übergibt alle Folgen der Gruppe in Staffel-/Folgenreihenfolge und startet den Workflow
ok 123 - E1-AK3: Klick auf "Alle verarbeiten" übergibt alle Folgen der Gruppe in Staffel-/Folgenreihenfolge und startet den Workflow
  ---
  duration_ms: 9.123216
  type: 'test'
  ...
# Subtest: E1-AK4: Nach erneutem renderSmartInboxList (6-s-Takt) existieren Staffel-Knöpfe und Alle-Knopf erneut und starten korrekt
ok 124 - E1-AK4: Nach erneutem renderSmartInboxList (6-s-Takt) existieren Staffel-Knöpfe und Alle-Knopf erneut und starten korrekt
  ---
  duration_ms: 11.344957
  type: 'test'
  ...
# Subtest: E1-AK5: Gruppenname mit ", ', < und & im strengen validateSelector-Mock: maskiert angezeigt, Staffel-Reihe gerendert, Staffel-Klick und Alle-Klick ohne Wurf
ok 125 - E1-AK5: Gruppenname mit ", ', < und & im strengen validateSelector-Mock: maskiert angezeigt, Staffel-Reihe gerendert, Staffel-Klick und Alle-Klick ohne Wurf
  ---
  duration_ms: 8.036136
  type: 'test'
  ...
# Subtest: E1-AK6: Banner bei >= 2 Staffeln zeigt Hinweiszeile und gruppiert bei Klick nur (kein Workflow-Start); bei 1 Staffel keine Hinweiszeile und Sofortstart inkl. Fehlerpfad
ok 126 - E1-AK6: Banner bei >= 2 Staffeln zeigt Hinweiszeile und gruppiert bei Klick nur (kein Workflow-Start); bei 1 Staffel keine Hinweiszeile und Sofortstart inkl. Fehlerpfad
  ---
  duration_ms: 8.758508
  type: 'test'
  ...
# Subtest: E1-AK7: Gemeinsame Sperre weist Zweitstarts von allen vier Startstellen (Banner-Apply, Alle-Knopf, Staffel-Knopf, Bulk-Leiste) still ab
ok 127 - E1-AK7: Gemeinsame Sperre weist Zweitstarts von allen vier Startstellen (Banner-Apply, Alle-Knopf, Staffel-Knopf, Bulk-Leiste) still ab
  ---
  duration_ms: 29.180097
  type: 'test'
  ...
# Subtest: E1-AK8: Nach erfolgreichem Abschluss des ersten Starts ist die Sperre frei (weiterer Start läuft) und Staffel-/Alle-Knöpfe sind nach Neuaufbau wieder aktiv
ok 128 - E1-AK8: Nach erfolgreichem Abschluss des ersten Starts ist die Sperre frei (weiterer Start läuft) und Staffel-/Alle-Knöpfe sind nach Neuaufbau wieder aktiv
  ---
  duration_ms: 13.916821
  type: 'test'
  ...
# Subtest: E2-AK1: Erzwungener Start-Fehler aus dem Alle-Knopf zeigt sichtbare Inline-Meldung in der betroffenen Gruppenzeile, ruft console.error auf, hält Knopf nach Neuaufbau benutzbar und gibt die Sperre frei
ok 129 - E2-AK1: Erzwungener Start-Fehler aus dem Alle-Knopf zeigt sichtbare Inline-Meldung in der betroffenen Gruppenzeile, ruft console.error auf, hält Knopf nach Neuaufbau benutzbar und gibt die Sperre frei
  ---
  duration_ms: 11.156123
  type: 'test'
  ...
# Subtest: E2-AK2: Erzwungener Start-Fehler aus einem Staffel-Knopf zeigt Meldung in derselben Gruppenzeile, ruft console.error auf, gibt Sperre frei und lässt appliedInboxGroups unverändert
ok 130 - E2-AK2: Erzwungener Start-Fehler aus einem Staffel-Knopf zeigt Meldung in derselben Gruppenzeile, ruft console.error auf, gibt Sperre frei und lässt appliedInboxGroups unverändert
  ---
  duration_ms: 7.945844
  type: 'test'
  ...
# Subtest: E2-AK3: Erzwungener Start-Fehler aus der Bulk-Leiste zeigt Inline-Meldung (width: 100% zwischen Info und Buttons, kein alert()), ruft console.error auf, hält Knopf benutzbar und gibt Sperre frei
ok 131 - E2-AK3: Erzwungener Start-Fehler aus der Bulk-Leiste zeigt Inline-Meldung (width: 100% zwischen Info und Buttons, kein alert()), ruft console.error auf, hält Knopf benutzbar und gibt Sperre frei
  ---
  duration_ms: 8.432468
  type: 'test'
  ...
# Subtest: E2-AK4: Fehlermeldungen in Gruppenzeile (Alle-Knopf / Staffel-Knopf) und Bulk-Leiste überleben erneutes renderSmartInboxList und updateBulkActionsBarUI
ok 132 - E2-AK4: Fehlermeldungen in Gruppenzeile (Alle-Knopf / Staffel-Knopf) und Bulk-Leiste überleben erneutes renderSmartInboxList und updateBulkActionsBarUI
  ---
  duration_ms: 6.428934
  type: 'test'
  ...
# Subtest: E2-AK5: Erfolgreicher Start derselben Stelle löscht die Fehlermeldung (jeder Startknopf derselben Gruppenzeile bzw. nächste erfolgreiche Bulk-Verarbeitung); "Auswahl aufheben" und Verschwinden der Leiste löschen die Bulk-Meldung
ok 133 - E2-AK5: Erfolgreicher Start derselben Stelle löscht die Fehlermeldung (jeder Startknopf derselben Gruppenzeile bzw. nächste erfolgreiche Bulk-Verarbeitung); "Auswahl aufheben" und Verschwinden der Leiste löschen die Bulk-Meldung
  ---
  duration_ms: 12.92345
  type: 'test'
  ...
# Subtest: E2-AK6: selectedInboxProjects, Zähler und Checkboxen bleiben nach einem Start-Fehler aus der Bulk-Leiste unverändert gesetzt, während die Inline-Fehlermeldung angezeigt wird
ok 134 - E2-AK6: selectedInboxProjects, Zähler und Checkboxen bleiben nach einem Start-Fehler aus der Bulk-Leiste unverändert gesetzt, während die Inline-Fehlermeldung angezeigt wird
  ---
  duration_ms: 8.756133
  type: 'test'
  ...
# Subtest: E2-AK7: Bestehende alert()-Pfade im Bulk-Handler bleiben unverändert und Staffel-/Alle-/Bulk-Fehlerpfade ändern appliedInboxGroups niemals
ok 135 - E2-AK7: Bestehende alert()-Pfade im Bulk-Handler bleiben unverändert und Staffel-/Alle-/Bulk-Fehlerpfade ändern appliedInboxGroups niemals
  ---
  duration_ms: 8.795466
  type: 'test'
  ...
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:656:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:656:5), <anonymous>:2292:9)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:656:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:656:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:656:5), <anonymous>:8324:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:656:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:656:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:656:5), <anonymous>:8324:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:656:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:656:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:656:5), <anonymous>:8324:64)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:656:5), <anonymous>:8324:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:656:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:656:5), <anonymous>:2292:9)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:656:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:656:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:656:5), <anonymous>:8324:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:656:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:656:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:656:5), <anonymous>:8324:64)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:656:5), <anonymous>:8324:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:656:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:656:5), <anonymous>:2292:9)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:656:5), <anonymous>:2323:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:656:5), <anonymous>:2292:9)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:656:5), <anonymous>:8324:64)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/inbox_selection.test.js:656:5), <anonymous>:8324:64)
# Subtest: AK1: Neuzeichnen mit Liste ohne B entfernt B aus selectedInboxProjects und aktualisiert Zähler auf "1 ausgewählt"
ok 136 - AK1: Neuzeichnen mit Liste ohne B entfernt B aus selectedInboxProjects und aktualisiert Zähler auf "1 ausgewählt"
  ---
  duration_ms: 21.415585
  type: 'test'
  ...
# Subtest: AK2: Neuzeichnen mit B in processingSet entfernt B aus Auswahl und B's Kästchen ist nicht checked
ok 137 - AK2: Neuzeichnen mit B in processingSet entfernt B aus Auswahl und B's Kästchen ist nicht checked
  ---
  duration_ms: 28.364558
  type: 'test'
  ...
# Subtest: AK3: Wenn alle ausgewählten Einträge verschwunden sind, ist die Auswahl nach Neuzeichnen leer und die Bulk-Leiste ausgeblendet
ok 138 - AK3: Wenn alle ausgewählten Einträge verschwunden sind, ist die Auswahl nach Neuzeichnen leer und die Bulk-Leiste ausgeblendet
  ---
  duration_ms: 9.024882
  type: 'test'
  ...
# Subtest: AK4: Bulk-Klick mit {A, X} ohne Treffer für X: nur A wird an Workflow übergeben, 1 übersprungener Eintrag per Alert gemeldet, X nicht mehr ausgewählt
ok 139 - AK4: Bulk-Klick mit {A, X} ohne Treffer für X: nur A wird an Workflow übergeben, 1 übersprungener Eintrag per Alert gemeldet, X nicht mehr ausgewählt
  ---
  duration_ms: 12.435952
  type: 'test'
  ...
# Subtest: AK5: Bulk-Klick wenn alle Einträge ohne Treffer sind: startSeriesGroupWorkflow wird nicht aufgerufen, Meldung erscheint, Knopf wieder aktiv
ok 140 - AK5: Bulk-Klick wenn alle Einträge ohne Treffer sind: startSeriesGroupWorkflow wird nicht aufgerufen, Meldung erscheint, Knopf wieder aktiv
  ---
  duration_ms: 7.043932
  type: 'test'
  ...
# Subtest: AK5: Bulk-Klick wenn alle Einträge in Verarbeitung sind: startSeriesGroupWorkflow wird nicht aufgerufen, Meldung erscheint, Knopf wieder aktiv
ok 141 - AK5: Bulk-Klick wenn alle Einträge in Verarbeitung sind: startSeriesGroupWorkflow wird nicht aufgerufen, Meldung erscheint, Knopf wieder aktiv
  ---
  duration_ms: 4.531983
  type: 'test'
  ...
# Subtest: AK6: Gültige Auswahl aus TV-Einzeldatei und Einzelvideo-Ordner (single_video_relpath) ruft startSeriesGroupWorkflow mit korrekten files auf, keine Meldung
ok 142 - AK6: Gültige Auswahl aus TV-Einzeldatei und Einzelvideo-Ordner (single_video_relpath) ruft startSeriesGroupWorkflow mit korrekten files auf, keine Meldung
  ---
  duration_ms: 7.872304
  type: 'test'
  ...
# Subtest: R1(c): Auswählbarkeit - Nicht auswählbare Einträge (gesperrter Film, Multi-Video-Ordner) werden beim Neuzeichnen entfernt
ok 143 - R1(c): Auswählbarkeit - Nicht auswählbare Einträge (gesperrter Film, Multi-Video-Ordner) werden beim Neuzeichnen entfernt
  ---
  duration_ms: 5.044648
  type: 'test'
  ...
# Subtest: AK9: Bulk-Klick mit {A, Show "X".mkv} ohne Treffer für den zweiten: maskiert/sicher gegen SyntaxError, nur A geht an Workflow, Meldung "1 Eintrag ...", Show "X".mkv abgewählt und Kästchen unchecked
ok 144 - AK9: Bulk-Klick mit {A, Show "X".mkv} ohne Treffer für den zweiten: maskiert/sicher gegen SyntaxError, nur A geht an Workflow, Meldung "1 Eintrag ...", Show "X".mkv abgewählt und Kästchen unchecked
  ---
  duration_ms: 16.591687
  type: 'test'
  ...
# Subtest: AK10: gui/static/app.js enthält weder setCurrentSmartInboxRawSuggestions noch getCurrentSmartInboxRawSuggestions
ok 145 - AK10: gui/static/app.js enthält weder setCurrentSmartInboxRawSuggestions noch getCurrentSmartInboxRawSuggestions
  ---
  duration_ms: 1.824118
  type: 'test'
  ...
# Could not read inbox sort state from sessionStorage: SyntaxError: Expected property name or '}' in JSON at position 2 (line 1 column 3)
#     at JSON.parse (<anonymous>)
#     at getInboxSortState (eval at setupEnvironment (file:///tmp/ws/tests/frontend/inbox_sort.test.js:220:5), <anonymous>:12449:37)
#     at TestContext.<anonymous> (file:///tmp/ws/tests/frontend/inbox_sort.test.js:415:30)
#     at Test.runInAsyncScope (node:async_hooks:214:14)
#     at Test.run (node:internal/test_runner/test:1047:25)
#     at Test.processPendingSubtests (node:internal/test_runner/test:744:18)
#     at Test.postRun (node:internal/test_runner/test:1173:19)
#     at Test.run (node:internal/test_runner/test:1101:12)
#     at async Test.processPendingSubtests (node:internal/test_runner/test:744:7)
# Subtest: AK3: sortInboxSuggestions sorts by name using German numeric/base localeCompare
ok 146 - AK3: sortInboxSuggestions sorts by name using German numeric/base localeCompare
  ---
  duration_ms: 14.085696
  type: 'test'
  ...
# Subtest: AK3: sortInboxSuggestions sorts by date (modified_at) and places null at the end for BOTH asc and desc
ok 147 - AK3: sortInboxSuggestions sorts by date (modified_at) and places null at the end for BOTH asc and desc
  ---
  duration_ms: 7.648013
  type: 'test'
  ...
# Subtest: AK3: sortInboxSuggestions sorts by size (total_size) and places null at the end for BOTH directions
ok 148 - AK3: sortInboxSuggestions sorts by size (total_size) and places null at the end for BOTH directions
  ---
  duration_ms: 2.300782
  type: 'test'
  ...
# Subtest: AK3: sortInboxSuggestions resolves ties deterministically by project name
ok 149 - AK3: sortInboxSuggestions resolves ties deterministically by project name
  ---
  duration_ms: 2.549115
  type: 'test'
  ...
# Subtest: AK4 & AK7: Default sort state without sessionStorage is date desc
ok 150 - AK4 & AK7: Default sort state without sessionStorage is date desc
  ---
  duration_ms: 2.770823
  type: 'test'
  ...
# Subtest: AK4: index.html contains \#smart-inbox-sort-bar with Name, Datum, Größe buttons
ok 151 - AK4: index.html contains \#smart-inbox-sort-bar with Name, Datum, Größe buttons
  ---
  duration_ms: 0.651789
  type: 'test'
  ...
# Subtest: AK4: Clicking inactive sort button activates it (asc), clicking active toggles asc<->desc
ok 152 - AK4: Clicking inactive sort button activates it (asc), clicking active toggles asc<->desc
  ---
  duration_ms: 7.591013
  type: 'test'
  ...
# Subtest: AK4: Sort bar is hidden when suggestions list is empty
ok 153 - AK4: Sort bar is hidden when suggestions list is empty
  ---
  duration_ms: 2.375325
  type: 'test'
  ...
# Subtest: AK5: Sort choice is persisted in sessionStorage and applied across renders
ok 154 - AK5: Sort choice is persisted in sessionStorage and applied across renders
  ---
  duration_ms: 2.66224
  type: 'test'
  ...
# Subtest: AK5: getInboxSortState handles corrupted sessionStorage defensively
ok 155 - AK5: getInboxSortState handles corrupted sessionStorage defensively
  ---
  duration_ms: 4.630733
  type: 'test'
  ...
# Subtest: AK6: Meta line formats video_count, size, and German date with separator
ok 156 - AK6: Meta line formats video_count, size, and German date with separator
  ---
  duration_ms: 2.437949
  type: 'test'
  ...
# Subtest: AK6: Meta line cleanly omits null/missing size or date without empty delimiters
ok 157 - AK6: Meta line cleanly omits null/missing size or date without empty delimiters
  ---
  duration_ms: 2.071409
  type: 'test'
  ...
# Subtest: updateHintElement - recInfo is null
ok 158 - updateHintElement - recInfo is null
  ---
  duration_ms: 0.420249
  type: 'test'
  ...
# Subtest: updateHintElement - recInfo is undefined
ok 159 - updateHintElement - recInfo is undefined
  ---
  duration_ms: 0.065333
  type: 'test'
  ...
# Subtest: updateHintElement - currentVal equals optimal
ok 160 - updateHintElement - currentVal equals optimal
  ---
  duration_ms: 0.061417
  type: 'test'
  ...
# Subtest: updateHintElement - currentVal is greater than optimal
ok 161 - updateHintElement - currentVal is greater than optimal
  ---
  duration_ms: 0.063333
  type: 'test'
  ...
# Subtest: updateHintElement - currentVal is less than optimal
ok 162 - updateHintElement - currentVal is less than optimal
  ---
  duration_ms: 0.643789
  type: 'test'
  ...
# Subtest: isMaskedValue detects masked strings correctly
ok 163 - isMaskedValue detects masked strings correctly
  ---
  duration_ms: 0.518248
  type: 'test'
  ...
# Subtest: AC1: Clear-on-Edit clears masked field on first keypress, not on focus
ok 164 - AC1: Clear-on-Edit clears masked field on first keypress, not on focus
  ---
  duration_ms: 0.549414
  type: 'test'
  ...
# Subtest: AC1: Clear-on-Edit with Backspace / Delete clears entire mask cleanly
ok 165 - AC1: Clear-on-Edit with Backspace / Delete clears entire mask cleanly
  ---
  duration_ms: 0.104916
  type: 'test'
  ...
# Subtest: AC2: Blur-Restore restores masked value when focused and left without edit
ok 166 - AC2: Blur-Restore restores masked value when focused and left without edit
  ---
  duration_ms: 0.154333
  type: 'test'
  ...
# Subtest: AC2: Escape key restores original masked value
ok 167 - AC2: Escape key restores original masked value
  ---
  duration_ms: 3.138863
  type: 'test'
  ...
# Subtest: AC3: Validation Gate marks field with **** as invalid and blocks submit
ok 168 - AC3: Validation Gate marks field with **** as invalid and blocks submit
  ---
  duration_ms: 0.26879
  type: 'test'
  ...
# Subtest: AC4: Dirty-Tracking includes only modified fields across all 6 fields
ok 169 - AC4: Dirty-Tracking includes only modified fields across all 6 fields
  ---
  duration_ms: 0.681497
  type: 'test'
  ...
# Subtest: AC5: Trimming removes leading and trailing whitespace from input values
ok 170 - AC5: Trimming removes leading and trailing whitespace from input values
  ---
  duration_ms: 0.065041
  type: 'test'
  ...
# Subtest: AC6: Decoupled Key Presence indicator works for short keys (****) and empty keys
ok 171 - AC6: Decoupled Key Presence indicator works for short keys (****) and empty keys
  ---
  duration_ms: 0.268124
  type: 'test'
  ...
# Subtest: AC12: Whitespace-only input is rejected and marked as invalid
ok 172 - AC12: Whitespace-only input is rejected and marked as invalid
  ---
  duration_ms: 0.265083
  type: 'test'
  ...
# Subtest: W1: Blur-Restore restores masked value when user triggers Clear-on-Edit but blurs with empty input
ok 173 - W1: Blur-Restore restores masked value when user triggers Clear-on-Edit but blurs with empty input
  ---
  duration_ms: 0.13125
  type: 'test'
  ...
# Subtest: W1: Blur-Restore restores masked value when user enters whitespace and blurs
ok 174 - W1: Blur-Restore restores masked value when user enters whitespace and blurs
  ---
  duration_ms: 0.062917
  type: 'test'
  ...
# Subtest: W1: Validation treats field cleared via Clear-on-Edit without new value as unchanged (changed=false)
ok 175 - W1: Validation treats field cleared via Clear-on-Edit without new value as unchanged (changed=false)
  ---
  duration_ms: 0.054791
  type: 'test'
  ...
# Subtest: W1: User clears field, types a new valid key, blurs -> new key is preserved and validation reports changed=true
ok 176 - W1: User clears field, types a new valid key, blurs -> new key is preserved and validation reports changed=true
  ---
  duration_ms: 0.103208
  type: 'test'
  ...
# Subtest: W1 / Decision A: Cleared input badge does not claim key removal (Roadmap Item \#59)
ok 177 - W1 / Decision A: Cleared input badge does not claim key removal (Roadmap Item \#59)
  ---
  duration_ms: 0.07425
  type: 'test'
  ...
# Subtest: Item 59 AK1: Configured key (dataset.hasKey='true') offers visible delete button
ok 178 - Item 59 AK1: Configured key (dataset.hasKey='true') offers visible delete button
  ---
  duration_ms: 0.052874
  type: 'test'
  ...
# Subtest: Item 59 AK2: Unconfigured key (dataset.hasKey='false') does not offer active delete button
ok 179 - Item 59 AK2: Unconfigured key (dataset.hasKey='false') does not offer active delete button
  ---
  duration_ms: 0.047375
  type: 'test'
  ...
# Subtest: Item 59 AK3: First click on delete button opens confirmation prompt without clearing input
ok 180 - Item 59 AK3: First click on delete button opens confirmation prompt without clearing input
  ---
  duration_ms: 0.110999
  type: 'test'
  ...
# Subtest: Item 59 AK4: Canceling confirmation prompt restores field to original state
ok 181 - Item 59 AK4: Canceling confirmation prompt restores field to original state
  ---
  duration_ms: 0.077375
  type: 'test'
  ...
# Subtest: Item 59 AK5: Confirming deletion clears input, marks delete flag, and validateMaskedInput reports changed=true with value=''
ok 182 - Item 59 AK5: Confirming deletion clears input, marks delete flag, and validateMaskedInput reports changed=true with value=''
  ---
  duration_ms: 0.146625
  type: 'test'
  ...
# Subtest: Item 59 AK6: Clear-on-Edit without delete confirmation preserves W1 protection (changed=false)
ok 183 - Item 59 AK6: Clear-on-Edit without delete confirmation preserves W1 protection (changed=false)
  ---
  duration_ms: 0.062208
  type: 'test'
  ...
# Subtest: Item 59 AK7: Masked value with **** is rejected and marked invalid regardless of delete flow
ok 184 - Item 59 AK7: Masked value with **** is rejected and marked invalid regardless of delete flow
  ---
  duration_ms: 0.053167
  type: 'test'
  ...
# Subtest: Item 59: Escape key resets delete confirmation and restores original value without bypassing focus path
ok 185 - Item 59: Escape key resets delete confirmation and restores original value without bypassing focus path
  ---
  duration_ms: 0.086792
  type: 'test'
  ...
# Subtest: Item 59: Typing a new value after delete confirmation resets delete flag
ok 186 - Item 59: Typing a new value after delete confirmation resets delete flag
  ---
  duration_ms: 0.065749
  type: 'test'
  ...
# Subtest: Item 59 DOM Structure: All 6 masked-key-field blocks in index.html contain delete button and confirmation dialog
ok 187 - Item 59 DOM Structure: All 6 masked-key-field blocks in index.html contain delete button and confirmation dialog
  ---
  duration_ms: 1.072662
  type: 'test'
  ...
# Subtest: updateMwDataPanel - with mw_data containing url and sync
ok 188 - updateMwDataPanel - with mw_data containing url and sync
  ---
  duration_ms: 9.440797
  type: 'test'
  ...
# Subtest: updateMwDataPanel - without mw_data
ok 189 - updateMwDataPanel - without mw_data
  ---
  duration_ms: 0.080917
  type: 'test'
  ...
# Subtest: prepareSeriesPayload - with mw_data
ok 190 - prepareSeriesPayload - with mw_data
  ---
  duration_ms: 0.208707
  type: 'test'
  ...
# Subtest: prepareSeriesPayload - without mw_data
ok 191 - prepareSeriesPayload - without mw_data
  ---
  duration_ms: 0.054416
  type: 'test'
  ...
# Subtest: updateMwDataPanel - with unsafe scheme source_url
ok 192 - updateMwDataPanel - with unsafe scheme source_url
  ---
  duration_ms: 0.254916
  type: 'test'
  ...
# Subtest: guessSeasonAndEpisode - S01E02-Format
ok 193 - guessSeasonAndEpisode - S01E02-Format
  ---
  duration_ms: 0.473248
  type: 'test'
  ...
# Subtest: guessSeasonAndEpisode - 1x05-Format
ok 194 - guessSeasonAndEpisode - 1x05-Format
  ---
  duration_ms: 0.100833
  type: 'test'
  ...
# Subtest: guessSeasonAndEpisode - Deutsche Formate
ok 195 - guessSeasonAndEpisode - Deutsche Formate
  ---
  duration_ms: 0.190166
  type: 'test'
  ...
# Subtest: guessSeasonAndEpisode - Kein Treffer
ok 196 - guessSeasonAndEpisode - Kein Treffer
  ---
  duration_ms: 0.728372
  type: 'test'
  ...
# Subtest: guessEpisodeNumber - Erkennung aus verschiedenen Formaten
ok 197 - guessEpisodeNumber - Erkennung aus verschiedenen Formaten
  ---
  duration_ms: 0.167791
  type: 'test'
  ...
# Subtest: guessEpisodeNumber - Grenzwerte im Ziffern-Fallback-Pfad
ok 198 - guessEpisodeNumber - Grenzwerte im Ziffern-Fallback-Pfad
  ---
  duration_ms: 0.076958
  type: 'test'
  ...
# Subtest: cleanFilenameForManualTitle - Bereinigungen
ok 199 - cleanFilenameForManualTitle - Bereinigungen
  ---
  duration_ms: 0.409706
  type: 'test'
  ...
# Subtest: cleanFilenameForManualTitle - Leereingaben (Guard)
ok 200 - cleanFilenameForManualTitle - Leereingaben (Guard)
  ---
  duration_ms: 0.18379
  type: 'test'
  ...
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:2302:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:2271:9)
# Error loading settings: TypeError: undefined is not iterable (cannot read property Symbol(Symbol.iterator))
#     at Function.from (<anonymous>)
#     at eval (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8651:50)
#     at Array.forEach (<anonymous>)
#     at updateDestinationDropdowns (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8634:16)
#     at loadSettings (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8575:13)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8303:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:2302:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:2271:9)
# Error loading settings: TypeError: undefined is not iterable (cannot read property Symbol(Symbol.iterator))
#     at Function.from (<anonymous>)
#     at eval (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8651:50)
#     at Array.forEach (<anonymous>)
#     at updateDestinationDropdowns (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8634:16)
#     at loadSettings (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8575:13)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8303:64)
# Subtest: Profile Dropdown Refresh - Case (a): ok:true and data.success:true refreshes dropdown and logs no error
ok 201 - Profile Dropdown Refresh - Case (a): ok:true and data.success:true refreshes dropdown and logs no error
  ---
  duration_ms: 37.109858
  type: 'test'
  ...
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:2302:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:2271:9)
# Error loading settings: TypeError: undefined is not iterable (cannot read property Symbol(Symbol.iterator))
#     at Function.from (<anonymous>)
#     at eval (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8651:50)
#     at Array.forEach (<anonymous>)
#     at updateDestinationDropdowns (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8634:16)
#     at loadSettings (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8575:13)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8303:64)
# Subtest: Profile Dropdown Refresh - Case (b): ok:true and data.success:false logs warning and does not refresh dropdown
ok 202 - Profile Dropdown Refresh - Case (b): ok:true and data.success:false logs warning and does not refresh dropdown
  ---
  duration_ms: 36.512444
  type: 'test'
  ...
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:2302:40)
#     at loadStatus (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:2271:9)
# Error loading settings: TypeError: undefined is not iterable (cannot read property Symbol(Symbol.iterator))
#     at Function.from (<anonymous>)
#     at eval (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8651:50)
#     at Array.forEach (<anonymous>)
#     at updateDestinationDropdowns (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8634:16)
#     at loadSettings (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8575:13)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8303:64)
# Error saving show profile on execution: Error: Failed to fetch network error
#     at mockFetch (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:155:23)
#     at Object.eval (eval at setupTestEnvironment (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:10683:40)
#     at Object.dispatchEvent (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:37:31)
#     at TestContext.<anonymous> (file:///tmp/ws/tests/frontend/profile_dropdown_refresh.test.js:339:22)
#     at async Test.run (node:internal/test_runner/test:1054:7)
#     at async Test.processPendingSubtests (node:internal/test_runner/test:744:7)
# Subtest: Profile Dropdown Refresh - Case (c): ok:false (HTTP 500) logs connection error and does not refresh dropdown
ok 203 - Profile Dropdown Refresh - Case (c): ok:false (HTTP 500) logs connection error and does not refresh dropdown
  ---
  duration_ms: 27.07098
  type: 'test'
  ...
# Subtest: Profile Dropdown Refresh - Case (d): Network exception / invalid JSON logs connection error and processing continues
ok 204 - Profile Dropdown Refresh - Case (d): Network exception / invalid JSON logs connection error and processing continues
  ---
  duration_ms: 24.605614
  type: 'test'
  ...
# Subtest: E3-AK1: Hängende Suche wird nach Auslösen des 30-s-Frist-Timers abgebrochen (signal-Abbruch, sichtbare Fristmeldung in series-search-results, Sperre frei für nachfolgenden Start)
ok 205 - E3-AK1: Hängende Suche wird nach Auslösen des 30-s-Frist-Timers abgebrochen (signal-Abbruch, sichtbare Fristmeldung in series-search-results, Sperre frei für nachfolgenden Start)
  ---
  duration_ms: 23.186537
  type: 'test'
  ...
# Subtest: E3-AK2: Suche A hängt, Suche B startet -> A endet still ohne Meldung; selbst wenn A-Frist-Timer nach B-Start ausgelöst wird, bleibt A still (Seq-Guard) und B-Ergebnisse bleiben stehen
ok 206 - E3-AK2: Suche A hängt, Suche B startet -> A endet still ohne Meldung; selbst wenn A-Frist-Timer nach B-Start ausgelöst wird, bleibt A still (Seq-Guard) und B-Ergebnisse bleiben stehen
  ---
  duration_ms: 10.341419
  type: 'test'
  ...
# Subtest: E3-AK3: Suche, die vor der Frist auflöst, rendert Ergebnisse wie bisher, zeigt keine Frist-Meldung und baut den Frist-Timer im finally zurück (Queue danach leer)
ok 207 - E3-AK3: Suche, die vor der Frist auflöst, rendert Ergebnisse wie bisher, zeigt keine Frist-Meldung und baut den Frist-Timer im finally zurück (Queue danach leer)
  ---
  duration_ms: 3.141572
  type: 'test'
  ...
# Subtest: E3-AK4: Pfadabdeckung für E3-AK1/AK2/AK3 auf manuellem Pfad (btn-search-series-Klick und Enter im Suchfeld) UND Workflow-Pfad (startSeriesGroupWorkflow -> searchSeries)
ok 208 - E3-AK4: Pfadabdeckung für E3-AK1/AK2/AK3 auf manuellem Pfad (btn-search-series-Klick und Enter im Suchfeld) UND Workflow-Pfad (startSeriesGroupWorkflow -> searchSeries)
  ---
  duration_ms: 11.872454
  type: 'test'
  ...
# Subtest: E3-AK5: Steuerbare Fake-Timer-Queue registriert Frist-Timer (delay >= 30000) ohne Sofortausführung, führt kleinere Delays (scrollIntoView 200ms) sofort aus und ersetzt die Sofort-Stubs in allen vier Bestands-Testdateien
ok 209 - E3-AK5: Steuerbare Fake-Timer-Queue registriert Frist-Timer (delay >= 30000) ohne Sofortausführung, führt kleinere Delays (scrollIntoView 200ms) sofort aus und ersetzt die Sofort-Stubs in allen vier Bestands-Testdateien
  ---
  duration_ms: 5.003898
  type: 'test'
  ...
# Subtest: DOM Structure & Styling: index.html contains settings-app-theme-error with theme class and no inline style
ok 210 - DOM Structure & Styling: index.html contains settings-app-theme-error with theme class and no inline style
  ---
  duration_ms: 1.647702
  type: 'test'
  ...
# Subtest: Theme Autosave AK1 & AK3 & AK5: non-ok response shows visible informative error and logs console.error
ok 211 - Theme Autosave AK1 & AK3 & AK5: non-ok response shows visible informative error and logs console.error
  ---
  duration_ms: 1.744577
  type: 'test'
  ...
# Subtest: Theme Autosave AK2 & AK3 & AK5: network exception in catch block shows visible informative error and logs console.error
ok 212 - Theme Autosave AK2 & AK3 & AK5: network exception in catch block shows visible informative error and logs console.error
  ---
  duration_ms: 2.146075
  type: 'test'
  ...
# Subtest: Theme Autosave AK4: successful save clears any previous error and keeps error hidden
ok 213 - Theme Autosave AK4: successful save clears any previous error and keeps error hidden
  ---
  duration_ms: 1.457078
  type: 'test'
  ...
# Subtest: Roadmap: Item 60 retains deferred context and reason in ROADMAP.md
ok 214 - Roadmap: Item 60 retains deferred context and reason in ROADMAP.md
  ---
  duration_ms: 0.495873
  type: 'test'
  ...
# Subtest: Theme Autosave Guard: second theme change aborts previous in-flight request and shows no error
ok 215 - Theme Autosave Guard: second theme change aborts previous in-flight request and shows no error
  ---
  duration_ms: 1.525702
  type: 'test'
  ...
# Subtest: Theme Autosave Guard: AbortError from fetch does not trigger error message or console.error
ok 216 - Theme Autosave Guard: AbortError from fetch does not trigger error message or console.error
  ---
  duration_ms: 1.453536
  type: 'test'
  ...
# Subtest: Roadmap: Item 62 retains deferred context and reason in ROADMAP.md
ok 217 - Roadmap: Item 62 retains deferred context and reason in ROADMAP.md
  ---
  duration_ms: 0.495956
  type: 'test'
  ...
# Subtest: cleanSeriesName - Leereingaben
ok 218 - cleanSeriesName - Leereingaben
  ---
  duration_ms: 0.374666
  type: 'test'
  ...
# Subtest: cleanSeriesName - Unterstriche ersetzen
ok 219 - cleanSeriesName - Unterstriche ersetzen
  ---
  duration_ms: 0.276541
  type: 'test'
  ...
# Subtest: cleanSeriesName - Mediathek- und URL-Sonderklammern entfernen
ok 220 - cleanSeriesName - Mediathek- und URL-Sonderklammern entfernen
  ---
  duration_ms: 0.121125
  type: 'test'
  ...
# Subtest: cleanSeriesName - Kanal-Tags / Bracket-Tags am Ende entfernen (wiederholt)
ok 221 - cleanSeriesName - Kanal-Tags / Bracket-Tags am Ende entfernen (wiederholt)
  ---
  duration_ms: 0.056625
  type: 'test'
  ...
# Subtest: cleanSeriesName - Kombination und Trimming
ok 222 - cleanSeriesName - Kombination und Trimming
  ---
  duration_ms: 0.597248
  type: 'test'
  ...
# Subtest: fetchStats - success
ok 223 - fetchStats - success
  ---
  duration_ms: 0.601956
  type: 'test'
  ...
# Subtest: fetchStats - non-ok status
ok 224 - fetchStats - non-ok status
  ---
  duration_ms: 0.132
  type: 'test'
  ...
# Subtest: fetchStats - network error
ok 225 - fetchStats - network error
  ---
  duration_ms: 0.828247
  type: 'test'
  ...
# Subtest: fetchYoutubeSubscriptions - success
ok 226 - fetchYoutubeSubscriptions - success
  ---
  duration_ms: 0.115458
  type: 'test'
  ...
# Subtest: fetchYoutubeSubscriptions - non-ok status
ok 227 - fetchYoutubeSubscriptions - non-ok status
  ---
  duration_ms: 0.065458
  type: 'test'
  ...
# Subtest: fetchYoutubeSubscriptions - network error
ok 228 - fetchYoutubeSubscriptions - network error
  ---
  duration_ms: 0.124499
  type: 'test'
  ...
# Subtest: fetchSmartInboxSuggestions - success
ok 229 - fetchSmartInboxSuggestions - success
  ---
  duration_ms: 0.077792
  type: 'test'
  ...
# Subtest: fetchSmartInboxSuggestions - non-ok status
ok 230 - fetchSmartInboxSuggestions - non-ok status
  ---
  duration_ms: 0.049749
  type: 'test'
  ...
# Subtest: fetchSmartInboxSuggestions - network error
ok 231 - fetchSmartInboxSuggestions - network error
  ---
  duration_ms: 0.232458
  type: 'test'
  ...
1..231
# tests 231
# suites 0
# pass 231
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 472.623858
npm notice
npm notice New major version of npm available! 10.9.8 -> 12.2.1
npm notice Changelog: https://github.com/npm/cli/releases/tag/v12.2.1
npm notice To update run: npm install -g npm@12.2.1
npm notice
EXIT=0
```
