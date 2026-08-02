VIMeasureAnalyzer Ver7

Recommended order:
1. 00_INSTALL_REQUIREMENTS.bat
2. run_python_debug.bat
3. 01_BUILD_EXE_NUITKA.bat
4. 02_RUN_BUILT_EXE.bat

Important Ver7 change:
The standard Nuitka build now uses console mode ON because the previous no-console EXE could fail silently on the target PC, while the console/debug EXE was confirmed to work.

Included BAT files:
- 01_BUILD_EXE_NUITKA.bat: recommended stable build, console enabled
- 01_BUILD_EXE_NUITKA_DEBUG_CONSOLE.bat: same idea, also starts EXE after build
- 01_BUILD_EXE_NUITKA_GUI_EXPERIMENTAL.bat: no-console experimental build only

Main features:
- Import File / Import Folder
- Prev / Next navigation
- V and I automatic axis split
- V-only or I-only display uses left axis only
- Data All / V All / I All controls at bottom
- Three-state group checks
- Drag rectangle zoom, Zoom Out, Reset Zoom
- Mouse-position data tooltip
- CSV export

Ver7: Fixed false Startup failed message shown when closing the EXE. Normal app close is no longer handled as an error.
