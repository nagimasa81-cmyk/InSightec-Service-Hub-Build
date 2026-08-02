# Commit0039 — Review Discovery/Viewer Unification

- Smart Discovery and Viewer share `_c38_review_records`.
- Generic zero-row summaries are overwritten with actual Review record counts.
- Dictionary and object Discovery row models are supported.
- Start/End are populated when timestamps exist.
- Timestamp-free Review rows still contribute to the row count.
