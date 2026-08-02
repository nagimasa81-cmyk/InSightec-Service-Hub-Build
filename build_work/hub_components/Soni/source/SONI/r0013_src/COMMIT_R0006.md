# RC2-R0006 - Live Replay Ownership Repair

## Runtime defect corrected

R0005 rebuilt the planning strips and then automatically selected the middle Planning CT slice. That direct selection replaced the live MR/thermometry view after load. Because frame navigation changed ReplayContext while the main viewer remained in a planning-reference state, the application appeared frozen on CT.

## Changes

- Planning thumbnail rebuild no longer auto-selects or displays CT.
- Initial main view remains Thermal Replay, falling back to Anatomy MR only when thermometry is absent.
- Timeline, first/previous/next/last, keyboard arrows, wheel and playback return the main viewer from a planning reference to live replay.
- Explicit clicks on Planning CT or Planning MR still display the selected reference image.
- A same-frame timeline action forces a deterministic redraw.
