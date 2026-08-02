@echo off
cd /d "%~dp0"
py -3.13 -m pip install --upgrade PySide6 openpyxl
py -3.13 LogMergeTool_NoExcel_Main.py
if errorlevel 1 (
  echo.
  echo Application ended with error. Check:
  echo %%LOCALAPPDATA%%\LogMergeTool_NoExcel\startup_error.log
  pause
)
