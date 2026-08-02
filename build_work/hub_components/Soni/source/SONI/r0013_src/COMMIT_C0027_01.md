# Commit C0027-01 — Replay Metadata Engine Foundation

- Added typed Study/Sonication/MR/Timing/Skull metadata models.
- Added generic Microsoft ADO XML rowset parser used by exported FUS XML files.
- Added parsers for SonicationSummary, ProtocolData, SpotData, LayerData, FusTreatmentData, review.out and SkullMeasures discovery.
- Added MetadataManager that scans the full extracted export tree and creates one SonicationMetadata object per sonication.
- Added `tools/metadata_probe.py` for reproducible dataset validation and JSON export.
- No UI behavior is changed in this commit.
