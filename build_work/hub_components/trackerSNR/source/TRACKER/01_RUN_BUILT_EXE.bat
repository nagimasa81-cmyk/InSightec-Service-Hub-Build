@echo off
setlocal
cd /d "%~dp0"
set EXE=dist\TrackerSNR_CLEAN_EXE.exe
if not exist "%EXE%" goto NOEXE
"%EXE%"
goto END
:NOEXE
echo Built EXE was not found.
echo Please run 00_BUILD_EXE_RECOMMENDED_PYINSTALLER.bat first.
pause
:END
endlocal
