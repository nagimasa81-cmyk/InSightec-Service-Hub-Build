# Foundation Commit0008b Fix

## Fixed
- Log Viewer window is clamped to the active screen and centered.
- Added **Reset Layout** to restore window, pane sizes, and default column widths.
- Added **Fit Columns** to auto-fit visible columns while keeping them manually resizable.
- All Viewer columns, including WaterSystem panes, remain `Interactive` after loading/filtering.
- Restored **Copy Rule Text** as an editable popup; OK copies the edited text.
- Improved Smart File Discovery progress with percentage, elapsed time, estimated remaining time, and current file.

## Foundation
- Added `common/master_data.py` for a Service Hub shared Site/Serial master.
- Canonical shared master path:
  `%LOCALAPPDATA%/InSightecServiceHub/MasterData/site_serial_master.json`
- Existing module-local `site_serial_map.json` is imported automatically on first use.
- Serial and Site selections remain linked; a Site with multiple systems narrows the Serial list instead of choosing an arbitrary system.

## Version
`2.0.0-rc1-foundation-0008b-fix`

## Verification Notes
- Python syntax compilation: PASS.
- Windows/PySide6 GUI runtime test: required on the target PC.
