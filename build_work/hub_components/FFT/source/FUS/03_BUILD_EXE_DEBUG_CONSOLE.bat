@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "PYTHON_CMD=py -3.13"
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 set "PYTHON_CMD=python"
if not exist ".venv_nuitka\Scripts\python.exe" %PYTHON_CMD% -m venv .venv_nuitka
call ".venv_nuitka\Scripts\activate.bat"
python prepare_build_mode.py
if errorlevel 1 exit /b 1
python -m pip install --disable-pip-version-check -r requirements-build-nuitka.txt
if errorlevel 1 goto :error
if exist "dist_nuitka_debug" rmdir /s /q "dist_nuitka_debug"
python -m nuitka ^
  --mode=standalone ^
  --enable-plugin=pyside6 ^
  --windows-console-mode=force ^
  --assume-yes-for-downloads ^
  --jobs=4 ^
  --output-dir=dist_nuitka_debug ^
  --output-filename=MRI_Raw_FFT_Explorer_DEBUG.exe ^
  --include-module=app ^
  --include-module=vendor_adapters ^
  --include-data-files=vendor_sdk_config.json=vendor_sdk_config.json ^
  --include-data-files=tracker_position_defaults.json=tracker_position_defaults.json ^
  --include-data-files=artifact_learning_defaults.json=artifact_learning_defaults.json ^
  --include-data-files=release_mode.json=release_mode.json ^
  --include-data-files=version.json=version.json ^
  --include-data-dir=database=database ^
  launcher.py
if errorlevel 1 goto :error
echo.
echo Debug EXE created under dist_nuitka_debug\launcher.dist
pause
exit /b 0
:error
echo Build failed.
pause
exit /b 1
