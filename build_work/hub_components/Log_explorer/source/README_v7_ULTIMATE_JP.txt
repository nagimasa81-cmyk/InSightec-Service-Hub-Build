Log Merge Tool NoExcel PSC Review FINAL v7 Ultimate
==================================================

Target:
- Windows 11
- Python 3.13
- PySide6 latest
- Nuitka latest

Main after build:
  dist\LogMergeTool_NoExcel.exe

This tool does not use Microsoft Excel, VBA, or COM.

v7 changes:
- PSC is shown only as "PSC" in Log Types.
- PSC can be used for Merge and Import Only.
- Review is shown as "Review (Import Only)".
- Review is not merged. Use the "Import Review Only" button.
- Review target files:
    review.out
    review.out.ar
    review.out.*
- Progress bar shows percent until completion.
- Pause / Resume button is available during merge.
- Cancel button is available during merge.
- Turbo CSV mode is available for large outputs.

Operation:
1. Run the built EXE.
2. Select Source Log Folder and Output Folder.
3. Select Date Range if needed.
4. Select Log Types for merge.
5. Press Run Log Merge.

Import Only:
- Press Import PSC Only for psc.log.
- Press Import Review Only for review.out / review.out.ar / review.out.*.

Build:
1. Install Python 3.13.
2. Run Check_Source_And_Dependencies.bat.
3. Run Build_EXE_Windows11_Python313_Nuitka_NO_EXCEL_FINAL.bat.

Debug:
- If normal EXE does not start, run Build_DEBUG_Console_EXE.bat and start the debug EXE from console.
- Startup error log is written to:
  %LOCALAPPDATA%\LogMergeTool_NoExcel\startup_error.log
