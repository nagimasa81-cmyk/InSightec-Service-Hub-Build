# Commit0015 BUILT-IN BASELINE

- WS structured parser: Timestamp / Type / State / Num / Message.
- CSA/CGA structured parser: Timestamp / Type / Num / Status / SubStatus / Message.
- First four CSA/CGA lines excluded; Release kept as metadata.
- Numeric values inside angle brackets are extracted without brackets and retained as NumericValue/Unit.
- Default Type=Err preset remains configurable per File Type.
- VIMeasure is built into the application and is the new baseline.
- Sonication Investigation includes VIMeasure and can chart its numeric current/voltage columns.
