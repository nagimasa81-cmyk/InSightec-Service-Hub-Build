# Commit0121 — Stability and Workflow Fix

- Quick Spike Detect now uses a fast sparse-peak screen and avoids the full Raw Data Compensation candidate pipeline.
- Auto Correct results can be reviewed immediately because comparison images are generated when the result is installed.
- Dragging an image into Spike Diag or Artifact Diag keeps the active diagnostic tab instead of returning to Image Workspace.
- Exit guide checkboxes use a visible high-contrast indicator in dark and light environments.
- Existing Image Workspace, Raw Data Compensation, Tracker Signal and build workflows are retained.

# Commit0118 — Guided Startup and Exit Confirmation

## User guidance

- Raw Data Compensation buttons include concise hover explanations.
- `? Raw Data Compensation Guide` opens a six-page workflow guide at any time.
- On startup, the application asks whether the guide and tour should be shown.
- Selecting **No — Do Not Ask Again** suppresses the startup question on later launches.
- On application close, a confirmation dialog prevents accidental exit.
- Its **Show the guide and guided tour at the next startup** checkbox is off by default.
- When checked before closing, the guide is forced to open once at the next startup.

# MR Image Explorer — Commit0103

## Commit0103 Auto Retry / Best Quality

- Auto Correct now completes up to six automatic Quick Adjust trials without requiring user input.
- Trial presets use Artifact Removal 50/60/70/80/90/100, Image Detail 75, and Protection 85/75/65/55/45/35.
- Every trial performs Candidate Detection, Validation, Virtual Compensation, and Quality Evaluation using the existing engine.
- Retry occurs when no validated candidate is found or Quality is below 60.
- After all trials, the best result is selected by Quality. Ties prefer less Image Change, less Residual Artifact, greater Detail Preservation, then greater Artifact Reduction.
- Progress displays Searching Artifacts, Trial n / 6, and Evaluating Quality.
- Only when all trials remain unreliable, Auto Correct offers Manual Paint, Expert Settings, or Close.
- Quick Adjust remains as optional fine tuning; Manual Paint remains the last resort; Expert Settings remains for research use.
- Existing functions, build scripts, GitHub Actions compatibility, and EXE startup structure are retained.

# MR Image Explorer — Commit0090

## Commit0090 updates

- Fixed **Clear Paint** so it immediately clears the logical RAW mask and the visible overlay.
- Clear Paint now also invalidates detection, preview, Difference data, comparison availability, and Apply state.
- Added **Frequency-aware Hybrid Compensation v2** with adaptive Low/Mid/High band gains.
- Added DC-region protection to preserve anatomical contrast.
- Added artifact-energy-driven spectral weighting and direction-aware Stripe/Band weighting.
- Retains Guided Poisson Solver, High/Extreme, Hermitian symmetry, History, and synchronized Difference Viewer.



## Commit0073 - Frame Lock + Spike Detection Review Deck

- Image Workspace slice changes now lock the viewer frame during image update.
- Delayed layout stabilization after DICOM selection was removed to prevent visible frame rebound.
- Viewer fit uses deterministic `fit_to_image()` instead of executable `autoRange()` calls.
- Added `docs/Spike_Detection_Review_Deck.md` and `docs/Spike_Detection_Review_Deck_Commit0073.pptx` for step-by-step spike detection review.
- Added `test_commit0073_frame_lock_review_deck.py`.

# MRI Raw & FFT Explorer — Commit 0008 Prototype

Windows desktop prototype based on the approved image-first workspace.

## Main prototype behavior

- Large main image viewer.
- FFT/k-space log-magnitude is the default display.
- One-click display buttons: **FFT**, **Original**, and **Both**.
- The selected button always indicates the current display state.
- Movable horizontal and vertical crosshair lines over the main image.
- Dragging either line updates the lower profile graph immediately.
- Row/Column profile selection with slider and numeric position control.
- Magnitude, Real, Imaginary, and Phase profile modes.
- Resizable upper/lower areas using a live Qt splitter.
- In Both mode, FFT and Original images are displayed side by side with synchronized line positions.
- Drop-only main import workflow. DICOM files, folders, ZIP, GE TrackerImg/PFile, CSV, TXT, NPY, and NPZ are supported by the prototype.
- Existing export operations remain under the File menu.
- DICOM header display, filtering, and Excel export.
- Tracker PFile candidate reconstruction and automatic registration of its complex raw stream in **1D Signal Studio**.
- Selected DICOM/k-space line can be sent directly to 1D Signal Studio.

## Important prototype limitations

- GE Tracker reconstruction uses heuristic matrix and complex-int16 detection. It is not a replacement for GE Orchestra reconstruction.
- Generic `.raw`, `.bin`, and Siemens `.dat` are detected, but the full interactive binary-layout dialog/vendor reconstruction workflow will be reintegrated after evaluation of this new layout.
- FFT shown for DICOM is pseudo-k-space generated from the reconstructed DICOM pixels.

## Run from Python

```text
01_RUN_PYTHON_DEBUG.bat
```

## Recommended local build

```text
02_BUILD_FAST_STANDALONE.bat
```

## GitHub Actions

Place the workflow at the repository root:

```text
.github/workflows/build_mri_raw_fft.yml
```

Run the workflow with `fast_pyinstaller`. The output is a standalone Windows ZIP artifact.


## Commit 0008 R1 — Simple GitHub Artifact

The workflow no longer creates `MRI_Raw_FFT_Explorer_Windows.zip` inside the
GitHub Artifact.

GitHub Actions now uploads the completed standalone folder contents directly.
When the Artifact is downloaded from GitHub, there is only one ZIP layer. After
opening or extracting it, `MRI_Raw_FFT_Explorer.exe`, `_internal`, README, and
BUILD_INFO are immediately available.

Expected download structure:

```text
MRI_Raw_FFT_Explorer_Windows-fast_pyinstaller.zip
├── MRI_Raw_FFT_Explorer.exe
├── _internal
├── README.md
├── BUILD_INFO.txt
└── vendor_sdk_config.json
```


## Commit 0008 R2 — Tab Navigation and Import Progress

- Image Workspace, 1D Signal Studio, and DICOM Header remain available as persistent top tabs.
- 1D Signal Studio includes a prominent Back to Image Workspace button.
- Selecting a Tracker signal in Explorer opens the 1D Signal Studio tab without replacing the main workspace.
- A modal progress window is shown while scanning folders, extracting ZIP files, detecting DICOM images, and loading Tracker/1D data.
- The progress window shows the current file and supports Cancel.
- ZIP extraction still validates paths before extraction.
- The single-layer GitHub Artifact packaging introduced in R1 is retained.


## Commit 0008 R3 — Spike Noise Detection

A `Spike` button is available in Image Workspace.

- Scans imported GE Tracker/PFile, extensionless TrackerImg, RAW, BIN, and DAT files.
- Uses robust median/MAD amplitude and first-difference scores.
- Threshold is adjustable in the Spike Detection tab.
- Lists score, spike-group count, strongest sample, and inspected sample count.
- Double-clicking a result opens the extracted raw signal in 1D Signal Studio.
- Detected spike positions are overlaid with red markers.
- Long generic binary files are analyzed from a bounded tail region to limit memory usage.

This is a screening function. Vendor-specific headers, channel layouts, and expected
sequence impulses can affect the score, so flagged files should be reviewed visually.


## Commit 0008 R4 — Tracker Signal Explorer

Tracker file inspection is separated from Spike Detection.

- Adds a dedicated `Tracker Signal Explorer` tab.
- Reads Tracker PFile / TrackerImg data without FFT.
- Automatically evaluates every raw line.
- Picks and ranks the strongest lines by Peak, RMS, Energy, Mean Magnitude, or Variance.
- Displays the top lines immediately.
- Supports Magnitude, Real, Imaginary, and Phase views.
- Allows up to eight selected lines to be overlaid.
- Includes Previous / Next Strong Line navigation.
- Exports line metrics to CSV.
- Keeps the existing Spike Detection tab as a separate diagnostic view.


## Versioned GitHub Artifact workflow fix

The Artifact name now includes the application version, release identifier, and build engine:

```text
MRI_Raw_FFT_Explorer_v0.8.3_Commit0008_R4_fast_pyinstaller.zip
```

The Artifact remains a single ZIP layer. `BUILD_INFO.txt` includes the application
name, version, release, Git SHA, engine, Python version, and UTC build time.


## Commit 0008 R5 — Image Editing and Display Controls

- Explorer selection follows Up/Down arrow keys and immediately updates the image.
- Image A/B registration with Add and Subtract processing.
- Processed Add/Subtract files include `_addsub` in the name.
- A movable rectangular compensation ROI interpolates the selected region from surrounding signals.
- Compensation files include `_comp` in the name.
- Processed files are stored under `MRI_Raw_FFT_Work` beside the source data.
- DICOM sources produce a derived DICOM plus an NPY working copy.
- Dynamic Range and Window Level are directly adjustable.
- Presets: Auto, Wide, Soft Tissue, High Contrast, and Narrow.
- Saved processed files appear under `Processed Files` in Explorer.


## Commit 0008 R6 — Tracker Position Conversion

Analysis of the attached TrackerApp identified the following position pipeline:

1. Zero-padded FFT of a selected tracker direction (`GE_FFTLength = 1024`).
2. Peak-bin conversion into millimeters using FOV.
3. Plane and in-plane rotation mapping.
4. Least-squares solution from at least three directional measurements.
5. CenterOffset addition.
6. Optional AP-coordinate sign inversion (`OpposeAPcoordinate = 1`).
7. Optional vendor gradient-map correction.

The new `Tracker Position` tab implements steps 1–6. It is separate from:

- `Tracker Signal Explorer`, which continues to display raw tracker lines without FFT.
- `Spike Detection`, which remains an independent diagnostic workflow.

Gradient-map correction is explicitly reported as not applied until compatible field
distribution files and their exact interpolation format are available.


## Commit 0009 R1 — Artifact Learning and Artifact DB

- DICOM Explorer is grouped by Series and supports expand/collapse.
- Multiple images can be selected for training.
- Artifact labels include Spike, Frequency, and expandable custom types.
- Images can be manually reclassified, including `Not Artifact`.
- How to Resolved supports dropdown values and manual additions.
- Normal images can be selected from the study or loaded separately.
- Artifact-vs-normal difference features are stored.
- SQLite is the working DB format.
- JSON import/export supports sharing and master updates.
- Spike Detection remains separate and can be used as a source for later labeling.


## Commit 0009 R2 — Compensation ROI Fix

- Automatically switches to Original image mode.
- Adds an explicit Preview Compensation step.
- Shows ROI coordinates and mean/max pixel change.
- Uses all four surrounding borders for interpolation.
- Shows the compensated result immediately.
- Apply & Save writes the `_comp` file and displays the exact save path.
- Cancel restores the original image.


## Commit 0010 R1 — DB-trained Artifact Detection and Strongest Tracker Line

### Artifact Detection

- Spike is classified from Artifact DB training samples instead of a fixed threshold.
- Frequency and all additional Artifact classes use the same trainable detector.
- Classes require a configurable minimum number of labeled samples.
- Results show predicted class, confidence, normalized distance, training support, and alternatives.
- Low-confidence and insufficient-training results are explicitly identified.
- Selected detection results can be sent to Artifact Learning for manual correction or reclassification.
- Spike Diagnostic remains separate for raw waveform inspection.

### Tracker Signal Explorer

- Automatically identifies exactly one strongest line using RMS signal strength.
- Displays that line's Magnitude by default.
- Reports the strongest line number, RMS, and peak.
- FFT remains disabled in Tracker Signal Explorer.

### Reusable GitHub workflow

- `.github/workflows/build_module_generic.yml` no longer contains a hard-coded version or commit.
- `version.json` controls application name, version, commit, EXE name, and Artifact name.
- Future releases only require a new SOURCE ZIP with an updated `version.json`.
- The same YML can be reused without modification.
- Artifact output remains a single ZIP layer.


## Commit 0010 R2 — Universal Build Metadata

- `version.json` is now a required standard file for this SOURCE ZIP.
- The included Universal Build System v2 prefers `version.json`.
- Older SOURCE ZIP files without `version.json` remain buildable.
- Legacy metadata is inferred from the SOURCE ZIP filename.
- Unrecognized metadata falls back to `Unknown` without stopping the build.
- Future releases update only `version.json`; the YML remains unchanged.
- Artifact output remains a single ZIP layer.


## Commit 0010 R3 — Universal Build System v3

The common workflow now resolves build structure automatically.

Build strategy priority:

1. `version.json` entry point
2. Known build BAT files
3. PyInstaller `.spec`
4. `pyproject.toml`
5. Known Python entry filenames
6. Python source scoring

Python source scoring considers:

- `if __name__ == "__main__"`
- `QApplication`
- `QMainWindow`
- Tk / wx application creation
- `def main()`
- `.show()`
- entry-like filenames

The workflow also locates the generated EXE automatically after BAT, SPEC,
PyInstaller, or Nuitka builds. Existing legacy SOURCE ZIP files remain supported.


## Commit 0010 R4 — Ready-to-Build Universal Build v4

- BAT execution is completely disabled.
- A valid PyInstaller SPEC is used when present.
- Otherwise, the Python entry point is detected and packaged directly.
- Old BAT references to obsolete Python filenames can no longer break the build.
- Resources and common installed packages are collected automatically.
- Generated EXE and output folder are detected automatically.
- Artifact output remains a single ZIP layer.


## Commit 0011 R1 — Raw Compensation, Add/Sub Preview, Learning Preview

### Raw compensation
- Selecting compensation does not change Display mode, preset, Window Level, or Dynamic Range.
- ROI coordinates always map to raw/k-space data.
- Preview compensates raw data first, runs IFFT reconstruction again, and refreshes the image.
- Levels: Low, Mid, High.
- Multiple ROIs can be committed sequentially.
- Previous / Next navigates compensation history.
- The displayed history state can be saved with reconstructed image and raw NPY.

### Add/Subtract
- Preview opens Image A, Image B, and Result in three synchronized panels.
- Results are saved only after preview confirmation.

### Artifact Learning
- Selected training images can be previewed.
- Previous / Next Selected navigates multiple selected images.


## Commit 0012 R1 — Shared Tracker Data

Tracker PFile / TrackerImg data is now retained as common application data.

- Image Workspace can display Tracker raw magnitude and reconstructed image.
- Strongest Tracker line is registered in 1D Signal Studio automatically.
- Tracker Signal Explorer provides buttons to open Image Workspace and 1D Studio.
- Explorer tree includes the strongest line and Tracker workspace views.
- Artifact Detection can classify the current Tracker raw matrix using Artifact DB.
- Artifact Learning can preview Tracker magnitude and save it as a training sample.
- Tracker Position continues to use the same loaded Tracker matrix.
- Loading a Tracker file does not discard the shared data when changing tabs.


## Commit 0013 R1 — Multi Tracker Navigation and Clear Controls

- Multiple Tracker files with Previous/Next, dropdown, and Left/Right keys.
- Clear Current/All Tracker files.
- Clear Selected/All imported images.
- Remove Selected/Clear All 1D signals.
- Clear Add/Sub A, B, result; clear compensation history; clear Artifact Learning selection.


## MR Image Explorer RC1 Prototype Pack1 — Commit0014a

- Renamed application and five-tab RC1 layout.
- Tracker Position integrated under Tracker Signal.
- Artifact Detection/Learning integrated under Artifact Diag.
- DICOM Header popup with copy, edit, numbered save, and close.
- Single-open accordion for Spike, Raw Compensation, and Add/Sub.
- Prototype Range/Level controls and Quick Spike Detect candidate highlighting.
- Initial modular project folders for Pack2/Pack3 migration.


## Commit0014a HotFix1

- Fixed ZIP import completion error caused by obsolete `header_table` access.
- DICOM list clicks now update the image immediately.
- Auto Window/Level recalculates for every selected image.
- Type changes update Original, FFT, and line profile in real time.
- Explorer entries now show filename, instance, matrix size, and bit depth.
- Artifact DB Open/Create and JSON Import now use the correct dialogs.
- Compensation History Clear repeatedly restores the original image.
- Image right-click menu includes Window/Level, Pan, Zoom, Paging, ROI, and Auto Window/Level.
- Paging mode supports mouse-wheel image navigation.


## Commit0014a HotFix2

- Initial display after image loading is Both.
- Tracker source selector was removed from Image Workspace.
- Selected Explorer rows use translucent light-blue highlighting.
- Compensation ROI now has resize handles at all four corners.
- Original and Raw Window/Level are managed independently.
- Original Auto Window/Level recalculates per image.
- Raw Window/Level remains manual until explicitly reset.
- Right-click image menu now controls Pan, Zoom, Paging, ROI, FFT, Original,
  Both, Auto Window/Level, and Back to Default.
- Window/Level mode uses mouse wheel for Level and Ctrl+wheel for Width.
- Add/Sub and generated images can be displayed in FFT, Original, or Both.
- Saved generated images are added to Explorer and remain selectable.
- Output top folder is shown in the lower-right and can be changed.
- Default output is created below the opened image folder.
- JPEG, PNG, and BMP files are supported as Original-only images.
- Spike Apply now processes selected DICOM original images using raw/k-space
  spike suppression; RAW/PFile scanning remains available when no DICOM is selected.


## Commit0014a HotFix3

- Right-side settings are placed in a vertical scroll area with wider controls.
- Explorer minimum width was reduced so the user can freely make it narrow.
- Explorer text is single-line and elided; full details remain in tooltips.
- pyqtgraph's default context menu is disabled.
- The MR Image Explorer context menu now opens reliably on image right-click.
- Context menu actions include operating instructions through tooltips.
- `FFT Current Image` immediately recalculates FFT from the selected image and displays it.
- Back to Default resets view, Type, levels, and zoom.
- Multi-spike detection now uses local robust k-space outlier scoring,
  conjugate-pair correction, and repeated-stripe validation.
- Wide / Mid / Fine sensitivity was increased for heavy multi-spike examples.


## Commit0014a HotFix4

- Larger Service Hub-style progress window.
- Quick Spike Detect limited to high-confidence candidates, maximum 100.
- FFT Current Image replaces content in the current panel.
- Back from FFT restores the pre-FFT image.
- Manual WW/WL no longer returns to Auto.
- Current mouse action is displayed with hover help.
- Crosshair starts at center and preserves its normalized position.
- Spike Processing refreshes the four-panel Spike Diag view.
- Compensation preserves the expected central MRI cross pattern and suppresses ROI outliers toward local background noise.
- ZIP import recursively reads deeply nested folders.
- Tracker `.dat` and same-name `.txt` analysis are loaded together.
- Multiple Tracker files remain listed and do not force-open Tracker Signal.


## Commit0014a HotFix5
- Fixed EXE startup failure caused by missing QGridLayout import.
- Added startup import validation.
- Reworked Quick Spike Detect using Series-relative robust classification with High Confidence, Review, and No Spike.
- Removed arbitrary candidate count cap.
- Added Explorer drag-out to Windows Explorer for original files, multiple selection, Series selection, and Tracker DAT/TXT pairs.


## Commit0014a HotFix6

- Fixed the initial-import hang caused by decoding every DICOM Pixel Data item.
- DICOM import now reads headers first and builds the Explorer list without pixel decompression.
- Pixel Data is loaded only when an image is selected or required for analysis.
- A bounded lazy-image cache keeps recently viewed images while releasing older arrays.
- Only the first DICOM image is decoded during initial import.
- Folder and ZIP scanning filter unsupported files before DICOM probing.
- Same-name Tracker TXT files are no longer opened as independent 1D signals.
- Tracker files are collected and loaded as a batch without repeated tab switching.
- Explorer multi-selection blocks display signals until selection is complete.


## Commit0014a HotFix7

- Fixed duplicate import requests from overlapping drop handlers.
- Import is deferred until the drag/click event has completed.
- The progress window is forced to the foreground and remains accessible.
- Folder scanning updates the progress window every 100 checked files.
- The drop banner is disabled during import and restored afterward.
- Clicking the drop banner opens a Files / Folder selection dialog.
- Added File menu commands for Import Files and Import Folder.
- Repeated import requests bring the existing progress dialog to the front.
- Main-window and banner drops now use one shared import-request path.


## Commit0014a HotFix8

- Build packaging now validates the embedded Python runtime DLL.
- If PyInstaller does not place `python313.dll` in `_internal`, the workflow
  copies it explicitly from the GitHub Actions Python installation.
- `python3.dll` is also copied when available.
- Staging uses `robocopy` rather than wildcard `Copy-Item`.
- The staged Artifact is rejected if the startup EXE or Python DLL is missing.
- Added `VERIFY_PACKAGE.bat` to check the extracted distribution.
- Added `RUN_MR_IMAGE_EXPLORER.bat` to start the packaged EXE from its own folder.
- A SHA-256 package manifest is generated before Artifact upload.


## Commit0014a HotFix9

- Restored the missing second half of `import_paths()`.
- Fixed drag/drop accepting files but performing no indexing or display update.
- DICOM metadata indexing, Explorer population, first-image display, Tracker loading,
  raw-file listing, bitmap listing, and signal loading are all executed again.
- Import now reports recognized and skipped file counts.
- Raw/P files that cannot yet be decoded are still listed in Explorer.
- Raw/P file selections can be dragged to Windows Explorer as original files.
- The application returns to Image Workspace after a successful import.


## Commit0014a HotFix10

- Import now performs indexing only while the progress window is open.
- DICOM Pixel Data decoding starts only after the Import window closes.
- Tracker files are listed without being parsed during import.
- Tracker parsing starts only when the user selects a Tracker item.
- Bitmap and signal files are also loaded only when selected.
- Import completion no longer depends on image decoding or Tracker analysis.
- Tracker loading no longer clears the main Explorer or forces tab navigation.


## Commit0014a HotFix11

- ZIP extraction, deep folder scanning, and DICOM header indexing now run in a QThread.
- The UI thread no longer performs ZIP extraction or metadata indexing.
- The progress window is non-modal, always-on-top, and updated through Qt signals.
- Large ZIP members are copied in 1 MB chunks with cancellation checks.
- Explorer construction occurs only after the background worker completes.
- First-image Pixel Data is decoded only after the progress window closes.
- Cancel remains responsive during folder scanning, ZIP extraction, and indexing.


## Commit0015 Import Engine RC

- Replaced the Qt Worker/QThread import path with a Python thread plus event queue.
- The progress window is painted before the background thread starts.
- ZIP extraction, recursive scanning, and DICOM header indexing never run on the UI thread.
- A 50 ms UI timer receives progress, completion, failure, and cancellation events.
- A worker that exits without a result is detected and reported instead of leaving Importing displayed forever.
- Cancel uses a thread-safe Event and remains responsive during ZIP extraction and scanning.
- The existing lazy Pixel Data loading and Explorer population are retained.


## Commit0015a Startup Fix

- Restored the missing `main()` application entry point.
- Restored `if __name__ == "__main__"` so the packaged EXE opens the UI.
- Added startup dependency validation.
- Startup exceptions are written to:
  `%LOCALAPPDATA%\MR_Image_Explorer\startup_error.log`
- Added a visible startup error dialog when initialization fails.
- Added Python and packaged-EXE startup smoke tests to GitHub Actions.
- The workflow now rejects source packages that do not contain a runnable entry point.


## Commit0015b Import Start Fix

- Fixed a race condition between the Import worker and the 50 ms watchdog timer.
- The background worker now starts before the polling timer.
- The watchdog no longer reports a stopped worker during its startup period.
- Added a 1.5-second worker startup grace period.
- The result queue is drained one final time before reporting abnormal worker exit.
- ZIP extraction sends heartbeat progress updates while copying large members.
- Import state is fully reset after completion, cancellation, or failure.


## Commit0015c Embedded Progress

- Replaced the separate Import progress window with an in-window overlay.
- The progress overlay is always rendered inside MR Image Explorer.
- Windows focus, modal state, multi-monitor position, and window stacking can no
  longer hide the Import progress display.
- The overlay remains centered when the main window is resized.
- The current phase, determinate/indeterminate progress, and Cancel button remain
  visible throughout ZIP extraction, folder scanning, and file indexing.


## Commit0015d Layout Progress

- Removed floating and overlay-style Import progress presentation.
- Import progress is now a regular layout panel directly below the drop area.
- The panel cannot be hidden behind pyqtgraph, OpenGL, or native child windows.
- The tab area moves downward while Import is active.
- Current phase, progress bar, and Cancel remain continuously visible.
- The panel is hidden after completion, cancellation, or failure and reused later.


## Commit0015e Progress Import Fix

- Fixed startup failure caused by missing `QProgressBar` import.
- Added the required `QSizePolicy` import used by the layout progress panel.
- Added both classes to startup dependency validation.
- The application now fails the GitHub startup smoke test if either class is missing.
- Commit0015d layout-based progress presentation is retained.


## Commit0016 Interaction Stability

- Improved Import progress text wrapping and clipping.
- Added deferred layout stabilization after Import and image changes.
- Removed DICOM list tooltip popups.
- Added DICOM checkboxes for reliable multi-image processing selection.
- Added Previous Import to restore the prior DICOM list.
- Simplified right-click actions to deterministic commands.
- Fixed Compensation Preview failure caused by missing line position ratios.
- Quick Spike Detect now loads lazy DICOM pixels before analysis.
- Quick Spike Detect reports High Confidence, Review, and read errors.


## Commit0016a Add/Sub Save Fix

- Add/Sub output no longer uses the temporary ZIP extraction folder.
- Default output is stored under the original ZIP/file/folder location:
  `MR_Image_Explorer_Output/AddSub`.
- Add/Sub DICOM metadata is taken from Image A.
- Both DICOM and NPY output creation are verified after saving.
- A visible success message shows the complete saved path.
- Save errors now display the exact failure reason.
- Existing filenames are preserved by automatically adding `_1`, `_2`, etc.


## Commit0017 Responsive Workspace and Spike Engine

### Responsive workspace

- Initial window is fitted within the current monitor's available desktop area.
- Taskbar area is excluded from the initial geometry.
- Window size is limited to 96% width and 94% height.
- Previous off-screen monitor positions are corrected automatically.
- Import, FFT, Both, Spike Diag, Compensation, Add/Sub, and tab changes trigger
  deferred responsive layout recalculation.
- The top workspace toolbar is horizontally scrollable.
- Right-side controls remain vertically scrollable and can shrink on notebooks.
- The lower profile/tracker plots collapse before the main images become inaccessible.
- Explorer, image, and right-panel splitter ratios adapt to the current width.
- The initial display is Both rather than FFT.

### Spike detection

- Image-domain periodic stripes are evaluated in row, column, and diagonal directions.
- Raw/k-space candidates use local median/MAD background noise estimation.
- The normal central MRI cross and low-frequency center are excluded.
- Randomly distributed isolated high-signal points contribute to the raw spike score.
- Conjugate-pair support, same-Series outlier score, and neighboring-slice difference
  contribute to confidence.
- Results remain High Confidence, Review, or No Spike without an artificial count cap.
- Spike correction replaces only isolated raw/k-space outliers and re-evaluates
  image-domain stripe strength after reconstruction.

### Latest-source audit fixes

- Removed duplicate `@staticmethod` decoration from compensation interpolation.
- Fixed hard-coded workspace splitter sizing.
- Fixed the workspace reverting to FFT at construction.
- Added responsive recalculation after mode and tab changes.


## Commit0018 Viewer and Spike Engine

- Initial display fits after layout within the active monitor.
- Import stage and current file use separate compact labels.
- Original and Raw Data WW/WL remain independent.
- Right-drag changes WW/WL; wheel zooms; Ctrl+wheel pages.
- Spike detection includes straight periodic stripe analysis at multiple angles.


## Commit0019 RC1 Prototype

- Window remains vertically and horizontally resizable after initial screen fit.
- Responsive layout no longer re-applies the initial window size on every resize.
- Spike logic starts with Original-image stripe extraction, maps stripe-only frequency support, and verifies it against actual Raw/k-space peaks.
- Multiple directions and Fine/Mid/Wide groups are retained.
- Curved/ring patterns without sparse Raw agreement are classified as Not Spike.
- Spike Diag provides Original, Stripe Only, Mapped Raw Candidate, Corrected, Actual Raw, and Processed Raw views.
- Developer Mode shows group angles, scale, peak strength, Raw agreement, and match count.
- Artifact Learning includes quick Spike and Not Spike class preparation.


## Commit0020 Compact Import Progress

- Removed the separate second progress-information line.
- The top row now contains only the Import title and an always-visible Cancel button.
- Cancel is aligned to the upper-right edge of the progress panel.
- The progress bar is displayed immediately below the top row.
- Only the current file or current item is shown under the progress bar.
- Long file paths preserve the useful filename ending with leading ellipsis.
- Progress panel height was reduced to preserve the image workspace.
- Cancel changes to `Canceling...` and is disabled after it is pressed.


## Commit0021 RAW Import Engine

- RAW-family files inside ZIPs, folders, and direct file selections are indexed.
- Added `.raw`, `.bin`, `.img`, `.kspace`, `.cfl`, `.rawdata`, `.complex`,
  compatible `.dat`, and extensionless-file detection.
- Clicking a RAW entry now performs real format detection and image loading.
- Supported automatic interpretations:
  - Signed/Unsigned Int16
  - Float32
  - Complex Int16
  - Complex Float32
  - Little Endian and Big Endian
  - Common MRI matrix dimensions from 64 to 2048
  - Small common header offsets
- Complex RAW is treated as k-space and reconstructed with inverse FFT.
- Real RAW is treated as an image/raw array and receives an FFT representation.
- Candidate selection uses file-size compatibility, dynamic range, entropy,
  reconstructability, matrix plausibility, and MRI-like frequency distribution.
- Low-confidence or unsupported RAW files are rejected with an explanation instead
  of displaying corrupted data.
- Successful interpretations are cached in
  `MR_Image_Explorer_Output/raw_import_profiles.json`.


## Commit0022 Orientation and RAW Display

- Original image panels show DICOM patient orientation by default.
- R/L/A/P/H/F and oblique two-letter labels are supported.
- Orientation can be manually edited and reset to DICOM defaults.
- FFT panels do not show patient-orientation labels.
- RAW Auto display compares Direct Array and Reconstructed Image quality.
- RAW no longer always displays the raw matrix as if it were a normal image.
- RAW Display can be changed later among Auto, Reconstructed Image,
  Direct Array, and k-space Magnitude.


## Commit0023 FUS RAW Decoder Integration

The RAW preview logic from `FUS Investigation Replay v1.6.0 RC1 Commit0011`
is integrated.

- Candidate arrays are normalized using the 1st and 99th percentiles.
- Horizontal and vertical adjacent-pixel correlations are calculated.
- Their average becomes the FUS image-likeness score.
- The same mild non-square matrix penalty is applied.
- Strong real-valued candidates are ranked above noise-like interpretations.
- High-scoring real RAW recommends `Direct Array`.
- Complex RAW continues to recommend inverse-FFT reconstruction.
- The file-information panel shows image-likeness and recommended display.
- This specifically supports treatment RAW such as 512×512 unsigned 16-bit
  images that should appear directly as normal anatomical MRI images.


## Commit0024 FUS RAW Preview Match

- High-confidence FUS real RAW is displayed directly, without inverse FFT.
- Direct preview uses the same 1st-99th percentile normalization as FUS Investigation Replay.
- Auto treats Direct Array with image-likeness >= 0.45 as authoritative.
- Intended to reproduce previews such as 256x256 <u2, image-likeness 0.992.


## Commit0025 Exact FUS RAW Instant Preview

The exact `try_render_raw()` logic from
`FUS Investigation Replay v1.8.0 RC1 Commit0013` is now the first decoder.

- Exact candidate data types: `<u2`, `<i2`, `<f4`.
- Exact candidate widths:
  128, 192, 256, 320, 384, 448, 512, 640, 768, 1024.
- Exact 1–99% normalization.
- Exact horizontal/vertical adjacent-pixel correlation score.
- Exact non-square layout penalty.
- Exact FUS decoding is performed during ImportWorker indexing.
- Successful previews are stored in an in-memory RAW preview cache.
- Clicking a cached RAW entry displays it immediately without a progress panel.
- The tree displays matrix, dtype, and image-likeness for predecoded entries.
- The broader RAW decoder remains as fallback for formats the exact FUS
  decoder cannot identify.


## Commit0026 RAW Visible Instant Fix

- RAW selection clears all WW/WL values inherited from the previous image.
- FUS preview data is re-normalized to a finite 0–1 display range.
- Original Image is painted directly before the Both workspace is restored.
- The direct first paint uses explicit levels `(0.0, 1.0)`.
- Both/FFT redraw is deferred until splitter geometry is ready.
- Cached RAW preview failures fall back to a fresh exact FUS decode.
- When an import contains RAW but no DICOM, the first RAW is displayed
  automatically after import.
- Selecting a RAW entry no longer leaves both image panels empty.


## Commit0027 RAW Selection Display Fix

Root cause found:

- RAW rows were highlighted in Explorer.
- `itemClicked` was the only event that opened RAW.
- `currentItemChanged` handled DICOM only.
- On some Windows interactions the RAW item became current/selected without
  delivering the expected click event.
- The result was a highlighted RAW row with `No file loaded`.

Fix:

- All Explorer file opening is routed through `_open_tree_item()`.
- Mouse click, current-item change, keyboard navigation and single-selection
  change can all open RAW.
- Clicking the already selected RAW forces it to reopen.
- Re-entrancy guards prevent duplicate decoding.
- RAW display errors are no longer silently swallowed; a visible error dialog
  identifies the failing stage.
- Successful RAW display updates the slice label to the decoded matrix size.


## Commit0028 RAW Selection Root Fix

The actual root cause of RAW rows highlighting without opening was identified.

- `_active_tree_source_key` and `_tree_open_in_progress` were accidentally
  initialized on `ImportWorker`.
- `_open_tree_item()` runs on `MainWindow`.
- The first access to `self._tree_open_in_progress` therefore raised an
  `AttributeError` before entering the method's visible error-handling block.
- Qt signal exceptions were not shown in the application UI, so the symptom was
  only a highlighted RAW row and `No file loaded`.

Fix:

- Both selection-state members now belong to `MainWindow`.
- They are removed from `ImportWorker`.
- `_open_tree_item()` defensively initializes them when absent.
- Mouse-click and current-item signal entry points now display unexpected
  exceptions instead of failing silently.
- RAW files are also included in Explorer drag-to-Windows file copying.


## Commit0029 RAW ndimage Import Fix

The RAW selection error shown in Commit0028 was:

`NameError: name 'ndimage' is not defined`

Root cause:

- `_raw_image_quality()` uses `ndimage.median_filter()`.
- `scipy.ndimage` was not imported in `app.py`.
- RAW decoding succeeded, but display-quality comparison stopped before image
  rendering.

Fix:

- Added `from scipy import ndimage`.
- Existing exact FUS RAW decoding, cache, selection handling and direct preview
  are unchanged.


## Commit0030 Remove SciPy Dependency

Commit0029 failed before the GUI opened because the packaged EXE did not
contain SciPy.

- Removed the SciPy import.
- Replaced the single 3×3 median-filter use with a NumPy-only implementation.
- No additional package or Nuitka hidden import is required.
- RAW/FUS decoding and immediate display behavior remain unchanged.


## Commit0032 Complete Image Inventory

ZIP and folder imports now build a complete recursive image inventory.

- Every file in every subfolder is inspected as possible DICOM first.
- DICOM without a standard extension is included.
- TIFF images are supported in addition to JPEG/PNG/BMP.
- All recognized DICOM, RAW and bitmap images are listed in Explorer.
- Source ZIP/folder and relative subfolder are preserved for grouping.
- DICOM hierarchy:
  Source → Patient → Study → Series → Image.
- RAW and bitmap hierarchy:
  Source → Relative folder → Image.
- RAW rows include matrix, data type, image-likeness and recognized/
  experimental status when available.
- Information from DICOM headers, RAW analysis, file structure and names is
  used together to organize the inventory.
- Unsupported RAW uses the Experimental Preview fallback instead of ending
  immediately with a matrix/data-type error.


## Commit0033 Orientation and Annotation

- Coronal default: top=S, bottom=I, left=R, right=L.
- DICOM ImageOrientationPatient remains first priority.
- Missing orientation falls back to metadata, filename and scan-plane presets.
- RAW defaults to Coronal for the FUS workflow.
- Orientation dialog supports Auto/Axial/Coronal/Sagittal.
- Manual labels, rotation and horizontal/vertical flips are supported.
- Added collapsible Annotation panel below Explorer.
- Annotation modes: Minimum and Full.
- Annotation is also overlaid on Original Image.
- Minimum mode keeps about 2/3 of left height for the list.
- Full mode keeps about 1/2 of left height for the list.


## Commit0054 Pre-Rendering Stable Baseline

This release restarts from Commit0033.

Included:

- Stable DICOM list selection and display.
- Original / FFT / Both.
- Fixed Explorer.
- RAW instant preview and RAW selection display.
- Orientation controls.
- Annotation.
- Spike and artifact tools already present in Commit0033.
- Minimal diagnostic logging.
- Tracking PFiles excluded from Spike Detection.

Intentionally excluded:

- 3D Workspace.
- Rendering Engine.
- Engine architecture/delegation.
- Delayed repaint recovery.
- Forced Original-only display.
- Experimental list popup or replacement list widgets.

Diagnostic logs:

`%LOCALAPPDATA%\MR_Image_Explorer\logs`

This version should be validated as the new Stable Baseline before any
Rendering module is added.


## Commit0055 Explorer Usability

Only the left Explorer was changed. The Commit0054 image-display route is
unchanged.

- Series-centered shallow hierarchy.
- Numeric Series and Instance ordering.
- Compact indentation and filename-first rows.
- MEMP, TMAP, Localizer, Planning, DWI, T1 and T2 purpose labels.
- Series dropdown, text search, type filter and sort selector.
- Clear Filter button.
- Expanded rows, selection and scroll position are preserved.
- Image row tooltips were removed.


## Commit0056 Layout Usability

The stable Commit0054/0055 image display path remains unchanged.

- Explorer, Annotation, and Message/File Info are now three movable vertical
  splitter sections.
- The message area has its own horizontal and vertical scrollbars.
- User-adjusted Explorer width is preserved after image selection and
  responsive-layout updates.
- User-adjusted message height is preserved while Annotation is shown/hidden.
- The image toolbar no longer uses a horizontal scroll area.
- Image-only controls remain directly above the image:
  FFT, Original, Both, Previous, Next, and Slice.
- Workspace-wide controls moved to a fixed toolbar above the tabs:
  Import, Previous Import, Clear Selected, Clear All Images, DICOM Header,
  Orientation, and Quick Spike Detect.


## Commit0057a Minimal MRI Viewer

Built directly from Commit0056. Added only:

- Patient / Exam / Series / Image hierarchy.
- Display Reset button in the upper toolbar.
- Saving Explorer width, Message height, all splitter positions, and window
  geometry at application close.
- Restoring the saved layout at next startup.
- Existing Commit0056 RAW Preview Cache retained.

Not included from the previous Commit0057:

- Thumbnails.
- Expanded Series cards.
- Additional search fields.
- New sort options.
- Header Summary changes.
- Automatic sequence classification.
- Clinical Order.
- Additional filter functions.

The Commit0056 DICOM / RAW / Original / FFT / Both display path is unchanged.


## Commit0057b Orientation Annotation

Only Orientation and Annotation calculations were changed.

- Reads PatientPosition (0018,5100).
- Reads ImageOrientationPatient (0020,0037).
- Reads ImagePositionPatient (0020,0032).
- Calculates row, column, and slice direction vectors.
- Calculates Top / Bottom / Left / Right labels from DICOM patient coordinates.
- Updates labels after display rotation and horizontal/vertical flips.
- Manual orientation overrides remain available.
- RAW and images without DICOM geometry keep the existing fallback behavior.
- Annotation includes the orientation vectors and final display labels.

The Commit0057a image-loading and rendering path is unchanged.


## Commit0057c Orientation Display Fix

- Fixed integration with the existing
  `ImagePanel.set_orientation_labels(self, values)` API.
- Orientation values are passed as one mapping object.
- Added H/F/R/L fallback orientation at startup.
- Orientation or annotation failures no longer stop image selection.
- PatientPosition, ImageOrientationPatient, and ImagePositionPatient support
  from Commit0057b is retained.
- DICOM/RAW image loading, Original/FFT/Both rendering, RAW Preview Cache,
  hierarchy, Display Reset, and layout persistence are unchanged.


## Commit0057d DICOM Orientation Geometry Fix

- RAW, FFT, and k-space panels no longer show patient-orientation labels.
- Orientation labels are shown only on the Original DICOM image.
- Corrected screen-edge mapping from ImageOrientationPatient:
  - screen right follows increasing image columns
  - screen bottom follows increasing image rows
  - left/top use the opposite vectors
- PatientPosition is no longer required and is retained only as diagnostic
  metadata.
- ImagePositionPatient and the slice normal are retained for diagnostics.
- Oblique DICOM images can show two-letter direction labels.
- The supplied GE DICOM samples are recorded in
  `Commit0057d_DICOM_Sample_Analysis.json`.
- Image loading, RAW cache, FFT calculation, rendering, hierarchy, reset, and
  layout persistence remain unchanged.


## Commit0057e Orientation Panel Routing Fix

- Uses the actual viewer state `view_mode`.
- `primary_panel` is FFT/k-space and has no patient-orientation labels.
- `secondary_panel` is Original DICOM and receives orientation labels.
- Both: FFT hidden / Original shown.
- Original: Original shown.
- FFT: all labels hidden.
- Commit0057d DICOM geometry is unchanged.


## Commit0057f Display Pipeline Orientation Sync

- Rebuilt from Commit0057e.
- The discarded fixed A/P swap is not included.
- DICOM base orientation is calculated from ImageOrientationPatient.
- Labels then follow the current display rotation, horizontal flip,
  vertical flip, and transpose state.
- FFT/RAW/k-space panels remain unlabeled.
- Original DICOM is the only panel showing patient orientation.
- Added `orientation_pipeline_trace` diagnostics and a source transform audit.
- Rendering, FFT calculation, and RAW cache are unchanged.


## Commit0059 — Orientation Engine v2

- Added `orientation_engine.py` as the single source of truth for DICOM patient geometry.
- Correctly interprets the first and second `ImageOrientationPatient` triplets.
- Synchronizes labels with pyqtgraph's upward-positive Y display coordinates.
- Keeps Original / FFT / Both image rendering unchanged.
- Adds regression coverage for axial, flipped, conventional-raster, and oblique geometry.
- Expected GE axial display after pyqtgraph mapping: Top=P, Bottom=A, Left=R, Right=L.

## Commit0060 - Orientation UI and GE display convention

- Fixed the Orientation toolbar button so the modal editor is raised and activated reliably.
- Added status/error feedback around the Orientation editor.
- Updated default display presets to the requested GE console convention:
  - Axial: Top A, Bottom P, Left L, Right R
  - Coronal: Top S, Bottom I, Left L, Right R
  - Sagittal: Top S, Bottom I, Left P, Right A
- Refreshes the image, labels, annotation, and button state immediately after Apply.
- Existing Original / FFT / Both rendering behavior is otherwise unchanged.


## Commit0060a Orientation / Navigation Hotfix

- Fixed the Orientation button runtime error caused by calling `_dicom_orientation_labels()` without a dataset argument.
- Removed the duplicate vertical label inversion so GE/JIS axial convention displays A at the top and P at the bottom.
- Previous and Next now navigate only within the currently displayed DICOM series.
- Slice position and navigation-button enabled state now use the current series count.
- Existing image loading, FFT, Original, Both, window/level, zoom and pan pipelines remain unchanged.

## Commit0060b Orientation Triple Check Hotfix

- Removed the obsolete duplicate `_dicom_orientation_labels` implementation.
- Locked normal display labels to the GE/JIS console convention by detected plane.
- Axial defaults: Top=A, Bottom=P, Left=L, Right=R.
- Added a no-image guard to the Orientation dialog.
- Hardened the fallback series identity used by Previous/Next navigation.
- Retained DICOM geometry output for orientation diagnostics.

## Commit0061 viewer interaction hotfix

- Previous/Next and mouse-wheel paging are locked to the current DICOM series.
- Series grouping uses UID plus visible series metadata to protect against malformed exports that reuse a UID.
- Slice changes preserve the selected Original / FFT / Both layout.
- Standard mouse controls: wheel pages images, left-drag pans, right-drag changes WL/WW, Ctrl+wheel zooms.
- Unverified mouse-mode selectors were removed from the right-click menu.
- The same calculated transform is applied to image pixels and orientation labels.


## Commit0062 — Image Component / Continuous Series Navigation

- Removed the visible Profile group from the right-side controls.
- Click `Magnitude` in each image title to choose Magnitude, Real, Imaginary, or Phase.
- Original Image and FFT keep independent component selections.
- After clicking an image, Up/Down updates slices immediately.
- At a series boundary, keyboard navigation continues into the adjacent series.
- The active series is expanded in Explorer and the previous series is collapsed.


## Commit0068 — Series / RAW Folder Boundary Navigation

- Navigation providers return an event-aware `NavigationResult`.
- Results can be unpacked as `(series_changed, current_item)`.
- DICOM Previous / Next crosses series boundaries across the full Study order.
- RAW Previous / Next crosses parent-folder boundaries in Explorer order.
- `TreeSyncEngine.change_series()` runs only when a series/folder boundary changes.
- Within the same series/folder, only the image selection is refreshed.


## Commit0068a - Tree series auto-sync fix

- Expands the destination DICOM series before loading the boundary image.
- Collapses every non-active series when a series boundary is crossed.
- Expands all destination ancestors, selects the target image, and scrolls it into view.
- Keeps same-series navigation lightweight without repeating tree expansion work.


## Commit0068b - FFT Compensation ROI target fix

- Select Compensation ROI now draws the ROI on the panel displaying FFT/raw k-space data.
- In Both mode, the ROI is attached to the right-side FFT panel.
- In FFT-only mode, the ROI is attached to the primary FFT panel.
- If invoked from Original-only mode, the display switches to Both before activating the ROI.
- The FFT panel becomes the active image panel while the ROI is edited.


## Commit0068c — Real Study Series Boundary Navigation Fix

- DICOM navigation now uses the same series boundary definition as the Explorer tree.
- Acquisition, echo, and temporal tags no longer split one displayed series during navigation.
- Previous/Next traverses all series in the current Study in Explorer order.
- Crossing a boundary clears a hiding Series filter, collapses the old series, expands the destination series, selects the destination image, and then loads it.


## Commit0068d - Tree-authoritative series navigation fix

- Previous/Next now derives Study and Series order from the visible Explorer tree.
- The current Exam node is treated as the Study boundary.
- The final image of one Series moves to the first image of the next Series.
- The first image of one Series moves to the final image of the previous Series.
- Destination Series is expanded and all other Series are collapsed before display.
- APP_VERSION updated so built EXEs can be identified as Commit0068d.


## Commit0068f - Source-type boundary navigation fix

- RAW Previous/Next now enumerates RAW leaves only; bitmap and tracker leaves are excluded.
- The currently displayed source path is used to recover the active tree leaf if focus moved away from it.
- Folder boundary transitions collapse the actual currently selected source folder, including the first transition after import.
- DICOM navigation remains isolated from RAW/bitmap/tracker navigation.
- Built EXE title identifies Commit0068f.


## Commit0068g - Reliable series expansion fix

- Destination tree items are resolved only after filters finish rebuilding the Explorer tree.
- Series expansion is applied before image load, immediately after image load, and once on the next Qt event-loop turn.
- The destination series and all ancestors stay expanded while sibling series in the same Exam are collapsed.
- DICOM tree selection now explicitly preserves the parent series expansion state.


## Commit0068h — Explorer keyboard navigation fix

Explorer Up/Down keys now call the same continuous navigation controller used by the Previous/Next buttons. Moving across a DICOM series boundary therefore expands the destination series, selects and displays the destination image, and collapses the previous series. Left/Right and modified selection keys retain standard tree behavior.


## Commit0068i — Explorer mouse-wheel continuous navigation

- Explorer wheel up routes to Previous Image.
- Explorer wheel down routes to Next Image.
- Wheel navigation uses the same NavigationController path as toolbar buttons and Up/Down keys.
- Crossing a DICOM series or RAW folder boundary therefore expands the destination, collapses the source, selects the destination image, and refreshes the display.
- High-resolution wheel/touchpad deltas are accumulated to one navigation step per 120 units.
- Modified wheel gestures retain the standard QTreeWidget behaviour.


## Commit0068j — Image wheel navigation and workspace curtains

- Original and FFT image-panel wheel paging now calls `change_slice_continuous()`.
- Wheel paging crosses DICOM series and RAW folder boundaries through the same navigation controller as Previous/Next.
- The complete right tool menu is wrapped in an expandable curtain and opens with the existing reference layout.
- The four lower crosshair profile charts are wrapped in an expandable curtain and open in the existing 2 x 2 arrangement.


## Commit0068k — Curtains initially closed

- Right Tool Menu curtain starts closed.
- Crosshair Profile Charts curtain starts closed.
- Opening either curtain restores the Commit0068j reference layout.


## Commit0068l — Vertical curtain and standard viewer context menu

- The collapsed Right Tool Menu is reduced to a 32 px vertical bar.
- Its title is rotated 90 degrees clockwise and returns to a horizontal header when opened.
- Original and FFT image panels now expose a standard viewer context menu with navigation, fit/actual-pixel/zoom, window-level presets, FFT processing, crosshair visibility, copy, save, DICOM Header, and Orientation commands.
- A stationary right click opens the menu; a right-button drag continues to adjust window level and width.


## Commit0068m — Persistent viewer layout state

- Crosshair Profile Charts open/closed state is preserved while changing images or series.
- Right Tool Menu open/closed state and expanded width are preserved during refreshes.
- Original/FFT splitter ratio is preserved while paging images in Both mode.
- Responsive layout no longer reopens a closed curtain or resizes it as if open.
- Display Reset reapplies the current curtain states instead of visually reopening them.


## Commit0068n
- Prevent transient programmatic splitter sizes from overwriting the saved Crosshair Profile Charts height.
- Enforce a valid expanded profile height after delayed responsive-layout passes.
- Preserve and restore the complete Original/FFT display state across FFT Current Image and Back from FFT.
- Keep Original and FFT Window/Level independent, including after returning to Original and selecting Both.
- Correct panel-role detection so level-wheel operations in Both mode affect the clicked panel only.

## Commit0068o

Modifier-free medical image viewer mouse controls:

- Mouse wheel: Previous / Next image with existing series-boundary navigation.
- Left drag: Pan the active Original or FFT view.
- Left double-click: Fit the active image to the view.
- Middle-button drag: Zoom the active view (up = zoom in, down = zoom out).
- Right drag: Window / Level adjustment for the active panel.
- Right click: Viewer context menu.
- Original and FFT panels keep independent view and Window / Level states.

## Commit0069 — Spike Diag automatic workflow

- Opening **Spike Diag** automatically resolves the DICOM image or Series selected in **Image Workspace**.
- Selecting a Series processes every image in that Series in Explorer order.
- All analyzed images are listed under **Processed Images**, including images classified as **No Spike**.
- For multiple images, the first/top image result is displayed initially.
- Selecting another item in **Processed Images** immediately updates all six diagnostic panels.


## Commit0070

- Calibrated Spike Diag with the supplied DICOMtest dataset.
- Added directional k-space line detection that retains evidence crossing the centre axes.
- Added full-line interpolation for periodic stripe-producing spike contamination.
- Image Workspace image selection now renders atomically to prevent the transient reset/flicker frame.
- Image Workspace selection and Display Reset use the same centered 50/50 Both layout and Fit path.

## Commit0071 — Fourier Physics Spike Validation

- Detects isolated point, row/column line, adjacent band, and oblique k-space candidates.
- Does not require row/column intersections for line or band candidates.
- Converts every candidate component with inverse FFT and evaluates its predicted spatial wave in the original image.
- Reports predicted wave direction, spatial period, image correlation, and integrated score.
- Displays accepted points as small circles and accepted lines/bands as line overlays; the normal DC cross is not marked as repeated point candidates.
- Uses a smaller corner-aligned paired-chevron frequency-direction marker.
- Removes the delayed second Fit operation that caused a one-frame left shift when selecting an image.


## Commit0074 — Step-by-Step Spike Review Mode

- Keeps the Commit0073 Image Workspace frame lock.
- Replaces the six-result Spike Diag screen with seven review steps: Input, FFT, Candidates, candidate-only IFFT, Correlation, Decision, and Compensation.
- Explicitly identifies DICOM pixel data as the FFT input and states that scanner acquisition RAW is unavailable when the source is DICOM.
- Lists every proposal, including rejected candidates, with type, robust Z, energy ratio, predicted angle/period, correlation, score, decision, and rejection reason.
- Selecting a candidate updates its mask, isolated k-space component, inverse FFT wave, image residual match, and final decision explanation.


## Commit0075
- DICOM-derived k-space is a supported primary workflow when native scanner RAW is unavailable.
- Localized high-energy cluster proposals are separated from full-span anatomical transform lines.
- Candidate decisions use candidate-only IFFT, image residual correlation, predicted direction/period, and compensation evidence.
- Compensation ROI now changes only robust local outliers, protects the DC cross, uses border interpolation with feathered blending, and maintains conjugate symmetry.


## Commit0076
- Removed full-row/full-column/oblique line proposals from Derived k-space detection.
- Added two-scale DoG-like compact blob detector with connected-component filtering.
- Preserved conjugate-pair evaluation and candidate-only IFFT validation.
- Compensation ROI now combines global robust magnitude and local residual confidence.
- Only high-confidence pixels are blended; DC cross and unaffected ROI pixels remain unchanged.

## Commit0077 — Unified Image Viewer Import and Build Validation

- Common image extension handling is now shared across the import worker, legacy import path, and processed-image loader.
- JPEG, PNG, BMP, TIFF, and TIF files follow the same display route everywhere.
- `version.json` now contains the metadata fields required by the reusable GitHub Actions workflow.
- Added `00_VALIDATE_SOURCE.bat` for Python compilation and focused regression tests before committing the SOURCE ZIP.
- Existing DICOM, ZIP, RAW, FFT, series navigation, and compensation behavior is retained.

### Recommended validation and build

```text
00_VALIDATE_SOURCE.bat
02_BUILD_EXE_NUITKA.bat
```

## Commit0077a startup fix

The Windows executable now starts through `launcher.py`. Import-time failures are written to
`%LOCALAPPDATA%\MR_Image_Explorer\startup_error.log` and are also displayed with a native
Windows error dialog. The Nuitka build explicitly packages the application module, default
JSON files, and the `database` directory.

Use `02_BUILD_EXE_NUITKA.bat` for the normal GUI build. If startup still fails, build with
`03_BUILD_EXE_DEBUG_CONSOLE.bat` or run `04_RUN_STARTUP_DIAGNOSTIC.bat` beside the packaged EXE.


## Commit0078 startup fix

Commit0078 removes any direct GDCM dependency from application startup. DICOM pixel
decoders are selected only when pixel data is opened. The Nuitka build explicitly
packages the complete pydicom and installed pylibjpeg decoder packages so the
`pydicom.pixels.decoders.gdcm` packaging error does not stop the EXE at launch.

Build the normal Windows package with `02_BUILD_EXE_NUITKA.bat`.

## Commit0079 — Nuitka pydicom decoder plugin packaging fix

pydicom 3 registers compressed-pixel decoder backends by module-name strings.
Nuitka cannot reliably discover these dynamic imports from `--include-package=pydicom`
alone. Commit0079 adds a static import anchor and explicitly packages the pydicom
GDCM, pylibjpeg, Pillow, pyjpegls and RLE plugin modules. The external `gdcm`
Python package remains optional; absence of GDCM no longer blocks application
startup. Both the local Nuitka BAT and the included GitHub Actions workflow use
the same decoder-module list.

## Commit0080 — Lazy DICOM decoder architecture

- Removed all decoder pre-imports from `launcher.py`.
- Removed the `pydicom_nuitka_plugins.py` runtime import anchor.
- Decoder selection now occurs only after a DICOM image is opened.
- Transfer Syntax UID determines the preferred decoder.
- GDCM is neither imported nor required.
- Nuitka packages pydicom and installed pylibjpeg codec packages at build time.
- Unsupported compressed images show a focused decoding error without terminating the viewer.


## Commit0081 — pydicom package-data startup fix

Commit0081 fixes the packaged EXE startup failure where pydicom could not find `data/urls.json`.
The Nuitka build now uses `--include-package-data=pydicom` in addition to code-package inclusion.
Both the local BAT and GitHub Actions stop the build if no `*urls.json` resource is found in the standalone output.
This is a build-resource correction; the Commit0080 lazy decoder design remains unchanged and no decoder is pre-imported at startup.

## Commit0082 — DICOM runtime stabilization

- Keeps optional pixel decoders lazy; no GDCM or codec pre-import occurs during startup.
- Adds `%LOCALAPPDATA%\\MR_Image_Explorer\\dicom_decoder.log` JSON-lines diagnostics for decode success/failure and available codecs.
- Keeps the decoded DICOM working set bounded. Set `MR_IMAGE_DICOM_CACHE` to 2–256 images when tuning memory use; default is 24.
- Preserves the same `(SeriesInstanceUID, position, instance, filename)` sort key before and after lazy pixel loading, preventing series order changes after an image is opened.
- Retains the Commit0081 pydicom package-data validation required for packaged startup.

## Commit0083 – Navigation and Lazy Cache Foundation

This revision preserves the confirmed-working Commit0082 decoder packaging while
introducing a reusable LRU cache policy for decoded DICOM pixels. DICOM headers
are still imported first and pixel data is decoded only when an image is shown.
The DICOM navigation provider now builds indexed lookup maps so series-boundary
movement does not repeatedly scan the complete Study order.

## Commit0087 Hybrid Compensation

- Adaptive-direction and frequency-aware Hybrid Compensation Engine
- Harmonic/Poisson multi-pass background reconstruction
- High and Extreme compensation profiles
- Auto/Line/Band/Block/Ring manual mask modes
- Automatic Spike/Line/Band/Block/Ring mask generation
- Difference FFT, Difference Phase, and Difference Image products
- Hermitian symmetry, ROI statistics, Artifact Reduction Score, and persistent History metadata


## Commit0089 Guided Poisson Solver

- Replaced the former harmonic-only approximation with a guided discrete Poisson solver.
- Keeps unmasked k-space fixed as Dirichlet boundary data.
- Uses the adaptive row/column Background Model as the Poisson guidance field.
- Uses boundary-safe Red-Black SOR for complex k-space.
- Records per-pass iterations, residuals and convergence in compensation metadata/history.
- Preserves Commit0088 synchronized Difference Viewer behavior.


## Commit0092

- Auto Detection v3 protects the central MRI k-space region from automatic selection.
- Auto-generated masks can be edited with Eraser or Remove Component.
- Manual Only mode uses the painted mask without running automatic detection.


## Commit0093

- Spike Detection v2 combines robust global excess, multi-scale local contrast, peak sharpness, isolation and compact component scoring.
- Block Detection v2 validates connected components by density, fill ratio, aspect ratio, surrounding halo contrast, edge contact and size.
- Auto Detection v4 reports per-candidate confidence and geometry diagnostics while preserving DC-centre protection.


## Commit0094
- Strengthened Block detection with multi-scale local response and geometry/halo scoring.
- Reduced vertical Line false positives using long-span and outer-k-space support requirements.
- Fixed reconstruction after adding or erasing mask pixels following `2. Use Painted Mask`.
- Preview now preserves the edited mask instead of regenerating and replacing it with Auto Detection.


## Commit0097
Auto Mask normal-signal preservation guard and collapsible Advanced Compensation Tuning controls.


## Commit0098 - Editable Advanced Compensation Tuning

Fixed the Commit0097 Qt group-box state that displayed the advanced controls while disabling their input. The controls are now always interactive. Presets populate tested values without locking the fields, manual edits switch the preset to Expert, and Preview applies all overrides to the current painted mask.


## Commit0101 - Auto Correct Engine v2
- Candidate-by-candidate virtual reconstruction and quality validation.
- Auto Correct, Quick Adjust, generated mask visibility, restore Auto result.
- Expert settings moved behind a dedicated toggle.


## Commit0102 - Compact Auto Correct UI
- Split ROI Raw Data Compensation into Auto, Paint, and Expert tabs.
- Made Auto Correct the primary default workflow.
- Collapsed Quick Adjust by default to reduce vertical scrolling.
- Added a dedicated wide Auto Correct progress dialog.
- Preserved Manual Paint, generated mask editing, history, and advanced tuning.


## Commit0104 — Auto Correct review workflow

After a reliable Auto Correct result, the application automatically opens **Review Reconstructed Image** and shows a **Next Step** panel in the Auto tab. Because this panel is part of the control area, it does not cover the generated mask image.

- **OK — Use This Result**: opens the reconstructed-image review and before/after comparison, then the result can be applied.
- **Quick Adjust**: fine-tunes Artifact Removal, Image Detail, and Protection. **Recalculate Once** performs exactly one calculation using the selected values; it does not run the six-trial Auto Retry sequence.
- **Paint**: directly adds, removes, or reshapes mask pixels using Brush, Line, Band, Block, Ring, Eraser, and Remove Component tools. It changes *where* compensation is applied.
- **Expert**: research and diagnostic controls that go beyond Paint. It can choose detection type and sensitivity, tune threshold, mask expansion, donor halo, pass count, strength, structure preservation, Hermitian symmetry, frequency-aware processing, Poisson reconstruction, and related compensation behavior. It changes *how candidates are detected and how reconstruction is calculated*.

The **Review Reconstructed Image** button is also available in Quick Adjust beside **Recalculate Once**. Button heights, padding, right-panel width, and the Quick Adjust button grid were updated to reduce clipped labels.


## Commit0105 — Auto Correct mask handoff

After Auto Correct, selecting **Paint** or **Expert** now enters the same RAW-mask editing state created by **Start Manual Paint on Raw Data**, without clearing the generated mask. The display returns to the original RAW/k-space data, the Auto Correct mask remains visible and editable, and the user can continue with **Use Painted Mask** or **Preview Reconstructed Image**.

- **Paint**: refine the retained Auto Correct mask with Brush, Line, Band, Block, Ring, Eraser, or Remove Component.
- **Expert**: refine the same retained mask and change advanced detection/reconstruction settings before previewing.
- Existing Auto Correct, Quick Adjust, review, comparison, apply, and history workflows are preserved.

## Commit0106 — Expert Direct Review

The Expert tab now includes **Review Reconstructed Image**. After editing the retained Auto Correct mask or changing Expert parameters, this button performs one reconstruction from the current mask and settings and opens the comparison review directly. Switching to the Paint tab is no longer required.


## Commit0107 — Quick Adjust Current Mask Recalculate

**Recalculate Once** now performs exactly one reconstruction using the currently visible/edited mask plus the current **Artifact Removal**, **Image Detail**, and **Protection** values. It does not run Candidate Detection, does not replace the current mask, and does not run the six-trial Auto Retry sequence. After successful calculation, **Review Reconstructed Image** opens automatically. An empty mask is reported clearly instead of displaying “Preview compensation first.”

## Commit0108 — Result Mode and Direct Review

After a successful Auto Correct result is installed, the primary **Auto Correct** button is hidden and the workflow changes to Result mode. The visible next actions are **OK — Use This Result**, **Quick Adjust**, **Paint**, and **Expert**. Re-running Auto Correct remains available only through **More... → Run Auto Correct Again**.

In Paint and Expert, **Review Reconstructed Image** now treats Preview as an output rather than a prerequisite. Clicking Review performs one reconstruction using the current editable mask and the current Expert settings, then immediately opens the before/after comparison. The user no longer has to switch to Paint or manually create a Preview first.


## Commit0109 — Quick Adjust and Mask Handoff

- Quick Adjust after Auto Correct now recalculates once from the untouched original RAW/k-space, the current mask, and the current slider values.
- Quick Adjust no longer replaces the stored Auto Correct restore result.
- Paint and Expert now enter the same manual-edit state as Start Manual Paint while retaining the generated Auto Correct mask.
- Moving between Paint and Expert keeps the current edited mask.

## Commit0110 — Detection and Session Stability

Auto Correct now includes conservative off-centre Blob detection in addition to Spike, Block, Diagonal, Line, Band, and Ring candidates. All candidates still pass through virtual compensation, validation, and quality ranking before acceptance.

The Auto Correct panel now shows the active compensation session: mask region count, mask pixel count, current Quick Adjust values, and whether the reconstructed preview is current. Auto Correct, Quick Adjust, Paint, Expert, and Review use the same authoritative current mask. Paint and Expert return to the original RAW editing view, equivalent to Start Manual Paint, while preserving the Auto Correct mask.

## Commit0111 — Quick Adjust single-trial detection

Quick Adjust now has two explicit paths:

- **Current mask exists:** `Apply Quick Adjust` reconstructs once from the current mask and current Artifact Removal, Image Detail, and Protection values.
- **Current mask is empty:** `Apply Quick Adjust` runs one candidate-detection, validation, compensation, and quality-evaluation trial using the current values. It does not run Auto Retry or compare six presets.

If the single trial does not find an acceptable candidate, no empty-mask dead end is shown. The controls remain available so the values can be changed and tried again, or the workflow can continue with Paint or Expert.


## RC1 Commit0112 — Expert Auto Mask and Auto Correct Reliability

- Expert Review now creates exactly one Difference / Before-After window. Existing review dialogs are closed and replaced safely.
- Expert numeric spin controls remain usable while Auto is selected. Clicking an arrow, using the keyboard, or entering a value switches only that parameter to manual mode and invalidates the prior preview.
- **Run Auto Mask Once** executes one detection pass with the visible Expert and Quick Adjust parameters. Existing masks can be replaced or merged.
- **Candidate Viewer** reports candidate type, acceptance, confidence, coverage, adaptive threshold, quality gain, score, and rejection reason.
- Auto Correct now adapts its threshold using a robust FFT noise-floor/tail estimate and ranks candidates using quality, confidence, shape and mask coverage.
- Paint tools add Undo/Redo, Hermitian symmetry paint, mask expand/shrink, fill-largest-region and delete-smallest-region operations.
- Quick Adjust remains single-trial: current mask reconstruction when a mask exists, one detection trial when it does not.

## RC1 Commit0113 — Candidate Viewer and Blob Detection

- Candidate Viewer is now an interactive dialog rather than a text message.
- Accepted and rejected candidates can be filtered, selected and inspected visually.
- FFT and candidate-mask previews are displayed with score details and explicit rejection reasons.
- Any usable candidate can be applied as the current mask or passed directly to Paint for editing.
- Mask Expansion, Donor Halo and Compensation Passes have explicit native arrow hit areas and support arrow keys/direct entry.
- Blob detection now combines robust global thresholds, local-contrast detection and conservative region growing to detect broader soft-edged off-centre blobs.


## Commit0114 — Edge Blob Detection Reliability

Auto Correct now detects broad, soft-edged FFT blobs that touch or are clipped by the image border, including the four left/right edge regions shown in the supplied reference image. The detector combines global robust thresholds, multi-scale local contrast, dedicated edge-band statistics, non-wrapping region growth, component shape checks, and Hermitian mirrored-pair support. DC-centre protection remains mandatory. Candidate Viewer continues to show and allow manual application of accepted or rejected candidates.


## Commit0115 — Blob Acceptance and Crosshair Safety

Reliable paired edge-Blob candidates may be auto-applied even when conservative global quality scoring previously rejected them. Acceptance remains bounded by image change, coverage, confidence, centre-axis occupancy and artifact reduction. High/Extreme compensation no longer aggressively expands edge masks into a centre line. Crosshairs are hidden by default in all image, review and diagnostic panels.


## Commit0116 — Detection Rollback and Crosshair Safety

The Auto Correct detection and candidate acceptance engine has been restored to the Commit0114 behavior because it performed better on the supplied real FFT data. Commit0115-specific Blob geometry acceptance overrides, paired-edge auto-accept rules, centre-axis occupancy weighting, and centre-axis mask removal are no longer used. Crosshair safety and the safer High / Extreme reconstruction presets remain in place. Candidate Viewer, Expert Auto Mask, Quick Adjust, Paint handoff, and direct Review workflows are unchanged.
## Commit0117 — Brush size controls and circular cursor

- Fixed Paint brush size controls that did not change when the arrow buttons were clicked.
- Added large dedicated ▼ / ▲ repeat buttons beside the size spin box.
- The native spin-box arrows, keyboard entry, and keyboard Up/Down remain supported.
- Brush and Eraser now display a circular image-space cursor whose diameter matches the selected brush size.
- The cursor scales correctly with image zoom and is hidden outside manual Brush/Eraser editing.
- Auto Correct detection behavior remains the Commit0116 rollback version.



## Commit0119 — Four-Phase Guide System

- Startup guidance now begins with the normal MR Image Explorer workflow.
- Raw Data Compensation is offered only after the normal guide and remains available from Help > Guide Library.
- Exit confirmation provides independent, default-OFF options for the next startup.
- Guide progress is saved separately for normal and advanced topics.


## Commit0120 — Diagnostic Engine and Tracker Drop Fix

- Spike Diag and Quick Spike Detect now combine their existing stripe/raw agreement logic with the Raw Data Compensation candidate detector.
- Artifact Diag includes a non-destructive Raw Data Compensation analysis summary for the current image.
- Tracker PFile and TrackerImg drops now load directly into Tracker Signal instead of redirecting to Image Workspace.
- The normal guide identifies Image Workspace as production-ready and labels all other analysis tabs as Work in Progress.

## RC1 Commit0122

- Quick Spike Detect now executes a real four-stage analysis for each selected image: image preparation, FFT generation, stripe evidence mapping, and robust k-space spike validation.
- The result reports completed image/stage counts and elapsed time, so a completed zero-candidate result is distinguishable from a skipped analysis.
- Clicking a collapsed Series in Explorer automatically expands it, selects its first image, scrolls it into view, and displays it.
