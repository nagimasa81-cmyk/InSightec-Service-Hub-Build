from pathlib import Path
import ast

source = Path(__file__).with_name("app.py").read_text(encoding="utf-8")
ast.parse(source)

for token in [
    'APP_VERSION = "5.5.0 RC1 Explorer Usability Commit0055"',
    "self.tree.setIndentation(12)",
    "self.series_filter_combo",
    "self.explorer_search_edit",
    "self.explorer_type_combo",
    "self.explorer_sort_combo",
    "def _apply_explorer_filters",
    "def _capture_explorer_state",
    "def _restore_explorer_state",
    "Thermometry MEMP",
    "Temperature Map",
    "self.current_kspace = fft2c(self.current_image)",
    'self.view_mode = "Both"',
]:
    assert token in source, token

print("Commit0055 Explorer regression: PASS")
