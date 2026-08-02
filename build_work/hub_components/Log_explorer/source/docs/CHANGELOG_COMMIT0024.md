# Commit0024

## Investigation Viewer
- Viewer count can be changed after opening Investigation Mode: 1–4.
- Viewer widths remain draggable with the splitter.
- Equal Widths button restores even widths.

## Acquisition
- Added a graphical Acquisition Dashboard.
- Acquisition is no longer limited to spreadsheet-style viewing.
- Selectable charts:
  - Event density
  - Acoustic power
  - Reflection max
  - Dangerous channels
  - XD impedance
- Event summary and chart-specific event table included.

## Spectrum
- Spectrum Analysis can launch independently from the main window.
- Windows Explorer file/folder drag-and-drop supported.
- Folder selection and automatic recursive search supported.
- Search is independent of loaded logs.
- Search always traverses arbitrary folder depth.
- Case-insensitive and suffix-tolerant detection:
  - `.dmp_FFT`
  - `.dmp.fft`
  - case variations
  - suffixed copies
- Direct file drops are accepted.
