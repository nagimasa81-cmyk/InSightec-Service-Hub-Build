# RC2-R0001 — ReplayContext foundation

- Started RC2 instead of continuing RC1 patch accumulation.
- Added immutable `ReplaySelection` and signal-driven `ReplayContext`.
- Routed previous, next and mouse-wheel navigation through the central context.
- Configured sonication/frame limits when a treatment package and sonication are selected.
- Kept existing decoders and UI temporarily to reduce migration risk.
- Added context boundary, wrap and signal tests.

This is an architecture foundation, not a claim that the treatment-analysis UI is complete.
