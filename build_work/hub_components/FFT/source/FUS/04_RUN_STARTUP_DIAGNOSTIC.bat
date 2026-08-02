@echo off
setlocal
cd /d "%~dp0"
set "LOG=%LOCALAPPDATA%\MR_Image_Explorer\startup_error.log"
echo Starting MR Image Explorer...
echo.
"%~dp0MRI_Raw_FFT_Explorer.exe"
set "RC=%ERRORLEVEL%"
echo.
echo Exit code: %RC%
if exist "%LOG%" (
  echo.
  echo Startup log: %LOG%
  echo ------------------------------------------------------------
  type "%LOG%"
  echo ------------------------------------------------------------
) else (
  echo No startup_error.log was created.
)
pause
exit /b %RC%
