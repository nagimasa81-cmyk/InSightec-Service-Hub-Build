from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_VERSION = "2.0.0-rc1-commit0061"
EXPECTED_COMMIT = "Commit0061"
EXPECTED_EXE = "LogMergeTool_RC1_Commit0061.exe"

meta = json.loads((ROOT / "version.json").read_text(encoding="utf-8"))
assert meta["version"] == EXPECTED_VERSION
assert meta["commit"] == EXPECTED_COMMIT
assert meta["artifact_base_name"] == EXPECTED_EXE.removesuffix(".exe")

source = (ROOT / "LogMergeTool_NoExcel_Main.py").read_text(encoding="utf-8")
versions = set(re.findall(r'^APP_VERSION\s*=\s*"([^"]+)"', source, flags=re.MULTILINE))
assert versions == {EXPECTED_VERSION}, versions

for bat_name in ("01_BUILD_EXE_GITHUB.bat", "01_BUILD_EXE_NUITKA.bat"):
    bat = (ROOT / bat_name).read_text(encoding="utf-8")
    assert EXPECTED_EXE.removesuffix(".exe") in bat, bat_name
    assert "Commit0061" in bat, bat_name
    assert "csa_error_rules.json" in bat, bat_name
    assert "site_serial_map.json" in bat, bat_name

print("Commit0061 version consistency: PASS")


def test_commit0061_filter_bindings_present():
    source = (ROOT / "LogMergeTool_NoExcel_Main.py").read_text(encoding="utf-8")
    assert "def _c60_set_quick_filter" in source
    assert "def _c60_header_menu" in source
    assert "MultiPaneLogViewer.apply_view_filters = _c60_apply_view_filters" in source
    assert "MultiPaneLogViewer.build_ui = _c60_build_ui" in source
    assert source.rfind("if __name__ == \"__main__\":") > source.rfind("MultiPaneLogViewer.build_ui = _c60_build_ui")
