@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "PY=python"
%PY% -c "import sys; assert sys.version_info[:2] == (3,13)" >nul 2>&1 || goto NOPY

echo [1/5] Installing build requirements...
%PY% -m pip install -U pip
if errorlevel 1 goto ERR
%PY% -m pip install -r requirements.txt
if errorlevel 1 goto ERR

echo [2/5] Running source self-test...
%PY% TrackerSNR_CLEAN_EXE.py --self-test
if errorlevel 1 goto ERR

echo [3/5] Cleaning previous outputs...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
rmdir /s /q release 2>nul
del /q TrackerSNR_CLEAN_EXE.spec 2>nul

echo [4/5] Building one-file EXE...
%PY% -m PyInstaller --noconfirm --clean --onefile --windowed --name TrackerSNR_CLEAN_EXE --collect-all PySide6 --collect-all openpyxl TrackerSNR_CLEAN_EXE.py
if errorlevel 1 goto ERR

echo [5/5] Creating GitHub artifact package...
mkdir release
copy /y dist\TrackerSNR_CLEAN_EXE.exe release\ >nul
copy /y README.txt release\ >nul
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path 'release\*' -DestinationPath 'dist\TrackerSNR_CLEAN_EXE_DISTRIBUTION.zip' -Force"
if errorlevel 1 goto ERR

echo.
echo BUILD COMPLETE
echo EXE: dist\TrackerSNR_CLEAN_EXE.exe
echo Artifact: dist\TrackerSNR_CLEAN_EXE_DISTRIBUTION.zip
exit /b 0
:NOPY
echo Python 3.13 was not found or the active Python is not 3.13.
exit /b 2
:ERR
echo BUILD FAILED. Review the console and TrackerSNR_runtime.log.
exit /b 1
