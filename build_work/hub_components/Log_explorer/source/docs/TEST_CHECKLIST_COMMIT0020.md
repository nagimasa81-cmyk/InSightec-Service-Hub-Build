# Commit0020 Test Checklist

## Viewer checkbox error
- [ ] Click pane 1/2/3/4 checkboxes repeatedly
- [ ] No TypeError popup appears
- [ ] Only one error dialog is shown for an actual error

## Large data
- [ ] Load 100,000+ rows
- [ ] Progress increases during table-row conversion
- [ ] Cancel works
- [ ] Viewer remains responsive enough to move the progress window
- [ ] Initial table display uses lazy rows

## CallID extraction
- [ ] WS CallID detected
- [ ] CSA CallID detected
- [ ] CGA CallID detected
- [ ] MRSERVER CallID detected
- [ ] CallID column appears only when present

## CallID linking
- [ ] Load two or more compatible panes
- [ ] Right-click a row containing CallID
- [ ] Link Same CallID Across Panes
- [ ] Matching rows appear in all visible panes
- [ ] Show Only This CallID works in one pane
- [ ] Clear Pane Filter restores all rows
