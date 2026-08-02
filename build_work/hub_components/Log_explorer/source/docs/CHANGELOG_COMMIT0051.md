# Commit0051 — Data Binding and Viewer Recovery

## Event Viewer
- Source selectors are populated from the canonical parsed cache.
- `Load This` reads directly from the parsed cache.
- Pane 1 and Pane 2 receive an automatic startup preview.
- Large logs use a 5,000-row beginning/end preview to protect responsiveness.
- The file label reports preview rows versus total rows.

## Value Viewer
- Value sources refresh from the same canonical parsed cache.
- Review, PSC, VIMeasure, Acquisition and WaterSystem remain available.

## Advanced tabs
- Operation remains manually rebuilt.
- Investigation remains manually started.
- Spectrum scanning remains manual.
