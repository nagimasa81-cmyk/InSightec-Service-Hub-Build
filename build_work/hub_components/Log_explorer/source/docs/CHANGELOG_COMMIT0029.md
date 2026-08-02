# Commit0029 — True Manual Start and Fast Rendering

- Removed the remaining Viewer-side automatic `load_template()` call.
- Entering Investigation Mode now only shows Ready state.
- Default rendering limit reduced to 5,000 rows/source.
- Added selectable limits from 1,000 to 50,000.
- Restored 0–1000 progress range after source loaders.
- Progress and Cancel checkpoints now occur every 250 rendered rows.
- Tables are hidden and repaint disabled during bulk population.
