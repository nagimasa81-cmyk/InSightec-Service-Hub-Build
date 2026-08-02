@echo off
setlocal
cd /d "%~dp0"
title Build DO Analysis Qt EXE - Nuitka Fixed

echo [1/6] Installing required packages...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 goto ERROR

echo.
echo [2/6] Cleaning old build files...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist do_analysis_qt_app.build rmdir /s /q do_analysis_qt_app.build
if exist do_analysis_qt_app.dist rmdir /s /q do_analysis_qt_app.dist
if exist do_analysis_qt_app.onefile-build rmdir /s /q do_analysis_qt_app.onefile-build
if exist "DO Analysis Qt.exe" del /q "DO Analysis Qt.exe"

echo.
echo [3/6] Building with Nuitka...
echo This version intentionally uses NO pandas, NO matplotlib, and NO QtCharts.
echo It avoids the pandas.tests / Scons compile error seen on Python 3.13.

python -m nuitka ^
 --standalone ^
 --onefile ^
 --enable-plugin=pyside6 ^
 --windows-console-mode=disable ^
 --assume-yes-for-downloads ^
 --remove-output ^
 --noinclude-pytest-mode=nofollow ^
 --nofollow-import-to=pandas,matplotlib,numpy,scipy,pytest,unittest,doctest ^
 --output-dir=dist ^
 --output-filename="DO Analysis Qt.exe" ^
 do_analysis_qt_app.py

if errorlevel 1 goto ERROR

echo.
echo [4/6] Build complete.
echo EXE location:
echo %CD%\dist\DO Analysis Qt.exe
echo.
if not defined CI pause
exit /b 0

:ERROR
echo.
echo EXE build failed.
echo Try build_debug.bat to see console errors, or use Python 3.12 if your Nuitka/Python 3.13 environment is unstable.
if not defined CI pause
exit /b 1
