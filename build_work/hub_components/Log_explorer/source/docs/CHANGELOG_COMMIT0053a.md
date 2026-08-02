# Commit0053a — Filter Engine Stabilization

- Rebound Quick Filter buttons directly to the unified filter engine.
- All / Error / Warning / Info / Critical refresh the table immediately.
- Contains uses NFKC normalization, trim, whitespace normalization and casefold.
- Exact uses normalized equality.
- Stable syntax: `Column~Value`, `Column=Value`, or bare Message text.
- Selection highlight changed to light blue.
- Event Sync from Commit0053 retained.
