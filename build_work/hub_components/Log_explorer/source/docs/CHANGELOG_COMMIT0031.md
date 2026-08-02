# Commit0031 — Spectrum and Sonication Acquisition Integration

## Spectrum from loaded sources
- Uses the same selected files, folder or ZIP as Log Viewer.
- Searches arbitrary-depth subfolders.
- Searches ZIP contents and one nested ZIP level.
- Spectrum Dump stays out of normal Log Viewer rows.
- Dedicated graphical modes remain available:
  Overlay, Waterfall, Heatmap, Harmonics, FFT Compare and Replay.
- Search diagnostics show scanned files, ZIPs and ZIP members.

## Standalone Spectrum Analysis
- Visible button on the initial source-selection screen.
- Select Spectrum files directly.
- Select a folder.
- Select a ZIP.
- Windows Explorer file/folder/ZIP drag-and-drop remains supported.
- Standalone operation does not require Log Viewer loading.

## Sonication Investigation Acquisition prototype
- Acquisition Dashboard receives parsed ACQUISITION rows automatically.
- Initial charts:
  Event density, Acoustic power, Reflection max, Dangerous channels,
  XD impedance, Spectrum save events and Sonication state.
- Dashboard refreshes when its tab is opened.
- Spectrum tab searches the same loaded source package.
