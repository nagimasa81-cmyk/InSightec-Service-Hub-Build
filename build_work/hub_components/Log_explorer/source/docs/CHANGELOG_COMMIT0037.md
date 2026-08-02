# Commit0037 — Final GESYS / LAIS / Review Load Path

## Root cause
Earlier recovery code was added before later Viewer method overrides. The
application therefore continued using a different final `source_to_records`
implementation.

## Correction
The definitive implementation is now placed immediately before the only
application entry point.

## File rules
- GESYS: `gesys_*.log`, `gesyslog*.log/.txt`, `gesys.log`
- LAIS: `lais*.log/.txt`
- Review: `review.out`, `review.out.*`, copied `review_*` / `review-*`

## Candidate resolution
1. Smart Discovery selected files
2. Other known selected/loaded-file attributes
3. Source file or recursive source-folder scan

## Parsing
- Existing dedicated GESYS and LAIS parsers first
- Existing Review structured parser first
- Loss-tolerant fallback preserves non-empty rows

## Diagnostics
Viewer log reports:
- detected files
- parsed files
- failed files
- extracted rows
- exact expected filename rule when no file was detected
