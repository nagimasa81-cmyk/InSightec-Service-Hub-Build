# Commit0023 — Comprehensive Evaluation

## Viewer
- Removed every automatic Error filter.
- Default is always All rows.
- Added per-pane Quick Filter buttons with counts:
  All / Error / Warning / Info / Critical.
- Quick Filter is in-memory and does not re-run parsers.

## CSA
- Added filename and content fallback classification.
- Added CSA recovery scan when the normal source path returns zero rows.
- Added pipeline status:
  detected files / parsed rows / displayed rows.
- Selected CSA files force CSA into Viewer source lists.

## Spectrum Analysis
- Spectrum Overlay
- Waterfall
- Heatmap
- Harmonic markers
- FFT comparison
- Sonication Replay slider and playback
- Spectrum Dumps remain excluded from normal Log Viewer.

## Existing scope retained
- Viewer-only START workflow
- Acquisition
- Spectrum-to-Acquisition link
- VIMeasure
- CallID linking
- Right-click menu
- row-fit layout
