# Commit0050 — Two-Phase Log Explore Bootstrap

## Root cause
The legacy Event Viewer was still constructed before Log Explore could paint.
Its constructor could inspect selected files and parsed cache, blocking the GUI
thread and leaving a white Not Responding window.

## New startup sequence
1. Show an empty Log Explore shell.
2. Construct Event Viewer while parent file/cache data is temporarily hidden.
3. Restore the parsed cache.
4. Construct Value Viewer.
5. Connect both viewers to parsed data.
6. Create Operation, Investigation and Spectrum only when selected.

## Result
The Log Explore frame, title, tabs and progress bar are painted before any
legacy viewer initialization begins.
