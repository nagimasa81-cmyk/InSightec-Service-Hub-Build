@echo off
setlocal
cd /d "%~dp0"
echo Installing build requirements...
py -3.13 -m pip install -U pip
py -3.13 -m pip install -r requirements.txt
if errorlevel 1 goto ERR

echo Cleaning old build folders...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul

echo Building EXE with PyInstaller fallback...
py -3.13 -m PyInstaller --noconfirm --clean --onedir --console --name TrackerSNR_CLEAN_EXE TrackerSNR_CLEAN_EXE.py
if errorlevel 1 goto ERR

echo.
echo Build complete.
echo Use this folder as a set:
echo dist\TrackerSNR_CLEAN_EXE\TrackerSNR_CLEAN_EXE.exe
pause
goto END
:ERR
echo.
echo BUILD FAILED.
pause
:END
endlocal
