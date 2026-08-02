DO Analysis Qt - GitHub Build Source
Version: 2026.07.28.2

Main features
- Drag and drop WaterSystem files, folders, or ZIP archives.
- ZIP contents are searched recursively and only matching WaterSystem files are loaded.
- Import / Settings can be folded to maximize the chart area.
- Change the displayed file from the Chart tab with the combo box or previous/next buttons.

Build
1. Extract this source ZIP in the GitHub module folder.
2. Run build_exe.bat locally, or let the GitHub workflow detect do_analysis_qt_app.py/version.json.
3. Output: dist/DO Analysis Qt.exe

Fallback
- build_pyinstaller_fallback.bat
- build_debug.bat
