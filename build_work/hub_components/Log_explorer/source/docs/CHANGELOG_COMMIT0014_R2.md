# Commit0014 Revision 2 Changelog

## ZIP input workflow

- ZIP archives are safely extracted to a temporary directory.
- The extracted directory is passed to Smart File Discovery.
- Recognized file types can be selected in multiples, using the normal All/Clear and date-range workflow.
- UNKNOWN is disabled and is not shown for ZIP input in this revision.
- ZIP files found inside the selected ZIP are not recursively extracted. Their file names are reported only.
- Selected recognized files are parsed into an in-memory cache before the temporary directory is deleted.
- Temporary extraction is deleted after success, cancellation, or error.

## Viewer

- The Viewer source list is refreshed from the in-memory ZIP import cache.
- VIMeasure and other installed File Type plugin results can appear without retaining extracted files.

## Parser requirement

- ZIP discovery and import use the currently installed/new parser routes for WS, CSA, CGA, WaterSystem and plugin file types.
- No silent UNKNOWN fallback is permitted in the ZIP workflow.
- Real-log regression validation for WS/CSA/CGA remains mandatory before RC1 acceptance.
