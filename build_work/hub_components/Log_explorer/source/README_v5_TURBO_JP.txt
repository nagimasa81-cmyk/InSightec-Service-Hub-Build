[Superseded by README_v7_ULTIMATE_JP.txt]

Log Merge Tool - No Excel / v6 Turbo Control Engine
============================================================

Target:
- Windows 11
- Python 3.13
- PySide6 latest
- Nuitka latest
- No Microsoft Excel / No VBA / No COM

Main build BAT:
- Build_EXE_Windows11_Python313_Nuitka_NO_EXCEL_FINAL.bat

Debug build BAT:
- Build_DEBUG_Console_EXE.bat

Build output:
- dist\LogMergeTool_NoExcel.exe

v6 Turbo Control changes:
1. Parallel parser
   - Files are parsed concurrently.
   - Default is Auto workers.
   - GUI setting: Performance > Parser workers.

2. Turbo CSV output for large data
   - When included records are 100,000 rows or more, full merged data is written to CSV.
   - Summary and configuration are written to a lightweight xlsx.
   - This avoids the very slow 480,000-row decorated xlsx writing step.

3. Summary xlsx only in Turbo mode
   - Search full data: *_Search.csv
   - Errors full data: *_Errors.csv
   - PSC detail full data: *_PSC_Log.csv / *_PSC_Params.csv
   - Summary xlsx: output file listed in completion dialog.

4. Normal xlsx mode remains available
   - Uncheck "v6 Turbo Control CSV for large data" to force xlsx output.
   - For large data this is slower.

Recommended settings for your 480,000-row case:
- v6 Turbo Control CSV for large data: ON
- Summary xlsx only in Turbo mode: ON
- Parser workers: Auto or 8

How to use:
1. Run Build_EXE_Windows11_Python313_Nuitka_NO_EXCEL_FINAL.bat
2. Start dist\LogMergeTool_NoExcel.exe
3. Select Source Log Folder and Output Folder
4. Select log types, including PSC if needed
5. Set Date Range if needed
6. Click Run Log Merge

Output example:
- LogMerge_NoExcel_Yokosuka_4278_YYYYMMDD_HHMMSS.xlsx
- LogMerge_NoExcel_Yokosuka_4278_YYYYMMDD_HHMMSS_Search.csv
- LogMerge_NoExcel_Yokosuka_4278_YYYYMMDD_HHMMSS_Errors.csv

If EXE does not start:
- Build_DEBUG_Console_EXE.bat
- Check %%LOCALAPPDATA%%\LogMergeTool_NoExcel\startup_error.log
