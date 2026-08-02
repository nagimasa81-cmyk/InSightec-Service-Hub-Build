# Commit0032C — Header Filter Value Dropdown

## Added
When a Log Viewer column header is right-clicked, the application reads the
actual distinct values currently available in that Viewer pane.

- 1–10 unique values: `Select value` submenu is displayed.
- 11 or more unique values: the submenu is not displayed.
- Selecting a value applies an exact, case-insensitive column filter.
- Blank values are shown as `(Blank)` and can be selected.

## Retained
- Filter contains...
- Filter exact...
- Clear column filter
- Per-pane filtering
- Quick Filter and time-range compatibility
