# Commit0059 Test Checklist

## Version and package

- [x] All active `APP_VERSION` assignments are `2.0.0-rc1-commit0059`.
- [x] `version.json` version and commit match Commit0059.
- [x] GitHub and local Nuitka BAT files output `LogMergeTool_RC1_Commit0059.exe`.
- [x] Both build BAT files embed Commit0059 Windows file metadata.
- [x] Required JSON runtime data files are included by both build BAT files.

## Workflow regression

- [ ] Smart Discovery requires manual START.
- [ ] Use, All, and Clear controls operate as before.
- [ ] Main window is not automatically minimized.

## Viewer freeze regression

- [ ] Open Log Viewer and click an empty table area.
- [ ] Click one populated row with Event Sync disabled.
- [ ] Click one populated row with Event Sync enabled.
- [ ] Test Highlight all in range with more than 250 matches.
- [ ] Move, resize, and switch panes after clicking a row.
- [ ] Confirm Windows does not show `Not Responding`.
