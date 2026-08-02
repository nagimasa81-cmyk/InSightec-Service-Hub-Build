from pathlib import Path
import ast
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

root = Path(__file__).resolve().parents[1]
source = (root / "LogMergeTool_NoExcel_Main.py").read_text(encoding="utf-8")
tree = ast.parse(source)
node = next(item for item in tree.body if isinstance(item, ast.ClassDef) and item.name == "LogRecord")
class_source = ast.get_source_segment(source, node)
namespace = {"dataclass": dataclass, "datetime": datetime, "Optional": Optional}
exec("@dataclass\n" + class_source, namespace)
LogRecord = namespace["LogRecord"]

ts = datetime(2026, 2, 19, 8, 30, 52, 496000)
record = LogRecord(ts, "CSA", "csa.log", 123, "Inf", "Calibration", "Initial state", "raw line")

assert record.get("_ts") == ts
assert record.get("Timestamp") == ts
assert record.get("Message") == "Initial state"
assert record.get("missing", "fallback") == "fallback"
assert record["SourceType"] == "CSA"
assert record["File"] == "csa.log"
assert record["Line"] == 123
assert record["Level"] == "Inf"
assert record["Category"] == "Calibration"
assert record["Raw"] == "raw line"
assert "Message" in record
assert "missing" not in record
assert dict(record.items())["Message"] == "Initial state"
assert record.to_dict()["_ts"] == ts

try:
    record["missing"]
except KeyError:
    pass
else:
    raise AssertionError("Missing key must raise KeyError")

print("Commit0032A LogRecord mapping compatibility: PASS")
