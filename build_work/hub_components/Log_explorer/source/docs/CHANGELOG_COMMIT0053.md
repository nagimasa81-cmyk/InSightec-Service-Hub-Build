# Commit0053 — Event Sync Engine

## Synchronization
- Replaced nearest-row-only behavior with timestamp-range synchronization.
- Modes: Exact, ±1 sec, ±5 sec, ±10 sec, ±30 sec and Custom.
- Default: ±5 sec.
- Every visible Pane is searched.
- All rows in the selected range can be highlighted.
- Best candidate is selected and centered automatically.

## Candidate priority
Candidates inside the time range are ranked by:
1. Timestamp proximity / exact timestamp
2. Message match
3. CallID match
4. Category match
5. Severity match

The priority checkboxes affect ranking, not the timestamp inclusion range.

## UI
- Added Event Sync control bar.
- Added Highlight all in range.
- Added Auto scroll.
- Added Message / CallID / Category / Severity priority toggles.
- Viewer tables now support extended row selection.

## Compatibility
- Commit0052a Quick Filter pipeline retained.
- Contains filter retained.
- Operation Summary retained.
- Pane 1–4 and legacy jump methods retained.
