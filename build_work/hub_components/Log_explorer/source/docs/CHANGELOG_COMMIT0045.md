# Commit0045 — Operation Intelligence

Adapted from the supplied FUS Investigation Platform Operation implementation.

## Added to Log Explore
- Operation tab
- Operator / Software / System classification
- Planning, Registration, Tracking, MRI, Treatment, Thermometry,
  Acoustic, Cooling, Data, Warning and Error categories
- Search and category filters
- Show DQA control
- Summary counts
- Operation timeline
- Sonication nearest-time linking within three minutes
- High / Medium / Low link confidence
- CallID / CorrelationID candidate extraction
- Row double-click source jump to Event Viewer

## Data source
Operation analysis uses the same canonical parsed record cache as Event Viewer
and Value Viewer. It does not re-open or re-parse deleted ZIP extraction files.
