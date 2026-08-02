@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

REM ============================================================
REM Log Merge Tool - NO EXCEL / NO COM v9 Content Timestamp BuildFix
REM Target OS : Windows 11
REM Python    : 3.13
REM GUI       : PySide6 latest
REM Builder   : Nuitka latest
REM Output    : dist\LogMergeTool_NoExcel.exe
REM
REM BuildFix:
REM - Uses a clean local .venv_build so unrelated packages such as numpy
REM   installed in the global Python environment are not pulled into Nuitka.
REM - Adds --nofollow-import-to for heavy optional packages.
REM ============================================================

set APP_NAME=LogMergeTool_NoExcel
set MAIN_PY=LogMergeTool_NoExcel_Main.py
set PYLAUNCHER=py -3.13
set VENV_DIR=.venv_build
set PY=%CD%\%VENV_DIR%\Scripts\python.exe

echo ============================================================
echo  Log Merge Tool - v9 CONTENT TIMESTAMP BUILDFIX
echo ============================================================
echo.

%PYLAUNCHER% --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.13 was not found.
    echo Install Python 3.13 from python.org and enable the py launcher.
    pause
    exit /b 1
)

if not exist "%MAIN_PY%" (
    echo [ERROR] %MAIN_PY% was not found in this folder.
    pause
    exit /b 1
)

echo [1/6] Creating clean local build venv...
if not exist "%VENV_DIR%\Scripts\python.exe" (
    %PYLAUNCHER% -m venv "%VENV_DIR%"
    if errorlevel 1 goto :ERR_VENV
)

echo [2/6] Installing/upgrading required packages in clean venv...
"%PY%" -m pip install --upgrade pip setuptools wheel
"%PY%" -m pip install --upgrade nuitka PySide6 openpyxl ordered-set zstandard
if errorlevel 1 goto :ERR_PIP

echo [3/6] Verifying source compile...
"%PY%" -m py_compile "%MAIN_PY%"
if errorlevel 1 goto :ERR_COMPILE

echo [4/6] Cleaning old output...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist %APP_NAME%.build rmdir /s /q %APP_NAME%.build
if exist %APP_NAME%.dist rmdir /s /q %APP_NAME%.dist
if exist %APP_NAME%.onefile-build rmdir /s /q %APP_NAME%.onefile-build
if exist nuitka-crash-report.xml del /q nuitka-crash-report.xml

echo [5/6] Building ONEFILE EXE with Nuitka...
"%PY%" -m nuitka ^
  --standalone ^
  --onefile ^
  --assume-yes-for-downloads ^
  --enable-plugin=pyside6 ^
  --windows-console-mode=disable ^
  --nofollow-import-to=numpy ^
  --nofollow-import-to=pandas ^
  --nofollow-import-to=scipy ^
  --nofollow-import-to=matplotlib ^
  --nofollow-import-to=PIL ^
  --company-name="LogMerge" ^
  --product-name="Log Merge Tool No Excel" ^
  --file-description="Log Merge Tool No Excel" ^
  --file-version=2.3.0.0 ^
  --product-version=2.3.0.0 ^
  --output-filename=%APP_NAME%.exe ^
  --output-dir=dist ^
  --include-data-file=csa_error_rules.json=csa_error_rules.json ^
  --include-data-file=site_serial_map.json=site_serial_map.json ^
  "%MAIN_PY%"
if errorlevel 1 goto :ERR_NUITKA

echo [6/6] Build completed.
echo.
echo Main EXE:
echo   %CD%\dist\%APP_NAME%.exe
echo.
pause
exit /b 0

:ERR_VENV
echo [ERROR] Could not create local build venv.
pause
exit /b 1

:ERR_PIP
echo [ERROR] Package installation failed.
pause
exit /b 1

:ERR_COMPILE
echo [ERROR] Python source compile check failed.
pause
exit /b 1

:ERR_NUITKA
echo [ERROR] Nuitka build failed.
echo.
echo If the error mentions module.numpy or Scons, delete .venv_build and run this BAT again.
echo If it still fails, run Build_DEBUG_Console_EXE.bat and send the console text.
pause
exit /b 1
