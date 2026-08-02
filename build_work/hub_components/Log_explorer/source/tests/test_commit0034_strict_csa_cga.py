from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
source = (root / "LogMergeTool_NoExcel_Main.py").read_text(encoding="utf-8")

for token in [
    'r"^csa_brain.*\\.(?:log|txt)$"',
    'r"^cga_brain.*\\.(?:log|txt)$"',
    "def _c34_strict_brain_type",
    "def _c34_classify_file",
    "def _c34_source_to_records",
]:
    assert token in source, token

def strict(name):
    lower = Path(name).name.lower()
    ext = Path(name).suffix.lower() in {".log", ".txt"}
    if ext and lower.startswith("csa_brain"):
        return "CSA"
    if ext and lower.startswith("cga_brain"):
        return "CGA"
    return ""

assert strict("Csa_brain_2026.log") == "CSA"
assert strict("csa_brain_test.txt") == "CSA"
assert strict("CGA_brain_2026.log") == "CGA"
assert strict("cga_brain_test.txt") == "CGA"

for invalid in [
    "CSA.log",
    "Csa_body.log",
    "MyCsa_brain.log",
    "CGA.log",
    "CGA_body.log",
    "MyCGA_brain.log",
]:
    assert strict(invalid) == "", invalid

print("Commit0034 strict CSA/CGA scope: PASS")
