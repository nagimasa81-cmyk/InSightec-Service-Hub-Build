@echo off
cd /d %~dp0
title Build DO Analysis Qt EXE - PyInstaller Fallback
python -m pip install --upgrade pip
python -m pip install PyInstaller PySide6
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
python -m PyInstaller ^
 --noconfirm ^
 --clean ^
 --onefile ^
 --windowed ^
 --name "DO Analysis Qt" ^
 do_analysis_qt_app.py
pause
