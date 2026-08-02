@echo off
setlocal
py -3.13 -m pip install --upgrade pip
py -3.13 -m pip install --upgrade PySide6 Nuitka ordered-set zstandard
pause
