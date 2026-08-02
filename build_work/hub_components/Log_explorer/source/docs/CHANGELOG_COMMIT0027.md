# Commit0027 — Investigation Viewer Control Ownership Fix

## Root cause
The Viewer count/width controls were inserted into `AcquisitionDashboard`
because a generic text replacement matched the first `top.addStretch(1)` in
the file.

Smart File Discovery later created Acquisition Dashboard, which attempted to
connect to `_change_viewer_count`, a method that only exists on
`InvestigationWorkspace`.

## Fix
- Removed Viewer count controls from Acquisition Dashboard.
- Added a dedicated Viewer control bar owned by `InvestigationWorkspace`.
- Viewer count 1–4 and Equal Widths now connect to methods on the same object.
- Added AST tests that reject signal connections to missing owner methods.
- Version updated to `2.0.0-rc1-commit0027`.
