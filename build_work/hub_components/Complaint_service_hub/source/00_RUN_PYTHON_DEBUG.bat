@echo off
setlocal
cd /d "%~dp0"
echo Python debug mode only. This is not the distribution launcher.
python -c "import PySide6" || (
  echo ERROR: PySide6 is not installed in this Python environment.
  echo Run: python -m pip install PySide6 comtypes
  pause
  exit /b 1
)
python hub_app.py
pause
