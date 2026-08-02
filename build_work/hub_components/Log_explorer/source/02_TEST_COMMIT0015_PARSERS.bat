@echo off
cd /d "%~dp0"
python tests\test_commit0015_parsers.py
if errorlevel 1 pause
