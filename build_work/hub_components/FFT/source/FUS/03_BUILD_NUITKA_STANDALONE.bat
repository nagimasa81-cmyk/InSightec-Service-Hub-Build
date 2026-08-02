@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PYTHON_CMD=py -3.13"
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 set "PYTHON_CMD=python"

if not exist ".venv_nuitka\Scripts\python.exe" (
    %PYTHON_CMD% -m venv .venv_nuitka
    if errorlevel 1 goto :error
)

call ".venv_nuitka\Scripts\activate.bat"
python prepare_build_mode.py
if errorlevel 1 exit /b 1
python -m pip install --disable-pip-version-check -r requirements-build-nuitka.txt
if errorlevel 1 goto :error

if exist "dist_nuitka" rmdir /s /q "dist_nuitka"
if exist "MRI_Raw_FFT_Explorer_Nuitka_Windows" rmdir /s /q "MRI_Raw_FFT_Explorer_Nuitka_Windows"
if exist "MRI_Raw_FFT_Explorer_Nuitka_Windows.zip" del /q "MRI_Raw_FFT_Explorer_Nuitka_Windows.zip"

python -m nuitka ^
  --mode=standalone ^
  --enable-plugin=pyside6 ^
  --windows-console-mode=disable ^
  --assume-yes-for-downloads ^
  --jobs=4 ^
  --output-dir=dist_nuitka ^
  --output-filename=MRI_Raw_FFT_Explorer.exe ^
  --include-module=app ^
  --include-module=vendor_adapters ^
  --include-module=decoder_manager ^
  --include-package=pydicom ^
  --include-package-data=pydicom ^
  --include-package=pylibjpeg ^
  --include-package=libjpeg ^
  --include-package=openjpeg ^
  --include-data-files=vendor_sdk_config.json=vendor_sdk_config.json ^
  --include-data-files=tracker_position_defaults.json=tracker_position_defaults.json ^
  --include-data-files=artifact_learning_defaults.json=artifact_learning_defaults.json ^
  --include-data-files=release_mode.json=release_mode.json ^
  --include-data-files=version.json=version.json ^
  --include-data-dir=database=database ^
  launcher.py
if errorlevel 1 goto :error

rem pydicom 3.x reads packaged JSON resources during import.  A build that
rem omitted these files starts and then immediately fails with FileNotFoundError.
dir /s /b "dist_nuitka\*urls.json" >nul 2>&1
if errorlevel 1 (
  echo ERROR: pydicom package data was not bundled. urls.json is missing.
  goto :error
)

mkdir "MRI_Raw_FFT_Explorer_Nuitka_Windows"
xcopy /e /i /y "dist_nuitka\launcher.dist\*" "MRI_Raw_FFT_Explorer_Nuitka_Windows\" >nul
copy /y README.md "MRI_Raw_FFT_Explorer_Nuitka_Windows\README.md" >nul
copy /y 04_RUN_STARTUP_DIAGNOSTIC.bat "MRI_Raw_FFT_Explorer_Nuitka_Windows\04_RUN_STARTUP_DIAGNOSTIC.bat" >nul
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path 'MRI_Raw_FFT_Explorer_Nuitka_Windows\*' -DestinationPath 'MRI_Raw_FFT_Explorer_Nuitka_Windows.zip' -Force"
if errorlevel 1 goto :error

echo.
echo Nuitka standalone build completed.
echo EXE: %CD%\MRI_Raw_FFT_Explorer_Nuitka_Windows\MRI_Raw_FFT_Explorer.exe
echo ZIP: %CD%\MRI_Raw_FFT_Explorer_Nuitka_Windows.zip
pause
exit /b 0

:error
echo.
echo Build failed. See the messages above.
pause
exit /b 1
