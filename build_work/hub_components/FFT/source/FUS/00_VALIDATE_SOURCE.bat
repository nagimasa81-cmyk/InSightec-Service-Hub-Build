@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PYTHON_CMD=py -3.13"
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 set "PYTHON_CMD=python"

%PYTHON_CMD% -m py_compile app.py launcher.py decoder_manager.py core\*.py
if errorlevel 1 goto :error

%PYTHON_CMD% -m pytest -q test_commit0076_blob_compensation.py test_commit0077_unified_bitmap_import.py test_commit0078_optional_decoder.py
if errorlevel 1 goto :error

echo.
echo Source validation passed.
exit /b 0

:error
echo.
echo Source validation failed.
exit /b 1

%PYTHON_CMD% -m pytest -q test_commit0083_navigation_cache_foundation.py
