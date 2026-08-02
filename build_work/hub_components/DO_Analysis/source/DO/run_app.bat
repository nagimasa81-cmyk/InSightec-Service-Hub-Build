@echo off
cd /d %~dp0
python -m pip install -r requirements.txt
python do_analysis_qt_app.py
pause
