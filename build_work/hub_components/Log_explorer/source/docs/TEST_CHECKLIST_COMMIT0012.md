# Log Merge Tool RC1 Commit0012 Test Checklist

## P0 — Window and monitor

- [ ] Move the main tool to monitor 2.
- [ ] Open Log Viewer; it opens on monitor 2.
- [ ] Open Smart File Discovery; it opens on monitor 2.
- [ ] Viewer and dialogs stay inside the monitor work area.
- [ ] Viewer uses almost all available vertical height.
- [ ] Confirm at Windows DPI 125%.
- [ ] Confirm at Windows DPI 150%.

## Viewer layout

- [ ] Loading a pane automatically fits columns.
- [ ] The Fit Columns button is not shown.
- [ ] Columns remain manually resizable.
- [ ] Reset Layout preserves 1-pane mode.
- [ ] Reset Layout preserves 2-pane mode.
- [ ] Reset Layout preserves 3-pane mode.
- [ ] Reset Layout preserves 4-pane mode.
- [ ] Reset Layout preserves loaded sources.
- [ ] Lower unused space is minimized.

## Per-pane filter

- [ ] Every pane has its own filter input.
- [ ] Filter searches visible and structured fields.
- [ ] Filtering pane 1 does not change pane 2/3/4.
- [ ] Clear restores rows.
- [ ] Filter works together with Viewer Time Range.

## Smart File Discovery

- [ ] Start dropdown shows actual starts from checked files.
- [ ] End dropdown shows actual ends from checked files.
- [ ] Unchecking a file refreshes the candidate boundaries.
- [ ] Checking a file refreshes the candidate boundaries.
- [ ] Earliest checked start is the default Start.
- [ ] Latest checked end is the default End.
- [ ] Custom Calendar allows manual dates.
- [ ] Selected files are preserved after range changes.

## File-type default display

### WS
- [ ] Default: Timestamp / Message.
- [ ] Timestamp is derived from content and filename/header date.
- [ ] Midnight rollover works.

### CSA
- [ ] Default: Timestamp / Level / Message.
- [ ] Line-leading timestamp is used.
- [ ] Embedded release/build dates do not overwrite the row timestamp.

### CGA
- [ ] Default: Timestamp / Level / Message.
- [ ] Line-leading timestamp is used.
- [ ] Embedded release/build dates do not overwrite the row timestamp.

### WaterSystem
- [ ] Default: Timestamp / MainState / Error.
- [ ] CoolingState is not shown.
- [ ] NO_ERROR is blank.
- [ ] Actual Error text is shown.
- [ ] Native numeric fields are available through Columns.

## Investigation Mode

- [ ] Normal Viewer switches to Investigation Mode in the same window.
- [ ] Logs mode works.
- [ ] WaterSystem Chart mode works.
- [ ] Logs + Chart mode works.
- [ ] Return to Log Viewer restores normal mode.

## Plugin / File Type

- [ ] File Type Builder opens.
- [ ] ZIP Generator creates an update ZIP.
- [ ] Generated ZIP installs.
- [ ] Plugin reload works.
- [ ] Plugin remains available after restart.

## Build

- [ ] Local source debug starts.
- [ ] Local Nuitka build succeeds.
- [ ] GitHub build_selected succeeds.
- [ ] EXE starts without Python/DLL errors.
