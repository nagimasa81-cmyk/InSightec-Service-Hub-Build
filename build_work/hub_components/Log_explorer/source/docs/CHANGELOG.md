# Log Merge Tool RC1 Changelog

## Commit0009 RC1

### Added
- Investigation Workspace integrated with the existing Log Viewer.
- Initial Investigation: WS / CSA / CGA.
- Water Investigation: WS / CSA / CGA / WaterSystem.
- MR Investigation: WS / MRSERVER / GESYS.
- Time synchronization: Exact, ±1, ±5, ±10 and ±30 seconds.
- Cross-log search, Critical Timeline, bookmarks and investigation notes.
- Investigation Summary for Critical, Warning, Restart, Watchdog and Timeout counts.
- Critical and Warning Timeline filters.
- Bookmark CSV export.

### Fixed
- WaterSystem native rows are parsed as Event / Cooling State / Error State.
- Prevented the same ERROR token from appearing as Level, Category and Message.
- WaterSystem Category now uses the event name.
- WaterSystem Message now preserves labelled Event, Cooling and Error information.
- WaterSystem, Review and PSC continue to use no hover popup.

### Foundation
- Existing RC1 Foundation, parser interface, Viewer data path and build BAT are retained.
- No Controller or Manager layer added.
