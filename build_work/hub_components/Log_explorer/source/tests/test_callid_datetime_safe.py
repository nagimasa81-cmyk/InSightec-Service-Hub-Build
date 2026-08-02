from datetime import datetime
from pathlib import Path

source = Path(__file__).resolve().parents[1] / "LogMergeTool_NoExcel_Main.py"
text = source.read_text(encoding="utf-8")

patterns_start = text.index("_C20_CALL_ID_PATTERNS")
patterns_end = text.index("\n\n\ndef _c20_extract_call_id", patterns_start)
func_start = text.index("def _c20_extract_call_id", patterns_end)
func_end = text.index("\n\n_old_c20_record_to_viewer_row", func_start)

namespace = {"json": __import__("json"), "re": __import__("re")}
exec(text[patterns_start:patterns_end], namespace)
exec(text[func_start:func_end], namespace)

extract = namespace["_c20_extract_call_id"]

record = {
    "timestamp": datetime(2026, 7, 13, 12, 30, 45),
    "message": "Processing Call ID: 123456",
    "nested": {"created": datetime(2026, 7, 13, 12, 30, 46)},
}

assert extract(record) == "123456"
assert extract({"CallID": 98765, "timestamp": datetime.now()}) == "98765"
assert extract(["noise", {"Case ID": "ABC-42"}]) == "ABC-42"

print("CallID datetime-safe extraction: PASS")
