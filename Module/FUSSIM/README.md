# FUS Treatment Replay Prototype

An anonymized treatment ZIP can be opened directly. The prototype displays parsed sonication parameters, a synchronized simulated phantom/general MR image with a simulated hotspot, four simulated hydrophone cavitation trends, and an uncalibrated preview extracted from each compressed Spectrum FFT payload.

## Important
- Research/service review prototype only. Not for diagnosis, treatment planning, or clinical decisions.
- Sonication parameters are parsed from `Summary_*.txt`.
- Patient MRI is not included, so all MR/phantom/hotspot displays are simulations and clearly labeled.
- Calibrated per-hydrophone time-series data was not identified in the supplied ZIP, so hydrophone traces are simulated.
- Spectrum files are proprietary compressed binaries. The current display is normalized and uses relative frequency bins, not physical frequency units.

Run `01_RUN_PYTHON.bat`. Build a Windows EXE with `02_BUILD_EXE_NUITKA.bat`.
