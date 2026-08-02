# C0032 - Image State and Planning Selector

- Fixed blank main image after package load.
- Clears previous Sonication image/chart state before switching.
- Initial display is always first valid replay frame.
- Removed Relative Acoustic Spectrum from Replay UI.
- Added three horizontal image selectors: Planning CT/MR, Anatomy MR, Thermal.
- Planning resources persist across Sonication changes.
- Anatomy selection displays magnitude without temperature overlay.
- Thermal selection restores synchronized temperature overlay and timeline.
