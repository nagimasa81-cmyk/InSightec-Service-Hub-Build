# RC1-C0045

## CPC Spectrum / 8CH Time-Frequency Analyzer

- Added Raw Data, Spectrum, Spectrogram, Band Energy, and Measure/Statistics tabs.
- Added editable MHz bands and time-resolved energy calculation for all eight channels.
- Added frame navigation, playback, per-channel raw peak/RMS and spectral measurements.
- Repaired the planning/hydrophone audit utility.
- CPC data remains independent from Sonication SpectrumMsg.

# RC1-C0041

- Completed CT/Power-Score/XD/metadata data binding fixes.

## RC1-C0041

- Unified CPC 8CH hydrophone scale to fixed 0–1 MHz and -60–0 dB for cavitation visibility.

# RC1-C0037 Replay Data Foundation Fix

- Linked CtImage.xml rowset records to exported RAW planning image payloads.
- Added ProtocolData.xml and MriImageParams.xml metadata extraction.
- Added CPC 8CH acoustic frame playback with 10 ms timeline display.
- Added XD colour scale minimum and maximum controls and continuous colour ramp.
- Stabilized embedded Power/Score curves and added visible planned-power fallback when measured telemetry is unavailable.

# C0036

Independent Sonication Acoustic Spectrum and CPCFiles 8CH Hydrophone display paths.

# RC1-C0035 Initial Main Image and Row Source Selection

- Display the first valid replay image immediately after loading a sonication.
- Prefer Thermal replay for the initial main image and fall back to Anatomy MR.
- Give all three image rows the same fixed choices: Planning CT, Planning MR, Anatomy MR, Thermal, and All images.
- Keep Planning CT and Planning MR as separate selectable image categories.
- Preserve Temperature Trend : Acoustic Spectrum at 3 : 4.

# RC1-C0034 ReplayDisplayXDScaleFix

- Fixed image selection, initial blank viewer, Power/Score stability, planning thumbnails, and XD colour scale.

## RC1-C0032
- Main image initialization/state reset and product-style Planning/Anatomy/Thermal selectors.
- Relative Acoustic Spectrum removed from Replay UI.

# RC1-C0031 Acoustic Timeline Synchronization

- Maps treatment Sonication 1-N to the final N Acquisition telemetry segments when pre-treatment/DQA segments exist.
- Uses the complete MR acquisition interval as the Replay time axis.
- Preserves acoustic onset at its measured offset from MR acquisition start.
- Hides Relative Acoustic Spectrum from the main Replay until its physical mapping is verified.
- Reloads Power/Score telemetry for every Sonication selection.


## RC1-C0027-02b-Fix1
- Fixed Diagnostics remaining empty after Replay data was loaded.
- Diagnostics now loads from the exact extracted Replay workspace before the first sonication is selected.
- Added Replay-package fallback metadata for datasets without workstation XML metadata files.
- Synchronized Replay sonication selection with Diagnostics.
- Fixed SkullMeasures parsing for concatenated signed numeric columns.
- Fixed SkullMeasures element-row counting to exclude numeric header lines.
# C0024 - Synchronized Cavitation Timeline

- Removed the fixed four-second temperature frame cadence.
- Reads planned and measured duration per sonication from SonicationSummary.xml.
- Rebased Acquisition telemetry to the measured acoustic power-ramp onset.
- Preserves measured telemetry time instead of normalizing CPC pre-roll over the MR replay.
- Temperature, replay cursor, Power, Score, waterfall and chart clicks now use one elapsed-time axis.
- Detects the first high cavitation score and abrupt power modulation events.
- Validated against the supplied Sonication 5 deliberate-cavitation test: 2.99041 s, 250 W.

# C0022 Hydrophone Reverse Engineering

- Added an evidence-first Hydrophone Reverse Engineering Lab for SpectrumMsg, Acquisition, Reflection and CavitationControl DMP files.
- Added binary structure profiling: ASCII markers, entropy, zero ratio, block periodicity, endian/type candidates and ranked spectrum-like numeric regions.
- Added Acquisition_Brain telemetry summary for Power and Score validation.
- Added Confirmed / Estimated / Unknown classifications and prevented speculative candidates from entering Replay rendering.
- Added JSON and CSV diagnostic exports plus a Windows launcher.
- Preserved the existing C0021 Replay display while the underlying format is investigated.

# C0021 Acoustic / Temperature Synchronization

- Replaced per-frame spectrum normalization with one fixed sonication baseline and scale so real acoustic-energy increases remain visible.
- Added Current, Average, Max Hold, and Baseline Δ spectrum modes; Average is the default score-window view.
- Added subharmonic, ultraharmonic, broadband, and total relative-energy calculations for the active channel.
- Kept embedded and popup Acoustic Spectrum on the same renderer and mode.
- Temperature Trend now fits the complete sonication by default, includes all finite Max/ROI Average/Cursor values, and moves only the replay cursor during playback.
- Temperature zoom/range and all acoustic controls remain persistent across sonication and CPC source changes.
- Missing temperature samples are rendered as gaps rather than artificial zero-temperature points.

# C0020 Acoustic Spectrum Workstation Reproduction

- Replaced pseudo-3D current spectrum with the workstation-style current-frame 1D FFT.
- Shared one CurrentSpectrumRenderer between embedded and popup charts.
- Fixed axes to 0.20-0.80 MHz and 0-4 relative amplitude.
- Added robust baseline subtraction, percentile normalization and light smoothing.
- Default single active channel uses the workstation orange trace; multi-CH keeps fixed colors.
- Added synchronized Time display and main/subharmonic guides.
- Added main-chart mouse-over frequency and per-channel relative amplitude.
- Preserved CPC, channel and chart-state behavior across Sonication changes.

# C0019 Acoustic Spectrum Engine v2 / Chart State

- Relative Acoustic Spectrum now uses all decoded FFT bins as a Time × Frequency heat map.
- Embedded chart and popup use the same renderer.
- Coloured overlay curves represent the selected channels current-frame FFT, replacing misleading peak-ridge lines.
- CPC remains OFF by default and only changes the data source; channel choices are retained.
- Sonication-local configured CH0–CH7 is used as the default channel.
- CH, CPC and future chart choices are retained across Sonication changes.

# Changelog

## RC1-C0017c
- Rebuilt embedded Power/Score curves on every telemetry refresh so the main chart and popup share the same visible data.
- Added hover values to the main Power/Score chart and all enlarged chart popups.
- Synchronized Temperature, Power/Score, Spectrum, and Waterfall popups with frame and sonication changes.
- Changed the visible ROI average curve to green and clarified it as the 5 mm x 5 mm voxel average.
- Kept the 20 mm target circle display-only and changed the calculation ROI/voxel square to 5 mm x 5 mm.
- Strengthened the enlarged acoustic-spectrum perspective with multiple receding traces.


## RC1-C0017b
- Reattached the embedded Power/Score curves to the main PlotWidget on every refresh, fixing the case where only the enlarged popup displayed telemetry.
- Unified main and popup chart data refresh for frame and sonication changes.
- Enlarged Temperature Trend and Acoustic Spectrum while reducing Power/Score and Waterfall height.
- Added Workstation-like pseudo-3D multi-depth Acoustic Spectrum traces with a visible quiet baseline and expanded peak range.
- Added a display-only 20 mm target circle plus a 10 mm x 10 mm square calculation ROI.
- Restored the Voxel (ROI) 10 mm x 10 mm label and reduced chart-panel padding.
- Renamed the waterfall panel to Relative Acoustic Spectrum vs Replay Time.

## RC1-C0017a
- Fixed acoustic telemetry start-line debouncing so Power/Score segments are populated.
- Added synchronized chart popups.
- Added temperature-map mouse hover readout below the cursor.
- Added Red Threshold step buttons.
- Restored Voxel 10 mm × 10 mm label.
- Increased Acoustic Spectrum headroom and visible quiet baseline.
- Reduced chart height and unused margins.

# C0016c Temperature / Acoustic Refinement

- Temperature Trend defaults to 40–60 °C with 2 °C major ticks, 1 °C minor ticks, background temperature bands, and synchronized replay cursor.
- Red Threshold now changes the temperature at which the overlay turns red; it no longer hides all temperatures below the threshold.
- Power and Score values are drawn inside their shared chart.
- Hydrophone channel selection moved to Acoustic Spectrum and supports single, multiple, and all-channel selection.
- Acoustic Spectrum uses 0.20–0.80 MHz and 0–4 Relative Amplitude axes.
- Waterfall renamed to Acoustic Spectrum Over Replay Time and uses relative-amplitude color intensity.
- Fallback voxel changed to 10 mm × 10 mm.

# C0016a
- Initialized Temperature Trend workspace
- Prepared Peak Navigation foundation


## RC1 C0016c ReplayVisibilityFix
- Reset WL/WW per sonication so DQA images do not inherit prior settings.
- Replaced inline hydrophone checkboxes with compact CH popup multi-selection.
- Added colored relative-amplitude waterfall LUT and clearer panel title.
- Fixed Acquisition_Brain segment start detection so Power/Score curves populate.
- Reduced chart header/margin waste.
- Added target-centered 20 mm blue circular ROI.
- Added Temperature Trend mouse-hover Max/Avg/Cursor temperature popup.


## C0018 Multi-CH 3D Heatmap / CPC Optional
- Fixed hydrophone labels to CH0 through CH7.
- Sonication-folder SpectrumMsg is the only default acoustic source.
- Added CPC OFF/ON button; CPCFiles SpectrumMsg/Acquisition DMP candidates are decoded only while enabled.
- Added per-Sonication main-frequency resolver with ACT/settings priority, then Xd INI, then 650 kHz fallback.
- Changed Relative Acoustic Spectrum into a perspective heat-map with channel-coloured ridge curves.
- Applied stable fixed colours to CH0..CH7.
- Explicitly marks Sonication and CPCFiles source kinds in decoded spectrum frames.

## RC1 C0024 — Synchronized Cavitation Timeline

- Added a standalone PySide6 Hydrophone RE Lab GUI.
- Added ZIP/folder/file drag-and-drop import and recursive candidate discovery.
- Added Hex/ASCII Binary Explorer with offset and length controls.
- Added Interactive Decoder for Float32/64, Int16/32, UInt16, UInt8 and endian selection.
- Added automatic structure profiling and ranked numeric candidates.
- Added waveform, FFT, PSD and dB previews with main/sub/ultraharmonic guides.
- Added band-energy table, candidate double-click loading, telemetry correlation and lag search.
- Added JSON/CSV/PNG session export and evidence report display.
- Updated build/04_HYDROPHONE_RE_LAB.bat to launch the GUI.
- Added build/05_BUILD_HYDROPHONE_RE_LAB_EXE.bat for standalone Nuitka EXE creation.

### C0024 timing/cavitation corrections
- Removed the fixed 4-second-per-frame replay time assumption.
- Removed telemetry normalization/stretching to the MR replay span.
- Added a measured common elapsed-time axis from Acquisition_Brain per sonication.
- Temperature, Power, Score, cursors, and replay navigation now share the same sonication duration.
- Added Cavitation Event Timeline tab with Sonication selector (default 5).
- Added synchronized Power/Score plot, log-event markers, findings, and CSV/JSON export.
- Added power-reduction candidate detection and Score threshold timing.


## RC1-C0025 DQA Information / XD Prototype
- Added left-side Sonication summary: Orientation, Frequency Dir, Energy, Power, Duration, Frequency.
- Updated Info window with DQA and result context.
- Added single-instance MR and Scan protocol information popups.
- Added single-instance XD popup for SkullMeasures element-map visualization.
- XD parameter selection redraws automatically and supports enabled/disabled element filtering and hover values.
- Sonication changes refresh all open information windows without creating duplicate popups.

## RC1-C0025a Information Data / XD Map Hot Fix
- Search metadata across the complete extracted export.
- Decode MR rows from MRFiles/review.out.
- Populate Scan information from Sonication ACT and resolved timing.
- Search SkullMeasures by active sonication across the workspace.
- Replace the XY chart with a workstation-style transducer element map and gradient scale.

## RC1 C0027-02b — Replay Diagnostics Framework
- Added a permanent Diagnostics tab connected to the C0027 Metadata Engine.
- Added automatic validation after ZIP/folder import.
- Added Health Score, metadata coverage, Warning Center and Resource Monitor.
- Added Sonication Metadata Explorer, Replay Inspector and double-click Replay navigation.
- Added timeline inventory for MR, sonication, replay, temperature and SpectrumMsg resources.
- Added metadata load/performance metrics.
- Added JSON, CSV and standalone HTML diagnostic report export.

## RC1-C0029 PlanningHydrophoneReplay
- Added PlanningDataService for CT/SDR, pre-treatment MR, registration and Sonication1 non-replay RAW classification.
- Added HydrophoneReplayService with eight-channel SpectrumMsg replay grouping.
- Added Planning / Reference and Hydrophone 1-8 application tabs.
- Added `03_AUDIT_PLANNING_HYDROPHONE.bat` and JSON audit output.

## RC2-R0003 Atomic Frame Snapshot

One immutable frame snapshot now carries the decoded replay frame, elapsed time, mapped magnitude/temperature indices, and mapped spectrum index to every synchronized view. Old snapshots are invalidated when the Sonication source changes.
