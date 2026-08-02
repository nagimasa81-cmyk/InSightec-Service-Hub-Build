from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
main_path = root / "LogMergeTool_NoExcel_Main.py"
source = main_path.read_text(encoding="utf-8")

entry = source.rfind('if __name__ == "__main__":')
assert entry > 0
assert source.count('if __name__ == "__main__":') == 1

assert 'APP_VERSION = "2.0.0-rc1-commit0026"' in source
assert "class MainWindow(QWidget):" in source
assert "class StandaloneSpectrumWindow(QMainWindow):" in source

patch_start = source.index("def _c24_build_ui")
patch_end = source.index(
    "MainWindow.build_ui = _c24_build_ui",
    patch_start,
)
patch = source[patch_start:patch_end]

assert "self.centralWidget()" not in patch
assert "root = self.layout()" in patch
assert "root.insertWidget" in patch

# Ensure the source parses and the Spectrum patch is active before startup.
ast.parse(source)
assert patch_start < entry
assert patch_end < entry

print("Commit0026 QWidget startup regression: PASS")
