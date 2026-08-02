LogMergeTool NoExcel v19 - Log Explorer Fix

Changes:
- Fixed Dual Log Viewer crash: parse_user_date was not defined.
- Fixed date range filtering in Viewer to use each row Timestamp, not file created/modified date.
- Added progress popup while Log Explorer loads/scans/parses logs.
- Added operator tooltips to Viewer buttons and selectors.
- Added cancel support in Viewer progress popup.

Usage:
1. Open Log Explorer / Dual Log Viewer.
2. Select left and right sources.
3. Click Load Left, Load Right, or Load Both.
4. A progress popup appears during scanning/loading.
5. Click a row on one side to jump to the nearest Timestamp on the other side.
