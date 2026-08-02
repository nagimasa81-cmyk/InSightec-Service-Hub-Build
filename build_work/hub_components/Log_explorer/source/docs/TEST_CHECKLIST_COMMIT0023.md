# Commit0023 Comprehensive Test Checklist

## Version and startup
- [ ] Window title shows `2.0.0-rc1-commit0023`
- [ ] START opens Discovery/Viewer workflow
- [ ] MERGE button remains absent
- [ ] No startup error dialog

## Viewer default filter
- [ ] Load WS: all rows display initially
- [ ] Load CSA: all rows display initially
- [ ] Load CGA: all rows display initially
- [ ] No hidden `Type=Err` expression is inserted
- [ ] All button is selected after each load

## Quick Filter
- [ ] All count matches indexed rows
- [ ] Error button filters immediately
- [ ] Warning button filters immediately
- [ ] Info button filters immediately
- [ ] Critical button filters immediately
- [ ] Counts remain visible
- [ ] Time filter and Quick Filter can be used together
- [ ] Manual column filter can be used together

## CSA pipeline
- [ ] CSA appears in source list when CSA files were selected
- [ ] Load This indexes CSA rows
- [ ] Status reports detected/indexed/displayed counts
- [ ] Renamed CSA file with CSA content is detected
- [ ] CSA structured columns appear
- [ ] CSA CallID appears when present
- [ ] CSA loads with zero default filtering

## Acquisition
- [ ] ACQUISITION is detected
- [ ] Acquisition loads in normal Viewer
- [ ] Acquisition is available in Sonication Investigation

## Spectrum
- [ ] Spectrum Dump is absent from normal Viewer
- [ ] Spectrum Analysis scans dumps
- [ ] Overlay mode displays
- [ ] Waterfall mode displays
- [ ] Heatmap mode displays
- [ ] Harmonic markers display
- [ ] FFT Compare displays a second dashed series
- [ ] Sonication Replay slider works
- [ ] Play/Pause Replay works
- [ ] Linear/Log switch works
- [ ] Hydrophone checkboxes work
- [ ] Acquisition link is displayed

## Other regressions
- [ ] VIMeasure values display
- [ ] WS / CGA / MRSERVER load
- [ ] Right-click menu opens
- [ ] CallID cross-pane link works
- [ ] Short tables do not leave a large lower blank area
- [ ] Progress advances for large datasets
- [ ] Cancel works
