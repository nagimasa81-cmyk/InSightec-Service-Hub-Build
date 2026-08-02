# C0036 — Independent CPC 8CH Hydrophone Popup

- Main Acoustic Spectrum uses Sonication `SpectrumMsg` only.
- CPCFiles are no longer assigned as fallback Sonication spectrum files.
- Added `Open 8CH Hydrophone` toolbar action.
- Added independent CPCFiles popup with 8 Panel, Overlay, and Single CH views.
- Popup Sonication selection synchronizes bidirectionally with Replay.
- CPC gzip FFT header validates eight channels, frame count, sampling frequency, and main-frequency candidate.
- Physical channel placement and proprietary payload amplitude scaling remain explicitly diagnostic.
