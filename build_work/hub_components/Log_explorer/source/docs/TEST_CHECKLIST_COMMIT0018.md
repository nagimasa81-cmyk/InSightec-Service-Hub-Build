# Commit0018 Test Checklist

## Drop-zone visibility
- [ ] A large `Drop Folder / ZIP / Log Files Here` area is visible below Folders.
- [ ] It remains visible at Windows display scaling 100%, 125%, and 150%.
- [ ] Dragging a supported item changes the text to `Release to Import`.

## Folder
- [ ] Drop one folder.
- [ ] Source Type changes to Folder.
- [ ] Source path is populated.
- [ ] Recursive search is enabled.
- [ ] START opens Smart File Discovery.

## ZIP
- [ ] Drop one ZIP.
- [ ] Source Type changes to ZIP File.
- [ ] START safely extracts it and opens Smart File Discovery.
- [ ] UNKNOWN is not shown.
- [ ] Nested ZIP filenames are reported but not expanded.
- [ ] Temporary extraction is deleted after import/cancel/error.

## Multiple files
- [ ] Drop multiple `.log`, `.txt`, `.out`, or `.ar` files.
- [ ] Files are staged safely.
- [ ] START opens Smart File Discovery.
- [ ] Closing the app removes the temporary staging folder.

## Invalid combinations
- [ ] Multiple folders are rejected with a clear message.
- [ ] ZIP mixed with ordinary files is rejected.
- [ ] Unsupported items do not crash the application.

## Regression
- [ ] Folder / ZIP / Project Browse workflow still works.
- [ ] WS / CSA / CGA / WaterSystem / VIMeasure parser tests pass.
- [ ] Viewer and Investigation Mode still open.
