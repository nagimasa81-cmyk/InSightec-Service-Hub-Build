# Hydrophone Reverse Engineering Lab

Launch with `build/04_HYDROPHONE_RE_LAB.bat` during development, or build a standalone executable with `build/05_BUILD_HYDROPHONE_RE_LAB_EXE.bat`.

The lab accepts an ANx ZIP, extracted export folder, Sonication folder, or individual DMP file. It provides:

- recursive SpectrumMsg / Acquisition / Reflection / Cavitation discovery;
- hex and ASCII inspection;
- numeric type, endian, offset, and count experimentation;
- automatic numeric candidate ranking;
- waveform, FFT, PSD, dB, and band-energy views;
- main, subharmonic, ultraharmonic, and harmonic guides;
- Score or other telemetry correlation with lag search;
- CSV, JSON, and PNG export;
- evidence reports marked Confirmed, Estimated, or Unknown.

Candidate decoding is diagnostic only. It is not automatically promoted into Replay.
