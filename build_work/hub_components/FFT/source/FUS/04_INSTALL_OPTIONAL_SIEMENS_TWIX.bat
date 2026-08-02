@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" py -3.13 -m venv .venv
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install twixtools
if errorlevel 1 (
  echo Failed to install twixtools.
  pause
  exit /b 1
)
echo Optional Siemens TWIX fallback installed.
pause
