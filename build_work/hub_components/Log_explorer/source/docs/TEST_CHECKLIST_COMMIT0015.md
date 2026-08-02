# Commit0015 Test Checklist (BUILT-IN BASELINE)

## Parsers
- [ ] Run 02_TEST_COMMIT0015_PARSERS.bat and confirm PASS
- [ ] WS columns: Timestamp, Type, State, Num, Message
- [ ] WS opens with Type=Err preset and can Show All
- [ ] CSA/CGA first 4 lines are not records
- [ ] Release metadata is available
- [ ] CSA/CGA columns: Timestamp, Type, Status, SubStatus, Message
- [ ] Acoustic Power <6.800000> displays 6.800000 and NumericValue=6.8
- [ ] Electric Power <10.000000> displays 10.000000 and NumericValue=10.0

## VIMeasure
- [ ] VIMEASURE is shown before UNKNOWN
- [ ] Smart Discovery detects VIMeasure files
- [ ] Viewer displays header-driven numeric columns
- [ ] Sonication Investigation lists VIMeasure
- [ ] Logs / Chart / Logs + Chart can chart VIMeasure values
