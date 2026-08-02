TrackerSNR FUS Comparison v2.9.2

Tracker SNR Analyzer - Single / Comparison Mode Source

Display mode behavior
- When only one valid Tracker SNR file is found, the application automatically opens the traditional Single File view.
- Single File view keeps File selection, P/N navigation, Block selection, Tracker curves, SNR Matrix, and File Index.
- When two or more valid files are found, the application opens Comparison view by default.
- With multiple files loaded, Display Mode can be switched freely between Single File and Comparison.
- In Single File mode with multiple inputs, the selected file is shown using the traditional display and controls.
- In Comparison mode, Tracker 0 through 3 are displayed as four separate time-series charts; each chart contains Scan 0 through 3 curves.

Input behavior
- Drag and drop: individual file, multiple files, folder, or ZIP.
- Supported direct targets: .log and .txt.
- ZIP archives: extracts target .log/.txt members only.
- Folder discovery: selected folder plus five levels below it.
- Nested ZIP archives are not expanded in this release.
- Invalid files without Tracker SNR rows are reported as skipped.

Other retained functions
- SNR / Signal / Noise selection.
- Excel export and project save/open.
- FUS-style dark-blue and blue-gray UI.
- Time ordering by YYYY_Mmm_DD_HH_MM_SS filename timestamp, with modified time fallback.

Build
1. Extract this source ZIP in the GitHub module folder.
2. Run 00_BUILD_EXE_RECOMMENDED_PYINSTALLER.bat.
3. EXE output: dist\TrackerSNR_CLEAN_EXE.exe
4. Distribution ZIP: dist\TrackerSNR_CLEAN_EXE_DISTRIBUTION.zip

Validation
- Python syntax compilation passed.
- Existing parser/export/project self-test passed: 2 valid files, 192 rows, 1 skipped file.
- GUI could not be instantiated in the packaging environment because PySide6 is not installed there; the GitHub BAT installs requirements before building.

Future Treatment Export integration
The input pipeline remains separated through collect_inputs(). A future Treatment Export adapter can locate Tracker logs and pass them into parse_files(), then expose this analysis as one output of the treatment replay/export workflow.

Version 2.9.3 comparison behavior
---------------------------------
Comparison mode expands every valid file into all of its Blocks.
Blocks are displayed in chronological order and kept together by calendar date.
The first Block of each date shows MM/DD; following Blocks in the same date group show B2, B3, etc.
Each Tracker 0-3 chart still contains the Scan 0-3 curves.

Version 2.9.4 comparison updates
- Block Display: All Blocks / File Block Median
- Comparison mode hides the lower-left SNR matrix
- Hover a chart point to show current metric, SNR, Signal and Noise when available
- Hover details work in SNR, Signal and Noise metric modes


Guide and exit behavior (v2.9.5)
--------------------------------
- At startup, the application asks whether to show the Quick Guide and Guided Tour.
- Yes — Show Guide opens the five-page guide.
- No — Do Not Ask Again skips the guide and disables future startup prompts.
- At exit, a confirmation dialog is shown.
- Select "Show the guide and guided tour at the next startup" to show the guide once at the next launch.
- The exit checkbox is OFF by default.
- Cancel keeps the application open.
- Per-user settings are stored under %%APPDATA%%\InSightec\TrackerSNRAnalyzer\settings.json.


Concrete Guide and Guided Tour (v3.0.0)
----------------------------------------
- Eight-page Quick Guide covering import, Single File, Comparison, chart hover, blocks/dates, export, and project restore.
- Start Guided Tour from the final guide page.
- The Guided Tour darkens the application and spotlights the actual Import, Mode, Metric, Block Display, Chart, Export, and Guide controls.
- Guided Tour controls: Back, Next, Skip Tour, Finish, and Esc.
- Use Guide / Tour on the main screen to reopen the guide at any time.
- Startup and exit guide settings remain stored in the per-user settings file under AppData.
