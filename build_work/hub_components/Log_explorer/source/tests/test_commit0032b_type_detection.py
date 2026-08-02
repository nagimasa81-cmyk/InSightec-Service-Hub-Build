from pathlib import Path
import ast
import re
from datetime import datetime
from dataclasses import dataclass
from typing import Optional

root = Path(__file__).resolve().parents[1]
source = (root / "LogMergeTool_NoExcel_Main.py").read_text(encoding="utf-8")

for token in [
    "def _c32b_filename_type",
    "def _c32b_probe_content_type",
    "def _c32b_parse_text_log",
    "def parse_gesys",
    "def parse_lais",
    "def parse_psc",
    "def parse_review_out",
]:
    assert token in source, token

start = source.index("def _c32b_filename_type")
end = source.index("def _c32b_timestamp_from_text", start)
segment = source[start:end]
namespace = {"Path": Path, "re": re}
exec(segment, namespace)
detect = namespace["_c32b_filename_type"]

cases = {
    "gesys_GEMR.log": "GESYS",
    "gesyslog0.txt": "GESYS",
    "LAIS.log": "LAIS",
    "lais_20260219.txt": "LAIS",
    "psc.log": "PSC",
    "PSC_2026_02_19.log": "PSC",
    "review.out": "Review",
    "review.out.ar": "Review",
}
for name, expected in cases.items():
    assert detect(Path(name)) == expected, (name, detect(Path(name)))

print("Commit0032B recovered filename detection: PASS")
