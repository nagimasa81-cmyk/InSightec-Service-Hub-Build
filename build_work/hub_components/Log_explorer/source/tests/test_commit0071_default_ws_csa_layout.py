from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "LogMergeTool_NoExcel_Main.py").read_text(encoding="utf-8")
version = json.loads((ROOT / "version.json").read_text(encoding="utf-8"))
contract = json.loads((ROOT / "insightec_build_contract.json").read_text(encoding="utf-8"))

assert 'APP_VERSION = "2.0.0-rc1-commit0071"' in source
assert version["commit"] == "Commit0071"
assert version["artifact_base_name"] == "LogMergeTool_RC1_Commit0071"
assert "def _c71_build_ui" in source
assert 'default_sources = ("WS", "CSA")' in source
assert 'self.mode_combo.setCurrentText("2 logs (Dual)")' in source
assert 'checkbox.setChecked(index < 2)' in source
assert contract["viewer_defaults"]["visible_panes"] == 2
assert contract["viewer_defaults"]["pane_1_source"] == "WS"
assert contract["viewer_defaults"]["pane_2_source"] == "CSA"
print("Commit0071 default WS + CSA 2 Show contract: PASS")
