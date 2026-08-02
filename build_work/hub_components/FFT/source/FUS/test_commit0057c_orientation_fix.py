from pathlib import Path
import ast
import re

source = Path(__file__).with_name("app.py").read_text(encoding="utf-8")
ast.parse(source)

required = [
    'APP_VERSION = "5.7.3 RC1 Orientation Display Fix Commit0057c"',
    "def set_orientation_labels(self, values):",
    "orientation_values = {",
    "panel.set_orientation_labels(orientation_values)",
    "QTimer.singleShot(0, self._apply_image_orientation)",
    "Orientation unavailable:",
    "PatientPosition",
    "ImageOrientationPatient",
    "ImagePositionPatient",
    "self.raw_preview_cache",
]
for token in required:
    assert token in source, token

# Regression: the incompatible keyword and 4-positional calls must not exist.
assert 'top=labels["top"]' not in source
assert 'bottom=labels["bottom"]' not in source
assert 'left=labels["left"]' not in source
assert 'right=labels["right"]' not in source

method = re.search(
    r"def _apply_image_orientation\(self\):.*?(?=\n    def |\Z)",
    source,
    re.S,
).group(0)

assert "panel.set_orientation_labels(orientation_values)" in method
assert not re.search(
    r"panel\.set_orientation_labels\(\s*labels\[",
    method,
    re.S,
)

print("Commit0057c final orientation regression: PASS")
