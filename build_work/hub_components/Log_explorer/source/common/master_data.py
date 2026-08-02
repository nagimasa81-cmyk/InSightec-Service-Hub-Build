"""Shared Site/Serial master used by Service Hub modules.

The canonical file lives under LocalAppData so every installed module can use
one master.  A legacy module-local JSON is imported automatically on first use.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def shared_master_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    return base / "InSightecServiceHub" / "MasterData" / "site_serial_master.json"


def _normalize(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        serial = str(row.get("serial", row.get("serial_number", ""))).strip()
        site = str(row.get("site", row.get("site_name", ""))).strip()
        if not serial and not site:
            continue
        key = (serial.casefold(), site.casefold())
        if key in seen:
            continue
        seen.add(key)
        result.append({"serial": serial, "site": site})
    return sorted(result, key=lambda r: (r["site"].casefold(), r["serial"].casefold()))


def load_shared_site_map(legacy_path: Path, defaults: list[dict[str, Any]]) -> list[dict[str, str]]:
    canonical = shared_master_path()
    candidates = [canonical, legacy_path]
    rows: list[dict[str, Any]] = []
    for path in candidates:
        try:
            if path.exists():
                loaded = json.loads(path.read_text(encoding="utf-8-sig"))
                if isinstance(loaded, list):
                    rows = loaded
                    break
        except Exception:
            continue
    if not rows:
        rows = list(defaults)
    normalized = _normalize(rows)
    try:
        canonical.parent.mkdir(parents=True, exist_ok=True)
        canonical.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return normalized
