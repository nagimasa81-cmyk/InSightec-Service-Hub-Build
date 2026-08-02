# RC2-R0005 Runtime Data Binding Repair

This release repairs the runtime failures observed on the Windows evaluation machine:

- Planning CT discovery now finds `CtImage.xml` below the exported wrapper directory and exposes the verified field-16 signed 512×512 stack.
- Main replay performs a deterministic first render after the complete sonication source set is bound.
- CPC Spectrum is a visible, functional source switch rather than a hidden/disabled path.
- CPC mode uses the validated independent 8-channel FFT decoder and maps the selected sonication only.
- `Calibration.ini` `SpectrumFactor`/`SpectrumCoef` and `HydrophonesResponseCalibration.ini` frequency/channel coefficients are parsed and applied before display calculations.
- Spectrum status reports source and `CAL ON`/`CAL OFF`.
- Regression and real-export audits cover CT, frame variation, Sonication SpectrumMsg, CPC 8CH data, and calibration.
