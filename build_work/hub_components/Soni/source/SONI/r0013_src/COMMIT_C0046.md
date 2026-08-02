# RC1-C0046 — CT Volume and Replay Layout Foundation

## Root causes corrected

- The final planning-asset sort overwrote the CT-specific ordering and sorted RAW names lexically. Derived field 12 appeared before the verified signed field 16 CT stack, and slice 100 could appear before slice 11.
- The UI mixed every 512×512 derived field into the default CT row, so the first displayed image was not reliably the planning CT volume.
- The replay graph splitter used a 3:4 temperature/spectrum ratio and restored that invalid ratio from earlier settings.

## Changes

- Field 16 signed CT/HU stack is ordered first.
- CT slices are ordered by numeric array index.
- Default Planning CT row uses verified field 16 only when it exists.
- The middle CT slice is selected and displayed after loading.
- Temperature Trend is the primary panel at 65%; Acoustic Spectrum is 35%.
- Pre-C0046 graph splitter state is ignored once, then the new user-adjusted state is persisted.
- Both panels have minimum widths and cannot collapse to zero.
