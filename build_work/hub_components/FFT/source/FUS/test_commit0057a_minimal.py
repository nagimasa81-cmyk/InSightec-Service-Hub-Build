from pathlib import Path
import ast

source = Path(__file__).with_name("app.py").read_text(encoding="utf-8")
ast.parse(source)

for token in [
    'APP_VERSION = "5.7.1 RC1 Minimal MRI Viewer Commit0057a"',
    "Patient:",
    "Exam:",
    "self.display_reset_button",
    "def reset_viewer_display",
    "def _save_viewer_layout",
    "def _restore_viewer_layout",
    "QSettings",
    "self.current_kspace = fft2c(self.current_image)",
    'self.view_mode = "Both"',
    "self.raw_preview_cache",
]:
    assert token in source, token

for forbidden in [
    "def _neutral_series_icon",
    "def _series_search_blob",
    '"Acquisition Time"',
    "Institution:",
    "InteractiveRenderPanel",
]:
    assert forbidden not in source, forbidden

print("Commit0057a minimal regression: PASS")
