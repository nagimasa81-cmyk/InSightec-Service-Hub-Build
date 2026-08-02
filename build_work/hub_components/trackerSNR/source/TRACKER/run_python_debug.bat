@echo off
setlocal
cd /d "%~dp0"
echo Running TrackerSNR Python debug mode...
echo.
py -3.13 -m pip install -r requirements.txt
if errorlevel 1 goto ERR
py -3.13 TrackerSNR_CLEAN_EXE.py
if errorlevel 1 goto ERR
goto END
:ERR
echo.
echo FAILED. Check TrackerSNR_runtime.log in this folder.
pause
:END
endlocal
