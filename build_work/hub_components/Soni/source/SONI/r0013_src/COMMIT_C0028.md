# RC1 C0028 DataReplayHardening

- Validated the supplied ANx package: 8 Sonications are discovered and replay RAW frames decode as 256 x 256.
- Fixed release metadata verification so `verify_source.py` is usable again.
- Added safe ZIP extraction and corrupted-member detection.
- Released the previous extracted workspace when another package is loaded.
- Added a command-line replay package audit tool.
- Added root-level verification, debug, and Nuitka build BAT files.
- Added a Windows GitHub Actions workflow that verifies, builds, packages, and uploads the EXE.
