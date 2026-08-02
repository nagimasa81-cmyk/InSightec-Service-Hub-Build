# Commit0032A — LogRecord Compatibility Fix

Investigation and Acquisition Dashboard still use dictionary-style row access,
while the parser returns typed `LogRecord` objects.

`LogRecord` now supports:
- `record.get(key, default)`
- `record[key]`
- `key in record`
- `keys`, `values`, `items`
- `to_dict`

Aliases cover timestamp, source type, file, line, level, category, message and
raw data. Compatibility works directly on the object without automatically
copying millions of records into dictionaries.
