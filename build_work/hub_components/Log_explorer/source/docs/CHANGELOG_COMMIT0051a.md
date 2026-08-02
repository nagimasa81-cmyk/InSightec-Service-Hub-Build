# Commit0051a — Event Viewer Header Filter Fix

## Root cause
Header filters compared the displayed column name directly with dictionary
keys. Case, spaces, aliases, and structured display columns caused every row
to fail the match.

## Fixed
- Case/space/punctuation-insensitive column-key resolution.
- Timestamp, Message, Level/Type, Category, SourceType, File and CallID aliases.
- Contains and exact matching use the resolved cell value.
- Dropdown values are generated from the Pane's unfiltered source rows.
- Clearing a zero-result filter restores the original Pane data.
