@echo off
setlocal
cd /d "%~dp0"
python tests\test_csa_cga_structured_parser.py
if errorlevel 1 pause
