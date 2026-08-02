# Commit0041 — GESYS Section and Review Cache Parser Fix

## GESYS
- ZIP cache now stores one record per GESYS section.
- Section timestamp lines define each record timestamp.
- Prologue/release text before the first section is ignored.
- Complete section content is retained in Raw JSON.
- Viewer no longer expands a 19,530-section file into roughly 140,000
  physical-line rows.

## Review
- UTF-16 is detected and decoded before NUL replacement.
- Supports UTF-16 LE/BE with or without BOM.
- Structured Review parser is attempted first.
- Meaningful decoded rows are retained when structured parsing returns zero.

## PSC
- ZIP cache explicitly uses `parse_psc_file_detail` LogRecord output.

## Scope
The fix is applied while building `zip_import_records_by_type`, before the
temporary extraction folder is deleted.
