from pathlib import Path
import ast

source = Path(__file__).with_name("app.py").read_text(encoding="utf-8")
ast.parse(source)

required = [
    'APP_VERSION = "5.6.0 RC1 Layout Usability Commit0056"',
    "self.global_toolbar",
    "self.global_import_button",
    "self.message_panel",
    "self.info_scroll",
    "self.left_content_splitter.addWidget(self.message_panel)",
    "def _remember_left_splitter_sizes",
    "self._user_left_split_sizes",
    "remembered = self._user_main_split_sizes",
    "self.mode_toolbar_widget",
    "self.current_kspace = fft2c(self.current_image)",
    'self.view_mode = "Both"',
]
for token in required:
    assert token in source, token

assert "self.mode_toolbar_scroll = QScrollArea()" not in source
assert "self.mode_toolbar_scroll.setMaximumHeight" not in source

print("Commit0056 layout regression: PASS")
