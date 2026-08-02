from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "LogMergeTool_NoExcel_Main.py").read_text(encoding="utf-8")

start = source.index("def _c30_parse_column_filter")
end = source.index(
    "# Commit0023 Viewer filter implementation",
    start,
)
namespace = {}
exec(source[start:end], namespace)

matches = namespace["_c30_manual_expression_matches"]
row = {
    "Message": "Watch Dog Error occurred",
    "Level": "Err",
    "Status": "SONICATION",
}

assert matches(row, "Message~dog error")
assert matches(row, "Message~WATCH DOG")
assert not matches(row, "Message~timeout")
assert matches(row, "Level=err")
assert not matches(row, "Level=warning")
assert matches(row, "sonication")
assert matches(row, "")
assert matches(row, "Message~")
assert matches({"Message": "A=B~C"}, "Message~B~C")

print("Commit0030 column filter logic: PASS")
