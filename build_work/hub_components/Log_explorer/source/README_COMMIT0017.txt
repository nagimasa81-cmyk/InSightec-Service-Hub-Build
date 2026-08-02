Log Merge Tool RC1 Commit0017

Main screen:
- File Type selection removed from the visible workflow.
- Date Range selection removed from the visible workflow.
- Source Type supports Folder, ZIP File, and Project.

Smart File Discovery:
- Compact grid for detected file types.
- Actual Start and End controls use two rows.
- Window is centered and constrained to the parent monitor.
- UNKNOWN is not shown for the normal Commit0017 workflow.

ZIP:
- ZIP can be selected directly from the main Source area.
- Nested ZIP files are reported by file name only.
- Recognized files are passed to Smart File Discovery.
- START preloads selected records before temporary extraction cleanup.
- MERGE keeps temporary extraction until merge success/failure.

Important foundation fix:
- The Python main entry point is now after all Commit0016/Commit0017 overrides.
