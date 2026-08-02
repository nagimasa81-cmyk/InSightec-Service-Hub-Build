from pathlib import Path
import json, re
ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/"LogMergeTool_NoExcel_Main.py").read_text(encoding="utf-8")
versions=set(re.findall(r'^APP_VERSION\s*=\s*"([^"]+)"', source, flags=re.MULTILINE))
assert versions == {"2.0.0-rc1-commit0062"}, versions
v=json.loads((ROOT/"version.json").read_text(encoding="utf-8"))
assert v["commit"] == "Commit0062"
assert v["artifact_base_name"] == "LogMergeTool_RC1_Commit0062"
for name in ["01_BUILD_EXE_GITHUB.bat", "01_BUILD_EXE_NUITKA.bat"]:
    assert "Commit0062" in (ROOT/name).read_text(encoding="utf-8-sig")
print("Commit0062 version consistency: PASS")
