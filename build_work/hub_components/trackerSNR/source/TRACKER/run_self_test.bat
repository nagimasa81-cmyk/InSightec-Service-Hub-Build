@echo off
setlocal
cd /d "%~dp0"
echo Running self test...
echo.
py -3.13 -m pip install -r requirements.txt
if errorlevel 1 goto ERR
py -3.13 TrackerSNR_CLEAN_EXE.py --self-test
if errorlevel 1 goto ERR
echo.
echo Self test completed successfully.
pause
goto END
:ERR
echo.
echo SELF TEST FAILED. Check TrackerSNR_runtime.log in this folder.
pause
:END
endlocal
