@echo off
setlocal
cd /d "%~dp0"
set QT_QPA_PLATFORM=offscreen
where py >nul 2>nul
if %errorlevel%==0 (
  py -3.13 tools_test_guide_buttons.py
) else (
  python tools_test_guide_buttons.py
)
if errorlevel 1 (
  echo.
  echo Guide test could not run. Install the same dependencies used by run_from_python.bat first.
  pause
  exit /b 1
)
echo.
echo Guide button regression test passed.
pause
