# Commit0066 — Viewer Shell First / Explicit LOAD LOGS

- Smart File Discovery now selects files only.
- Log Viewer opens immediately after discovery without parsing WS, PSC, or other logs.
- Operator configures pane count and source types before loading.
- Log parsing starts only when **LOAD LOGS** or **Load This** is pressed.
- Existing Viewer data is cleared when a new discovery session opens the Viewer.
- Commit0065 progress integration remains available for explicit load operations only.
