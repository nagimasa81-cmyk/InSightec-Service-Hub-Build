@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
set APP=VIMeasureAnalyzer

echo ============================================================
echo Building %APP%.exe with Nuitka - Ver6 stable console onefile
echo ============================================================
echo.

echo [1/4] Closing running %APP%.exe if it exists...
taskkill /F /IM %APP%.exe >nul 2>nul
ping 127.0.0.1 -n 2 >nul

echo [2/4] Removing old build/dist folders...
if exist "%APP%.build" rmdir /S /Q "%APP%.build" 2>nul
if exist "%APP%.dist" rmdir /S /Q "%APP%.dist" 2>nul
if exist "%APP%.onefile-build" rmdir /S /Q "%APP%.onefile-build" 2>nul
if exist "build" rmdir /S /Q "build" 2>nul
if exist "dist" rmdir /S /Q "dist" 2>nul
if exist "VIMeasureAnalyzer_error.log" del /Q "VIMeasureAnalyzer_error.log" 2>nul

if exist "dist\%APP%.exe" (
  echo Could not remove old dist\%APP%.exe.
  echo Please close the EXE and Explorer preview panes, then retry.
if not defined CI pause
  exit /b 1
)

echo [3/4] Running Nuitka...
py -3.13 -c "from PySide6.QtCore import QTimer; print('QTimer import OK')" || exit /b 1

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
  echo.
  echo Build failed.
if not defined CI pause
  exit /b 1
)

echo.
echo [4/4] Build complete: dist\%APP%.exe
echo This Ver6 standard build keeps the console enabled because the console build is confirmed to start correctly on the target PC.
if not defined CI pause