@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "APP_NAME=LogMergeTool_RC1_Commit0072"
set "MAIN_PY=LogMergeTool_NoExcel_Main.py"
set "PYEXE=python"

%PYEXE% -m pip install --upgrade pip setuptools wheel
if errorlevel 1 exit /b 1
%PYEXE% -m pip install --upgrade nuitka PySide6 openpyxl ordered-set zstandard
if errorlevel 1 exit /b 1
%PYEXE% -m py_compile "%MAIN_PY%"
if errorlevel 1 exit /b 1

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

%PYEXE% -m nuitka ^
  --standalone ^
  --onefile ^
  --assume-yes-for-downloads ^
  --enable-plugin=pyside6 ^
  --windows-console-mode=disable ^
  --output-dir=dist ^
  --output-filename=%APP_NAME%.exe ^
  --company-name="InSightec" ^
  --product-name="Log Merge Tool - No Excel" ^
  --file-description="Log Merge Tool RC1 Commit0071" ^
  --file-version=2.0.0.69 ^
  --product-version=2.0.0.69 ^
  --include-data-file=csa_error_rules.json=csa_error_rules.json ^
  --include-data-file=site_serial_map.json=site_serial_map.json ^
  "%MAIN_PY%"
if errorlevel 1 exit /b 1
exit /b 0
