# AK0 — Ausgangsmessung #64 (vor dem Gate-A2-Lauf)

Ausgeführt von Claude Code, 2026-10-08 (2026-10-08T10:05:32Z bis 2026-10-08T10:06:05Z), auf einem `git clone` des Worktrees `feat/roadmap-64-inbox-sortierbar` @ `288130a` (Codestand = `main`, vor jeder #64-Änderung), im Worker-Image `openhands-agy-worker:1.2.12`.

Befehl:

```
docker run --rm --entrypoint /bin/sh -v <clone>:/work -w /work openhands-agy-worker:1.2.12 -c "python3 -m pip install -q --user --break-system-packages -r requirements.txt pytest && python3 -m pytest -q -p no:cacheprovider --deselect tests/test_utils.py::TestMediawerkzeugLogic::test_conversion_estimation_test_encode && npm run test:frontend"
```

Ergebnis: **478 passed, 1 deselected** (pytest) und **138/138** (Frontend), Exit 0.

Wörtliche Ausgabe (einzige Änderung: 0 Zeilen mit Trailing Whitespace am Zeilenende gekürzt, Pre-Commit-Hook; Original: Kit `scripts/gate-a2/logs/2026-10-08-roadmap64-65/ak0-output.txt`):

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
........................................................................ [ 15%]
........................................................................ [ 30%]
........................................................................ [ 45%]
........................................................................ [ 60%]
........................................................................ [ 75%]
........................................................................ [ 90%]
..............................................                           [100%]
=============================== warnings summary ===============================
tests/test_onboarding.py::TestOnboarding::test_complete_and_skip_endpoints
  /work/gui/core/telemetry.py:42: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    "timestamp": datetime.datetime.utcnow().isoformat() + "Z"

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
478 passed, 1 deselected, 1 warning in 26.96s

> medienwerkzeug@1.3.0 test:frontend
> node --test "tests/frontend/**/*.test.js"

TAP version 13
# Subtest: renderHealthStatus - warning state renders warning alert, not success
ok 1 - renderHealthStatus - warning state renders warning alert, not success
  ---
  duration_ms: 1.051557
  type: 'test'
  ...
# Subtest: renderDuplicateStatus - warning state renders warning alert, not success
ok 2 - renderDuplicateStatus - warning state renders warning alert, not success
  ---
  duration_ms: 0.239379
  type: 'test'
  ...
# Subtest: loadNormalizePreview - status 400 shows warning alert, not success
ok 3 - loadNormalizePreview - status 400 shows warning alert, not success
  ---
  duration_ms: 0.142586
  type: 'test'
  ...
# Subtest: renderNormalizePlan - 1 item renders Singular "Vorschlag"
ok 4 - renderNormalizePlan - 1 item renders Singular "Vorschlag"
  ---
  duration_ms: 0.112418
  type: 'test'
  ...
# Subtest: renderNormalizePlan - 2 items renders Plural "Vorschläge"
ok 5 - renderNormalizePlan - 2 items renders Plural "Vorschläge"
  ---
  duration_ms: 0.102044
  type: 'test'
  ...
# Subtest: renderNormalizePlan - empty plan renders neutral empty state without emoji
ok 6 - renderNormalizePlan - empty plan renders neutral empty state without emoji
  ---
  duration_ms: 0.065709
  type: 'test'
  ...
# Subtest: renderQueue - pipeline step message uses existing HTML escaping helper
ok 7 - renderQueue - pipeline step message uses existing HTML escaping helper
  ---
  duration_ms: 0.656135
  type: 'test'
  ...
# Subtest: renderHealthStatus - renders summary chips with total and group counts and no severity grouping
ok 8 - renderHealthStatus - renders summary chips with total and group counts and no severity grouping
  ---
  duration_ms: 12.40027
  type: 'test'
  ...
# Subtest: renderHealthStatus - type grouping renders type groups, checkboxes and tool-connectors
ok 9 - renderHealthStatus - type grouping renders type groups, checkboxes and tool-connectors
  ---
  duration_ms: 0.408298
  type: 'test'
  ...
# Subtest: renderHealthStatus - only nested_duplicate / structure issues displays tab specific empty state on media tab
ok 10 - renderHealthStatus - only nested_duplicate / structure issues displays tab specific empty state on media tab
  ---
  duration_ms: 0.31913
  type: 'test'
  ...
# Subtest: renderHealthStatus - structure-only result wires structure batch button
ok 11 - renderHealthStatus - structure-only result wires structure batch button
  ---
  duration_ms: 0.13171
  type: 'test'
  ...
# Subtest: renderHealthStatus - transition running -> warning clears loading spinner and hides structure container
ok 12 - renderHealthStatus - transition running -> warning clears loading spinner and hides structure container
  ---
  duration_ms: 0.090002
  type: 'test'
  ...
# Subtest: renderNfoAgentFiles - mediaType tvshow renders tvshow.nfo status matrix
ok 13 - renderNfoAgentFiles - mediaType tvshow renders tvshow.nfo status matrix
  ---
  duration_ms: 0.414464
  type: 'test'
  ...
# Subtest: NFO Agent combines the main NFO status with the metadata editor
ok 14 - NFO Agent combines the main NFO status with the metadata editor
  ---
  duration_ms: 0.806678
  type: 'test'
  ...
# Subtest: NFO Agent movie mode renders movie.nfo without series controls
ok 15 - NFO Agent movie mode renders movie.nfo without series controls
  ---
  duration_ms: 0.119252
  type: 'test'
  ...
# Subtest: submitNfoAgentJob - payload structures and write_show_nfo semantics
ok 16 - submitNfoAgentJob - payload structures and write_show_nfo semantics
  ---
  duration_ms: 0.691635
  type: 'test'
  ...
# Subtest: NFO Agent shows a calm non-blocking completeness hint
ok 17 - NFO Agent shows a calm non-blocking completeness hint
  ---
  duration_ms: 0.073376
  type: 'test'
  ...
# Subtest: waitForServerRestart succeeds after a temporary connection failure
ok 18 - waitForServerRestart succeeds after a temporary connection failure
  ---
  duration_ms: 0.116168
  type: 'test'
  ...
# Subtest: waitForServerRestart stops after the configured attempt limit
ok 19 - waitForServerRestart stops after the configured attempt limit
  ---
  duration_ms: 0.082501
  type: 'test'
  ...
# Subtest: restoreServerRestartButton clears the loading state
ok 20 - restoreServerRestartButton clears the loading state
  ---
  duration_ms: 0.046501
  type: 'test'
  ...
# Subtest: Cache-Busting: index.html app.js version matches all ES-module import versions in app.js
ok 21 - Cache-Busting: index.html app.js version matches all ES-module import versions in app.js
  ---
  duration_ms: 3.222591
  type: 'test'
  ...
# Subtest: Cache-Busting: style.css in index.html has a non-empty ?v= version query
ok 22 - Cache-Busting: style.css in index.html has a non-empty ?v= version query
  ---
  duration_ms: 1.173393
  type: 'test'
  ...
# Subtest: Cache-Busting: utilities.css in index.html has a non-empty ?v= version query
ok 23 - Cache-Busting: utilities.css in index.html has a non-empty ?v= version query
  ---
  duration_ms: 0.472591
  type: 'test'
  ...
# Subtest: formatBytes - Nullwert
ok 24 - formatBytes - Nullwert
  ---
  duration_ms: 0.34213
  type: 'test'
  ...
# Subtest: formatBytes - Werte unter 1 KB
ok 25 - formatBytes - Werte unter 1 KB
  ---
  duration_ms: 0.077876
  type: 'test'
  ...
# Subtest: formatBytes - Einheiten und Schwellenwerte
ok 26 - formatBytes - Einheiten und Schwellenwerte
  ---
  duration_ms: 0.10521
  type: 'test'
  ...
# Subtest: formatBytes - Nachkommastellen und Rundung
ok 27 - formatBytes - Nachkommastellen und Rundung
  ---
  duration_ms: 0.073584
  type: 'test'
  ...
# Subtest: osBasename - extracts filename correctly
ok 28 - osBasename - extracts filename correctly
  ---
  duration_ms: 0.374923
  type: 'test'
  ...
# Subtest: formatFskLabel - formats FSK labels correctly
ok 29 - formatFskLabel - formats FSK labels correctly
  ---
  duration_ms: 0.094418
  type: 'test'
  ...
# Subtest: resolveSendPaths - resolves hierarchy properly
ok 30 - resolveSendPaths - resolves hierarchy properly
  ---
  duration_ms: 0.894888
  type: 'test'
  ...
# Subtest: openFskBatchModal - opens modal and sets up state
ok 31 - openFskBatchModal - opens modal and sets up state
  ---
  duration_ms: 0.503383
  type: 'test'
  ...
# Subtest: Scope-Change-Event - triggers new preview fetch
ok 32 - Scope-Change-Event - triggers new preview fetch
  ---
  duration_ms: 21.788203
  type: 'test'
  ...
# Subtest: Null-Ziel-Sperre im DOM
ok 33 - Null-Ziel-Sperre im DOM
  ---
  duration_ms: 23.224267
  type: 'test'
  ...
# Subtest: Apply-Fetch-Payload and preview rendering
ok 34 - Apply-Fetch-Payload and preview rendering
  ---
  duration_ms: 12.128225
  type: 'test'
  ...
# Subtest: Darstellung von partial und failed
ok 35 - Darstellung von partial und failed
  ---
  duration_ms: 23.105973
  type: 'test'
  ...
# Subtest: No native Dialogs and Inline Error Rendering
ok 36 - No native Dialogs and Inline Error Rendering
  ---
  duration_ms: 12.676483
  type: 'test'
  ...
# Subtest: Dynamic Button Text and Disabled State
ok 37 - Dynamic Button Text and Disabled State
  ---
  duration_ms: 21.494533
  type: 'test'
  ...
# Subtest: Apply payload includes status field
ok 38 - Apply payload includes status field
  ---
  duration_ms: 23.121474
  type: 'test'
  ...
# Subtest: show-group-fsk-btn click - triggers openFskBatchModal and fetches series scope
ok 39 - show-group-fsk-btn click - triggers openFskBatchModal and fetches series scope
  ---
  duration_ms: 1.203477
  type: 'test'
  ...
# Subtest: season-group-fsk-btn click - triggers openFskBatchModal and fetches season scope
ok 40 - season-group-fsk-btn click - triggers openFskBatchModal and fetches season scope
  ---
  duration_ms: 0.271546
  type: 'test'
  ...
# Subtest: Out-of-order preview requests are correctly discarded
ok 41 - Out-of-order preview requests are correctly discarded
  ---
  duration_ms: 0.154502
  type: 'test'
  ...
# Subtest: Modal direct scope and prevent dual requests
ok 42 - Modal direct scope and prevent dual requests
  ---
  duration_ms: 0.068543
  type: 'test'
  ...
# Subtest: 409 Conflict keeps error message visible after preview load
ok 43 - 409 Conflict keeps error message visible after preview load
  ---
  duration_ms: 45.668231
  type: 'test'
  ...
# Subtest: Apply-Lock blocks closeFskBatchModal
ok 44 - Apply-Lock blocks closeFskBatchModal
  ---
  duration_ms: 0.161002
  type: 'test'
  ...
# Subtest: Media view routes series, season and episode metadata actions through the NFO Agent
ok 45 - Media view routes series, season and episode metadata actions through the NFO Agent
  ---
  duration_ms: 0.608426
  type: 'test'
  ...
# Subtest: Media summary stays calm and exposes exact actions only in details
ok 46 - Media summary stays calm and exposes exact actions only in details
  ---
  duration_ms: 0.589467
  type: 'test'
  ...
# Subtest: Media view separates season findings from collapsible episode metadata findings
ok 47 - Media view separates season findings from collapsible episode metadata findings
  ---
  duration_ms: 0.225879
  type: 'test'
  ...
# Subtest: Scoped ignore modal lists present issue types grouped by catalog group and posts the exact scope
ok 48 - Scoped ignore modal lists present issue types grouped by catalog group and posts the exact scope
  ---
  duration_ms: 5.652085
  type: 'test'
  ...
# Subtest: Media view separates series and movies into tabs with counts
ok 49 - Media view separates series and movies into tabs with counts
  ---
  duration_ms: 0.199795
  type: 'test'
  ...
# Subtest: Scoped ignore modal is static, explicit, and reversible
ok 50 - Scoped ignore modal is static, explicit, and reversible
  ---
  duration_ms: 0.955348
  type: 'test'
  ...
# Subtest: Media-oriented movie view treats invalid FSK as a metadata problem
ok 51 - Media-oriented movie view treats invalid FSK as a metadata problem
  ---
  duration_ms: 0.208753
  type: 'test'
  ...
# Subtest: Media view does not resurrect an ignored missing series NFO from structural status
ok 52 - Media view does not resurrect an ignored missing series NFO from structural status
  ---
  duration_ms: 0.056834
  type: 'test'
  ...
# Subtest: nfo_missing visibility and action suppression
ok 53 - nfo_missing visibility and action suppression
  ---
  duration_ms: 0.707011
  type: 'test'
  ...
# Subtest: Film-Rendering in FSK Modal uses media_kind
ok 54 - Film-Rendering in FSK Modal uses media_kind
  ---
  duration_ms: 12.345228
  type: 'test'
  ...
# Subtest: Successful apply leaves one terminal action and refreshes health immediately
ok 55 - Successful apply leaves one terminal action and refreshes health immediately
  ---
  duration_ms: 13.148365
  type: 'test'
  ...
# Subtest: NFO-Agent rendered in skipped_missing
ok 56 - NFO-Agent rendered in skipped_missing
  ---
  duration_ms: 12.174101
  type: 'test'
  ...
# Subtest: Fertig-Klick bei ready=0 schliesst Modal
ok 57 - Fertig-Klick bei ready=0 schliesst Modal
  ---
  duration_ms: 21.310072
  type: 'test'
  ...
# Subtest: NFO Agent Lifecycle wertet done, error, cancelled und fehlende Queue-Jobs aus
ok 58 - NFO Agent Lifecycle wertet done, error, cancelled und fehlende Queue-Jobs aus
  ---
  duration_ms: 26.231645
  type: 'test'
  ...
# Error: TMDB-Filmmetadaten konnten nicht geladen werden: timed out
#     at eval (eval at <anonymous> (file:///work/tests/frontend/fsk_batch_dom.test.js:236:1), <anonymous>:16116:35)
# Subtest: Escaping-Sicherheit bei NFO-Agent-Event-Delegation
ok 59 - Escaping-Sicherheit bei NFO-Agent-Event-Delegation
  ---
  duration_ms: 13.817042
  type: 'test'
  ...
# Subtest: NFO Agent switches between entry context and whole-series editing
ok 60 - NFO Agent switches between entry context and whole-series editing
  ---
  duration_ms: 0.441256
  type: 'test'
  ...
# Subtest: Submit label reflects the visible episode fields in season mode
ok 61 - Submit label reflects the visible episode fields in season mode
  ---
  duration_ms: 0.344797
  type: 'test'
  ...
# Subtest: Mediathek search result switches to manual entry instead of a TVDB fetch
ok 62 - Mediathek search result switches to manual entry instead of a TVDB fetch
  ---
  duration_ms: 0.084918
  type: 'test'
  ...
# Error: TMDB-Filmmetadaten konnten nicht geladen werden: timed out
#     at eval (eval at <anonymous> (file:///work/tests/frontend/fsk_batch_dom.test.js:236:1), <anonymous>:16116:35)
# Subtest: Failed detail loads render an inline retry action instead of an alert
ok 63 - Failed detail loads render an inline retry action instead of an alert
  ---
  duration_ms: 5.903589
  type: 'test'
  ...
# Subtest: NFO Agent hides the back button when whole-series is the entry point
ok 64 - NFO Agent hides the back button when whole-series is the entry point
  ---
  duration_ms: 0.180586
  type: 'test'
  ...
# Subtest: NFO Agent submits manually when no provider ID is given
ok 65 - NFO Agent submits manually when no provider ID is given
  ---
  duration_ms: 0.336172
  type: 'test'
  ...
# Subtest: NFO Agent season mode edits the season without writing the series NFO
ok 66 - NFO Agent season mode edits the season without writing the series NFO
  ---
  duration_ms: 0.215712
  type: 'test'
  ...
# Subtest: NFO Agent episode mode submits only the selected episode
ok 67 - NFO Agent episode mode submits only the selected episode
  ---
  duration_ms: 0.295422
  type: 'test'
  ...
# Subtest: NFO Agent uses concise mode controls and clear missing-source copy
ok 68 - NFO Agent uses concise mode controls and clear missing-source copy
  ---
  duration_ms: 1.039807
  type: 'test'
  ...
# Subtest: Type-oriented episode findings preserve the focused episode context
ok 69 - Type-oriented episode findings preserve the focused episode context
  ---
  duration_ms: 1.276227
  type: 'test'
  ...
# Subtest: updateHintElement - recInfo is null
ok 70 - updateHintElement - recInfo is null
  ---
  duration_ms: 0.432256
  type: 'test'
  ...
# Subtest: updateHintElement - recInfo is undefined
ok 71 - updateHintElement - recInfo is undefined
  ---
  duration_ms: 0.060793
  type: 'test'
  ...
# Subtest: updateHintElement - currentVal equals optimal
ok 72 - updateHintElement - currentVal equals optimal
  ---
  duration_ms: 0.055376
  type: 'test'
  ...
# Subtest: updateHintElement - currentVal is greater than optimal
ok 73 - updateHintElement - currentVal is greater than optimal
  ---
  duration_ms: 0.054209
  type: 'test'
  ...
# Subtest: updateHintElement - currentVal is less than optimal
ok 74 - updateHintElement - currentVal is less than optimal
  ---
  duration_ms: 0.619467
  type: 'test'
  ...
# Subtest: isMaskedValue detects masked strings correctly
ok 75 - isMaskedValue detects masked strings correctly
  ---
  duration_ms: 0.569675
  type: 'test'
  ...
# Subtest: AC1: Clear-on-Edit clears masked field on first keypress, not on focus
ok 76 - AC1: Clear-on-Edit clears masked field on first keypress, not on focus
  ---
  duration_ms: 0.489382
  type: 'test'
  ...
# Subtest: AC1: Clear-on-Edit with Backspace / Delete clears entire mask cleanly
ok 77 - AC1: Clear-on-Edit with Backspace / Delete clears entire mask cleanly
  ---
  duration_ms: 0.107043
  type: 'test'
  ...
# Subtest: AC2: Blur-Restore restores masked value when focused and left without edit
ok 78 - AC2: Blur-Restore restores masked value when focused and left without edit
  ---
  duration_ms: 0.159669
  type: 'test'
  ...
# Subtest: AC2: Escape key restores original masked value
ok 79 - AC2: Escape key restores original masked value
  ---
  duration_ms: 0.102377
  type: 'test'
  ...
# Subtest: AC3: Validation Gate marks field with **** as invalid and blocks submit
ok 80 - AC3: Validation Gate marks field with **** as invalid and blocks submit
  ---
  duration_ms: 0.294921
  type: 'test'
  ...
# Subtest: AC4: Dirty-Tracking includes only modified fields across all 6 fields
ok 81 - AC4: Dirty-Tracking includes only modified fields across all 6 fields
  ---
  duration_ms: 0.763136
  type: 'test'
  ...
# Subtest: AC5: Trimming removes leading and trailing whitespace from input values
ok 82 - AC5: Trimming removes leading and trailing whitespace from input values
  ---
  duration_ms: 0.067168
  type: 'test'
  ...
# Subtest: AC6: Decoupled Key Presence indicator works for short keys (****) and empty keys
ok 83 - AC6: Decoupled Key Presence indicator works for short keys (****) and empty keys
  ---
  duration_ms: 0.32363
  type: 'test'
  ...
# Subtest: AC12: Whitespace-only input is rejected and marked as invalid
ok 84 - AC12: Whitespace-only input is rejected and marked as invalid
  ---
  duration_ms: 0.27192
  type: 'test'
  ...
# Subtest: W1: Blur-Restore restores masked value when user triggers Clear-on-Edit but blurs with empty input
ok 85 - W1: Blur-Restore restores masked value when user triggers Clear-on-Edit but blurs with empty input
  ---
  duration_ms: 0.119502
  type: 'test'
  ...
# Subtest: W1: Blur-Restore restores masked value when user enters whitespace and blurs
ok 86 - W1: Blur-Restore restores masked value when user enters whitespace and blurs
  ---
  duration_ms: 0.057751
  type: 'test'
  ...
# Subtest: W1: Validation treats field cleared via Clear-on-Edit without new value as unchanged (changed=false)
ok 87 - W1: Validation treats field cleared via Clear-on-Edit without new value as unchanged (changed=false)
  ---
  duration_ms: 0.059335
  type: 'test'
  ...
# Subtest: W1: User clears field, types a new valid key, blurs -> new key is preserved and validation reports changed=true
ok 88 - W1: User clears field, types a new valid key, blurs -> new key is preserved and validation reports changed=true
  ---
  duration_ms: 0.10896
  type: 'test'
  ...
# Subtest: W1 / Decision A: Cleared input badge does not claim key removal (Roadmap Item \#59)
ok 89 - W1 / Decision A: Cleared input badge does not claim key removal (Roadmap Item \#59)
  ---
  duration_ms: 0.077377
  type: 'test'
  ...
# Subtest: Item 59 AK1: Configured key (dataset.hasKey='true') offers visible delete button
ok 90 - Item 59 AK1: Configured key (dataset.hasKey='true') offers visible delete button
  ---
  duration_ms: 0.060042
  type: 'test'
  ...
# Subtest: Item 59 AK2: Unconfigured key (dataset.hasKey='false') does not offer active delete button
ok 91 - Item 59 AK2: Unconfigured key (dataset.hasKey='false') does not offer active delete button
  ---
  duration_ms: 0.052084
  type: 'test'
  ...
# Subtest: Item 59 AK3: First click on delete button opens confirmation prompt without clearing input
ok 92 - Item 59 AK3: First click on delete button opens confirmation prompt without clearing input
  ---
  duration_ms: 0.129502
  type: 'test'
  ...
# Subtest: Item 59 AK4: Canceling confirmation prompt restores field to original state
ok 93 - Item 59 AK4: Canceling confirmation prompt restores field to original state
  ---
  duration_ms: 0.085002
  type: 'test'
  ...
# Subtest: Item 59 AK5: Confirming deletion clears input, marks delete flag, and validateMaskedInput reports changed=true with value=''
ok 94 - Item 59 AK5: Confirming deletion clears input, marks delete flag, and validateMaskedInput reports changed=true with value=''
  ---
  duration_ms: 0.183253
  type: 'test'
  ...
# Subtest: Item 59 AK6: Clear-on-Edit without delete confirmation preserves W1 protection (changed=false)
ok 95 - Item 59 AK6: Clear-on-Edit without delete confirmation preserves W1 protection (changed=false)
  ---
  duration_ms: 0.061001
  type: 'test'
  ...
# Subtest: Item 59 AK7: Masked value with **** is rejected and marked invalid regardless of delete flow
ok 96 - Item 59 AK7: Masked value with **** is rejected and marked invalid regardless of delete flow
  ---
  duration_ms: 0.053168
  type: 'test'
  ...
# Subtest: Item 59: Escape key resets delete confirmation and restores original value without bypassing focus path
ok 97 - Item 59: Escape key resets delete confirmation and restores original value without bypassing focus path
  ---
  duration_ms: 0.073334
  type: 'test'
  ...
# Subtest: Item 59: Typing a new value after delete confirmation resets delete flag
ok 98 - Item 59: Typing a new value after delete confirmation resets delete flag
  ---
  duration_ms: 0.057959
  type: 'test'
  ...
# Subtest: Item 59 DOM Structure: All 6 masked-key-field blocks in index.html contain delete button and confirmation dialog
ok 99 - Item 59 DOM Structure: All 6 masked-key-field blocks in index.html contain delete button and confirmation dialog
  ---
  duration_ms: 1.102184
  type: 'test'
  ...
# Subtest: updateMwDataPanel - with mw_data containing url and sync
ok 100 - updateMwDataPanel - with mw_data containing url and sync
  ---
  duration_ms: 8.94751
  type: 'test'
  ...
# Subtest: updateMwDataPanel - without mw_data
ok 101 - updateMwDataPanel - without mw_data
  ---
  duration_ms: 0.067918
  type: 'test'
  ...
# Subtest: prepareSeriesPayload - with mw_data
ok 102 - prepareSeriesPayload - with mw_data
  ---
  duration_ms: 0.204462
  type: 'test'
  ...
# Subtest: prepareSeriesPayload - without mw_data
ok 103 - prepareSeriesPayload - without mw_data
  ---
  duration_ms: 0.061876
  type: 'test'
  ...
# Subtest: updateMwDataPanel - with unsafe scheme source_url
ok 104 - updateMwDataPanel - with unsafe scheme source_url
  ---
  duration_ms: 0.529508
  type: 'test'
  ...
# Subtest: guessSeasonAndEpisode - S01E02-Format
ok 105 - guessSeasonAndEpisode - S01E02-Format
  ---
  duration_ms: 0.545508
  type: 'test'
  ...
# Subtest: guessSeasonAndEpisode - 1x05-Format
ok 106 - guessSeasonAndEpisode - 1x05-Format
  ---
  duration_ms: 0.099877
  type: 'test'
  ...
# Subtest: guessSeasonAndEpisode - Deutsche Formate
ok 107 - guessSeasonAndEpisode - Deutsche Formate
  ---
  duration_ms: 0.208045
  type: 'test'
  ...
# Subtest: guessSeasonAndEpisode - Kein Treffer
ok 108 - guessSeasonAndEpisode - Kein Treffer
  ---
  duration_ms: 0.565383
  type: 'test'
  ...
# Subtest: guessEpisodeNumber - Erkennung aus verschiedenen Formaten
ok 109 - guessEpisodeNumber - Erkennung aus verschiedenen Formaten
  ---
  duration_ms: 0.155544
  type: 'test'
  ...
# Subtest: guessEpisodeNumber - Grenzwerte im Ziffern-Fallback-Pfad
ok 110 - guessEpisodeNumber - Grenzwerte im Ziffern-Fallback-Pfad
  ---
  duration_ms: 0.078835
  type: 'test'
  ...
# Subtest: cleanFilenameForManualTitle - Bereinigungen
ok 111 - cleanFilenameForManualTitle - Bereinigungen
  ---
  duration_ms: 0.242795
  type: 'test'
  ...
# Subtest: cleanFilenameForManualTitle - Leereingaben (Guard)
ok 112 - cleanFilenameForManualTitle - Leereingaben (Guard)
  ---
  duration_ms: 0.047667
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
ok 113 - Profile Dropdown Refresh - Case (a): ok:true and data.success:true refreshes dropdown and logs no error
  ---
  duration_ms: 39.580764
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
ok 114 - Profile Dropdown Refresh - Case (b): ok:true and data.success:false logs warning and does not refresh dropdown
  ---
  duration_ms: 36.383174
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
ok 115 - Profile Dropdown Refresh - Case (c): ok:false (HTTP 500) logs connection error and does not refresh dropdown
  ---
  duration_ms: 23.597273
  type: 'test'
  ...
# Subtest: Profile Dropdown Refresh - Case (d): Network exception / invalid JSON logs connection error and processing continues
ok 116 - Profile Dropdown Refresh - Case (d): Network exception / invalid JSON logs connection error and processing continues
  ---
  duration_ms: 25.561803
  type: 'test'
  ...
# Subtest: DOM Structure & Styling: index.html contains settings-app-theme-error with theme class and no inline style
ok 117 - DOM Structure & Styling: index.html contains settings-app-theme-error with theme class and no inline style
  ---
  duration_ms: 1.6399
  type: 'test'
  ...
# Subtest: Theme Autosave AK1 & AK3 & AK5: non-ok response shows visible informative error and logs console.error
ok 118 - Theme Autosave AK1 & AK3 & AK5: non-ok response shows visible informative error and logs console.error
  ---
  duration_ms: 2.340993
  type: 'test'
  ...
# Subtest: Theme Autosave AK2 & AK3 & AK5: network exception in catch block shows visible informative error and logs console.error
ok 119 - Theme Autosave AK2 & AK3 & AK5: network exception in catch block shows visible informative error and logs console.error
  ---
  duration_ms: 1.913946
  type: 'test'
  ...
# Subtest: Theme Autosave AK4: successful save clears any previous error and keeps error hidden
ok 120 - Theme Autosave AK4: successful save clears any previous error and keeps error hidden
  ---
  duration_ms: 1.546649
  type: 'test'
  ...
# Subtest: Roadmap: Item 60 retains deferred context and reason in ROADMAP.md
ok 121 - Roadmap: Item 60 retains deferred context and reason in ROADMAP.md
  ---
  duration_ms: 0.440048
  type: 'test'
  ...
# Subtest: Theme Autosave Guard: second theme change aborts previous in-flight request and shows no error
ok 122 - Theme Autosave Guard: second theme change aborts previous in-flight request and shows no error
  ---
  duration_ms: 1.27902
  type: 'test'
  ...
# Subtest: Theme Autosave Guard: AbortError from fetch does not trigger error message or console.error
ok 123 - Theme Autosave Guard: AbortError from fetch does not trigger error message or console.error
  ---
  duration_ms: 1.354562
  type: 'test'
  ...
# Subtest: Roadmap: Item 62 retains deferred context and reason in ROADMAP.md
ok 124 - Roadmap: Item 62 retains deferred context and reason in ROADMAP.md
  ---
  duration_ms: 0.381714
  type: 'test'
  ...
# Subtest: cleanSeriesName - Leereingaben
ok 125 - cleanSeriesName - Leereingaben
  ---
  duration_ms: 0.383672
  type: 'test'
  ...
# Subtest: cleanSeriesName - Unterstriche ersetzen
ok 126 - cleanSeriesName - Unterstriche ersetzen
  ---
  duration_ms: 0.260296
  type: 'test'
  ...
# Subtest: cleanSeriesName - Mediathek- und URL-Sonderklammern entfernen
ok 127 - cleanSeriesName - Mediathek- und URL-Sonderklammern entfernen
  ---
  duration_ms: 0.119293
  type: 'test'
  ...
# Subtest: cleanSeriesName - Kanal-Tags / Bracket-Tags am Ende entfernen (wiederholt)
ok 128 - cleanSeriesName - Kanal-Tags / Bracket-Tags am Ende entfernen (wiederholt)
  ---
  duration_ms: 0.066918
  type: 'test'
  ...
# Subtest: cleanSeriesName - Kombination und Trimming
ok 129 - cleanSeriesName - Kombination und Trimming
  ---
  duration_ms: 0.586384
  type: 'test'
  ...
# Subtest: fetchStats - success
ok 130 - fetchStats - success
  ---
  duration_ms: 0.625218
  type: 'test'
  ...
# Subtest: fetchStats - non-ok status
ok 131 - fetchStats - non-ok status
  ---
  duration_ms: 0.118877
  type: 'test'
  ...
# Subtest: fetchStats - network error
ok 132 - fetchStats - network error
  ---
  duration_ms: 0.722719
  type: 'test'
  ...
# Subtest: fetchYoutubeSubscriptions - success
ok 133 - fetchYoutubeSubscriptions - success
  ---
  duration_ms: 0.096209
  type: 'test'
  ...
# Subtest: fetchYoutubeSubscriptions - non-ok status
ok 134 - fetchYoutubeSubscriptions - non-ok status
  ---
  duration_ms: 0.057626
  type: 'test'
  ...
# Subtest: fetchYoutubeSubscriptions - network error
ok 135 - fetchYoutubeSubscriptions - network error
  ---
  duration_ms: 0.075376
  type: 'test'
  ...
# Subtest: fetchSmartInboxSuggestions - success
ok 136 - fetchSmartInboxSuggestions - success
  ---
  duration_ms: 0.185627
  type: 'test'
  ...
# Subtest: fetchSmartInboxSuggestions - non-ok status
ok 137 - fetchSmartInboxSuggestions - non-ok status
  ---
  duration_ms: 0.070751
  type: 'test'
  ...
# Subtest: fetchSmartInboxSuggestions - network error
ok 138 - fetchSmartInboxSuggestions - network error
  ---
  duration_ms: 0.252671
  type: 'test'
  ...
1..138
# tests 138
# suites 0
# pass 138
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 449.664952
npm notice
npm notice New major version of npm available! 10.9.8 -> 12.2.0
npm notice Changelog: https://github.com/npm/cli/releases/tag/v12.2.0
npm notice To update run: npm install -g npm@12.2.0
npm notice
exit=0
```
