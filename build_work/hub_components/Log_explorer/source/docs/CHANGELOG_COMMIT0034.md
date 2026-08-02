# Commit0034 — Strict CSA/CGA and Spectrum/Acquisition Corrections

## CSA/CGA scope
- CSA accepts only filenames beginning with `Csa_brain`.
- CGA accepts only filenames beginning with `CGA_brain`.
- Matching is case-insensitive.
- Only `.log` and `.txt` are accepted.
- Broad legacy CSA/CGA classification is blocked.
- The same rule is applied to Smart Discovery, selected files, folder scan,
  Viewer loading and Investigation loading.

## Spectrum Analysis
- Fixed PySide6 type error caused by `QRect.contains(QPointF)`.
- Crosshair containment now uses `QRectF`.
- Zoom rectangle is stored as `QRectF`.
- Fix applies to embedded Investigation and standalone Spectrum Analysis.

## Acquisition Dashboard
- Chart and tables are separated by a vertical splitter.
- Chart receives the primary visible area.
- Sonication Summary and Selected Series Events are tabbed below it.
- Summary cards have maximum heights and can no longer hide the chart.
- Added chart grid lines for readability.
