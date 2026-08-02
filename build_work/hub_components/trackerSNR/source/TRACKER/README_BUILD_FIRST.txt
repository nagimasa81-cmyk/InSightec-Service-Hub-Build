TrackerSNR CLEAN BUILD - build instructions

Recommended build:
  1. run_self_test.bat
  2. run_python_debug.bat
  3. 00_BUILD_EXE_RECOMMENDED_PYINSTALLER.bat
  4. 01_RUN_BUILT_EXE.bat

Important:
- The previous Nuitka build can fail with:
    FATAL: Failed unexpectedly in Scons backend compilation
    nuitka-crash-report.xml
  This is a Nuitka/Scons/compiler build issue.
- The recommended BAT uses PyInstaller one-folder mode instead.
- Keep the whole dist\\TrackerSNR_CLEAN_EXE folder together when using the EXE.

Nuitka:
- 99_BUILD_EXE_NUITKA_EXPERIMENTAL.bat is left only for testing.
- If Nuitka fails, use the PyInstaller build.
