Commit0014 RC1 test build

New:
1. Shared Feedback Engine v1 integrated.
2. Import one log file from a ZIP archive.

ZIP import flow:
Import -> Import selected file -> choose ZIP -> choose one contained log -> extract -> import.
Only one contained file is imported in this commit.

Feedback flow:
Feedback -> enter comment/context -> Prepare Feedback.
The tool writes a feedback_template TXT and feedback_manifest JSON under the feedback folder.
