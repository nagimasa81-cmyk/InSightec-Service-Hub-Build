# Commit0014 Revision 2 Test Checklist

## ZIP to Smart File Discovery

- [ ] Select a ZIP containing multiple recognized log files.
- [ ] Smart File Discovery opens once.
- [ ] UNKNOWN is not displayed.
- [ ] Recognized files can be selected in multiples.
- [ ] All Files and Clear Files work.
- [ ] Actual Start/End candidates are based on checked files.
- [ ] START opens the Viewer with all selected recognized types.
- [ ] Temporary extraction folder is deleted after records are loaded.

## Nested ZIP

- [ ] A ZIP inside the selected ZIP is not extracted.
- [ ] Only the nested ZIP file name is reported.
- [ ] Other recognized files remain selectable.

## File Types / Parsers

- [ ] WS uses the new parser route.
- [ ] CSA uses the new parser route.
- [ ] CGA uses the new parser route.
- [ ] WaterSystem uses Timestamp / MainState / Error and native numeric fields.
- [ ] VIMeasure is detected after its File Type Update ZIP is installed.
- [ ] VIMeasure appears in the Viewer source list.
- [ ] No selected recognized file is reclassified as UNKNOWN.

## Cleanup and stability

- [ ] Cancel at ZIP selection leaves no temporary folder.
- [ ] Cancel in Smart File Discovery leaves no temporary folder.
- [ ] Parser error leaves no temporary folder.
- [ ] Viewer remains usable after temporary extraction is deleted.
