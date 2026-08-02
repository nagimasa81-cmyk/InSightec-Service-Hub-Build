# Commit0019 R2

## Viewer fixes
- Context menu is connected directly to every MultiPaneLogViewer table.
- Removed dependency on the previously missing show_row_context_menu method.
- Right-click menu includes copy, filtering, rule and export operations.
- The menu is reconnected after load, search, time-range and noise-filter changes.

## Lower empty area
- For 1 to 25 displayed rows, row heights stretch to fill the table viewport.
- For more than 25 rows, compact 22-pixel rows and normal scrolling are used.
- The old detail text area is fully hidden with zero height.
- Viewer tables retain expanding vertical size behavior.
