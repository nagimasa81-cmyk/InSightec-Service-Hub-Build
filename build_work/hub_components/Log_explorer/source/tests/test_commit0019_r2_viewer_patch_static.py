from pathlib import Path
import ast
import re

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "LogMergeTool_NoExcel_Main.py"
text = MAIN.read_text(encoding="utf-8")
ast.parse(text)

required = [
    'APP_VERSION = "2.0.0-rc1-commit0019-r2"',
    'def _c19r2_context_menu',
    'def _c19r2_update_row_fit',
    'def _c19r2_install_table_handlers',
    'table.setContextMenuPolicy(Qt.CustomContextMenu)',
    'customContextMenuRequested.connect',
    'menu.addAction("Copy Cell")',
    'menu.addAction("Filter by This Value")',
    'menu.addAction("Export Selected Row")',
    'header.setSectionResizeMode(QHeaderView.Stretch)',
    'viewer.detail.setMaximumHeight(0)',
]
for item in required:
    assert item in text, item

assert text.count('if __name__ == "__main__":') == 1
assert text.index('def _c19r2_context_menu') < text.index('if __name__ == "__main__":')
assert re.search(r'from PySide6\.QtCore import .*\bQTimer\b', text)
assert re.search(r'from PySide6\.QtWidgets import \([\s\S]*\bQMenu\b[\s\S]*\bQSizePolicy\b', text)
print('Commit0019 R2 Viewer patch static validation: PASS')
