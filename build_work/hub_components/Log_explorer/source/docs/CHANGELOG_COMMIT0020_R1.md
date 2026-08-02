# Commit0020 R1

## Fix
- Fixed Viewer loading failure caused by datetime values inside parsed dictionaries.
- CallID extraction no longer requires the complete dictionary to be JSON serializable.
- Nested dictionaries, lists, tuples and sets are searched safely.
- JSON fallback uses `default=str`.
- Existing CallID linking and large-table progress behavior are retained.
