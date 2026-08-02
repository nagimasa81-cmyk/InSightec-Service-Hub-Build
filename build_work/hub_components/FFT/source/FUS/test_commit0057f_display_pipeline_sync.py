from pathlib import Path
import ast

source = Path(__file__).with_name("app.py").read_text(encoding="utf-8")
ast.parse(source)

for token in [
    'APP_VERSION = "5.9.0 RC1 Orientation Engine v2 Commit0059"',
    "def _current_original_display_transform",
    "def _sync_labels_to_original_display",
    "def _orientation_pipeline_trace",
    "display_rotation_degrees",
    "display_flip_horizontal",
    "display_flip_vertical",
    "orientation_pipeline_trace",
]:
    assert token in source, token

assert "Top=P" not in source
assert "Bottom=A" not in source
assert 'if patient_position == "HFS"' not in source

print("Commit0057f display-pipeline regression retained under Commit0059: PASS")
