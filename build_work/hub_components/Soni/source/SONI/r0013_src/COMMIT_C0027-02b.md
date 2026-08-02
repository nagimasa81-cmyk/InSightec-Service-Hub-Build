# Commit C0027-02b — Replay Diagnostics Framework

Implemented a permanent Diagnostics tab backed by the C0027 Metadata Engine.

## Included
- Automatic metadata validation after importing a ZIP or folder
- Health Score and metadata coverage
- Sonication inspector and metadata explorer
- Warning Center
- Resource state monitor (Loaded / Missing / Parse Error)
- Timeline inventory for MR, sonication, replay, temperature and SpectrumMsg
- Performance and cache/load metrics
- Replay inspector
- JSON, CSV and standalone HTML diagnostic reports
- Double-click a sonication in Diagnostics to select it in Replay

## Build compatibility
The implementation uses only PySide6 and the Python standard library. No new package dependency is required.
