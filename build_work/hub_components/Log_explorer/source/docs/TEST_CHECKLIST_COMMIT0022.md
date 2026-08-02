# Commit0022 Test Checklist

## Acquisition
- [ ] Smart File Discovery identifies Acquisition as `ACQUISITION`
- [ ] ACQUISITION appears in normal Viewer
- [ ] Load This displays Acquisition rows
- [ ] Sonication Investigation includes Acquisition when available

## Spectrum Analysis
- [ ] Spectrum Dump does not appear in normal Log Viewer
- [ ] Open Investigation Mode
- [ ] Spectrum Analysis tab is visible
- [ ] Opening the tab scans `Spectrum_*.dmp_FFT`
- [ ] Dump list shows timestamp, power and frequency
- [ ] Selecting a dump displays graphical curves
- [ ] Linear/Log switching works
- [ ] Hydrophone candidate checkboxes work
- [ ] Peak table is populated
- [ ] Acquisition link shows file and line
- [ ] Cancel works while scanning multiple dumps

## Regression
- [ ] START remains Viewer-only
- [ ] MERGE button remains hidden
- [ ] WS / CSA / CGA / MRSERVER load
- [ ] CallID linking works
- [ ] VIMeasure loads
