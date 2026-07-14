@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt nuitka ordered-set zstandard
python -m nuitka --standalone --onefile --enable-plugin=pyside6 --include-package=matplotlib --windows-console-mode=disable --output-filename=FUS_Treatment_Replay.exe fus_treatment_replay.py
pause
