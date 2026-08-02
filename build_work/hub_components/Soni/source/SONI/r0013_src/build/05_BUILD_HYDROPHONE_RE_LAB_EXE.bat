@echo off
setlocal
cd /d "%~dp0\.."
if not exist ".venv\Scripts\python.exe" py -3.13 -m venv .venv
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt nuitka ordered-set zstandard
if exist dist\Hydrophone_RE_Lab.dist rmdir /s /q dist\Hydrophone_RE_Lab.dist
python -m nuitka --standalone --enable-plugin=pyside6 --include-package=pyqtgraph --windows-console-mode=disable --assume-yes-for-downloads --output-dir=dist --output-filename=Hydrophone_RE_Lab.exe hre_lab_main.py
if errorlevel 1 goto :error
echo Build completed: dist\hre_lab_main.dist\Hydrophone_RE_Lab.exe
pause
exit /b 0
:error
echo Build failed.
pause
exit /b 1
