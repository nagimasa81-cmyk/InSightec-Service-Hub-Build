# Commit0047 — Embedded Investigation and Spectrum Workspaces

## Root cause fixed
The Log Explore constructor still connected buttons to missing legacy APIs:

- `MainWindow.open_investigation_workspace`
- `MainWindow.open_standalone_spectrum_analysis`

## New canonical structure
Log Explore now directly creates:

- Event Viewer
- Value Viewer
- Operation
- Investigation
- Spectrum

`InvestigationWorkspace` receives the shared Event Viewer.
`SpectrumAnalysisWidget` receives the embedded Investigation workspace.

## Compatibility
Canonical public navigation methods are provided for any older menu/button that
still requests Investigation or Spectrum. They select the embedded Log Explore
tab rather than creating a second workspace.

## Performance
Opening Log Explore does not automatically start Investigation analysis or a
Spectrum scan. The operator starts these actions from their tabs.
