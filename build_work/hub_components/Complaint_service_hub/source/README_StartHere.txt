Complaint Service Hub 0003u38a - Build Instructions

Production build must run BUILD_EXE.bat (or 01_BUILD_EXE_NUITKA.bat).
Do not package main.py or hub_app.py as a Python-runtime artifact.
Expected BUILD_INFO.txt: BuildMode=standalone / BuildEngine=Nuitka.
Run the distributed Complaint_Service_Hub_Launcher.exe from the complete extracted folder.

InSightec Complaint Service Hub v0.5 Alpha - Build 0002u3

Recommended build:
1. Extract this ZIP.
2. Run 01_BUILD_EXE_NUITKA.bat on Windows.
3. Start dist\Complaint_Service_Hub\Complaint_Service_Hub_Launcher.exe.

Python test run:
- Run run_from_python.bat.

Important:
- This version does not use tkinter.
- Launcher, Hub, and Updater are separated.
- Program Update is staged and applied by Launcher on the next start.
- Master Update is applied from Hub > Update ZIP.

InSightec password: 5963


Commit 0003 Build Note:
Use 01_BUILD_EXE_NUITKA.bat. GitHub Actions should use .github/workflows/build_windows_nuitka.yml and Python 3.13.


0003u2: Fixed Windows CMD batch syntax error caused by Python heredoc.


Commit 0003u8:
- Outlook feedback connection retries up to 3 times.
- Open Outlook button starts Outlook automatically and waits before retrying.
- Retry, Open Template, and Cancel choices are available.
- Internal module errors skip ineffective retries and offer Template fallback.


0003u38a Phase 3 additions:
- Common validation library
- Real-time required-field status for Basic, Medical, and Additional
- Red/green field highlighting and tab completion indicators
- Missing-field dialog with jump-to-field navigation
- Expanded localization for all currently supported languages
