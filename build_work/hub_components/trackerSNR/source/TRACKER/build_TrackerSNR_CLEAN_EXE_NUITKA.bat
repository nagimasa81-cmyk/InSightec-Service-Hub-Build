@echo off
echo This Nuitka BAT is kept for compatibility, but Nuitka may fail with Scons on some PCs.
echo Recommended: run 00_BUILD_EXE_RECOMMENDED_PYINSTALLER.bat instead.
echo.
pause
call "%~dp099_BUILD_EXE_NUITKA_EXPERIMENTAL.bat"
