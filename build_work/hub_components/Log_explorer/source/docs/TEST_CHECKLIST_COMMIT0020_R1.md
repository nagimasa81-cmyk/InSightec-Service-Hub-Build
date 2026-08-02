# Commit0020 R1 Test Checklist

- [ ] Press Load This on WS
- [ ] Press Load This on CSA
- [ ] Press Load This on CGA
- [ ] Press Load This on MRSERVER
- [ ] No `datetime is not JSON serializable` error appears
- [ ] Progress increases during row conversion
- [ ] CallID column appears when a CallID exists
- [ ] Right-click CallID linking works
- [ ] Cancel still works during large-table conversion

## Triple-check additions
- [ ] Viewer pane checkboxes can be clicked repeatedly without a TypeError
- [ ] Load This completes for records containing datetime objects
- [ ] Progress moves above 0% during large row conversion
- [ ] Error dialog appears only once for one failure
- [ ] WS / CSA / CGA / MRSERVER CallID is extracted when present
- [ ] Link Same CallID Across Panes filters every matching visible pane
- [ ] Clear Pane Filter restores all rows
- [ ] Right-click menu opens on a populated cell
- [ ] Short tables do not leave a large unused lower region
