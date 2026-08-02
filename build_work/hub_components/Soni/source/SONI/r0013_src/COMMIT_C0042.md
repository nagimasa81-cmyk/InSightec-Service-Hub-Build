# Commit C0043 — CPC Spectrum / 8CH Time-Frequency Analyzer

- Rebuilt the independent CPC Hydrophone popup as a five-tab analysis workspace.
- Added 8-channel raw waveform display using CPC `Spectrum_*.dmp` payloads.
- Added current-measure FFT display with overlay, single-channel and 8-panel modes.
- Added channel-selectable time-frequency spectrogram.
- Added six editable frequency bands and time-resolved band-energy analysis.
- Added Measure Navigator and per-channel raw peak, RMS, dominant frequency, peak level and band-energy table.
- Kept CPCFiles independent from Sonication `SpectrumMsg` data.
- Repaired `03_AUDIT_PLANNING_HYDROPHONE.bat` backend for the current service API.

The CPC per-record binary envelope is proprietary. Header fields and CPC source separation are verified; payload record slicing remains explicitly diagnostic and is isolated in the decoder for future schema replacement.
