# Log Merge Tool RC1 - Commit0010 Test Checklist

## Startup

- [ ] Main window opens centered on first launch
- [ ] Main window remains inside the active monitor
- [ ] Viewer opens centered and fully visible
- [ ] No startup error
- [ ] No regression in Smart Discovery

## General Log Viewer

- [ ] Existing Double View behavior unchanged
- [ ] Show 1 / Show 2 / Show 3 / Show 4 unchanged
- [ ] Search works
- [ ] Filter works
- [ ] Time Range works
- [ ] Cross Reference works
- [ ] Columns... works

## WaterSystem Viewer

- [ ] WaterSystem file loads successfully
- [ ] Default columns are Timestamp / MainState / Error
- [ ] CoolingState is not displayed
- [ ] Message is not synthesized or displayed by default
- [ ] NO_ERROR appears blank
- [ ] Real Error value appears in Error column
- [ ] Error column width is compact
- [ ] MainState width is appropriate
- [ ] ChillerTemp is parsed correctly
- [ ] PrimaryFlowMeter is parsed correctly
- [ ] AbsolutePressure is parsed correctly
- [ ] DynamicPressure is parsed correctly
- [ ] XdTemperature is parsed correctly
- [ ] VacuumLevel is parsed correctly
- [ ] DOLevel is parsed correctly
- [ ] WaterVolume is parsed correctly
- [ ] SecondaryFlowMeter is parsed correctly
- [ ] Remaining numeric columns are parsed correctly
- [ ] Numeric columns are hidden by default
- [ ] Numeric columns can be enabled from Columns...
- [ ] Hover popup remains disabled
- [ ] Open WaterSystem Analyzer action identifies the loaded file

## Investigation Workspace

- [ ] Investigation Workspace opens
- [ ] Initial Investigation works
- [ ] Water Investigation works
- [ ] MR Investigation works
- [ ] Time synchronization works
- [ ] Timeline works
- [ ] Bookmark works
- [ ] Notes work
- [ ] Return to Viewer works

## CSA / CGA Regression

- [ ] CSA timestamp extraction remains correct
- [ ] CGA timestamp extraction remains correct
- [ ] Release/header dates do not override record timestamps
- [ ] CSA/CGA messages remain readable
- [ ] Investigation synchronization works

## File Type / ZIP Generator

- [ ] PluginBuilder opens
- [ ] New File Type ZIP can be generated
- [ ] Generated ZIP can be installed
- [ ] Plugin reload works
- [ ] Plugin update works
- [ ] Plugin delete works
- [ ] Existing file types remain unchanged

## Build

- [ ] Local BAT build succeeds
- [ ] build_selected succeeds
- [ ] build_all succeeds
- [ ] Standalone distribution contains required DLLs
- [ ] EXE starts on evaluation PC
