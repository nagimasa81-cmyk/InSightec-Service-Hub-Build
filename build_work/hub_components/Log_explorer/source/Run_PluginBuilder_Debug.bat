@echo off
cd /d "%~dp0"
python PluginBuilder.py
if errorlevel 1 pause
