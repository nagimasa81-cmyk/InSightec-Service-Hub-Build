# Commit0038 — review.out Zero Row Fix

- Discovery and Viewer now share one canonical Review parser.
- Supports NUL-separated, mixed-newline and mixed-encoding review.out files.
- Every meaningful non-empty row is retained even without a timestamp.
- Review/REVIEW source labels are normalized.
- Viewer log reports detected files, parsed files and final row count.
