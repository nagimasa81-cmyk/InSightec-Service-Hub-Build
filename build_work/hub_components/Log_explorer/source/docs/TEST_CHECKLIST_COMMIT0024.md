# Commit0024 Test Checklist

## Investigation Viewer
- [ ] Open Investigation Mode
- [ ] Change viewer count to 1, 2, 3, and 4
- [ ] Change count again after loading data
- [ ] Drag the splitter to change widths
- [ ] Equal Widths restores equal widths

## Acquisition Dashboard
- [ ] Load ACQUISITION
- [ ] Open Acquisition Dashboard
- [ ] Refresh from Viewer
- [ ] Event density displays
- [ ] Acoustic power displays
- [ ] Reflection max displays
- [ ] Dangerous channels displays
- [ ] XD impedance displays
- [ ] Event table changes with chart selection

## Independent Spectrum Analysis
- [ ] Main window has Spectrum Analysis button
- [ ] Spectrum window opens without loading logs
- [ ] Select a search folder
- [ ] Recursive search finds deeply nested dumps
- [ ] Drop one Spectrum Dump from Windows Explorer
- [ ] Drop multiple Spectrum Dumps
- [ ] Drop a folder
- [ ] `.dmp_FFT` is found
- [ ] `.DMP_FFT` is found
- [ ] `.dmp.fft` is found
- [ ] copied/suffixed dump names are found
- [ ] Spectrum charts work without Acquisition logs

## Regression
- [ ] START remains Viewer-only
- [ ] CSA loads
- [ ] Quick Filters work
- [ ] CallID linking works
- [ ] Spectrum Dump remains absent from Log Viewer
