# Commit0022 — Acquisition and Spectrum Analysis

## Acquisition
- Added `ACQUISITION` file classification for `Acquisition_*.txt`.
- Added Acquisition to normal Viewer sources.
- Added Acquisition to Sonication Investigation.

## Spectrum Dump
- Detects `Spectrum_*.dmp_FFT` only inside Spectrum Analysis.
- Spectrum Dump is not added to normal Log Viewer rows or source selectors.
- Reads gzip-compressed proprietary binary dumps.
- Decodes stable header fields:
  - cycle count
  - spectrum count
  - hydrophone count
  - FFT size
  - averaging count
  - sample rate
  - acoustic power
  - main frequency
- Conservatively extracts repeated plausible float32 spectrum blocks.
- Shows Hydrophone candidate overlays, Linear/Log scale and peak table.
- Links each dump to Acquisition by exact dump filename or nearest FFT-save event.
- Shows Acquisition file, line and Spectrum measurement start time.

## Decode status
The supplied binary format is proprietary. Header fields are decoded directly.
Spectrum curves are labelled heuristic until more sample dumps confirm all
record boundaries.
