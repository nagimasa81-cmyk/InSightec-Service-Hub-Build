@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo TrackerSNR CLEAN EXE build - ONEDIR FALLBACK
echo Use this if one-file build has problems.
echo ============================================
py -3.13 -m pip install -U pip
py -3.13 -m pip install -r requirements.txt
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
py -3.13 -m PyInstaller --noconfirm --clean --onedir --console --name TrackerSNR_CLEAN_EXE --collect-all PySide6 --collect-all openpyxl TrackerSNR_CLEAN_EXE.py
if errorlevel 1 goto ERR
echo Build complete. Use the whole folder: dist\TrackerSNR_CLEAN_EXE\
pause
goto END
:ERR
echo BUILD FAILED.
pause
:END
endlocal
