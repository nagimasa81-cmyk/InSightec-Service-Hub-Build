# FUS Treatment Replay Prototype v3

Research/review prototype for FUS treatment ZIP packages.

## Added in v3
- DQA (phantom, including calibration/test) vs Treatment (patient) categorization
- Conservative automatic phase split based primarily on workflow time gaps, with confidence/reason
- Per-sonication manual category override saved in `.fus_review.json`
- MR geometry from review.out where available; manual plane/frequency direction fallback
- WS/WaterSystem/acquisition/sonication log scan for MR–FUS timing evidence and explicit clock offsets
- Time Synchronization tab; no fabricated offset or pre/post duration
- Spectrum defaults to Frequency vs Amplitude, with Amplitude/dB and interval selectors
- Hydrophone selector, while clearly labeling unverified channel identity as Unknown
- External MR/DICOM folder registration for later image integration

## Run
`01_RUN_PYTHON.bat`

## Build EXE
`02_BUILD_EXE_NUITKA.bat`

## Important
This prototype is for review/research only and must not be used for clinical decisions. Simulated phantom/MR/hotspot/cavitation elements are labeled in the UI. Proprietary spectrum sample-rate and hydrophone-channel decoding remain unverified.
