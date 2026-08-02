# Log Merge Tool RC1 - Commit0010

## Updated

- General Log Viewer layout and workflow remain unchanged.
- WaterSystem is now parsed as its native structured table rather than a synthesized message log.
- WaterSystem default Viewer columns are now:
  - Timestamp
  - MainState
  - Error
- CoolingState is intentionally omitted.
- NO_ERROR is displayed as blank.
- Numeric columns are parsed and retained but hidden by default.
- Numeric columns remain available through Columns...
- Added practical WaterSystem column widths.
- Added Open WaterSystem Analyzer action.
- Added main window centering and off-screen protection.
- Existing Investigation Workspace is retained.
- Existing PluginBuilder / File Type ZIP Generator is retained.
- Existing CSA/CGA timestamp and header fixes are retained.

## Numeric WaterSystem columns retained

- ChillerTemp
- PrimaryFlowMeter
- AbsolutePressure
- DynamicPressure
- XdTemperature
- VacuumLevel
- DOLevel
- WaterVolume
- SecondaryFlowMeter
- HsCombitac
- ChillerStatus
- ChillerLowLevelInd
- PressureSetPoint
