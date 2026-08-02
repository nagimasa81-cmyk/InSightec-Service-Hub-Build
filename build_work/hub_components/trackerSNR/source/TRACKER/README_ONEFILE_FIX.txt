TrackerSNR CLEAN REBUILD - ONEFILE PATH FIX

Recommended:
1. run_self_test.bat
2. run_python_debug.bat
3. 00_BUILD_EXE_RECOMMENDED_PYINSTALLER.bat
4. 01_RUN_BUILT_EXE.bat

This version builds a single EXE:
  dist\TrackerSNR_CLEAN_EXE.exe

You can copy this EXE alone to another folder.

Fixes:
- Supports standalone single EXE operation.
- Normalizes selected file/folder paths before checking existence.
- Logs missing selected paths to TrackerSNR_runtime.log.
- Runtime log is written next to EXE, or TEMP if the EXE folder is not writable.

If the single EXE still has issues, use:
  00_BUILD_EXE_ONEDIR_FALLBACK.bat
and keep the entire dist\TrackerSNR_CLEAN_EXE folder together.
