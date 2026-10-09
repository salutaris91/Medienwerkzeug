# AK0 — Ausgangsmessung #65 (vor Gate-A2 Lauf A)

Ausgeführt von Claude Code (2026-10-09T06:32:03Z bis 2026-10-09T06:32:35Z) auf einem `git clone` des Worktrees `feat/roadmap-65-als-serie-gruppieren` @ `c66cb20` (Code = `main` @ `6152839` nach #64; `c66cb20` ändert nur ROADMAP.md), im Worker-Image `openhands-agy-worker:1.2.12`.

Befehl:

```
docker run --rm --entrypoint /bin/sh -v <clone>:/work -w /work openhands-agy-worker:1.2.12 -c "python3 -m pip install -q --user --break-system-packages -r requirements.txt pytest && python3 -m pytest -q -p no:cacheprovider --deselect tests/test_utils.py::TestMediawerkzeugLogic::test_conversion_estimation_test_encode && npm run test:frontend"
```

Ergebnis: **481 passed, 1 deselected** (pytest) und **150/150** (Frontend), Exit 0.

Wörtliche Ausgabe (einzige Änderung: 0 Zeilen mit Trailing Whitespace am Zeilenende gekürzt; Original: Kit `scripts/gate-a2/logs/2026-10-09-roadmap65-lauf-a/ak0-output.txt`):

```
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
........................................................................ [ 29%]
........................................................................ [ 44%]
........................................................................ [ 59%]
........................................................................ [ 74%]
........................................................................ [ 89%]
.................................................                        [100%]
=============================== warnings summary ===============================
tests/test_onboarding.py::TestOnboarding::test_complete_and_skip_endpoints
  /work/gui/core/telemetry.py:42: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    "timestamp": datetime.datetime.utcnow().isoformat() + "Z"

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
481 passed, 1 deselected, 1 warning in 27.02s

> medienwerkzeug@1.3.0 test:frontend
> node --test "tests/frontend/**/*.test.js"

TAP version 13
# Subtest: renderHealthStatus - warning state renders warning alert, not success
ok 1 - renderHealthStatus - warning state renders warning alert, not success
  ---
  duration_ms: 1.714245
  type: 'test'
  ...
# Subtest: renderDuplicateStatus - warning state renders warning alert, not success
ok 2 - renderDuplicateStatus - warning state renders warning alert, not success
  ---
  duration_ms: 0.304958
  type: 'test'
  ...
# Subtest: loadNormalizePreview - status 400 shows warning alert, not success
ok 3 - loadNormalizePreview - status 400 shows warning alert, not success
  ---
  duration_ms: 0.226791
  type: 'test'
  ...
# Subtest: renderNormalizePlan - 1 item renders Singular "Vorschlag"
ok 4 - renderNormalizePlan - 1 item renders Singular "Vorschlag"
  ---
  duration_ms: 0.180375
  type: 'test'
  ...
# Subtest: renderNormalizePlan - 2 items renders Plural "Vorschläge"
ok 5 - renderNormalizePlan - 2 items renders Plural "Vorschläge"
  ---
  duration_ms: 0.143458
  type: 'test'
  ...
# Subtest: renderNormalizePlan - empty plan renders neutral empty state without emoji
ok 6 - renderNormalizePlan - empty plan renders neutral empty state without emoji
  ---
  duration_ms: 0.097416
  type: 'test'
  ...
# Subtest: renderQueue - pipeline step message uses existing HTML escaping helper
ok 7 - renderQueue - pipeline step message uses existing HTML escaping helper
  ---
  duration_ms: 0.728123
  type: 'test'
  ...
# Subtest: renderHealthStatus - renders summary chips with total and group counts and no severity grouping
ok 8 - renderHealthStatus - renders summary chips with total and group counts and no severity grouping
  ---
  duration_ms: 11.319181
  type: 'test'
  ...
# Subtest: renderHealthStatus - type grouping renders type groups, checkboxes and tool-connectors
ok 9 - renderHealthStatus - type grouping renders type groups, checkboxes and tool-connectors
  ---
  duration_ms: 0.391166
  type: 'test'
  ...
# Subtest: renderHealthStatus - only nested_duplicate / structure issues displays tab specific empty state on media tab
ok 10 - renderHealthStatus - only nested_duplicate / structure issues displays tab specific empty state on media tab
  ---
  duration_ms: 0.316957
  type: 'test'
  ...
# Subtest: renderHealthStatus - structure-only result wires structure batch button
ok 11 - renderHealthStatus - structure-only result wires structure batch button
  ---
  duration_ms: 0.134708
  type: 'test'
  ...
# Subtest: renderHealthStatus - transition running -> warning clears loading spinner and hides structure container
ok 12 - renderHealthStatus - transition running -> warning clears loading spinner and hides structure container
  ---
  duration_ms: 0.105417
  type: 'test'
  ...
# Subtest: renderNfoAgentFiles - mediaType tvshow renders tvshow.nfo status matrix
ok 13 - renderNfoAgentFiles - mediaType tvshow renders tvshow.nfo status matrix
  ---
  duration_ms: 0.405707
  type: 'test'
  ...
# Subtest: NFO Agent combines the main NFO status with the metadata editor
ok 14 - NFO Agent combines the main NFO status with the metadata editor
  ---
  duration_ms: 0.89554
  type: 'test'
  ...
# Subtest: NFO Agent movie mode renders movie.nfo without series controls
ok 15 - NFO Agent movie mode renders movie.nfo without series controls
  ---
  duration_ms: 0.131
  type: 'test'
  ...
# Subtest: submitNfoAgentJob - payload structures and write_show_nfo semantics
ok 16 - submitNfoAgentJob - payload structures and write_show_nfo semantics
  ---
  duration_ms: 0.627873
  type: 'test'
  ...
# Subtest: NFO Agent shows a calm non-blocking completeness hint
ok 17 - NFO Agent shows a calm non-blocking completeness hint
  ---
  duration_ms: 0.058291
  type: 'test'
  ...
# Subtest: waitForServerRestart succeeds after a temporary connection failure
ok 18 - waitForServerRestart succeeds after a temporary connection failure
  ---
  duration_ms: 0.102083
  type: 'test'
  ...
# Subtest: waitForServerRestart stops after the configured attempt limit
ok 19 - waitForServerRestart stops after the configured attempt limit
  ---
  duration_ms: 0.072791
  type: 'test'
  ...
# Subtest: restoreServerRestartButton clears the loading state
ok 20 - restoreServerRestartButton clears the loading state
  ---
  duration_ms: 0.044791
  type: 'test'
  ...
# Subtest: Cache-Busting: index.html app.js version matches all ES-module import versions in app.js
ok 21 - Cache-Busting: index.html app.js version matches all ES-module import versions in app.js
  ---
  duration_ms: 3.872991
  type: 'test'
  ...
# Subtest: Cache-Busting: style.css in index.html has a non-empty ?v= version query
ok 22 - Cache-Busting: style.css in index.html has a non-empty ?v= version query
  ---
  duration_ms: 1.697745
  type: 'test'
  ...
# Subtest: Cache-Busting: utilities.css in index.html has a non-empty ?v= version query
ok 23 - Cache-Busting: utilities.css in index.html has a non-empty ?v= version query
  ---
  duration_ms: 0.856123
  type: 'test'
  ...
# Subtest: formatBytes - Nullwert
ok 24 - formatBytes - Nullwert
  ---
  duration_ms: 0.581457
  type: 'test'
  ...
# Subtest: formatBytes - Werte unter 1 KB
ok 25 - formatBytes - Werte unter 1 KB
  ---
  duration_ms: 0.104291
  type: 'test'
  ...
# Subtest: formatBytes - Einheiten und Schwellenwerte
ok 26 - formatBytes - Einheiten und Schwellenwerte
  ---
  duration_ms: 0.126458
  type: 'test'
  ...
# Subtest: formatBytes - Nachkommastellen und Rundung
ok 27 - formatBytes - Nachkommastellen und Rundung
  ---
  duration_ms: 0.086458
  type: 'test'
  ...
# Subtest: osBasename - extracts filename correctly
ok 28 - osBasename - extracts filename correctly
  ---
  duration_ms: 0.660707
  type: 'test'
  ...
# Subtest: formatFskLabel - formats FSK labels correctly
ok 29 - formatFskLabel - formats FSK labels correctly
  ---
  duration_ms: 0.21325
  type: 'test'
  ...
# Subtest: resolveSendPaths - resolves hierarchy properly
ok 30 - resolveSendPaths - resolves hierarchy properly
  ---
  duration_ms: 0.91379
  type: 'test'
  ...
# Subtest: openFskBatchModal - opens modal and sets up state
ok 31 - openFskBatchModal - opens modal and sets up state
  ---
  duration_ms: 0.431249
  type: 'test'
  ...
# Subtest: Scope-Change-Event - triggers new preview fetch
ok 32 - Scope-Change-Event - triggers new preview fetch
  ---
  duration_ms: 20.605116
  type: 'test'
  ...
# Subtest: Null-Ziel-Sperre im DOM
ok 33 - Null-Ziel-Sperre im DOM
  ---
  duration_ms: 20.796324
  type: 'test'
  ...
# Subtest: Apply-Fetch-Payload and preview rendering
ok 34 - Apply-Fetch-Payload and preview rendering
  ---
  duration_ms: 11.972595
  type: 'test'
  ...
# Subtest: Darstellung von partial und failed
ok 35 - Darstellung von partial und failed
  ---
  duration_ms: 23.390358
  type: 'test'
  ...
# Subtest: No native Dialogs and Inline Error Rendering
ok 36 - No native Dialogs and Inline Error Rendering
  ---
  duration_ms: 13.447758
  type: 'test'
  ...
# Subtest: Dynamic Button Text and Disabled State
ok 37 - Dynamic Button Text and Disabled State
  ---
  duration_ms: 23.576108
  type: 'test'
  ...
# Subtest: Apply payload includes status field
ok 38 - Apply payload includes status field
  ---
  duration_ms: 23.5174
  type: 'test'
  ...
# Subtest: show-group-fsk-btn click - triggers openFskBatchModal and fetches series scope
ok 39 - show-group-fsk-btn click - triggers openFskBatchModal and fetches series scope
  ---
  duration_ms: 1.197997
  type: 'test'
  ...
# Subtest: season-group-fsk-btn click - triggers openFskBatchModal and fetches season scope
ok 40 - season-group-fsk-btn click - triggers openFskBatchModal and fetches season scope
  ---
  duration_ms: 0.260499
  type: 'test'
  ...
# Subtest: Out-of-order preview requests are correctly discarded
ok 41 - Out-of-order preview requests are correctly discarded
  ---
  duration_ms: 0.165833
  type: 'test'
  ...
# Subtest: Modal direct scope and prevent dual requests
ok 42 - Modal direct scope and prevent dual requests
  ---
  duration_ms: 0.077833
  type: 'test'
  ...
# Subtest: 409 Conflict keeps error message visible after preview load
ok 43 - 409 Conflict keeps error message visible after preview load
  ---
  duration_ms: 49.044753
  type: 'test'
  ...
# Subtest: Apply-Lock blocks closeFskBatchModal
ok 44 - Apply-Lock blocks closeFskBatchModal
  ---
  duration_ms: 0.153124
  type: 'test'
  ...
# Subtest: Media view routes series, season and episode metadata actions through the NFO Agent
ok 45 - Media view routes series, season and episode metadata actions through the NFO Agent
  ---
  duration_ms: 0.63204
  type: 'test'
  ...
# Subtest: Media summary stays calm and exposes exact actions only in details
ok 46 - Media summary stays calm and exposes exact actions only in details
  ---
  duration_ms: 0.560165
  type: 'test'
  ...
# Subtest: Media view separates season findings from collapsible episode metadata findings
ok 47 - Media view separates season findings from collapsible episode metadata findings
  ---
  duration_ms: 0.222041
  type: 'test'
  ...
# Subtest: Scoped ignore modal lists present issue types grouped by catalog group and posts the exact scope
ok 48 - Scoped ignore modal lists present issue types grouped by catalog group and posts the exact scope
  ---
  duration_ms: 5.344945
  type: 'test'
  ...
# Subtest: Media view separates series and movies into tabs with counts
ok 49 - Media view separates series and movies into tabs with counts
  ---
  duration_ms: 0.197833
  type: 'test'
  ...
# Subtest: Scoped ignore modal is static, explicit, and reversible
ok 50 - Scoped ignore modal is static, explicit, and reversible
  ---
  duration_ms: 0.862373
  type: 'test'
  ...
# Subtest: Media-oriented movie view treats invalid FSK as a metadata problem
ok 51 - Media-oriented movie view treats invalid FSK as a metadata problem
  ---
  duration_ms: 0.190291
  type: 'test'
  ...
# Subtest: Media view does not resurrect an ignored missing series NFO from structural status
ok 52 - Media view does not resurrect an ignored missing series NFO from structural status
  ---
  duration_ms: 0.054583
  type: 'test'
  ...
# Subtest: nfo_missing visibility and action suppression
ok 53 - nfo_missing visibility and action suppression
  ---
  duration_ms: 0.669873
  type: 'test'
  ...
# Subtest: Film-Rendering in FSK Modal uses media_kind
ok 54 - Film-Rendering in FSK Modal uses media_kind
  ---
  duration_ms: 12.472635
  type: 'test'
  ...
# Subtest: Successful apply leaves one terminal action and refreshes health immediately
ok 55 - Successful apply leaves one terminal action and refreshes health immediately
  ---
  duration_ms: 11.572804
  type: 'test'
  ...
# Subtest: NFO-Agent rendered in skipped_missing
ok 56 - NFO-Agent rendered in skipped_missing
  ---
  duration_ms: 12.610594
  type: 'test'
  ...
# Subtest: Fertig-Klick bei ready=0 schliesst Modal
ok 57 - Fertig-Klick bei ready=0 schliesst Modal
  ---
  duration_ms: 22.616986
  type: 'test'
  ...
# Subtest: NFO Agent Lifecycle wertet done, error, cancelled und fehlende Queue-Jobs aus
ok 58 - NFO Agent Lifecycle wertet done, error, cancelled und fehlende Queue-Jobs aus
  ---
  duration_ms: 25.970228
  type: 'test'
  ...
# Error: TMDB-Filmmetadaten konnten nicht geladen werden: timed out
#     at eval (eval at <anonymous> (file:///work/tests/frontend/fsk_batch_dom.test.js:236:1), <anonymous>:16285:35)
# Subtest: Escaping-Sicherheit bei NFO-Agent-Event-Delegation
ok 59 - Escaping-Sicherheit bei NFO-Agent-Event-Delegation
  ---
  duration_ms: 13.507217
  type: 'test'
  ...
# Subtest: NFO Agent switches between entry context and whole-series editing
ok 60 - NFO Agent switches between entry context and whole-series editing
  ---
  duration_ms: 0.441332
  type: 'test'
  ...
# Subtest: Submit label reflects the visible episode fields in season mode
ok 61 - Submit label reflects the visible episode fields in season mode
  ---
  duration_ms: 0.210416
  type: 'test'
  ...
# Subtest: Mediathek search result switches to manual entry instead of a TVDB fetch
ok 62 - Mediathek search result switches to manual entry instead of a TVDB fetch
  ---
  duration_ms: 0.10375
  type: 'test'
  ...
# Error: TMDB-Filmmetadaten konnten nicht geladen werden: timed out
#     at eval (eval at <anonymous> (file:///work/tests/frontend/fsk_batch_dom.test.js:236:1), <anonymous>:16285:35)
# Subtest: Failed detail loads render an inline retry action instead of an alert
ok 63 - Failed detail loads render an inline retry action instead of an alert
  ---
  duration_ms: 2.384744
  type: 'test'
  ...
# Subtest: NFO Agent hides the back button when whole-series is the entry point
ok 64 - NFO Agent hides the back button when whole-series is the entry point
  ---
  duration_ms: 0.150166
  type: 'test'
  ...
# Subtest: NFO Agent submits manually when no provider ID is given
ok 65 - NFO Agent submits manually when no provider ID is given
  ---
  duration_ms: 0.404082
  type: 'test'
  ...
# Subtest: NFO Agent season mode edits the season without writing the series NFO
ok 66 - NFO Agent season mode edits the season without writing the series NFO
  ---
  duration_ms: 0.2695
  type: 'test'
  ...
# Subtest: NFO Agent episode mode submits only the selected episode
ok 67 - NFO Agent episode mode submits only the selected episode
  ---
  duration_ms: 0.379749
  type: 'test'
  ...
# Subtest: NFO Agent uses concise mode controls and clear missing-source copy
ok 68 - NFO Agent uses concise mode controls and clear missing-source copy
  ---
  duration_ms: 1.117622
  type: 'test'
  ...
# Subtest: Type-oriented episode findings preserve the focused episode context
ok 69 - Type-oriented episode findings preserve the focused episode context
  ---
  duration_ms: 0.267374
  type: 'test'
  ...
# Could not read inbox sort state from sessionStorage: SyntaxError: Expected property name or '}' in JSON at position 2 (line 1 column 3)
#     at JSON.parse (<anonymous>)
#     at getInboxSortState (eval at setupEnvironment (file:///work/tests/frontend/inbox_sort.test.js:220:5), <anonymous>:12313:37)
#     at TestContext.<anonymous> (file:///work/tests/frontend/inbox_sort.test.js:415:30)
#     at Test.runInAsyncScope (node:async_hooks:214:14)
#     at Test.run (node:internal/test_runner/test:1047:25)
#     at Test.processPendingSubtests (node:internal/test_runner/test:744:18)
#     at Test.postRun (node:internal/test_runner/test:1173:19)
#     at Test.run (node:internal/test_runner/test:1101:12)
#     at async Test.processPendingSubtests (node:internal/test_runner/test:744:7)
# Subtest: AK3: sortInboxSuggestions sorts by name using German numeric/base localeCompare
ok 70 - AK3: sortInboxSuggestions sorts by name using German numeric/base localeCompare
  ---
  duration_ms: 15.361212
  type: 'test'
  ...
# Subtest: AK3: sortInboxSuggestions sorts by date (modified_at) and places null at the end for BOTH asc and desc
ok 71 - AK3: sortInboxSuggestions sorts by date (modified_at) and places null at the end for BOTH asc and desc
  ---
  duration_ms: 6.987066
  type: 'test'
  ...
# Subtest: AK3: sortInboxSuggestions sorts by size (total_size) and places null at the end for BOTH directions
ok 72 - AK3: sortInboxSuggestions sorts by size (total_size) and places null at the end for BOTH directions
  ---
  duration_ms: 1.974578
  type: 'test'
  ...
# Subtest: AK3: sortInboxSuggestions resolves ties deterministically by project name
ok 73 - AK3: sortInboxSuggestions resolves ties deterministically by project name
  ---
  duration_ms: 1.707371
  type: 'test'
  ...
# Subtest: AK4 & AK7: Default sort state without sessionStorage is date desc
ok 74 - AK4 & AK7: Default sort state without sessionStorage is date desc
  ---
  duration_ms: 1.855537
  type: 'test'
  ...
# Subtest: AK4: index.html contains \#smart-inbox-sort-bar with Name, Datum, Größe buttons
ok 75 - AK4: index.html contains \#smart-inbox-sort-bar with Name, Datum, Größe buttons
  ---
  duration_ms: 0.529249
  type: 'test'
  ...
# Subtest: AK4: Clicking inactive sort button activates it (asc), clicking active toggles asc<->desc
ok 76 - AK4: Clicking inactive sort button activates it (asc), clicking active toggles asc<->desc
  ---
  duration_ms: 6.461025
  type: 'test'
  ...
# Subtest: AK4: Sort bar is hidden when suggestions list is empty
ok 77 - AK4: Sort bar is hidden when suggestions list is empty
  ---
  duration_ms: 2.127411
  type: 'test'
  ...
# Subtest: AK5: Sort choice is persisted in sessionStorage and applied across renders
ok 78 - AK5: Sort choice is persisted in sessionStorage and applied across renders
  ---
  duration_ms: 2.065911
  type: 'test'
  ...
# Subtest: AK5: getInboxSortState handles corrupted sessionStorage defensively
ok 79 - AK5: getInboxSortState handles corrupted sessionStorage defensively
  ---
  duration_ms: 4.104573
  type: 'test'
  ...
# Subtest: AK6: Meta line formats video_count, size, and German date with separator
ok 80 - AK6: Meta line formats video_count, size, and German date with separator
  ---
  duration_ms: 1.699371
  type: 'test'
  ...
# Subtest: AK6: Meta line cleanly omits null/missing size or date without empty delimiters
ok 81 - AK6: Meta line cleanly omits null/missing size or date without empty delimiters
  ---
  duration_ms: 1.390954
  type: 'test'
  ...
# Subtest: updateHintElement - recInfo is null
ok 82 - updateHintElement - recInfo is null
  ---
  duration_ms: 0.45179
  type: 'test'
  ...
# Subtest: updateHintElement - recInfo is undefined
ok 83 - updateHintElement - recInfo is undefined
  ---
  duration_ms: 0.071166
  type: 'test'
  ...
# Subtest: updateHintElement - currentVal equals optimal
ok 84 - updateHintElement - currentVal equals optimal
  ---
  duration_ms: 0.060541
  type: 'test'
  ...
# Subtest: updateHintElement - currentVal is greater than optimal
ok 85 - updateHintElement - currentVal is greater than optimal
  ---
  duration_ms: 0.056459
  type: 'test'
  ...
# Subtest: updateHintElement - currentVal is less than optimal
ok 86 - updateHintElement - currentVal is less than optimal
  ---
  duration_ms: 0.563873
  type: 'test'
  ...
# Subtest: isMaskedValue detects masked strings correctly
ok 87 - isMaskedValue detects masked strings correctly
  ---
  duration_ms: 0.726498
  type: 'test'
  ...
# Subtest: AC1: Clear-on-Edit clears masked field on first keypress, not on focus
ok 88 - AC1: Clear-on-Edit clears masked field on first keypress, not on focus
  ---
  duration_ms: 0.768081
  type: 'test'
  ...
# Subtest: AC1: Clear-on-Edit with Backspace / Delete clears entire mask cleanly
ok 89 - AC1: Clear-on-Edit with Backspace / Delete clears entire mask cleanly
  ---
  duration_ms: 0.207749
  type: 'test'
  ...
# Subtest: AC2: Blur-Restore restores masked value when focused and left without edit
ok 90 - AC2: Blur-Restore restores masked value when focused and left without edit
  ---
  duration_ms: 0.212708
  type: 'test'
  ...
# Subtest: AC2: Escape key restores original masked value
ok 91 - AC2: Escape key restores original masked value
  ---
  duration_ms: 0.184083
  type: 'test'
  ...
# Subtest: AC3: Validation Gate marks field with **** as invalid and blocks submit
ok 92 - AC3: Validation Gate marks field with **** as invalid and blocks submit
  ---
  duration_ms: 0.68754
  type: 'test'
  ...
# Subtest: AC4: Dirty-Tracking includes only modified fields across all 6 fields
ok 93 - AC4: Dirty-Tracking includes only modified fields across all 6 fields
  ---
  duration_ms: 1.190205
  type: 'test'
  ...
# Subtest: AC5: Trimming removes leading and trailing whitespace from input values
ok 94 - AC5: Trimming removes leading and trailing whitespace from input values
  ---
  duration_ms: 0.216916
  type: 'test'
  ...
# Subtest: AC6: Decoupled Key Presence indicator works for short keys (****) and empty keys
ok 95 - AC6: Decoupled Key Presence indicator works for short keys (****) and empty keys
  ---
  duration_ms: 0.403957
  type: 'test'
  ...
# Subtest: AC12: Whitespace-only input is rejected and marked as invalid
ok 96 - AC12: Whitespace-only input is rejected and marked as invalid
  ---
  duration_ms: 0.322833
  type: 'test'
  ...
# Subtest: W1: Blur-Restore restores masked value when user triggers Clear-on-Edit but blurs with empty input
ok 97 - W1: Blur-Restore restores masked value when user triggers Clear-on-Edit but blurs with empty input
  ---
  duration_ms: 0.166749
  type: 'test'
  ...
# Subtest: W1: Blur-Restore restores masked value when user enters whitespace and blurs
ok 98 - W1: Blur-Restore restores masked value when user enters whitespace and blurs
  ---
  duration_ms: 0.105416
  type: 'test'
  ...
# Subtest: W1: Validation treats field cleared via Clear-on-Edit without new value as unchanged (changed=false)
ok 99 - W1: Validation treats field cleared via Clear-on-Edit without new value as unchanged (changed=false)
  ---
  duration_ms: 0.079209
  type: 'test'
  ...
# Subtest: W1: User clears field, types a new valid key, blurs -> new key is preserved and validation reports changed=true
ok 100 - W1: User clears field, types a new valid key, blurs -> new key is preserved and validation reports changed=true
  ---
  duration_ms: 0.125916
  type: 'test'
  ...
# Subtest: W1 / Decision A: Cleared input badge does not claim key removal (Roadmap Item \#59)
ok 101 - W1 / Decision A: Cleared input badge does not claim key removal (Roadmap Item \#59)
  ---
  duration_ms: 0.083249
  type: 'test'
  ...
# Subtest: Item 59 AK1: Configured key (dataset.hasKey='true') offers visible delete button
ok 102 - Item 59 AK1: Configured key (dataset.hasKey='true') offers visible delete button
  ---
  duration_ms: 0.061166
  type: 'test'
  ...
# Subtest: Item 59 AK2: Unconfigured key (dataset.hasKey='false') does not offer active delete button
ok 103 - Item 59 AK2: Unconfigured key (dataset.hasKey='false') does not offer active delete button
  ---
  duration_ms: 0.051333
  type: 'test'
  ...
# Subtest: Item 59 AK3: First click on delete button opens confirmation prompt without clearing input
ok 104 - Item 59 AK3: First click on delete button opens confirmation prompt without clearing input
  ---
  duration_ms: 0.134625
  type: 'test'
  ...
# Subtest: Item 59 AK4: Canceling confirmation prompt restores field to original state
ok 105 - Item 59 AK4: Canceling confirmation prompt restores field to original state
  ---
  duration_ms: 0.313582
  type: 'test'
  ...
# Subtest: Item 59 AK5: Confirming deletion clears input, marks delete flag, and validateMaskedInput reports changed=true with value=''
ok 106 - Item 59 AK5: Confirming deletion clears input, marks delete flag, and validateMaskedInput reports changed=true with value=''
  ---
  duration_ms: 0.606499
  type: 'test'
  ...
# Subtest: Item 59 AK6: Clear-on-Edit without delete confirmation preserves W1 protection (changed=false)
ok 107 - Item 59 AK6: Clear-on-Edit without delete confirmation preserves W1 protection (changed=false)
  ---
  duration_ms: 0.279375
  type: 'test'
  ...
# Subtest: Item 59 AK7: Masked value with **** is rejected and marked invalid regardless of delete flow
ok 108 - Item 59 AK7: Masked value with **** is rejected and marked invalid regardless of delete flow
  ---
  duration_ms: 0.208208
  type: 'test'
  ...
# Subtest: Item 59: Escape key resets delete confirmation and restores original value without bypassing focus path
ok 109 - Item 59: Escape key resets delete confirmation and restores original value without bypassing focus path
  ---
  duration_ms: 0.310332
  type: 'test'
  ...
# Subtest: Item 59: Typing a new value after delete confirmation resets delete flag
ok 110 - Item 59: Typing a new value after delete confirmation resets delete flag
  ---
  duration_ms: 0.111416
  type: 'test'
  ...
# Subtest: Item 59 DOM Structure: All 6 masked-key-field blocks in index.html contain delete button and confirmation dialog
ok 111 - Item 59 DOM Structure: All 6 masked-key-field blocks in index.html contain delete button and confirmation dialog
  ---
  duration_ms: 1.147581
  type: 'test'
  ...
# Subtest: updateMwDataPanel - with mw_data containing url and sync
ok 112 - updateMwDataPanel - with mw_data containing url and sync
  ---
  duration_ms: 9.184352
  type: 'test'
  ...
# Subtest: updateMwDataPanel - without mw_data
ok 113 - updateMwDataPanel - without mw_data
  ---
  duration_ms: 0.0945
  type: 'test'
  ...
# Subtest: prepareSeriesPayload - with mw_data
ok 114 - prepareSeriesPayload - with mw_data
  ---
  duration_ms: 0.263958
  type: 'test'
  ...
# Subtest: prepareSeriesPayload - without mw_data
ok 115 - prepareSeriesPayload - without mw_data
  ---
  duration_ms: 0.06125
  type: 'test'
  ...
# Subtest: updateMwDataPanel - with unsafe scheme source_url
ok 116 - updateMwDataPanel - with unsafe scheme source_url
  ---
  duration_ms: 0.527832
  type: 'test'
  ...
# Subtest: guessSeasonAndEpisode - S01E02-Format
ok 117 - guessSeasonAndEpisode - S01E02-Format
  ---
  duration_ms: 0.541416
  type: 'test'
  ...
# Subtest: guessSeasonAndEpisode - 1x05-Format
ok 118 - guessSeasonAndEpisode - 1x05-Format
  ---
  duration_ms: 0.103333
  type: 'test'
  ...
# Subtest: guessSeasonAndEpisode - Deutsche Formate
ok 119 - guessSeasonAndEpisode - Deutsche Formate
  ---
  duration_ms: 0.177791
  type: 'test'
  ...
# Subtest: guessSeasonAndEpisode - Kein Treffer
ok 120 - guessSeasonAndEpisode - Kein Treffer
  ---
  duration_ms: 0.659749
  type: 'test'
  ...
# Subtest: guessEpisodeNumber - Erkennung aus verschiedenen Formaten
ok 121 - guessEpisodeNumber - Erkennung aus verschiedenen Formaten
  ---
  duration_ms: 0.165125
  type: 'test'
  ...
# Subtest: guessEpisodeNumber - Grenzwerte im Ziffern-Fallback-Pfad
ok 122 - guessEpisodeNumber - Grenzwerte im Ziffern-Fallback-Pfad
  ---
  duration_ms: 0.097416
  type: 'test'
  ...
# Subtest: cleanFilenameForManualTitle - Bereinigungen
ok 123 - cleanFilenameForManualTitle - Bereinigungen
  ---
  duration_ms: 0.353416
  type: 'test'
  ...
# Subtest: cleanFilenameForManualTitle - Leereingaben (Guard)
ok 124 - cleanFilenameForManualTitle - Leereingaben (Guard)
  ---
  duration_ms: 0.061584
  type: 'test'
  ...
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///work/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:2298:40)
#     at loadStatus (eval at setupTestEnvironment (file:///work/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:2271:9)
# Error loading settings: TypeError: undefined is not iterable (cannot read property Symbol(Symbol.iterator))
#     at Function.from (<anonymous>)
#     at eval (eval at setupTestEnvironment (file:///work/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8581:50)
#     at Array.forEach (<anonymous>)
#     at updateDestinationDropdowns (eval at setupTestEnvironment (file:///work/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8564:16)
#     at loadSettings (eval at setupTestEnvironment (file:///work/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8505:13)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///work/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8233:64)
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///work/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:2298:40)
#     at loadStatus (eval at setupTestEnvironment (file:///work/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:2271:9)
# Error loading settings: TypeError: undefined is not iterable (cannot read property Symbol(Symbol.iterator))
#     at Function.from (<anonymous>)
#     at eval (eval at setupTestEnvironment (file:///work/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8581:50)
#     at Array.forEach (<anonymous>)
#     at updateDestinationDropdowns (eval at setupTestEnvironment (file:///work/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8564:16)
#     at loadSettings (eval at setupTestEnvironment (file:///work/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8505:13)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///work/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8233:64)
# Subtest: Profile Dropdown Refresh - Case (a): ok:true and data.success:true refreshes dropdown and logs no error
ok 125 - Profile Dropdown Refresh - Case (a): ok:true and data.success:true refreshes dropdown and logs no error
  ---
  duration_ms: 36.956075
  type: 'test'
  ...
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///work/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:2298:40)
#     at loadStatus (eval at setupTestEnvironment (file:///work/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:2271:9)
# Error loading settings: TypeError: undefined is not iterable (cannot read property Symbol(Symbol.iterator))
#     at Function.from (<anonymous>)
#     at eval (eval at setupTestEnvironment (file:///work/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8581:50)
#     at Array.forEach (<anonymous>)
#     at updateDestinationDropdowns (eval at setupTestEnvironment (file:///work/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8564:16)
#     at loadSettings (eval at setupTestEnvironment (file:///work/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8505:13)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///work/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8233:64)
# Subtest: Profile Dropdown Refresh - Case (b): ok:true and data.success:false logs warning and does not refresh dropdown
ok 126 - Profile Dropdown Refresh - Case (b): ok:true and data.success:false logs warning and does not refresh dropdown
  ---
  duration_ms: 33.184918
  type: 'test'
  ...
# Error fetching status: TypeError: Cannot read properties of undefined (reading 'length')
#     at renderProjectList (eval at setupTestEnvironment (file:///work/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:2298:40)
#     at loadStatus (eval at setupTestEnvironment (file:///work/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:2271:9)
# Error loading settings: TypeError: undefined is not iterable (cannot read property Symbol(Symbol.iterator))
#     at Function.from (<anonymous>)
#     at eval (eval at setupTestEnvironment (file:///work/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8581:50)
#     at Array.forEach (<anonymous>)
#     at updateDestinationDropdowns (eval at setupTestEnvironment (file:///work/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8564:16)
#     at loadSettings (eval at setupTestEnvironment (file:///work/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8505:13)
# Error loading dashboard data: TypeError: Cannot read properties of undefined (reading 'name')
#     at loadDashboard (eval at setupTestEnvironment (file:///work/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:8233:64)
# Error saving show profile on execution: Error: Failed to fetch network error
#     at mockFetch (file:///work/tests/frontend/profile_dropdown_refresh.test.js:155:23)
#     at Object.eval (eval at setupTestEnvironment (file:///work/tests/frontend/profile_dropdown_refresh.test.js:212:5), <anonymous>:10569:40)
#     at Object.dispatchEvent (file:///work/tests/frontend/profile_dropdown_refresh.test.js:37:31)
#     at TestContext.<anonymous> (file:///work/tests/frontend/profile_dropdown_refresh.test.js:339:22)
#     at async Test.run (node:internal/test_runner/test:1054:7)
#     at async Test.processPendingSubtests (node:internal/test_runner/test:744:7)
# Subtest: Profile Dropdown Refresh - Case (c): ok:false (HTTP 500) logs connection error and does not refresh dropdown
ok 127 - Profile Dropdown Refresh - Case (c): ok:false (HTTP 500) logs connection error and does not refresh dropdown
  ---
  duration_ms: 25.62252
  type: 'test'
  ...
# Subtest: Profile Dropdown Refresh - Case (d): Network exception / invalid JSON logs connection error and processing continues
ok 128 - Profile Dropdown Refresh - Case (d): Network exception / invalid JSON logs connection error and processing continues
  ---
  duration_ms: 28.146722
  type: 'test'
  ...
# Subtest: DOM Structure & Styling: index.html contains settings-app-theme-error with theme class and no inline style
ok 129 - DOM Structure & Styling: index.html contains settings-app-theme-error with theme class and no inline style
  ---
  duration_ms: 2.540368
  type: 'test'
  ...
# Subtest: Theme Autosave AK1 & AK3 & AK5: non-ok response shows visible informative error and logs console.error
ok 130 - Theme Autosave AK1 & AK3 & AK5: non-ok response shows visible informative error and logs console.error
  ---
  duration_ms: 3.379616
  type: 'test'
  ...
# Subtest: Theme Autosave AK2 & AK3 & AK5: network exception in catch block shows visible informative error and logs console.error
ok 131 - Theme Autosave AK2 & AK3 & AK5: network exception in catch block shows visible informative error and logs console.error
  ---
  duration_ms: 3.180908
  type: 'test'
  ...
# Subtest: Theme Autosave AK4: successful save clears any previous error and keeps error hidden
ok 132 - Theme Autosave AK4: successful save clears any previous error and keeps error hidden
  ---
  duration_ms: 1.603246
  type: 'test'
  ...
# Subtest: Roadmap: Item 60 retains deferred context and reason in ROADMAP.md
ok 133 - Roadmap: Item 60 retains deferred context and reason in ROADMAP.md
  ---
  duration_ms: 0.936956
  type: 'test'
  ...
# Subtest: Theme Autosave Guard: second theme change aborts previous in-flight request and shows no error
ok 134 - Theme Autosave Guard: second theme change aborts previous in-flight request and shows no error
  ---
  duration_ms: 1.540955
  type: 'test'
  ...
# Subtest: Theme Autosave Guard: AbortError from fetch does not trigger error message or console.error
ok 135 - Theme Autosave Guard: AbortError from fetch does not trigger error message or console.error
  ---
  duration_ms: 1.433538
  type: 'test'
  ...
# Subtest: Roadmap: Item 62 retains deferred context and reason in ROADMAP.md
ok 136 - Roadmap: Item 62 retains deferred context and reason in ROADMAP.md
  ---
  duration_ms: 0.404249
  type: 'test'
  ...
# Subtest: cleanSeriesName - Leereingaben
ok 137 - cleanSeriesName - Leereingaben
  ---
  duration_ms: 0.506832
  type: 'test'
  ...
# Subtest: cleanSeriesName - Unterstriche ersetzen
ok 138 - cleanSeriesName - Unterstriche ersetzen
  ---
  duration_ms: 0.303082
  type: 'test'
  ...
# Subtest: cleanSeriesName - Mediathek- und URL-Sonderklammern entfernen
ok 139 - cleanSeriesName - Mediathek- und URL-Sonderklammern entfernen
  ---
  duration_ms: 0.168208
  type: 'test'
  ...
# Subtest: cleanSeriesName - Kanal-Tags / Bracket-Tags am Ende entfernen (wiederholt)
ok 140 - cleanSeriesName - Kanal-Tags / Bracket-Tags am Ende entfernen (wiederholt)
  ---
  duration_ms: 0.084625
  type: 'test'
  ...
# Subtest: cleanSeriesName - Kombination und Trimming
ok 141 - cleanSeriesName - Kombination und Trimming
  ---
  duration_ms: 0.919789
  type: 'test'
  ...
# Subtest: fetchStats - success
ok 142 - fetchStats - success
  ---
  duration_ms: 0.588457
  type: 'test'
  ...
# Subtest: fetchStats - non-ok status
ok 143 - fetchStats - non-ok status
  ---
  duration_ms: 0.123417
  type: 'test'
  ...
# Subtest: fetchStats - network error
ok 144 - fetchStats - network error
  ---
  duration_ms: 0.791873
  type: 'test'
  ...
# Subtest: fetchYoutubeSubscriptions - success
ok 145 - fetchYoutubeSubscriptions - success
  ---
  duration_ms: 0.087083
  type: 'test'
  ...
# Subtest: fetchYoutubeSubscriptions - non-ok status
ok 146 - fetchYoutubeSubscriptions - non-ok status
  ---
  duration_ms: 0.058333
  type: 'test'
  ...
# Subtest: fetchYoutubeSubscriptions - network error
ok 147 - fetchYoutubeSubscriptions - network error
  ---
  duration_ms: 0.077875
  type: 'test'
  ...
# Subtest: fetchSmartInboxSuggestions - success
ok 148 - fetchSmartInboxSuggestions - success
  ---
  duration_ms: 0.08125
  type: 'test'
  ...
# Subtest: fetchSmartInboxSuggestions - non-ok status
ok 149 - fetchSmartInboxSuggestions - non-ok status
  ---
  duration_ms: 0.057875
  type: 'test'
  ...
# Subtest: fetchSmartInboxSuggestions - network error
ok 150 - fetchSmartInboxSuggestions - network error
  ---
  duration_ms: 0.289125
  type: 'test'
  ...
1..150
# tests 150
# suites 0
# pass 150
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 450.442551
npm notice
npm notice New major version of npm available! 10.9.8 -> 12.2.0
npm notice Changelog: https://github.com/npm/cli/releases/tag/v12.2.0
npm notice To update run: npm install -g npm@12.2.0
npm notice
exit=0
```
