# Architecture - C0016c

## Priority

1. Sonication-folder discovery
2. Synchronized replay context
3. FUS workstation-inspired Replay UI
4. Preserved analysis workspace
5. Later validated acoustic/temperature analysis expansion

## Replay synchronization

A single replay index drives every visible stream. Raw image and thermometry indices use the ReplayService mapping. SpectrumMsg uses explicit replay-to-stream ratio mapping when a timestamp is not available. All visual cursors and labels are updated from the same replay index.

## Baseline

The replay baseline is cached per Sonication folder and currently resolves to the first Temperature RAW frame. This is intentionally explicit and visible in the UI.

- `src/services/acoustic_control_service.py`: Acquisition telemetry parser and frame resampling.

## RC2-R0003 Atomic Frame Snapshot

One immutable frame snapshot now carries the decoded replay frame, elapsed time, mapped magnitude/temperature indices, and mapped spectrum index to every synchronized view. Old snapshots are invalidated when the Sonication source changes.
