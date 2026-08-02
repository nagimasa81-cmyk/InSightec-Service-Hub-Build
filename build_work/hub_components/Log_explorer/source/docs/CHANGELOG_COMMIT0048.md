# Commit0048 — Investigation Import Runtime Fix

## Root cause
`InvestigationWorkspace` was implemented in `foundation/investigation.py`,
but `LogMergeTool_NoExcel_Main.py` referenced it without importing it.

## Fixed
- Added:
  `from foundation.investigation import InvestigationWorkspace`
- Retained the canonical `SpectrumAnalysisWidget` import.
- Added an embedded-workspace class contract.
- Kept Investigation and Spectrum embedded directly in Log Explore.

## Validation note
The build environment used for source packaging does not contain PySide6, so a
real Qt window construction test cannot run here. AST checks verify the class
definitions, imports, constructor signatures and call sites. Final GUI startup
must be confirmed with the Windows EXE.
