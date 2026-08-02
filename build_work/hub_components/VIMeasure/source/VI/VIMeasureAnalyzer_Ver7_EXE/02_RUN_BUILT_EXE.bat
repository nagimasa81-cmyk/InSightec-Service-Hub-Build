@echo off
setlocal
cd /d "%~dp0"
if exist "dist\VIMeasureAnalyzer.exe" (
  "dist\VIMeasureAnalyzer.exe"
) else (
  echo dist\VIMeasureAnalyzer.exe was not found. Run 01_BUILD_EXE_NUITKA.bat first.
  pause
)
