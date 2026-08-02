# Commit0032C Test Checklist

## Dropdown shown
- [ ] Right-click a Level column containing 10 or fewer distinct values
- [ ] `Select value` is visible
- [ ] Actual values are listed
- [ ] Select one value
- [ ] Only exact matching rows remain

## Dropdown hidden
- [ ] Right-click Message or another column with 11+ distinct values
- [ ] `Select value` is not displayed
- [ ] Text-based contains/exact filters remain available

## Edge cases
- [ ] Duplicate values appear only once
- [ ] Case-only duplicates appear only once
- [ ] Blank values appear as `(Blank)`
- [ ] Selecting `(Blank)` filters blank cells
- [ ] Clear column filter restores rows
- [ ] Each Viewer pane remains independent
