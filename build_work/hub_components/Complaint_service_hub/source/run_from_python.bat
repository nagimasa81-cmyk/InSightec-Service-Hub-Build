@echo off
cd /d "%~dp0"
py -m pip install PySide6 comtypes
py launcher.py
pause
