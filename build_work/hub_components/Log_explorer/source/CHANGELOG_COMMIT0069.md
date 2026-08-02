# Commit0069 — Guide Accuracy and Daily Clean Paths

## Changes
- Removed all MERGE workflow references from Quick Guide and Guided Tour.
- Updated Source instructions to explain both drag-and-drop and Browse selection.
- Reduced Guided Tour from 5 steps to 4 steps to match the current workflow.
- On the first application launch of each calendar day, Source and Output are cleared.
- On later launches on the same day, the most recently saved Source and Output are restored.
- Updated version metadata to Commit0069.

## Validation
- Python syntax compilation passed.
- Guide and tour strings were checked for obsolete MERGE instructions.
- Daily reset uses a persistent yyyy-MM-dd launch-date key in QSettings.
