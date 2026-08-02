# Commit0040 — ZIP Cache Viewer Path Fix

## Observed behavior
Smart File Discovery showed valid row counts for GESYS and PSC, but their
Viewer panes were empty after pressing Start.

## Root cause
ZIP files are parsed into `zip_import_records_by_type`, then the temporary
extraction directory is deleted. Later Commit0037+ Viewer overrides skipped
the cache and attempted to rescan deleted files.

## Correction
- Viewer checks the in-memory ZIP cache before every filesystem scan.
- Applies to GESYS, LAIS, PSC, Review, CSA, CGA, WS, WaterSystem,
  MRSERVER, VIMeasure and Acquisition.
- Viewer source selectors are rebuilt from non-empty cached types.
- Merged combines all cached rows.
- Viewer log reports the cached row count.
