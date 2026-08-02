from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (
    root / "LogMergeTool_NoExcel_Main.py"
).read_text(encoding="utf-8")

assert "_, _, records = parse_psc_file_detail(path)" in source
assert 'return "PSC", list(records or []), "psc-dedicated"' in source

print("Commit0041 PSC dedicated cache parser: PASS")
