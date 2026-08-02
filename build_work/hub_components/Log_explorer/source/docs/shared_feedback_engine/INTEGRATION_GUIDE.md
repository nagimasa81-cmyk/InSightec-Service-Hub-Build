# InSightec Shared Feedback Engine v1

Copy `feedback_engine` beside the tool entry Python file. Build a runtime context when Feedback opens, including current screen, active file, module version and relevant hospital/serial values. Build a `FeedbackRequest`, then call `engine.prepare(request, validation_rows)`. The host UI remains responsible for screenshot capture, drag-and-drop and Outlook COM.

Required UI: category, priority, reproducible, related tool, comment, screenshot, files, recent logs, validation report, attachment remove/clear, Outlook/template mode.

For “Send this screen”, capture the active window, set `current_page`, add the active file and analysis state to `extra`, attach recent logs, and open the form pre-populated.

Outputs use schema `insightec.feedback.v1`: `feedback_template_*.txt` and `feedback_manifest_*.json`.
