from __future__ import annotations
import re
from pathlib import Path

def parse_header_and_count(path: str | Path) -> tuple[list[str], int]:
    lines = Path(path).read_text(encoding="utf-8", errors="ignore").splitlines()
    header: list[str] = []
    count = 0
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if not header and any(ch.isalpha() for ch in s):
            header = [x.strip() for x in re.split(r"[,;\t]+|\s{2,}", s) if x.strip()]
            continue
        nums = re.findall(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", s)
        # Count only actual 47-column element rows, not numbered header text.
        if len(nums) >= 47:
            try:
                element_no = int(float(nums[0]))
            except ValueError:
                continue
            if 0 <= element_no <= 4096:
                count += 1
    return header, count
