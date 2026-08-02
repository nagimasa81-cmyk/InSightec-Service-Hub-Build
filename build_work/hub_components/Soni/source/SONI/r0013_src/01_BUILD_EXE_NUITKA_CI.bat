@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "PYTHON_EXE=python"
%PYTHON_EXE% -c "import sys; assert sys.version_info[:2] == (3,13)" || exit /b 1
%PYTHON_EXE% -m pip install --upgrade pip setuptools wheel || exit /b 1
%PYTHON_EXE% -m pip install -r requirements.txt nuitka ordered-set zstandard || exit /b 1
%PYTHON_EXE% verify_source.py || exit /b 1
%PYTHON_EXE% -m compileall -q main.py src tools || exit /b 1
if exist dist rmdir /s /q dist
%PYTHON_EXE% -m nuitka --standalone --onefile --enable-plugin=pyside6 --windows-console-mode=disable --assume-yes-for-downloads --output-dir=dist --output-filename=Sonication_Replay_Engine.exe main.py
if errorlevel 1 exit /b 1
if not exist "dist\Sonication_Replay_Engine.exe" exit /b 1
exit /b 0
