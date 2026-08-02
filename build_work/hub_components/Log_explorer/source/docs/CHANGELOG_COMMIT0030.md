# Commit0030 — Header Right-Click Column Filter

## Log Viewer
- Right-click any visible column header.
- `Filter contains...` performs case-insensitive partial matching.
- `Filter exact...` performs case-insensitive exact matching.
- `Clear column filter` removes the active manual filter.
- The existing Filter field displays the active expression:
  - `Column~text` for partial matching
  - `Column=text` for exact matching
- Works independently in each Viewer pane.
- Combines with Quick Filter and Viewer time range.

## Safety
- Header-to-model column mapping uses the logical column index.
- Duplicate signal connections are prevented when UI is rebuilt.
- Empty text clears the filter.
