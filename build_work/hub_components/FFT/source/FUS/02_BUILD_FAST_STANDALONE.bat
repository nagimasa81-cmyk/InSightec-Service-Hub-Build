@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PYTHON_CMD=py -3.13"
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 set "PYTHON_CMD=python"

if not exist ".venv\Scripts\python.exe" (
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 goto :error
)

call ".venv\Scripts\activate.bat"
python prepare_build_mode.py
if errorlevel 1 exit /b 1
python -m pip install --disable-pip-version-check -r requirements-build-fast.txt
if errorlevel 1 goto :error

if exist "build_fast" rmdir /s /q "build_fast"
if exist "dist_fast" rmdir /s /q "dist_fast"
if exist "MRI_Raw_FFT_Explorer_Windows" rmdir /s /q "MRI_Raw_FFT_Explorer_Windows"
if exist "MRI_Raw_FFT_Explorer_Windows.zip" del /q "MRI_Raw_FFT_Explorer_Windows.zip"

python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --onedir ^
  --name MRI_Raw_FFT_Explorer ^
  --distpath dist_fast ^
  --workpath build_fast ^
  --specpath build_fast ^
  --add-data "vendor_sdk_config.json;." ^
  --collect-all pyqtgraph ^
  --collect-all pydicom ^
  --collect-all pylibjpeg ^
  --collect-all pylibjpeg_libjpeg ^
  --collect-all openjpeg ^
  --hidden-import vendor_adapters ^
  app.py
if errorlevel 1 goto :error

mkdir "MRI_Raw_FFT_Explorer_Windows"
xcopy /e /i /y "dist_fast\MRI_Raw_FFT_Explorer\*" "MRI_Raw_FFT_Explorer_Windows\" >nul
copy /y README.md "MRI_Raw_FFT_Explorer_Windows\README.md" >nul
copy /y vendor_sdk_config.json "MRI_Raw_FFT_Explorer_Windows\vendor_sdk_config.json" >nul
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path 'MRI_Raw_FFT_Explorer_Windows\*' -DestinationPath 'MRI_Raw_FFT_Explorer_Windows.zip' -Force"
if errorlevel 1 goto :error

echo.
echo Fast standalone build completed.
echo EXE: %CD%\MRI_Raw_FFT_Explorer_Windows\MRI_Raw_FFT_Explorer.exe
echo ZIP: %CD%\MRI_Raw_FFT_Explorer_Windows.zip
pause
exit /b 0

:error
echo.
echo Build failed. See the messages above.
pause
exit /b 1
