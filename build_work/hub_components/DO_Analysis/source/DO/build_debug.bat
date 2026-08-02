@echo off
setlocal
cd /d %~dp0
title Build DO Analysis Qt DEBUG EXE - Nuitka
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m nuitka ^
 --standalone ^
 --onefile ^
 --enable-plugin=pyside6 ^
 --windows-console-mode=force ^
 --assume-yes-for-downloads ^
 --remove-output ^
 --noinclude-pytest-mode=nofollow ^
 --nofollow-import-to=pandas,matplotlib,numpy,scipy,pytest,unittest,doctest ^
 --output-dir=dist ^
 --output-filename="DO Analysis Qt Debug.exe" ^
 do_analysis_qt_app.py
pause
