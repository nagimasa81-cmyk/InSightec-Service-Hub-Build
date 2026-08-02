# Known Issues — Commit0012 Test Build

- WS/CSA/CGA extraction must be confirmed with actual field logs; this build re-applies the intended content timestamp and default display paths.
- The per-pane filter is a direct text match across all structured fields. Advanced column/operator filters remain an RC1 follow-up if required.
- Auto-fit is bounded to avoid extremely wide Message/Raw columns; operators can resize columns manually afterward.
- Custom Calendar uses date-level boundaries, while normal Smart Discovery dropdowns use actual parsed timestamps.
