# Commit0049 — Responsive Log Explore Lazy Loading

## Root cause
Opening Log Explore synchronously performed multiple heavy actions on the GUI
thread:

1. Investigation and Spectrum widgets were constructed immediately.
2. Operation analysis was rebuilt during every `refresh_data()`.
3. `refresh_data()` was called both before `show()` and from `showEvent()`.

This could leave the window white and marked Not Responding.

## Fixed
- Log Explore shows Event Viewer immediately.
- Investigation is constructed only when its tab is selected.
- Spectrum is constructed only when its tab is selected.
- Investigation analysis does not start automatically.
- Spectrum scanning does not start automatically.
- Operation analysis does not rebuild automatically.
- Startup refresh is deferred with `QTimer.singleShot`.
- Duplicate first-show refresh is prevented.

## Operator actions
- Operation: press `Rebuild Operation Analysis`
- Investigation: select profile, then press `Start Analysis`
- Spectrum: press `Scan Spectrum Dumps`
