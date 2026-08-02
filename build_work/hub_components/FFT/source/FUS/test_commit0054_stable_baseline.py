from pathlib import Path
import ast

root = Path(__file__).parent
source = (root / "app.py").read_text(encoding="utf-8")
ast.parse(source)

required = [
    'APP_VERSION = "5.4.0 RC1 Pre-Rendering Stable Baseline Commit0054"',
    "def show_dicom",
    "def refresh_images",
    "def set_view_mode",
    "self.current_kspace = fft2c(self.current_image)",
    'self.view_mode = "Both"',
    "def load_raw_file",
    "def _apply_image_orientation",
    "def _update_annotation_display",
    "self.annotation_panel",
    "StableDiagnosticLogger",
    "Tracking PFiles are excluded",
]
for token in required:
    assert token in source, token

assert "InteractiveRenderPanel" not in source
assert "def open_3d_workspace" not in source
assert "from engines import" not in source
assert "if self.looks_tracker(path):\n                continue" in source

logger = (root / "stable_diagnostic_logger.py").read_text(encoding="utf-8")
ast.parse(logger)
assert "Stable_Baseline_" in logger
assert "export_zip" in logger

print("Commit0054 stable baseline regression: PASS")
