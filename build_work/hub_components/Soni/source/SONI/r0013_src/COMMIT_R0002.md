# RC2-R0002 — Synchronized Views

## Purpose
Move frame navigation from widget-owned callbacks to one ReplayContext-driven render pipeline.

## Implemented
- Added ReplayViewCoordinator with deterministic ordered view dispatch.
- Frame slider, arrows, keyboard, wheel and playback now mutate ReplayContext only.
- Main replay render is subscribed to immutable ReplaySelection state.
- Removed recursive/double `set_frame()` calls after context navigation.
- Added explicit refresh for first render after sonication source preparation.
- Added stale-sonication guard during asynchronous UI replacement.

## Scope
This commit changes synchronization architecture, not CT decoding or cavitation interpretation.
