# Commit0028 Test Checklist

## Opening Investigation
- [ ] Open Investigation Mode
- [ ] No Initial Investigation starts automatically
- [ ] Ready message is displayed
- [ ] Select a profile
- [ ] Press Start Analysis

## Progress
- [ ] Progress bar moves during source loading
- [ ] Progress bar moves during row indexing
- [ ] Progress bar moves during table rendering
- [ ] Progress text changes for each stage
- [ ] Source and row counts update

## Cancel
- [ ] Cancel during source loading
- [ ] Cancel during row indexing
- [ ] Cancel during table rendering
- [ ] Window closes after cancellation
- [ ] Application remains responsive

## Performance
- [ ] Large CGA source no longer attempts to display all 3M+ rows
- [ ] Status shows total indexed and representative displayed rows
- [ ] Investigation window appears significantly faster
- [ ] Search update is faster
- [ ] Timeline generation completes without a long frozen period

## Regression
- [ ] Viewer count 1–4 works
- [ ] Equal Widths works
- [ ] Acquisition Dashboard works
- [ ] Spectrum Analysis works
- [ ] CSA loads
- [ ] Quick Filters and CallID linking work
