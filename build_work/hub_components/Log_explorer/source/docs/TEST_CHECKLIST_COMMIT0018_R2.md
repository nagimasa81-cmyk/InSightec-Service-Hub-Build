# Commit0018 R2 Test Checklist

## Output Folder
- [ ] Drop a folder: Output becomes the dropped folder
- [ ] Drop a ZIP: Output becomes the ZIP parent folder
- [ ] Drop one file: Output becomes its parent folder
- [ ] Drop multiple files from one folder: Output becomes that folder
- [ ] Drop multiple files from different folders: first file parent is used and reported
- [ ] Browse Folder / ZIP / Files follow the same rules
- [ ] A new input overwrites the previous Output Folder

## Same-monitor placement
- [ ] Start Log Merge on monitor 1: all child windows open on monitor 1
- [ ] Start Log Merge on monitor 2: all child windows open on monitor 2
- [ ] Smart File Discovery is fully visible
- [ ] Viewer is fully visible
- [ ] Investigation is fully visible
- [ ] Progress popup is centered
- [ ] No title bar or action button is outside the screen

## Display scaling
- [ ] Windows scaling 100%
- [ ] Windows scaling 125%
- [ ] Windows scaling 150%
- [ ] Taskbar on bottom
- [ ] Taskbar on left/right if available

## Regression
- [ ] Folder / ZIP / multiple-file drop works
- [ ] START opens Smart File Discovery
- [ ] MERGE still works
- [ ] Viewer opens
- [ ] Investigation Mode opens
- [ ] WS / CSA / CGA / WaterSystem / VIMeasure parser tests pass
