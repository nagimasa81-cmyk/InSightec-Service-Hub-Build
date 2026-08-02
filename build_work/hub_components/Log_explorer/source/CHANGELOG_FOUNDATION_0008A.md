# Commit0008 Foundation 0008a

## Implemented
- Added `foundation/viewer.py` as the first real Foundation module.
- Captured the original `MultiPaneLogViewer` initializer before legacy compatibility patches.
- Installed one deterministic final Viewer initializer.
- Removed the runtime dependency on chained v41 / v41.1 / v41.2 Viewer initializers.
- Centralized Viewer post-initialization: legacy view-mode hiding, pane defaults, loaded-source refresh, window sizing, table sizing, and double-click time connection.
- Restored operator-resizable columns by applying `QHeaderView.Interactive` to every column.

## Intentionally not implemented yet
- Column filters.
- Context-menu recovery.
- Calendar manager extraction.
- WS / CSA parser extraction.

Those remain Recovery tasks after the Foundation entry path is verified.
