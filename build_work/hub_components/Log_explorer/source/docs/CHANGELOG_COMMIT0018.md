# Commit0018

## Clear source drop zone
- Added a large always-visible drop area directly below the source controls.
- Accepts one folder, one ZIP archive, or multiple log files.
- Shows `Release to Import` while dragging.
- Added Browse Folder, Browse ZIP, and Browse Files buttons inside the drop area.
- Dropped ZIP archives use the existing ZIP -> Smart File Discovery workflow.
- Dropped individual files are safely staged in a temporary folder and passed to Smart File Discovery.
- Temporary dropped-file staging is cleaned when the window closes or a new source is chosen.
- The entire main window also accepts drops and redirects them to the same handler.
