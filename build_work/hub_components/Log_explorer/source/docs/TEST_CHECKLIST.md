# Log Merge Tool RC1 Test Checklist

Version: Commit0009 RC1

## Startup / Foundation
- [ ] EXE starts without error
- [ ] Main window opens
- [ ] Smart Discovery opens
- [ ] ZIP loading works
- [ ] Viewer opens without crash
- [ ] Existing Merge workflow has no regression

## Investigation Workspace
- [ ] Investigation Workspace button opens
- [ ] Return to Viewer works
- [ ] Initial Investigation shows WS / CSA / CGA
- [ ] Water Investigation shows WS / CSA / CGA / WaterSystem
- [ ] MR Investigation shows WS / MRSERVER / GESYS
- [ ] Exact time sync
- [ ] ±1 second sync
- [ ] ±5 second sync
- [ ] ±10 second sync
- [ ] ±30 second sync
- [ ] Cross-log search
- [ ] Critical Timeline
- [ ] Critical Timeline filter
- [ ] Warning Timeline filter
- [ ] Investigation Summary counts
- [ ] Bookmark add and jump
- [ ] Bookmark CSV export
- [ ] Investigation Notes

## WaterSystem Parser
- [ ] Timestamp is extracted correctly
- [ ] Event is shown in Category
- [ ] Cooling state is retained in Message
- [ ] Error state is retained in Message
- [ ] NO_ERROR does not create ERROR level
- [ ] Actual error state creates ERROR level
- [ ] ERROR is not duplicated across Level / Category / Message
- [ ] Default WaterSystem columns are Timestamp / Level / Category / Message / File / Line
- [ ] Hover popup is disabled
- [ ] WaterSystem works in Water Investigation time sync

## Regression
- [ ] WS display unchanged
- [ ] CSA display unchanged
- [ ] CGA display unchanged
- [ ] PSC display unchanged
- [ ] Review display unchanged
- [ ] Existing parser and Viewer loading are reused
- [ ] Local BAT build succeeds
- [ ] GitHub build_selected succeeds
- [ ] GitHub build_all succeeds
