@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
set APP=VIMeasureAnalyzer

echo ============================================================
echo Building %APP%.exe with DEBUG CONSOLE - Ver6
echo ============================================================
echo.

taskkill /F /IM %APP%.exe >nul 2>nul
ping 127.0.0.1 -n 2 >nul
if exist "%APP%.build" rmdir /S /Q "%APP%.build" 2>nul
if exist "%APP%.dist" rmdir /S /Q "%APP%.dist" 2>nul
if exist "%APP%.onefile-build" rmdir /S /Q "%APP%.onefile-build" 2>nul
if exist "build" rmdir /S /Q "build" 2>nul
if exist "dist" rmdir /S /Q "dist" 2>nul
if exist "VIMeasureAnalyzer_error.log" del /Q "VIMeasureAnalyzer_error.log" 2>nul

py -3.13 -m nuitka ^
  --standalone ^
  --onefile ^
  --enable-plugin=pyside6 ^
  --include-module=PySide6.QtCharts ^
  --include-module=PySide6.QtWidgets ^
  --include-module=PySide6.QtGui ^
  --include-module=PySide6.QtCore ^
  --windows-console-mode=force ^
  --assume-yes-for-downloads ^
  --remove-output ^
  --output-dir=dist ^
  --output-filename=%APP%.exe ^
  %APP%.py

if errorlevel 1 (
  echo Build failed.
  pause
  exit /b 1
)

echo.
echo Build complete. Starting debug EXE now...
echo.
"dist\%APP%.exe"
echo.
echo EXE finished or closed. If it failed, check VIMeasureAnalyzer_error.log.
pause
