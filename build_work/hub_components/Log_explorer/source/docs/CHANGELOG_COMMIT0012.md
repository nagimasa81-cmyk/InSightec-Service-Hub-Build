# Log Merge Tool RC1 Commit0012 Test Build

## Implemented for field evaluation

- Viewer and Smart File Discovery open on the same monitor as the parent window.
- Viewer uses nearly the full available vertical monitor work area.
- Columns auto-fit once after pane loading; the manual Fit Columns button is removed.
- Reset Layout preserves the current visible pane count and loaded sources.
- Per-pane Filter and Clear controls are added.
- Smart File Discovery Start/End selections use actual parsed boundaries from checked files.
- Calendar input is available through Custom Calendar only.
- File-type defaults are applied:
  - WS: Timestamp / Message
  - CSA: Timestamp / Level / Message
  - CGA: Timestamp / Level / Message
  - WaterSystem: Timestamp / MainState / Error
- WaterSystem numeric native fields remain hidden by default and selectable through Columns.
- Existing Investigation Mode, chart modes, Plugin Builder and ZIP Generator are retained.

## Important evaluation note

CSA/CGA timestamp handling uses the existing content-timestamp rule that prioritizes line-leading time and ignores embedded release/build dates. This build requires real-log regression confirmation.
