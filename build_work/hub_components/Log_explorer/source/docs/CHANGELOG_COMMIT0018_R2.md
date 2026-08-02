# Commit0018 R2

## Output Folder auto-selection
- Dropped folder: Output Folder becomes that folder.
- Dropped ZIP: Output Folder becomes the ZIP parent folder.
- Dropped one or multiple files: Output Folder becomes the first file parent folder.
- Mixed source folders are reported in the status line.
- Browse Folder / ZIP / Files follow the same rule.
- Existing Output Folder values are overwritten when a new source is selected.

## Window placement
- Main window, Smart File Discovery, Viewer, Investigation and progress dialogs use the parent window's monitor.
- Every window is clamped to the monitor available geometry.
- Taskbar area and display scaling are respected through Qt screen geometry.
- Smart File Discovery is centered and capped at 1150 x 860.
- Viewer and Investigation use nearly all available screen area without going outside it.
- Progress dialogs are centered over the parent monitor.
