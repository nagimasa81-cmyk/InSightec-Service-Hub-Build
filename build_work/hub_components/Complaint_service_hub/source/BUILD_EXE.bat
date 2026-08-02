@echo off
setlocal
cd /d "%~dp0"
call 01_BUILD_EXE_NUITKA.bat
exit /b %errorlevel%
