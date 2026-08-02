# Commit0028 — Investigation Performance and Start Control

## Workflow
- Opening Investigation Mode no longer starts Initial Investigation.
- User selects a profile and presses `Start Analysis`.
- `Reload Analysis` reruns the selected profile.

## Performance
- Investigation tables no longer attempt to render millions of rows.
- Each source displays up to 50,000 representative rows.
- Total indexed and displayed row counts are shown.
- Table updates are suspended during bulk population.
- Timeline is limited to the latest 5,000 critical/warning items.
- Chart and table stages are separated.

## Progress and Cancel
- Progress range is 0–1000 for finer movement.
- Progress text changes by stage and source.
- Cancel is checked during:
  - source loading
  - row conversion
  - table rendering
  - timeline generation
- QApplication events are processed at regular batch intervals.

## Version
- Updated to `2.0.0-rc1-commit0028`.
