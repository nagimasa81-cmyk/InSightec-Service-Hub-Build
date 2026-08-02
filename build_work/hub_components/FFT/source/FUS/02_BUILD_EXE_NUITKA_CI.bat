@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "PYTHON_EXE=python"
%PYTHON_EXE% -c "import sys; assert sys.version_info[:2] == (3,13)" || exit /b 1
if not exist ".venv_nuitka\Scripts\python.exe" (
  %PYTHON_EXE% -m venv .venv_nuitka || exit /b 1
)
call ".venv_nuitka\Scripts\activate.bat" || exit /b 1
python prepare_build_mode.py
if errorlevel 1 exit /b 1
python -m pip install --disable-pip-version-check -r requirements-build-nuitka.txt || exit /b 1
python -c "import pydicom, pylibjpeg, libjpeg, openjpeg; from PySide6 import QtOpenGL, QtOpenGLWidgets; print('Decoder and Qt OpenGL imports OK')" || exit /b 1
if exist dist_nuitka rmdir /s /q dist_nuitka
if exist dist rmdir /s /q dist
python -m nuitka ^
  --mode=standalone ^
  --enable-plugin=pyside6 ^
  --windows-console-mode=disable ^
  --assume-yes-for-downloads ^
  --jobs=4 ^
  --output-dir=dist_nuitka ^
  --output-filename=MR_Image_Explorer_RC1.exe ^
  --include-module=app ^
  --include-module=vendor_adapters ^
  --include-module=decoder_manager ^
  --include-module=PySide6.QtOpenGL ^
  --include-module=PySide6.QtOpenGLWidgets ^
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
if errorlevel 1 exit /b 1
dir /s /b "dist_nuitka\*urls.json" >nul 2>&1 || exit /b 1
mkdir "dist\MR_Image_Explorer_RC1" || exit /b 1
xcopy /e /i /y "dist_nuitka\launcher.dist\*" "dist\MR_Image_Explorer_RC1\" >nul || exit /b 1
if not exist "dist\MR_Image_Explorer_RC1\MR_Image_Explorer_RC1.exe" exit /b 1
exit /b 0
