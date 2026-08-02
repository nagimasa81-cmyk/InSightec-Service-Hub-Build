@echo off
setlocal
cd /d "%~dp0\.."
if not exist ".venv\Scripts\python.exe" py -3.13 -m venv .venv
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt nuitka ordered-set zstandard
if exist dist rmdir /s /q dist
python -m nuitka --standalone --enable-plugin=pyside6 --windows-console-mode=disable --assume-yes-for-downloads --output-dir=dist --output-filename=Sonication_Replay_Engine.exe main.py
if errorlevel 1 goto :error
echo Build completed.
pause
exit /b 0
:error
echo Build failed.
pause
exit /b 1
