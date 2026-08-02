from pathlib import Path
import json

root = Path(__file__).resolve().parents[1]
main = (root / "LogMergeTool_NoExcel_Main.py").read_text(encoding="utf-8-sig")
version = json.loads((root / "version.json").read_text(encoding="utf-8-sig"))
github_bat = (root / "01_BUILD_EXE_GITHUB.bat").read_text(encoding="utf-8-sig")
nuitka_bat = (root / "01_BUILD_EXE_NUITKA.bat").read_text(encoding="utf-8-sig")

assert 'APP_VERSION = "2.0.0-rc1-commit0066"' in main
assert version["version"] == "2.0.0-rc1-commit0066"
assert version["commit"] == "Commit0066"
assert version["artifact_base_name"] == "LogMergeTool_RC1_Commit0066"
assert "LogMergeTool_RC1_Commit0066" in github_bat
assert "LogMergeTool_RC1_Commit0066" in nuitka_bat
assert "def _c66_start_import_clicked" in main
assert "Configure the Viewer and press LOAD LOGS" in main
assert "viewer.load_pane(pane_index)" in main  # retained only in older inactive history
# Final binding must point to explicit-load workflow.
assert "MainWindow.start_import_clicked = _c66_start_import_clicked" in main
assert "MainWindow.open_dual_viewer = _c66_open_dual_viewer" in main
print("Commit0066 explicit LOAD LOGS workflow checks passed")
