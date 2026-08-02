@echo off
setlocal
cd /d "%~dp0\.."
if not exist ".venv\Scripts\python.exe" py -3.13 -m venv .venv
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt nuitka ordered-set zstandard
if exist dist_debug rmdir /s /q dist_debug
python -m nuitka --standalone --enable-plugin=pyside6 --windows-console-mode=force --assume-yes-for-downloads --output-dir=dist_debug --output-filename=Sonication_Replay_Engine_DEBUG.exe main.py
pause
