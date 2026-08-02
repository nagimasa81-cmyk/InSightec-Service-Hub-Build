# Commit0068

## Added
- Concise hover help popups for main action buttons without replacing existing detailed tooltips.
- Startup prompt: **Yes — Show Guide** / **No — Do Not Ask Again**.
- Quick Guide dialog and five-step Guided Tour.
- Exit confirmation dialog with default-off checkbox: **Show the guide and guided tour at the next startup**.

## Behavior
- Selecting No at startup permanently suppresses the startup question.
- Checking the exit checkbox schedules one automatic guide/tour display at the next startup.
- The one-time request is cleared before the guide is displayed, so it does not repeat after a crash or later restart.
- Cancel in the exit dialog keeps the application open and preserves the active ZIP discovery session.
