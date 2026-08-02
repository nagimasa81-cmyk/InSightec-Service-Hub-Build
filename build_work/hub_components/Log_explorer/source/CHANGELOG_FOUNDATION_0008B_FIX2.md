# Commit0008b FIX2

## Critical fix
- Fixed Smart File Discovery startup crash caused by an invalid Qt enum reference in Viewer Foundation initialization.
- Replaced `table.ScrollPerPixel` with `QAbstractItemView.ScrollPerPixel`.

## Expected result
- Smart File Discovery can complete and open the Log Viewer without the `QTableView has no attribute ScrollPerPixel` exception.
- Existing Commit0008b fixes remain included.
