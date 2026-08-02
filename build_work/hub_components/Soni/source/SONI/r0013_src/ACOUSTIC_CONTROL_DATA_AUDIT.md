# Acoustic Control Data Audit

Validated against the supplied `09-49-14_ANx.zip` and `17-00-24_ANx.zip`.

## Power %
The Acquisition log emits `AblPowerRatio`. A ratio of `1.0000` is 100%, while ramp/decrease values appear below 1.0. The application displays `AblPowerRatio × 100`.

## Score
The same control loop emits `Calculated Energy` and `Bottom Limit Of Harmless Energy`. Their ratio matches the expected workstation behavior: normal DQA-like values are around the low teens in the first supplied case, while a cavitation event rises sharply. The application displays `Calculated Energy / Bottom Limit × 100`.

## Example findings
- 09-49-14 case: 11 detected control segments. Segment 1 score range approximately 12.0–19.3%; segment 5 reached approximately 72.9%.
- 17-00-24 case: 15 detected control segments. Early segments were approximately 28–39%, showing that score baseline is case/sonication dependent.

The source remains explicit in the UI. No score is fabricated from spectrum peaks or decoder confidence.
