@echo off
setlocal
cd /d "%~dp0"
set TESTS=test_commit0068_series_boundary_navigation.py test_commit0068a_tree_series_autosync.py test_commit0068c_real_series_grouping.py test_commit0068d_tree_authoritative_navigation.py test_commit0068e_source_type_navigation.py test_commit0068g_reliable_series_expansion.py test_commit0068h_explorer_keyboard_navigation.py test_commit0068i_explorer_wheel_navigation.py
py -3 -m pytest -q %TESTS%
if errorlevel 1 (
  python -m pytest -q %TESTS%
)
pause
