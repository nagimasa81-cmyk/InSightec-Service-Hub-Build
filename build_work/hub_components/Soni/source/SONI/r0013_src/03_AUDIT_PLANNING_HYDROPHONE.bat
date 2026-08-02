@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo Drag a treatment ZIP or folder onto this BAT.
  pause
  exit /b 1
)
py -3 tools\audit_planning_hydrophone.py "%~1" "%~dp0planning_hydrophone_audit.json"
if errorlevel 1 pause
endlocal
