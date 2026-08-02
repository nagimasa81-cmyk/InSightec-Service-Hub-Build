@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "APP_NAME=LogMergeTool_RC1_Commit0069"
set "MAIN_PY=LogMergeTool_NoExcel_Main.py"
set "BUILD_DIR=build_commit0069"

where py >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python launcher "py" was not found.
  exit /b 1
)

py -3.13 -c "import sys" >nul 2>nul
if not errorlevel 1 (
  set "PY=py -3.13"
) else (
  py -3.14 -c "import sys" >nul 2>nul
  if not errorlevel 1 (
    set "PY=py -3.14"
  ) else (
    set "PY=py -3"
  )
)

%PY% -m pip install --upgrade pip setuptools wheel
if errorlevel 1 exit /b 1
%PY% -m pip install --upgrade PySide6 openpyxl nuitka ordered-set zstandard
if errorlevel 1 exit /b 1

%PY% -m py_compile "%MAIN_PY%"
if errorlevel 1 exit /b 1
%PY% tests\test_commit0067_version_consistency.py
if errorlevel 1 exit /b 1

if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
if not exist dist mkdir dist

%PY% -m nuitka ^
  --standalone ^
  --onefile ^
  --enable-plugin=pyside6 ^
  --windows-console-mode=disable ^
  --assume-yes-for-downloads ^
  --output-dir="%BUILD_DIR%" ^
  --output-filename="%APP_NAME%.exe" ^
  --company-name="InSightec" ^
  --product-name="Log Merge Tool - No Excel" ^
  --file-description="Log Merge Tool RC1 Commit0069" ^
  --file-version=2.0.0.69 ^
  --product-version=2.0.0.69 ^
  --include-data-file=csa_error_rules.json=csa_error_rules.json ^
  --include-data-file=site_serial_map.json=site_serial_map.json ^
  "%MAIN_PY%"
if errorlevel 1 exit /b 1

copy /y "%BUILD_DIR%\%APP_NAME%.exe" "dist\%APP_NAME%.exe" >nul
if errorlevel 1 exit /b 1

echo [OK] dist\%APP_NAME%.exe
endlocal
