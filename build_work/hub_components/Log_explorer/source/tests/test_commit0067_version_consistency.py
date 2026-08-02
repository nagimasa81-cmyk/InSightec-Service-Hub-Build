import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
main = (ROOT / "LogMergeTool_NoExcel_Main.py").read_text(encoding="utf-8", errors="ignore")
version = json.loads((ROOT / "version.json").read_text(encoding="utf-8"))
match = re.search(r'^APP_VERSION\s*=\s*["\']([^"\']+)["\']', main, re.MULTILINE)
assert match, "APP_VERSION was not found in LogMergeTool_NoExcel_Main.py"
assert version.get("version"), "version.json does not contain version"
assert match.group(1) == version["version"], f"APP_VERSION {match.group(1)!r} != version.json {version['version']!r}"
assert version.get("application") == "Log Merge Tool - No Excel"
print("[PASS] Version consistency:", version["version"])
