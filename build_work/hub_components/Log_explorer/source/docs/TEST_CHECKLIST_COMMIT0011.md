# Commit0011 Investigation Mode Test Checklist

## Mode switching
- [ ] Log Viewer starts in Normal Log Viewer mode
- [ ] Investigation Mode button switches within the same window
- [ ] Return to Log Viewer restores the normal viewer
- [ ] Existing loaded viewer data is not lost
- [ ] No second Investigation window opens

## Investigation profiles
- [ ] Initial Investigation loads WS / CSA / CGA
- [ ] Water Investigation loads WS / CSA / CGA / WaterSystem
- [ ] MR Investigation loads WS / MRSERVER / GESYS

## Investigation views
- [ ] Logs view
- [ ] WaterSystem Chart view
- [ ] Logs + Chart view
- [ ] Water Investigation defaults to Logs + Chart

## WaterSystem chart
- [ ] DO Level displayed
- [ ] Vacuum displayed
- [ ] Primary Flow displayed
- [ ] Secondary Flow displayed
- [ ] Chiller Temp can be enabled
- [ ] XD Temp can be enabled
- [ ] Series checkboxes update immediately
- [ ] Chart click synchronizes visible logs
- [ ] Log row selection moves chart cursor

## Existing RC1 functions
- [ ] Search
- [ ] Time tolerance Exact / ±1 / ±5 / ±10 / ±30 sec
- [ ] Critical Timeline
- [ ] Bookmark
- [ ] Bookmark CSV export
- [ ] Investigation Notes
- [ ] Investigation Summary
- [ ] PluginBuilder opens
- [ ] File Type ZIP Generator works
- [ ] GitHub selected build succeeds
- [ ] Local BAT build succeeds
