# Commit0026 — QWidget Foundation Startup Fix

## Root cause
`MainWindow` inherits from `QWidget`, but the standalone Spectrum button patch
called `self.centralWidget()`, which only exists on `QMainWindow`.

## Fix
- Spectrum button is inserted directly into `MainWindow.layout()`.
- A safe parent/position fallback is used if no layout is available.
- Startup no longer depends on a nonexistent `centralWidget()` method.
- Standalone Spectrum window remains a real `QMainWindow`.
- Version updated to `2.0.0-rc1-commit0026`.

## Validation
- Checks that MainWindow is QWidget-based.
- Checks that the active Spectrum patch contains no centralWidget call.
- Checks definition order before application startup.
