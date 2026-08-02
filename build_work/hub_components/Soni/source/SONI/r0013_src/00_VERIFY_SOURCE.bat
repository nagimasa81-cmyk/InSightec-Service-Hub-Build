@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" py -3.13 -m venv .venv
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python verify_source.py
if errorlevel 1 exit /b 1
python -m compileall -q main.py src tools tests
if errorlevel 1 exit /b 1
python -m pytest -q
exit /b %errorlevel%
