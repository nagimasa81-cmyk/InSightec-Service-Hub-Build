# Commit0049a Triple Check Cleanup

## Finding
Commit0049 retained two generations of `MainWindow.open_log_explore` assignment:

- obsolete `_f44_open_log_explore`
- canonical `_f46_open_log_explore`

The final assignment worked, but the obsolete definition increased regression risk.

## Cleanup
- Removed the obsolete `_f44_open_log_explore` function and assignment.
- Retained one canonical `MainWindow.open_log_explore` assignment.
- Retained lazy Investigation/Spectrum loading.
- Retained deferred lightweight refresh.
- Retained manual Operation rebuild.

## Validation
- [x] 63 Python files compile
- [x] One `MainWindow.open_log_explore` assignment
- [x] One `LogExploreWindow.__init__` assignment
- [x] One `LogExploreWindow.refresh_data` assignment
- [x] No eager Investigation construction
- [x] No eager Spectrum construction
- [x] No automatic Operation rebuild
- [x] Five Log Explore tabs retained
- [x] Review canonical parser retained
- [x] No CSA/CGA automatic Type=Err setter
- [x] ZIP integrity passes
