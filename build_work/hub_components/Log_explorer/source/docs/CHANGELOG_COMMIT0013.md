# Commit0013 - File Type ZIP Builder Test / VIMeasure

## Added
- File Type ZIP Builder with presets, multi-sample testing and build blocking on failed tests.
- Generic structured-whitespace plugin parser support in the main Log Merge Tool.
- VIMeasure File Type Update plugin for Sonication Investigation.
- Dynamic columns from the `; Data:` header.
- Filename date + row time timestamp construction.
- `viewer_defaults.json` and `investigation_profile.json` support.
- Standalone CI validation test for the VIMeasure plugin ZIP.

## VIMeasure defaults
- Visible: Timestamp, 4vI, 4vV, -6vI, -6vV, 6vI, 6vV
- Optional: FE/ER 48 V, -15 V and 15 V current/voltage columns
- Hover popup: disabled
- Investigation profile: Sonication
