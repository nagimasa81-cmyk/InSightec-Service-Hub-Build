# Commit0014 R4 Test Checklist

## Automated test
- [ ] Run `02_TEST_CSA_CGA_NEW_PARSER.bat`
- [ ] Result is `CSA/CGA structured parser tests: PASS`

## Header
- [ ] First four lines do not appear as Viewer records
- [ ] Process and Version are retained in file metadata
- [ ] Release and Release Date are retained in file metadata
- [ ] Release Date is not used as a row Timestamp

## Row extraction
- [ ] Timestamp is built from filename date plus row time
- [ ] Type preserves the original three-letter value: Inf / Wrn / Err
- [ ] Num is extracted independently
- [ ] Remaining text is parsed as the message section

## Original
- [ ] `[WATER_SYSTEM] Message` becomes Original=`WATER_SYSTEM`
- [ ] Brackets are removed from Original
- [ ] For a normal row, text before the first meaningful `:` becomes Original
- [ ] Text after the separator remains Message
- [ ] Windows drive colon such as `D:\` is not treated as the separator
- [ ] C++ `::` is not treated as the normal Original separator

## Sub Original
- [ ] One-level indented continuation rows inherit Timestamp / Type / Num
- [ ] Text before `:` or `::` becomes Sub Original
- [ ] Remaining text becomes Message
- [ ] Sub Original is available through Columns and hidden by default

## Viewer
- [ ] Default columns are Timestamp / Type / Original / Message
- [ ] Num is available through Columns
- [ ] Sub Original is available through Columns
- [ ] Initial visible filter is `Type=Err`
- [ ] Filter state is clearly visible
- [ ] Clear shows Inf / Wrn / Err rows

## Regression
- [ ] Right-click context menu remains available
- [ ] ZIP recognized files can still be selected as multiple files
- [ ] UNKNOWN is not shown for ZIP input
- [ ] Nested ZIP names are reported but not expanded
- [ ] Temporary ZIP extraction folder is removed after completion/cancel/error
