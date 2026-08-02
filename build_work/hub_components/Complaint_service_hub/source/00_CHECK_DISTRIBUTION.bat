@echo off
setlocal
cd /d "%~dp0"
set ERR=0
for %%F in (Complaint_Service_Hub_Launcher.exe Complaint_Service_Hub.exe Complaint_Service_Hub_Updater.exe app_version.json manifest.json) do (
  if not exist "%%F" (
    echo MISSING: %%F
    set ERR=1
  ) else (
    echo OK: %%F
  )
)
if "%ERR%"=="1" (
  echo.
  echo Distribution is incomplete. Extract or copy the whole artifact folder.
) else (
  echo.
  echo Distribution structure is OK.
)
pause
exit /b %ERR%
