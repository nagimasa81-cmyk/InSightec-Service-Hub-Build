@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set PY=py -3.13

echo ============================================================
echo  LogMergeTool source/dependency check
echo ============================================================
%PY% --version || goto :ERR
%PY% -m pip install --upgrade PySide6 openpyxl || goto :ERR
%PY% -m py_compile LogMergeTool_NoExcel_Main.py || goto :ERR
%PY% -c "import PySide6, openpyxl; print('PySide6/openpyxl import OK')" || goto :ERR

echo.
echo Source and dependencies look OK.
pause
exit /b 0
:ERR
echo.
echo [ERROR] Check failed.
pause
exit /b 1
