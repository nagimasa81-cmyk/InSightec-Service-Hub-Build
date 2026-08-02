from pathlib import Path
import ast

source = Path(__file__).with_name("app.py").read_text(encoding="utf-8")
ast.parse(source)

required = [
    'APP_VERSION = "5.7.2 RC1 Orientation Annotation Commit0057b"',
    "PatientPosition",
    "ImageOrientationPatient",
    "ImagePositionPatient",
    "def _dicom_orientation_labels",
    "def _patient_axis_label",
    "def _apply_orientation_transform_to_labels",
    "np.cross",
    "current_orientation_labels",
    "self.current_kspace = fft2c(self.current_image)",
    'self.view_mode = "Both"',
]
for token in required:
    assert token in source, token

assert "InteractiveRenderPanel" not in source

print("Commit0057b orientation regression: PASS")
