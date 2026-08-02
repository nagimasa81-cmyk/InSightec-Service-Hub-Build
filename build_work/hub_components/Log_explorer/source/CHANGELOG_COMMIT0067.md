# Commit0067 — ZIP Smart Discovery Handoff Fix

- Fixed START after ZIP selection/drop opening an empty Smart File Discovery dialog.
- START now extracts the ZIP first and gives the extracted folder to Smart File Discovery.
- Smart File Discovery opens only once per START operation.
- Selected extracted files remain available until the Viewer LOAD LOGS action.
- Temporary ZIP extraction is removed on cancellation, next discovery session, or application close.
- Explicit LOAD LOGS workflow from Commit0066 is preserved.
