from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
main = (root / "LogMergeTool_NoExcel_Main.py").read_text(encoding="utf-8")
entry = main.rfind('if __name__ == "__main__":')
assert entry > 0
assert main.count('if __name__ == "__main__":') == 1

widgets = re.search(r"from PySide6\.QtWidgets import \((.*?)\n\)", main, re.S)
assert widgets
for symbol in ["QMainWindow", "QApplication", "QWidget", "QPushButton", "QFileDialog"]:
    assert symbol in widgets.group(1), symbol

for token in [
    'APP_VERSION = "2.0.0-rc1-commit0025"',
    "class StandaloneSpectrumWindow(QMainWindow)",
    "MainWindow.open_spectrum_analysis = _c24_open_spectrum_analysis",
]:
    position = main.find(token)
    assert 0 <= position < entry, token

print("Commit0025 foundation startup validation: PASS")
