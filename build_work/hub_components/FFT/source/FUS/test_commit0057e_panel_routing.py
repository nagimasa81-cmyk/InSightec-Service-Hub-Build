from pathlib import Path
import ast

source = Path(__file__).with_name("app.py").read_text(encoding="utf-8")
ast.parse(source)

required = [
    'APP_VERSION = "5.7.5 RC1 Orientation Panel Routing Fix Commit0057e"',
    'self.primary_panel = ImagePanel("FFT (k-space)")',
    'self.secondary_panel = ImagePanel("Original")',
    'getattr(self, "view_mode", "Both")',
    'if view_mode == "both":',
]
for token in required:
    assert token in source, token

start = source.index("    def _apply_image_orientation(self):")
end = source.find("\n    def ", start + 10)
method = source[start:] if end < 0 else source[start:end]

assert 'getattr(self, "display_mode"' not in method
assert "self.primary_panel.set_orientation_labels(" in method
assert "self.secondary_panel.set_orientation_labels(" in method
assert "orientation_values" in method
assert "empty_values" in method

print("Commit0057e orientation panel routing regression: PASS")
