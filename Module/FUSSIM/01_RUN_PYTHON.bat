@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt
python fus_treatment_replay.py
