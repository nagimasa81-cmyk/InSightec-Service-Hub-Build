# Commit0013 Test Checklist

## Builder
- [ ] File Type ZIP Builder starts.
- [ ] VIMeasure preset is selected by default.
- [ ] Multiple sample logs can be added.
- [ ] Run Tests shows PASS for both included samples.
- [ ] ZIP build is blocked when a parser test fails.
- [ ] Built ZIP contains manifest, parser, viewer defaults, investigation profile and test report.

## Update File Type
- [ ] Open Plugin Manager / Update File Type.
- [ ] Validate `VIMeasure_FileType_Update_v1_0_0.plugin.zip`.
- [ ] Install/update succeeds.
- [ ] Reload shows VIMeasure enabled.
- [ ] EXE restart preserves the plugin.

## Discovery and Viewer
- [ ] Smart Discovery detects `VIMeasure_*.txt`.
- [ ] Filename date is combined with row time.
- [ ] All columns are generated from the `; Data:` header.
- [ ] 14-column samples load without column shift.
- [ ] Default visible columns match viewer defaults.
- [ ] Columns dialog exposes all other numeric columns.
- [ ] Hover popup is disabled.
- [ ] Numeric column filters work.

## Sonication Investigation
- [ ] VIMeasure is available in Sonication Investigation.
- [ ] Logs view works.
- [ ] VIMeasure Chart view can use numeric columns.
- [ ] Logs + Chart time synchronization works.
