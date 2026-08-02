@echo off
setlocal
cd /d "%~dp0\.."
if not exist ".venv\Scripts\python.exe" py -3.13 -m venv .venv
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m compileall -q .
if errorlevel 1 goto :error
python verify_source.py
if errorlevel 1 goto :error
echo.
echo Verification completed successfully.
pause
exit /b 0
:error
echo Verification failed.
pause
exit /b 1
