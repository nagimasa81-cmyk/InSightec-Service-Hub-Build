# Commit0014 R4 — CSA/CGA Structured Parser Test

## Added
- Dedicated CSA/CGA structured parser in `parser_rc1.py`.
- First four physical lines are treated as file header and are not emitted as log records.
- Process, Version and Release information are retained as file metadata.
- Normal rows are split into Timestamp, Type, Num and Message.
- `[ORIGINAL]` prefixes are extracted into `Original`.
- For normal messages, text before the first meaningful single colon is extracted into `Original`.
- Indented continuation/detail rows inherit Timestamp, Type and Num and extract `Sub Original` before `:` or `::`.
- Viewer default columns for CSA/CGA: Timestamp, Type, Original, Message.
- Num and Sub Original remain available through Columns.
- CSA/CGA open with visible default filter `Type=Err`; Clear removes it.
- Existing ZIP -> Smart File Discovery multi-file import, Feedback Engine and VIMeasure plugin are retained.

## Important
- The three-character Type value is preserved exactly (`Inf`, `Wrn`, `Err`).
- Release dates inside the header are metadata only and never become row timestamps.
