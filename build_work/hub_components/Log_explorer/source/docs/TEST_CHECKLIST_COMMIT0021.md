# Commit0021 Test Checklist

## Main UI
- [ ] Version shows `2.0.0-rc1-commit0021`
- [ ] START button is visible
- [ ] MERGE button is not visible
- [ ] Split Merge is not visible
- [ ] Merge-only checkboxes are not visible

## START
- [ ] Press START
- [ ] Smart File Discovery opens
- [ ] No Excel/CSV merge output is created
- [ ] Log Explorer opens after selection
- [ ] Progress says `Indexing ... for Viewer`

## Multiple files of the same type
- [ ] Select two or more WS files
- [ ] WS Viewer shows records from all selected WS files
- [ ] File column identifies the original file
- [ ] Select two or more CSA/CGA/MRSERVER files
- [ ] Each type is shown as one continuous Viewer dataset
- [ ] No `Merged` source appears in Viewer

## Regression
- [ ] Load This works
- [ ] CallID extraction works
- [ ] Same CallID linking works across panes
- [ ] Right-click menu works
- [ ] Viewer lower-area row fit works
