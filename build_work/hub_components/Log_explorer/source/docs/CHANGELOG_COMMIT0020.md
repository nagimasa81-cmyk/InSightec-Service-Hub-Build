# Commit0020

## Viewer error correction
- Fixed update_view_mode callback signature.
- Checkbox stateChanged signals can pass an integer without causing a TypeError.
- Duplicate popup behavior is removed.

## Large viewer loading
- Row conversion is processed in batches of 2,000.
- Progress is updated throughout conversion instead of remaining at 0%.
- Cancel is honored during row conversion.
- Existing lazy model fetch remains enabled.

## CallID cross-link
- Extracts CallID/Call ID/Case ID from WS, CSA, CGA and MRSERVER.
- Adds a CallID column when detected.
- Right-click supports:
  - Link Same CallID Across Panes
  - Show Only This CallID
  - Clear Pane Filter
- Visible panes containing the same CallID are filtered together.
