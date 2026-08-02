# Commit0019 R2 Double Check

## Passed
- Source ZIP integrity
- Python syntax compile for main, parser, viewer, and investigation modules
- AST parse of main application
- Exactly one application entry point
- QTimer, QMenu, QSizePolicy and required Qt imports are present
- Context-menu code is defined after all prior Viewer overrides and before application startup
- Every Viewer table is assigned Qt.CustomContextMenu
- Menu actions include Copy, Filter, Noise Rule and Export
- Row-fit logic uses stretched rows for 1–25 visible rows
- Detail pane is hidden with minimum and maximum height set to zero
- Parser regression tests for WS, CSA, CGA, WaterSystem and VIMeasure pass

## Important Windows checks
- Right-click must be tested on a populated cell, not the empty viewport
- Confirm rows stretch after loading a short file and after filtering
- Confirm 26+ rows switch back to compact scrolling
- Confirm context menu remains after Reload, search, time filtering and noise filtering

## Limitation
PySide6 is unavailable in the validation container, so an actual Qt GUI click test could not be executed here. The source-level connection path was verified directly.
