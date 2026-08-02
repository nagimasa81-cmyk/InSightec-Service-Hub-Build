# Spike Detection Review Deck - Commit0073

Purpose: review spike detection one step at a time before further changing thresholds.

## Review stages

1. Input frame
   - Original image
   - FFT/k-space magnitude
   - DICOM phase direction tag `(0018,1312)`
2. Normal structure mask
   - DC center box
   - Normal horizontal/vertical k-space cross
   - Low-confidence background
3. Candidate extraction
   - Point candidates
   - Line candidates
   - Band candidates
   - Oblique candidates
4. Candidate classification
   - Type
   - k-space centroid
   - angle
   - length/width
   - local MAD z-score
   - background ratio
5. Candidate-only inverse FFT
   - Predicted stripe/wave from candidate only
   - Predicted period
   - predicted wave angle
6. Original image validation
   - projection profile at predicted angle
   - stripe strength
   - correlation with predicted wave
7. Decision
   - Accepted
   - Rejected
   - reason and score breakdown
8. Correction preview
   - Original
   - Candidate only
   - Corrected
   - Difference map

## Commit0073 frame-lock rule

Image selection must not call delayed layout stabilization or autoRange.  The viewer frame is locked while images are set, fit ranges are deterministic, and the final layout is painted once.
