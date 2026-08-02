# Commit0053 Event Sync Test

1. Load two to four logs with overlapping timestamps.
2. Select `Exact` and click a row.
   - Only rows with the same timestamp should highlight in other visible panes.
3. Select `±5 sec` and click a row.
   - All events within five seconds should highlight.
   - The highest-ranked row should be current and centered.
4. Disable `Highlight all in range`.
   - Only the best candidate should be selected.
5. Disable `Auto scroll`.
   - Selection should update without centering the Pane.
6. Change to `Custom`, enter a range, and repeat.
7. Verify Message / CallID / Category / Severity checkboxes alter best-row priority.
8. Verify Quick Filter and Contains still operate after synchronized selection.
