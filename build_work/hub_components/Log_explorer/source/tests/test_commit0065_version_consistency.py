from pathlib import Path
import json

root = Path(__file__).resolve().parents[1]
main = (root / "LogMergeTool_NoExcel_Main.py").read_text(encoding="utf-8-sig")
version = json.loads((root / "version.json").read_text(encoding="utf-8-sig"))
github_bat = (root / "01_BUILD_EXE_GITHUB.bat").read_text(encoding="utf-8-sig")
nuitka_bat = (root / "01_BUILD_EXE_NUITKA.bat").read_text(encoding="utf-8-sig")

assert 'APP_VERSION = "2.0.0-rc1-commit0065"' in main
assert version["version"] == "2.0.0-rc1-commit0065"
assert version["commit"] == "Commit0065"
assert version["artifact_base_name"] == "LogMergeTool_RC1_Commit0065"
assert "LogMergeTool_RC1_Commit0065" in github_bat
assert "LogMergeTool_RC1_Commit0065" in nuitka_bat
assert "_C65UnifiedProgressProxy" in main
assert "_c65_shared_progress" in main
print("Commit0065 version and unified progress checks passed")
