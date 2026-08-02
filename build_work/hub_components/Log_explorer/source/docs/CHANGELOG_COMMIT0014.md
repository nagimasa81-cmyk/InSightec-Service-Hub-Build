# Commit0014 — Shared Feedback Engine and ZIP Single-File Import

## Added
- Integrated InSightec Shared Feedback Engine v1.
- Added a Feedback button that creates `insightec.feedback.v1` template and manifest files with runtime context.
- Added one-file ZIP import to the existing selected-file import workflow.
- ZIP contents are listed without full extraction; the operator selects one supported log file.
- Safe extraction blocks absolute paths and `..` traversal and applies a 1 GB member limit.

## Scope limitation
- This test build imports one file from a ZIP only.
- Smart Discovery does not yet scan all files directly inside ZIP archives.
- Outlook COM sending is not enabled; template/manifest generation is complete.
