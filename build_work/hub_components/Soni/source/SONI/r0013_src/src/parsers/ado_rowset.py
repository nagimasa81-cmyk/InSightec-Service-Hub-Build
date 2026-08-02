from __future__ import annotations
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROW_NS = "urn:schemas-microsoft-com:rowset"

def local_name(name: str) -> str:
    return name.rsplit("}", 1)[-1]

def coerce(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    low = value.lower()
    if low in {"true", "false"}:
        return low == "true"
    try:
        if any(c in value for c in ".eE"):
            return float(value)
        return int(value)
    except ValueError:
        return value

def parse_ado_rowset(path: str | Path) -> list[dict[str, Any]]:
    root = ET.parse(path).getroot()
    rows: list[dict[str, Any]] = []
    for element in root.iter():
        if local_name(element.tag).lower() != "row":
            continue
        record: dict[str, Any] = {}
        for key, value in element.attrib.items():
            record[local_name(key).lower()] = coerce(value)
        if record:
            rows.append(record)
    return rows
