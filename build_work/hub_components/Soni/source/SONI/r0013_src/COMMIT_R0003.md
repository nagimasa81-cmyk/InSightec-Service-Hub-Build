# RC2-R0003 — Atomic Frame Snapshot Pipeline

## Objective

Remove the remaining per-widget frame decoding path.  One immutable snapshot is
now created for each replay cursor position and used as the source for the
synchronized image, temperature, spectrum, acoustic and status views.

## Changes

- Added `ReplayFrameSnapshot` and `ReplaySnapshotProvider`.
- The active Sonication is bound atomically; changing it invalidates every old
  snapshot and increments a source generation.
- Replay RAW decoding is cached once per Sonication/frame/channel selection.
- Magnitude, temperature and spectrum source indices are mapped from the same
  `ReplaySelection`.
- Stale selections from a previous Sonication are rejected.
- Main window rendering now starts from a validated snapshot rather than
  calling `ReplayService.frame()` directly from a view callback.
- The synchronization label exposes the snapshot generation and reports any
  spectrum mapping mismatch instead of silently displaying inconsistent data.

## Scope

This is a data-flow correction, not a visual redesign.  Planning/CT presentation
and the final Treatment Analysis Console layout remain later RC2 work.
