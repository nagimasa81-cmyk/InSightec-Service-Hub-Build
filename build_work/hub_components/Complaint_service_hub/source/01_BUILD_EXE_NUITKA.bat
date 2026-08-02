@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo ============================================================
echo InSightec Complaint Service Hub - Stable Nuitka Build
echo Launcher + Hub + Updater separated / No Tkinter
echo Build 0003u39c: Salesforce complaint workflow and registration reply
echo ============================================================

REM Use a project-local writable temp/cache area. This avoids WinError 5
REM when Nuitka helper executables are blocked in the runner account TEMP.
set "CI_TEMP=%CD%\.build_temp"
set "TEMP=%CI_TEMP%"
set "TMP=%CI_TEMP%"
set "NUITKA_CACHE_DIR=%CD%\.nuitka_cache"
if exist "%CI_TEMP%" rmdir /s /q "%CI_TEMP%" 2>nul
if exist "%NUITKA_CACHE_DIR%" rmdir /s /q "%NUITKA_CACHE_DIR%" 2>nul
mkdir "%CI_TEMP%" || exit /b 1
mkdir "%NUITKA_CACHE_DIR%" || exit /b 1
icacls "%CI_TEMP%" /grant "%USERNAME%:(OI)(CI)F" /T /C >nul 2>&1
icacls "%NUITKA_CACHE_DIR%" /grant "%USERNAME%:(OI)(CI)F" /T /C >nul 2>&1

echo TEMP=%TEMP%
echo NUITKA_CACHE_DIR=%NUITKA_CACHE_DIR%

python --version
python -c "import sys; major, minor = sys.version_info[:2]; print(f'Python {major}.{minor} detected.'); sys.exit(0 if (major, minor) in [(3,13),(3,14)] else 1)"
if errorlevel 1 (
    echo ERROR: Please use Python 3.13 or 3.14.
    exit /b 1
)
for /f "delims=" %%V in ('python -c "import platform; print(platform.python_version())"') do set PYTHON_VERSION=%%V
echo Python version accepted: %PYTHON_VERSION%

echo.
echo Updating version metadata...
python tools_update_version.py
if errorlevel 1 exit /b 1

echo Installing build dependencies...
python -m pip install --upgrade pip
python -m pip install "nuitka>=4.1.3,<4.2" ordered-set zstandard "PySide6>=6.11.1,<6.12" comtypes
if errorlevel 1 exit /b 1

echo.
echo Cleaning old build outputs...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
mkdir dist

set NUITKA_COMMON=--standalone --assume-yes-for-downloads --remove-output --windows-console-mode=disable --output-dir=build

echo [1/3] Build Hub...
python -m nuitka %NUITKA_COMMON% --enable-plugin=pyside6 --include-package=comtypes --include-module=comtypes.stream --output-filename=Complaint_Service_Hub.exe hub_app.py
if errorlevel 1 exit /b 1

echo [2/3] Build Launcher...
python -m nuitka %NUITKA_COMMON% --output-filename=Complaint_Service_Hub_Launcher.exe launcher.py
if errorlevel 1 exit /b 1

echo [3/3] Build Updater...
python -m nuitka %NUITKA_COMMON% --output-filename=Complaint_Service_Hub_Updater.exe updater.py
if errorlevel 1 exit /b 1

echo.
echo Packaging distribution folder...
mkdir dist\Complaint_Service_Hub
xcopy /E /I /Y build\hub_app.dist\* dist\Complaint_Service_Hub\ >nul
xcopy /E /I /Y build\launcher.dist\* dist\Complaint_Service_Hub\ >nul
xcopy /E /I /Y build\updater.dist\* dist\Complaint_Service_Hub\ >nul
if not exist dist\Complaint_Service_Hub\Complaint_Service_Hub.exe echo ERROR: Hub EXE missing & exit /b 1
if not exist dist\Complaint_Service_Hub\Complaint_Service_Hub_Launcher.exe echo ERROR: Launcher EXE missing & exit /b 1
if not exist dist\Complaint_Service_Hub\Complaint_Service_Hub_Updater.exe echo ERROR: Updater EXE missing & exit /b 1
xcopy /E /I /Y config dist\Complaint_Service_Hub\config\ >nul
xcopy /E /I /Y masters dist\Complaint_Service_Hub\masters\ >nul
xcopy /E /I /Y templates dist\Complaint_Service_Hub\templates\ >nul
xcopy /E /I /Y profiles dist\Complaint_Service_Hub\profiles\ >nul
xcopy /E /I /Y docs dist\Complaint_Service_Hub\docs\ >nul
xcopy /E /I /Y common_guide dist\Complaint_Service_Hub\common_guide\ >nul
xcopy /E /I /Y common_validation dist\Complaint_Service_Hub\common_validation\ >nul
mkdir dist\Complaint_Service_Hub\updates 2>nul
mkdir dist\Complaint_Service_Hub\backups 2>nul
mkdir dist\Complaint_Service_Hub\logs 2>nul
copy /Y app_version.json dist\Complaint_Service_Hub\app_version.json >nul
copy /Y version.json dist\Complaint_Service_Hub\version.json >nul
copy /Y manifest.json dist\Complaint_Service_Hub\manifest.json >nul
copy /Y README_StartHere.txt dist\Complaint_Service_Hub\README_StartHere.txt >nul
copy /Y 00_CHECK_DISTRIBUTION.bat dist\Complaint_Service_Hub\00_CHECK_DISTRIBUTION.bat >nul
(
  echo Module=Complaint_Service_Hub
  echo Application=Complaint_Service_Hub
  echo Version=0.5.0-alpha
  echo Commit=0003u39c
  echo Build=0003u39c
  echo BuildMode=standalone
  echo BuildEngine=Nuitka
  echo Runtime=embedded
  echo Python=%PYTHON_VERSION%
  echo EntryPoint=Complaint_Service_Hub_Launcher.exe
  echo MainExecutable=Complaint_Service_Hub.exe
  echo UpdaterExecutable=Complaint_Service_Hub_Updater.exe
  echo PySide6=Included
  echo FeedbackEngine=1.0
  echo BuildDateUTC=%DATE% %TIME%
) > dist\Complaint_Service_Hub\BUILD_INFO.txt

echo.
echo Build complete.
echo Run: dist\Complaint_Service_Hub\Complaint_Service_Hub_Launcher.exe
exit /b 0
