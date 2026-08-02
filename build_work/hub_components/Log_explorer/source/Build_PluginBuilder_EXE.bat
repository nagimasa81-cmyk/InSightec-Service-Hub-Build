@echo off
setlocal
cd /d "%~dp0"
if not exist .venv_build (
  py -3.13 -m venv .venv_build
)
call .venv_build\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt nuitka ordered-set zstandard
python -m nuitka --standalone --onefile --enable-plugin=pyside6 --windows-console-mode=disable --output-filename=PluginBuilder.exe PluginBuilder.py
pause
