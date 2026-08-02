@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo TrackerSNR CLEAN EXE build - EXPERIMENTAL
echo Backend: Nuitka standalone
echo.
echo Note: If this fails with a Scons crash report,
echo       use 00_BUILD_EXE_RECOMMENDED_PYINSTALLER.bat.
echo ============================================
echo.

py -3.13 -m pip install -U pip
if errorlevel 1 goto ERR
py -3.13 -m pip install -r requirements.txt
if errorlevel 1 goto ERR

rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
mkdir dist 2>nul

py -3.13 -m nuitka ^
  --standalone ^
  --assume-yes-for-downloads ^
  --enable-plugin=pyside6 ^
  --include-qt-plugins=sensible,styles,platforms,imageformats ^
  --windows-console-mode=attach ^
  --output-dir=dist ^
  --output-filename=TrackerSNR_CLEAN_EXE.exe ^
  TrackerSNR_CLEAN_EXE.py
if errorlevel 1 goto ERR

echo.
echo Build complete.
echo Use this folder as a set:
echo dist\TrackerSNR_CLEAN_EXE.dist\TrackerSNR_CLEAN_EXE.exe
pause
goto END

:ERR
echo.
echo Nuitka build failed.
echo This is a build-tool/compiler/Scons issue, not a parser result issue.
echo Please use 00_BUILD_EXE_RECOMMENDED_PYINSTALLER.bat.
pause
:END
endlocal
