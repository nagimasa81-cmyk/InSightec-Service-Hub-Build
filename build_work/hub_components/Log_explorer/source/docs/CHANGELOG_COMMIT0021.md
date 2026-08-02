# Commit0021 — Viewer-only workflow

## Root-cause correction
- START was already opening Discovery/Viewer, but multiple selected files of the
  same type were combined into one in-memory Viewer dataset.
- This looked like Merge because the old Merge button and merge terminology
  were still present in the same UI.

## Changes
- Removed the MERGE button from the UI.
- Disabled `run_clicked` so stale shortcuts/signals cannot create merge output.
- Removed Split Merge and merge-only options from the visible UI.
- Removed `Merged` from Viewer source selections.
- START is the only primary workflow.
- Progress wording changed from `Building table rows` to
  `Indexing selected rows for Viewer`.
- Multiple files of the same type are still combined in memory for one
  continuous Explorer table.
- No merged Excel/CSV output is created by START.
