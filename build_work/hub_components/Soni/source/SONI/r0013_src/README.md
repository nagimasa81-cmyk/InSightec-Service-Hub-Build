## RC1-C0035

Replay display selection, acoustic trend stability, planning image filtering, and XD scale controls.

## RC1-C0033

- Opens the first genuinely displayable replay frame instead of assuming frame 0 is valid.
- Filters empty/constant thermal acquisition placeholders from the thumbnail strip.
- Planning images are selectable by series class: Planning MR, Planning CT, or Planning Other.
- Temperature Trend and Acoustic Spectrum use an explicit 3:4 horizontal splitter ratio.
- MR and Scan Protocol windows show source-derived fallback information when protocol metadata is unavailable.

- Relative Acoustic Spectrum removed from Replay UI.

# Sonication Replay Engine — RC1 C0016c ReplayVisibilityFix

Replay-first FUS workstation-style viewer.

## C0007 thermometry
- Absolute-temperature map is the default display.
- RAW data is classified as absolute temperature or delta temperature.
- Delta RAW is converted to absolute temperature with an explicit 37.0 C fallback reference.
- Max and Average temperatures are calculated inside an explicit ROI.
- The current fallback ROI is shown as `Default center ROI (ACT/Protocol pending)`; it is never hidden.
- Workstation-style temperature scale presets: 30–90, 35–60, and 40–60 C.
- Red-threshold overlay and investigation-only ΔTemperature mode.
- Temperature chart, image, spectrum, acoustic controls, and frame navigator remain replay-synchronized.

The next thermometry step is reading the exact target/ROI and reference temperature from ACT/Protocol metadata when present.


## C0014 current release
- New file/Sonication load starts from an initialized Fit/WL/WW view.
- SpectrumMsg internal frames are decoded and mapped to Replay frames.
- Spectrum amplitude is normalized to relative dB for visible plotting.
- Acoustic Spectrum and Waterfall use the 200–800 kHz display range.
- `version.json`, `VERSION`, `APP_VERSION`, and `pyproject.toml` are synchronized.

## C0013 data integrity note
The supplied Sonication `.act` file is an element table (1024 element amplitude/phase values). It does not provide a validated frame-by-frame Workstation `Power %` or `Score` stream. C0013 therefore does not synthesize these values from SpectrumMsg decoder confidence or peak amplitude.

## C0016c current release
- Reads `Acquisition_Brain_*.txt` control telemetry from the ANx/CPCFiles tree.
- Power % is taken from `AblPowerRatio × 100`, representing applied/requested acoustic power.
- Score is taken from `Calculated Energy / Bottom Limit Of Harmless Energy × 100`.
- Both curves are synchronized to the selected Sonication replay frames.
- The cards show Power %, Score, and the measured energy/limit pair.
- Values are not inferred from SpectrumMsg peak amplitude.


### C0018 acoustic source rules
The default is **Sonication only**. Press **CPC OFF** to switch it to **CPC ON** and include compatible `CPCFiles` Spectrum/Acquisition DMP candidates. Hydrophone slots are displayed as CH0–CH7. Sonication-local ACT/settings frequency has priority over package-level Xd INI.


### C0025 prototype controls
The Replay page now includes Info, MR, Scan, and XD controls beside the Sonication summary. XD reads `SkullMeasures_sonic*_cue*.log`, maps element positions, and recolors the transducer map immediately when the selected parameter changes.

### C0025a hot fix
Info, MR, Scan, and XD now use the complete export workspace. XD is rendered as an element map rather than an XY chart.

## RC1-C0045 CPC Spectrum Analyzer

Open **CPC 8CH Hydrophone Analyzer** from the replay window. The analyzer now provides:

- 8-channel raw waveform display from `CPCFiles/Spectrum_*.dmp`
- current-measure FFT spectrum from `Spectrum_*.dmp_FFT`
- channel-selectable time-frequency spectrogram
- six editable MHz bands with energy-versus-time plots
- measure navigation and per-channel raw peak, RMS, dominant frequency, peak dB and band-energy statistics

CPC data is kept independent from Sonication-folder `SpectrumMsg` data. The vendor record envelope is proprietary, so the isolated record decoder is marked diagnostic while all displayed analysis is calculated from the CPC payload itself.

## RC2-R0003 Atomic Frame Snapshot

One immutable frame snapshot now carries the decoded replay frame, elapsed time, mapped magnitude/temperature indices, and mapped spectrum index to every synchronized view. Old snapshots are invalidated when the Sonication source changes.
