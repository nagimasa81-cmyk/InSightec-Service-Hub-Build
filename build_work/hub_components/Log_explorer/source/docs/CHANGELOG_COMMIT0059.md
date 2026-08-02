# Commit0059 — Viewer Click Freeze Fix

Base: Commit0053a. Smart File Discovery and import workflow remain in the original manual-confirmation specification.

## Fixed call path

`QTableView.selectionChanged` previously started Event Sync for model-side and programmatic selection changes. Event Sync then selected up to 2,000 matching rows one at a time, generating repeated Qt selection notifications and repaints on the GUI thread.

## Changes

- Event Sync starts only from an actual table `clicked` signal.
- Synchronized rows are applied in one `QItemSelection` operation.
- Selection notifications and table repainting are suspended during batch selection.
- `Highlight all in range` remains available and defaults to OFF.
- Highlight-all is capped at 250 rows while preserving the best match.
- Smart Discovery retains START, Use, All, and Clear controls.
- Auto-import and automatic main-window minimization are not included.
- Build scripts, executable metadata, and `version.json` are aligned to Commit0059.
