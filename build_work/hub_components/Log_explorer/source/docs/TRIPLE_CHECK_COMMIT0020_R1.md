# Commit0020 R1 Triple Check

- PASS: 55
- WARN: 1
- FAIL: 0

## Results
- **PASS** Required file — LogMergeTool_NoExcel_Main.py
- **PASS** Required file — parser_rc1.py
- **PASS** Required file — foundation/viewer.py
- **PASS** Required file — foundation/investigation.py
- **PASS** Required file — 01_BUILD_EXE_NUITKA.bat
- **PASS** Required file — version.json
- **PASS** Required file — docs/TEST_CHECKLIST_COMMIT0020_R1.md
- **PASS** Python compilation — 15 files
- **PASS** APP_VERSION — ['2.0.0-rc1-commit0020-r1']
- **PASS** Single application entry point — 1
- **PASS** version.json version — 2.0.0-rc1-commit0020-r1
- **PASS** version.json commit — Commit0020_R1
- **PASS** Qt import QTimer
- **PASS** Qt import QMenu
- **PASS** Qt import QSizePolicy
- **PASS** Qt import QHeaderView
- **PASS** Qt import QApplication
- **PASS** Qt import QFileDialog
- **PASS** Datetime-safe CallID extraction
- **PASS** Active before startup: Datetime-safe CallID extraction
- **PASS** Nested value traversal
- **PASS** Active before startup: Nested value traversal
- **PASS** Large-row progress updates
- **PASS** Active before startup: Large-row progress updates
- **PASS** Viewer callback fix
- **PASS** Active before startup: Viewer callback fix
- **PASS** Viewer callback assignment
- **PASS** Active before startup: Viewer callback assignment
- **PASS** CallID cross-pane menu
- **PASS** Active before startup: CallID cross-pane menu
- **PASS** Load This replacement
- **PASS** Active before startup: Load This replacement
- **PASS** Context menu policy
- **PASS** Active before startup: Context menu policy
- **PASS** Short-table row fit
- **PASS** Active before startup: Short-table row fit
- **PASS** Unsafe datetime JSON serialization absent
- **WARN** Historical callback remains in source — It is overridden later by Commit0020 before startup; active method is the fixed *args/**kwargs version.
- **PASS** Legacy null package path absent
- **PASS** Single definition _c20_extract_call_id — [9463]
- **PASS** Single definition _c20_record_to_viewer_row — [9522]
- **PASS** Single definition _c20_build_rows_with_progress — [9551]
- **PASS** Single definition _c20_update_view_mode — [9580]
- **PASS** Single definition _c20_load_pane — [9756]
- **PASS** Automated test tests/test_callid_datetime_safe.py — CallID datetime-safe extraction: PASS
Traceback (most recent call last):
- **PASS** Automated test tests/test_commit0015_parsers.py — PASS WS=494168 CSA=4940 CGA=2658 VIMEASURE=4487
Traceback (most recent call last):
- **PASS** Automated test tests/test_csa_cga_structured_parser.py — Commit0017 R1 CSA/CGA structured parser tests: PASS
Traceback (most recent call last):
- **PASS** Automated test tests/test_vimeasure_plugin.py — SKIP: optional VIMeasure plugin ZIP not bundled: /mnt/data/commit0020_r1_triple_checked_final/sample_plugins/VIMeasure_FileType_Update_v1_0_0.plugin.zip
Traceback (most recent call last):
- **PASS** CallID edge case — '100200' / expected '100200'
- **PASS** CallID edge case — 'ABC-999' / expected 'ABC-999'
- **PASS** CallID edge case — 'CASE_42' / expected 'CASE_42'
- **PASS** CallID edge case — '777888' / expected '777888'
- **PASS** CallID edge case — '' / expected ''
- **PASS** Build BAT commit metadata
- **PASS** Build BAT file version
- **PASS** Checklist expanded for current regressions

## Windows-only checks still required
- Built EXE GUI startup
- Actual right-click interaction
- 100k–500k row progress responsiveness
- Same-monitor placement
- Real-file CallID linking across WS / CSA / CGA / MRSERVER
