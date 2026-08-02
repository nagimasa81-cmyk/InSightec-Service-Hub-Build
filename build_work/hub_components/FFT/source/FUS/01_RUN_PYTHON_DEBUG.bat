@echo off
setlocal
cd /d "%~dp0"
python app.py
if errorlevel 1 (
  echo.
  echo MR Image Explorer exited with an error.
  echo Check:
  echo %%LOCALAPPDATA%%\MR_Image_Explorer\startup_error.log
  pause
)
