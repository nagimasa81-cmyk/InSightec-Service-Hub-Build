# Log Merge Tool RC1 Commit0011

## Investigation Mode confirmation build

- Changed Investigation Workspace from a separate window to an in-viewer mode.
- Added one-button switching between Normal Log Viewer and Investigation Mode.
- Added Investigation view choices:
  - Logs
  - WaterSystem Chart
  - Logs + Chart
- Added lightweight WaterSystem chart inside Investigation Mode.
- Added chart series toggles for DO Level, Vacuum, Primary Flow, Secondary Flow, Chiller Temp, and XD Temp.
- Added bidirectional time synchronization:
  - Log row selection moves the chart cursor.
  - Chart click moves visible investigation logs to the selected time.
- Water Investigation defaults to Logs + Chart.
- Normal Log Viewer Foundation and PluginBuilder / ZIP Generator remain included.
- External WaterSystem Analyzer launch is not used inside Investigation Mode.
