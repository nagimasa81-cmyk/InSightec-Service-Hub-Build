# Commit0059 — Viewer Click Freeze Fix

Base: Commit0053a. Smart File Discovery and import workflow are unchanged.

## Fixed call path

`QTableView.selectionChanged` previously ran Event Sync for model-side and programmatic selection changes. Event Sync then selected as many as 2,000 matching rows one by one, causing thousands of Qt selection notifications and repaints on the GUI thread.

Changes:
- Event Sync starts only from an actual table `clicked` signal.
- Synchronized row selection is applied once with `QItemSelection`.
- Selection notifications and table repaints are suspended during the batch update.
- "Highlight all in range" remains available but defaults to OFF.
- Highlight-all is capped at 250 rows while preserving the best match.
- Original Smart Discovery START / Use / All / Clear workflow is retained.
