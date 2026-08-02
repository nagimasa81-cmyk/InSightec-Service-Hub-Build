# RC2-R0007 — MR Timeline and Thumbnail Binding Repair

## Root causes repaired

1. `replay_frame_count` incorrectly included SpectrumMsg count. A treatment with 7 MR frames and 51 spectrum records therefore exposed 51 navigation positions; most arrow presses reused the same MR image.
2. Thumbnail activation depended on `currentRowChanged`. Replay synchronization already selected the current thumbnail, so clicking that same Anatomy/Thermal item emitted no signal.
3. Thumbnail source index was passed through the replay-to-data mapper in the wrong direction.
4. The ROI was labelled 5 mm x 5 mm despite missing pixel spacing and its even-matrix mask could not represent an exact requested pixel voxel.

## Changes

- MR magnitude/temperature streams exclusively own replay frame count.
- Spectrum remains mapped onto the MR timeline.
- `itemClicked` activates already-selected thumbnails.
- Added explicit `_map_data_to_replay()` for thumbnail navigation.
- Planning reference navigation always returns to live Thermal/Anatomy replay.
- ROI changed to an exact 3 x 3 pixel mask and display box.

## Verification

- Full pytest suite.
- Source metadata verification.
- Python compileall.
- Real treatment export audit: MR timeline count and consecutive magnitude differences.
